"""OIDC signature, nonce/state/PKCE transport and single-use session regression."""
import time
from urllib.parse import parse_qs, urlsplit

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk, jwt

from app.api.v1 import sso
from app.models import AuthChallenge, SystemConfig
from test_core_review import fixture  # noqa: F401


def prepare(fixture, monkeypatch, bad_nonce=False):
    client, db = fixture
    config = {"sso_enabled": "true", "sso_provider": "oidc", "issuer_url": "http://127.0.0.1:9091", "client_id": "isolated-client", "client_secret": "isolated-client-secret", "redirect_uri": "http://localhost/api/v1/auth/sso/callback"}
    for key, value in config.items():
        db.add(SystemConfig(group="auth", key=key, value=value))
    db.commit()
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    jwks = {"keys": [{**jwk.construct(public, algorithm="RS256").to_dict(), "kid": "test"}]}
    metadata = {"issuer": config["issuer_url"], "authorization_endpoint": config["issuer_url"] + "/authorize", "token_endpoint": config["issuer_url"] + "/token", "jwks_uri": config["issuer_url"] + "/jwks"}
    captured = {}
    class IdentityClient:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, url):
            return httpx.Response(200, json=jwks if url.endswith("/jwks") else metadata, request=httpx.Request("GET", url))
        def post(self, url, data, auth):
            context = db.query(AuthChallenge).filter_by(kind="oidc").one().data
            assert data["code_verifier"] == context["verifier"]
            assert auth == (config["client_id"], config["client_secret"])
            captured.update(data)
            claims = {"iss": config["issuer_url"], "aud": config["client_id"], "sub": "external-user", "name": "Test identity", "iat": int(time.time()), "exp": int(time.time()) + 120, "nonce": "bad" if bad_nonce else context["nonce"]}
            encoded = jwt.encode(claims, private, algorithm="RS256", headers={"kid": "test"})
            return httpx.Response(200, json={"id_token": encoded}, request=httpx.Request("POST", url))
    monkeypatch.setattr(sso.httpx, "Client", IdentityClient)
    return client, db, captured


def test_oidc_flow_nonce_pkce_one_use_ticket_and_viewer_role(fixture, monkeypatch):
    client, db, captured = prepare(fixture, monkeypatch)
    start = client.get("/api/v1/auth/sso/start?redirect=/ontology/list", follow_redirects=False)
    assert start.status_code == 302
    params = parse_qs(urlsplit(start.headers["location"]).query)
    assert params["code_challenge_method"] == ["S256"]
    state = params["state"][0]
    callback = client.get("/api/v1/auth/sso/callback", params={"state": state, "code": "provider-code"}, follow_redirects=False)
    assert callback.status_code == 302, callback.text
    ticket = parse_qs(urlsplit(callback.headers["location"]).query)["sso_code"][0]
    assert "token=" not in callback.headers["location"]
    result = client.post("/api/v1/auth/sso/exchange", json={"code": ticket})
    assert result.status_code == 200 and result.json()["user"]["role"] == "viewer"
    token = result.json()["token"]
    assert client.get("/api/v1/entities", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    assert client.post("/api/v1/auth/sso/exchange", json={"code": ticket}).status_code == 401
    assert captured["redirect_uri"].endswith("/api/v1/auth/sso/callback")


def test_oidc_wrong_nonce_and_state_rejected(fixture, monkeypatch):
    client, db, _ = prepare(fixture, monkeypatch, bad_nonce=True)
    start = client.get("/api/v1/auth/sso/start", follow_redirects=False)
    state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    assert client.get("/api/v1/auth/sso/callback", params={"state": "wrong", "code": "code"}).status_code == 401
    assert client.get("/api/v1/auth/sso/callback", params={"state": state, "code": "code"}).status_code == 401
    assert db.query(AuthChallenge).filter_by(kind="ticket").count() == 0
    assert client.get("/api/v1/auth/sso/start", params={"redirect": "//external.test"}, follow_redirects=False).status_code == 422
