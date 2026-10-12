"""OIDC code flow with PKCE, verified ID tokens and single-use login tickets.

Reference: https://openid.net/specs/openid-connect-core-1_0.html#CodeFlowAuth
New identities receive the existing viewer role; no email-based account linking.
"""
import base64
import hashlib
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode, urlsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.api.v1.system_config import _get_config_value
from app.core.permissions import role_permissions
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.database import get_db
from app.models import AuthChallenge, User
from app.schemas.auth import TokenResponse, UserOut

router = APIRouter(prefix="/auth/sso", tags=["auth-sso"])


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _settings(db):
    if _get_config_value(db, "auth.sso_enabled") != "true":
        raise HTTPException(400, "SSO 未启用")
    if (_get_config_value(db, "auth.sso_provider") or "oidc") != "oidc":
        raise HTTPException(422, "当前登录协议需 OIDC；SAML/LDAP 需要测试身份源和接入契约")
    config = {k: _get_config_value(db, f"auth.{k}") or "" for k in ("issuer_url", "client_id", "client_secret", "redirect_uri")}
    if not all(config[k] for k in ("issuer_url", "client_id", "redirect_uri")):
        raise HTTPException(422, "请配置 OIDC issuer_url、client_id 和 redirect_uri")
    _url(config["issuer_url"])
    _url(config["redirect_uri"])
    return config


def _url(value):
    parts = urlsplit(value)
    if parts.scheme != "https" and not (parts.scheme == "http" and parts.hostname in {"127.0.0.1", "localhost", "::1"}):
        raise HTTPException(422, "OIDC 地址需要 HTTPS（本机隔离测试可以使用 HTTP）")
    if parts.username or parts.password or not parts.hostname:
        raise HTTPException(422, "OIDC 地址无效")
    return value


def _metadata(client, config):
    response = client.get(f"{config['issuer_url'].rstrip('/')}/.well-known/openid-configuration")
    response.raise_for_status()
    metadata = response.json()
    if metadata.get("issuer") != config["issuer_url"]:
        raise HTTPException(502, "身份源 issuer 与配置不一致")
    for key in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
        _url(metadata[key])
    return metadata


def _consume(db, secret, kind):
    row = db.get(AuthChallenge, digest(secret))
    if not row or row.kind != kind or row.state != "pending" or row.expires_at <= datetime.utcnow():
        raise HTTPException(401, "登录请求已使用或过期，请重新开始")
    changed = db.execute(update(AuthChallenge).where(AuthChallenge.id == row.id, AuthChallenge.state == "pending").values(state="consumed")).rowcount
    db.commit()
    if changed != 1:
        raise HTTPException(409, "登录请求已被使用")
    return row.data


@router.get("/config")
def config(db: Session = Depends(get_db)):
    provider = _get_config_value(db, "auth.sso_provider") or "oidc"
    return {"enabled": _get_config_value(db, "auth.sso_enabled") == "true" and provider == "oidc", "provider": provider}


@router.get("/start")
def start(redirect: str = "/dashboard", db: Session = Depends(get_db)):
    config = _settings(db)
    if not redirect.startswith("/") or redirect.startswith("//") or "\\" in redirect:
        raise HTTPException(422, "登录后跳转必须是本地页面")
    state, nonce, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(32), secrets.token_urlsafe(48)
    try:
        with httpx.Client(timeout=10) as client:
            metadata = _metadata(client, config)
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise HTTPException(502, "无法读取身份源配置") from exc
    db.query(AuthChallenge).filter(AuthChallenge.expires_at < datetime.utcnow()).delete(synchronize_session=False)
    db.add(AuthChallenge(id=digest(state), kind="oidc", data={"nonce": nonce, "verifier": verifier, "redirect": redirect}, expires_at=datetime.utcnow() + timedelta(minutes=10)))
    db.commit()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    url = metadata["authorization_endpoint"] + "?" + urlencode({"response_type": "code", "scope": "openid profile email", "client_id": config["client_id"], "redirect_uri": config["redirect_uri"], "state": state, "nonce": nonce, "code_challenge": challenge, "code_challenge_method": "S256"})
    response = RedirectResponse(url, status_code=302)
    response.set_cookie("ontology_oidc_state", state, max_age=600, httponly=True, secure=config["redirect_uri"].startswith("https://"), samesite="lax", path="/api/v1/auth/sso")
    return response


