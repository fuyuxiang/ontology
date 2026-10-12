"""Fresh acceptance server: production app/lifespan, isolated source and protocols.

Only source rows and protocol credentials are prepared. Ontologies, assets,
bindings, versions, skills and agents MUST be created through the application.
Usage: python3 tests/run_review_server.py [--reuse /private/tmp/ontology-agent-skills-browser-*]
The existing browser fixture supplies its controlled OpenAI protocol, but its
build_app (which seeds released business objects and omits lifespan) is not used.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import sqlite3
import sys
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

import run_agent_skills_browser_fixture as protocol
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt

STATE = protocol.STATE
SOURCE_ROOT = STATE / "sources"
SOURCE_ROOT.mkdir(exist_ok=True)
(STATE / "workspace").mkdir(exist_ok=True)
os.environ.update(WORKSPACE_ROOT=str(STATE / "workspace"), LOCAL_DATA_ROOT=str(SOURCE_ROOT),
                  MONITOR_ENABLED="false", CORS_ORIGINS="http://127.0.0.1:5178,http://localhost:5178")
source_db = SOURCE_ROOT / "devices.db"
if not source_db.exists():
    with sqlite3.connect(source_db) as db:
        db.execute("CREATE TABLE devices (device_id TEXT PRIMARY KEY, temperature REAL NOT NULL, status TEXT NOT NULL)")
        db.execute("INSERT INTO devices VALUES ('DEV-001', 92, 'alarm')")
        db.execute("CREATE TABLE workorders (id TEXT PRIMARY KEY, device_id TEXT NOT NULL, reason TEXT, status TEXT NOT NULL)")
        db.commit()

KEY_FILE = STATE / "oidc-key.pem"
if KEY_FILE.exists():
    private_key = serialization.load_pem_private_key(KEY_FILE.read_bytes(), password=None)
else:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    KEY_FILE.write_bytes(private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                   serialization.NoEncryption()))
    KEY_FILE.chmod(0o600)
ISSUER = f"http://127.0.0.1:{protocol.LLM_PORT}/oidc"
AUTH_CODES = {}
AUTH_LOCK = threading.Lock()


def b64int(value):
    return base64.urlsafe_b64encode(value.to_bytes((value.bit_length() + 7) // 8, "big")).rstrip(b"=").decode()


class AcceptanceProtocols(protocol.ControlledOpenAI):
    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == "/oidc/.well-known/openid-configuration":
            return self.json_response({"issuer": ISSUER, "authorization_endpoint": ISSUER + "/authorize",
                                       "token_endpoint": ISSUER + "/token", "jwks_uri": ISSUER + "/jwks",
                                       "token_endpoint_auth_methods_supported": ["client_secret_basic"],
                                       "id_token_signing_alg_values_supported": ["RS256"]})
        if url.path == "/oidc/jwks":
            public = private_key.public_key().public_numbers()
            return self.json_response({"keys": [{"kty": "RSA", "kid": "isolated", "use": "sig", "alg": "RS256",
                                                   "n": b64int(public.n), "e": b64int(public.e)}]})
        if url.path == "/oidc/authorize":
            values = {k: v[0] for k, v in parse_qs(url.query).items()}
            redirect = values.get("redirect_uri", "")
            if values.get("client_id") != "review-client" or urlsplit(redirect).hostname not in ("127.0.0.1", "localhost") or not redirect.endswith("/api/v1/auth/sso/callback"):
                return self.json_response({"error": "invalid_client_or_redirect"}, 400)
            code = secrets.token_urlsafe(24)
            with AUTH_LOCK:
                AUTH_CODES[code] = {**values, "expires": time.time() + 120}
            self.send_response(302)
            self.send_header("Location", redirect + "?" + urlencode({"code": code, "state": values["state"]}))
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if url.path == "/v1/models":
            return self.json_response({"object": "list", "data": [{"id": "fixture-controlled-chat", "object": "model"}]})
        return super().do_GET()

    def do_POST(self):
        if self.path != "/oidc/token":
            return super().do_POST()
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
        params = {k: v[0] for k, v in parse_qs(body).items()}
        with AUTH_LOCK:
            authorization = AUTH_CODES.pop(params.get("code"), None)
        expected_basic = "Basic " + base64.b64encode(b"review-client:isolated-oidc-secret").decode()
        challenge = base64.urlsafe_b64encode(hashlib.sha256(params.get("code_verifier", "").encode()).digest()).rstrip(b"=").decode()
        if (not authorization or authorization["expires"] < time.time() or params.get("grant_type") != "authorization_code"
                or challenge != authorization.get("code_challenge") or params.get("redirect_uri") != authorization.get("redirect_uri")
                or self.headers.get("Authorization") != expected_basic):
            return self.json_response({"error": "invalid_grant"}, 400)
        now = int(time.time())
        id_token = jwt.encode({"iss": ISSUER, "aud": "review-client", "sub": "isolated-user", "name": "隔离 SSO 用户",
                               "iat": now, "exp": now + 120, "nonce": authorization["nonce"]}, KEY_FILE.read_bytes(),
                              algorithm="RS256", headers={"kid": "isolated"})
        return self.json_response({"access_token": "isolated-provider-access", "token_type": "Bearer", "expires_in": 120, "id_token": id_token})


if __name__ == "__main__":
    import uvicorn
    from app.main import app
    (STATE / "review-manifest.json").write_text(json.dumps({"state": str(STATE), "source_db": str(source_db),
        "api_port": protocol.API_PORT, "protocol_port": protocol.LLM_PORT, "issuer": ISSUER,
        "lifespan": "production", "prepared": ["source rows", "protocol signing key"], "preseeded_business_objects": []}, indent=2))
    print(json.dumps({"state": str(STATE), "source_db": str(source_db), "api": protocol.API_PORT}, ensure_ascii=False), flush=True)
    server = ThreadingHTTPServer(("127.0.0.1", protocol.LLM_PORT), AcceptanceProtocols)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        uvicorn.run(app, host="127.0.0.1", port=protocol.API_PORT, log_level="info")
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
