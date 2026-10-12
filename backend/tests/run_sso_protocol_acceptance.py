"""Real loopback OIDC HTTP redirects/JWKS/token exchange; not a real enterprise IdP."""
import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit

import httpx

API = "http://127.0.0.1:5055/api/v1"
FRONT = "http://127.0.0.1:5178"
evidence = []
with httpx.Client(trust_env=False, timeout=15, follow_redirects=False) as client:
    login = client.post(API + "/auth/login", json={"username": "admin", "password": os.environ["REVIEW_PASSWORD"]})
    assert login.status_code == 200
    admin_headers = {"Authorization": "Bearer " + login.json()["token"]}
    values = {"sso_enabled": "true", "sso_provider": "oidc", "issuer_url": "http://127.0.0.1:5056/oidc",
              "client_id": "review-client", "client_secret": "isolated-oidc-secret",
              "redirect_uri": FRONT + "/api/v1/auth/sso/callback"}
    saved = client.put(API + "/system-config", json={"group": "auth", "items": [{"key": k, "value": v} for k, v in values.items()]}, headers=admin_headers)
    assert saved.status_code == 200, saved.text
    response = client.get(FRONT + "/api/v1/auth/sso/start", params={"redirect": "/ontology/list"})
    for _ in range(4):
        evidence.append({"path": urlsplit(str(response.url)).path, "status": response.status_code,
                         "location_path": urlsplit(response.headers.get("Location", "")).path})
        assert response.status_code in (302, 303, 307), response.text
        destination = urljoin(str(response.url), response.headers["Location"])
        parsed = urlsplit(destination)
        if parsed.path == "/login":
            assert parse_qs(parsed.query)["redirect"] == ["/ontology/list"]
            ticket = parse_qs(parsed.query)["sso_code"][0]
            break
        response = client.get(destination)
    else:
        raise AssertionError("OIDC did not return to the application login page")
    exchange = client.post(API + "/auth/sso/exchange", json={"code": ticket})
    assert exchange.status_code == 200, exchange.text
    result = exchange.json()
    assert result["user"]["role"] == "viewer"
    me = client.get(API + "/auth/me", headers={"Authorization": "Bearer " + result["token"]})
    assert me.status_code == 200 and me.json()["id"] == result["user"]["id"]
    replay = client.post(API + "/auth/sso/exchange", json={"code": ticket})
    assert replay.status_code == 401
    denied = client.post(API + "/scenarios", headers={"Authorization": "Bearer " + result["token"]}, json={"code": "unauthorized", "name": "must not create"})
    assert denied.status_code == 403
    invalid_redirect = client.get(API + "/auth/sso/start", params={"redirect": "//external.invalid"})
    assert invalid_redirect.status_code == 422
    evidence.append({"exchange": "passed", "single_use_replay_http": replay.status_code, "viewer_mutation_http": denied.status_code,
                     "external_redirect_http": invalid_redirect.status_code, "user_id": result["user"]["id"], "role": "viewer"})
Path("../docs/review/evidence/sso-protocol.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2))
print("OIDC signed protocol, PKCE, callback, single-use ticket and viewer permission checks passed.")