@router.get("/callback")
def callback(request: Request, state: str, code: str | None = None, error: str | None = None, db: Session = Depends(get_db)):
    config = _settings(db)
    cookie = request.cookies.get("ontology_oidc_state", "")
    if not cookie or not secrets.compare_digest(state, cookie):
        raise HTTPException(401, "OIDC state 校验失败")
    context = _consume(db, state, "oidc")
    if error or not code:
        raise HTTPException(401, "身份源拒绝登录，请重新开始")
    try:
        with httpx.Client(timeout=15) as client:
            metadata = _metadata(client, config)
            payload = {"grant_type": "authorization_code", "code": code, "redirect_uri": config["redirect_uri"], "client_id": config["client_id"], "code_verifier": context["verifier"]}
            auth = None
            if config["client_secret"]:
                methods = metadata.get("token_endpoint_auth_methods_supported", ["client_secret_basic"])
                if "client_secret_basic" in methods:
                    auth = (config["client_id"], config["client_secret"])
                else:
                    payload["client_secret"] = config["client_secret"]
            token_response = client.post(metadata["token_endpoint"], data=payload, auth=auth)
            token_response.raise_for_status()
            tokens = token_response.json()
            id_token = tokens["id_token"]
            keys_response = client.get(metadata["jwks_uri"])
            keys_response.raise_for_status()
            claims = jwt.decode(id_token, keys_response.json(), algorithms=["RS256", "ES256"], audience=config["client_id"], issuer=config["issuer_url"], access_token=tokens.get("access_token"), options={"require_exp": True, "require_iat": True, "require_sub": True})
        if claims.get("nonce") != context["nonce"] or (claims.get("azp") and claims["azp"] != config["client_id"]):
            raise JWTError("nonce/azp mismatch")
        if isinstance(claims["aud"], list) and len(claims["aud"]) > 1 and claims.get("azp") != config["client_id"]:
            raise JWTError("missing authorized party")
    except (httpx.HTTPError, JWTError, ValueError, KeyError) as exc:
        raise HTTPException(401, "身份源令牌验证失败，请重新登录") from exc
    username = "sso_" + digest(config["issuer_url"] + "\x00" + claims["sub"])[:40]
    user = db.query(User).filter_by(username=username).first()
    if not user:
        user = User(username=username, name=str(claims.get("name") or claims["sub"])[:100], role="viewer", password_hash=hash_password(secrets.token_urlsafe(40)))
        db.add(user)
        db.flush()
    if not user.is_active:
        raise HTTPException(403, "账号已被禁用")
    ticket = secrets.token_urlsafe(32)
    db.add(AuthChallenge(id=digest(ticket), kind="ticket", data={"user_id": user.id}, expires_at=datetime.utcnow() + timedelta(seconds=120)))
    db.commit()
    # Only a short-lived, single-use ticket crosses the browser redirect. JWTs
    # and identity-provider tokens never appear in URLs.
    response = RedirectResponse("/login?" + urlencode({"sso_code": ticket, "redirect": context["redirect"]}), status_code=302)
    response.delete_cookie("ontology_oidc_state", path="/api/v1/auth/sso")
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


class TicketRequest(BaseModel):
    code: str


@router.post("/exchange", response_model=TokenResponse)
def exchange(body: TicketRequest, db: Session = Depends(get_db)):
    data = _consume(db, body.code, "ticket")
    user = db.get(User, data["user_id"])
    if not user or not user.is_active:
        raise HTTPException(401, "账号不存在或已禁用")
    user.last_login_at = datetime.utcnow()
    db.commit()
    timeout = _get_config_value(db, "auth.session_timeout")
    return TokenResponse(token=create_access_token(user.id, user.token_version, int(timeout) if timeout else None), refresh_token=create_refresh_token(user.id, user.token_version), user=UserOut(id=user.id, username=user.username, name=user.name, role=user.role, permissions=role_permissions(db, user.role)))
