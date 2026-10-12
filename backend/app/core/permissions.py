"""Persistent role permissions shared by session APIs and production routes."""
import json

from fastapi import Depends, HTTPException, WebSocketException
from sqlalchemy.orm import Session
from starlette.requests import HTTPConnection

from app.core.security import decode_token_payload
from app.database import get_db
from app.models.system_config import SystemConfig
from app.models.user import User
from app.schemas.auth import ROLE_PERMISSIONS


def role_permissions(db: Session, role: str) -> list[str]:
    row = db.query(SystemConfig).filter(SystemConfig.key == f"auth.role_permissions.{role}").first()
    if row and row.value:
        value = json.loads(row.value)
        if isinstance(value, list) and all(isinstance(p, str) for p in value):
            return value
        raise HTTPException(500, "角色权限配置损坏")
    return list(ROLE_PERMISSIONS.get(role, []))


def has_permission(user: User | None, permission: str, db: Session | None = None) -> bool:
    if not user or not user.is_active:
        return False
    from sqlalchemy.orm import object_session
    db = db or object_session(user)
    return permission in (role_permissions(db, user.role) if db else ROLE_PERMISSIONS.get(user.role, []))


def require_platform_access(connection: HTTPConnection, db: Session = Depends(get_db)) -> User:
    """All UI/internal routes require a live account; public protocols own their auth.

    Existing permissions govern reads and mutations. Testing authored code is
    available to rule writers; execution is also available to rule executors.
    Agent/skill ownership and release gates remain enforced by their services.
    """
    auth = connection.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else None
    is_ws = connection.scope["type"] == "websocket"
    if is_ws and not token:
        offered = connection.headers.get("sec-websocket-protocol", "").split(",")
        token = next((value.strip()[4:] for value in offered if value.strip().startswith("jwt.")), None)
        token = token or connection.query_params.get("token")
    payload = decode_token_payload(token, "access") if token else None
    user = db.get(User, payload["sub"]) if payload else None

    def deny(code: int, message: str):
        if is_ws:
            raise WebSocketException(code=1008, reason=message)
        raise HTTPException(code, message)

    if not user or not user.is_active or payload.get("tv", 0) != user.token_version:
        deny(401, "请使用有效登录会话")
    permissions = set(role_permissions(db, user.role))
    path = connection.url.path.removeprefix("/api/v1/")
    method = connection.scope.get("method", "GET")
    segment = path.split("/", 1)[0]
    reading = method in {"GET", "HEAD", "OPTIONS"}
    execution = any(part in path.split("/") for part in ("execute", "test", "chat", "run", "confirm", "reject", "reconcile"))
    if segment in {"system-config", "auth"}:
        allowed = "admin:users" in permissions
    elif segment in {"monitor", "governance", "traces", "evals", "audit", "execution-logs"}:
        allowed = "audit:read" in permissions
        if method not in {"GET", "HEAD", "OPTIONS"}:
            allowed = allowed and "entity:write" in permissions
    elif segment == "agents":
        allowed = "strategy:read" in permissions if reading else (
            bool({"strategy:execute", "rule:write"} & permissions) if execution else "rule:write" in permissions)
    elif segment in {"functions", "actions", "registry", "skills", "models", "prompt-templates", "ai-code"}:
        if reading:
            allowed = "rule:read" in permissions
        elif execution:
            allowed = bool({"rule:execute", "rule:write"} & permissions)
        else:
            allowed = "rule:write" in permissions
    elif reading or path.endswith(("/query", "/preview", "/fields", "/schema", "/probe", "/test-connection")):
        allowed = "entity:read" in permissions
    elif method == "DELETE" and segment in {"entities", "scenarios"}:
        allowed = "entity:delete" in permissions
    else:
        allowed = "entity:write" in permissions
    if not allowed:
        deny(403, "当前角色没有此操作权限")
    connection.state.user_id = user.id
    return user
