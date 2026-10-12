"""Authenticated model catalog with credential redaction and dependency protection."""
import copy
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.deps import require_user
from app.core.permissions import has_permission
from app.database import get_db
from app.models.agent import Agent, ModelRegistry
from app.models.agent_runtime import AgentVersion
from app.models.user import User

router = APIRouter(prefix="/models", tags=["models"])
SECRET_NAMES = {"key", "api_key", "apikey", "api_secret", "secret_key", "token",
                "access_token", "refresh_token", "auth_token", "bearer_token",
                "password", "secret", "client_secret", "authorization",
                "credential", "credentials", "private_key"}
URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+")


def require_model_user(user: User = Depends(require_user)) -> User:
    if not user.is_active:
        raise HTTPException(403, "账号已停用")
    return user


def require_model_editor(user: User = Depends(require_model_user), db: Session = Depends(get_db)) -> User:
    if not has_permission(user, "rule:write", db):
        raise HTTPException(403, "需要规则编写权限")
    return user


class ModelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    provider: str = Field(min_length=1, max_length=50)
    model_name: str = Field(min_length=1, max_length=200)
    api_base: str | None = None
    api_key: str | None = None
    capabilities: list | None = None
    config_json: dict | None = None

    @field_validator("name", "provider", "model_name")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("模型名称、提供方和标识不能为空")
        return value.strip()


class ModelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    provider: str | None = Field(default=None, min_length=1, max_length=50)
    model_name: str | None = Field(default=None, min_length=1, max_length=200)
    api_base: str | None = None
    api_key: str | None = None
    capabilities: list | None = None
    config_json: dict | None = None
    status: str | None = None

    @field_validator("name", "provider", "model_name")
    @classmethod
    def nonblank(cls, value):
        if value is not None and not value.strip():
            raise ValueError("模型名称、提供方和标识不能为空")
        return value.strip() if value else value

    @field_validator("status")
    @classmethod
    def valid_status(cls, value):
        if value is not None and value not in {"active", "inactive"}:
            raise ValueError("模型状态只能为 active 或 inactive")
        return value


def _secret_name(key):
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(key)).lower().replace("-", "_")
    return name in SECRET_NAMES or name.removeprefix("x_") in SECRET_NAMES


def _redact_config(value):
    """Model options may contain nested provider credentials; never echo them."""
    if isinstance(value, dict):
        return {key: "***" if _secret_name(key)
                else _redact_config(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_config(item) for item in value]
    if isinstance(value, str):
        return URL_PATTERN.sub(lambda match: _redact_base(match.group()), value)
    return value


def _redact_base(value):
    if not value:
        return value
    try:
        parsed = urlsplit(value)
        pairs = parse_qsl(parsed.query, keep_blank_values=True)
        if "@" not in parsed.netloc and not any(_secret_name(key) for key, _ in pairs):
            return value
        query = urlencode([(key, "***" if _secret_name(key) else item) for key, item in pairs])
        return urlunsplit(parsed._replace(netloc=parsed.netloc.rsplit("@", 1)[-1], query=query))
    except ValueError:
        return "[invalid endpoint]"


def _restore_masked_config(incoming, stored):
    """Treat the catalog's mask as unchanged while applying editable options."""
    if incoming == "***":
        return copy.deepcopy(stored) if stored is not None else None
    if isinstance(incoming, dict):
        existing = stored if isinstance(stored, dict) else {}
        merged = copy.deepcopy(existing)
        for key, value in incoming.items():
            merged[key] = _restore_masked_config(value, existing.get(key))
        return merged
    if isinstance(incoming, list):
        existing = stored if isinstance(stored, list) else []
        return [_restore_masked_config(value, existing[index] if index < len(existing) else None)
                for index, value in enumerate(incoming)]
    if isinstance(incoming, str) and isinstance(stored, str) and incoming == _redact_config(stored):
        return stored
    return copy.deepcopy(incoming)


def _model_out(m: ModelRegistry) -> dict:
    return {
        "id": m.id,
        "name": m.name,
        "provider": m.provider,
        "model_name": m.model_name,
        "api_base": _redact_base(m.api_base),
        "api_key": "***" if m.api_key else None,
        "capabilities": m.capabilities or [],
        "config_json": _redact_config(m.config_json or {}),
        "status": m.status,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


@router.get("")
def list_models(db: Session = Depends(get_db), user: User = Depends(require_model_user)):
    query = db.query(ModelRegistry)
    if not has_permission(user, "rule:write", db):
        query = query.filter_by(status="active")
    return [_model_out(m) for m in query.all()]


@router.post("", status_code=201)
def create_model(body: ModelCreate, db: Session = Depends(get_db), user: User = Depends(require_model_editor)):
    m = ModelRegistry(**body.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return _model_out(m)


@router.get("/{mid}")
def get_model(mid: str, db: Session = Depends(get_db), user: User = Depends(require_model_user)):
    m = db.get(ModelRegistry, mid)
    if not m or (m.status != "active" and not has_permission(user, "rule:write", db)):
        raise HTTPException(404, "Model not found")
    return _model_out(m)


@router.put("/{mid}")
def update_model(mid: str, body: ModelUpdate, db: Session = Depends(get_db), user: User = Depends(require_model_editor)):
    m = db.get(ModelRegistry, mid)
    if not m:
        raise HTTPException(404, "Model not found")
    for k, v in body.model_dump(exclude_none=True).items():
        if k == "api_key" and v == "***":
            continue
        if k == "config_json":
            v = _restore_masked_config(v, m.config_json or {})
        if k == "api_base" and v == _redact_base(m.api_base):
            continue
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return _model_out(m)


@router.delete("/{mid}")
def delete_model(mid: str, db: Session = Depends(get_db), user: User = Depends(require_model_editor)):
    m = db.get(ModelRegistry, mid)
    if not m:
        raise HTTPException(404, "Model not found")
    if db.query(Agent).filter_by(model_id=mid).first():
        raise HTTPException(409, "模型仍被智能体草稿引用，请先更换模型")
    for version in db.query(AgentVersion).all():
        snapshot = version.config_snapshot or {}
        model_snapshot = snapshot.get("model_snapshot") or {}
        if snapshot.get("model_id") == mid or model_snapshot.get("model_id") == mid or model_snapshot.get("id") == mid:
            raise HTTPException(409, "模型仍被已发布或历史智能体版本引用，不能删除")
    db.delete(m)
    db.commit()
    return {"ok": True}


@router.post("/{mid}/test")
def test_model(mid: str, db: Session = Depends(get_db), user: User = Depends(require_model_editor)):
    m = db.get(ModelRegistry, mid)
    if not m or m.status != "active":
        raise HTTPException(404, "Model not found")
    if not m.api_key:
        return {"ok": False, "error": "API key is not configured"}
    try:
        from app.services.llm_resolver import get_llm_client
        client = get_llm_client(
            db=db,
            scene="agent",
            api_key=m.api_key,
            api_base=m.api_base or "https://api.openai.com/v1",
        )
        cfg = m.config_json or {}
        resp = client.chat.completions.create(
            model=m.model_name,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=cfg.get("max_tokens", 10),
            temperature=cfg.get("temperature", 0.1),
        )
        return {"ok": True, "reply": resp.choices[0].message.content}
    except Exception as e:
        return {"ok": False, "error": _redact_config(str(e).replace(m.api_key, "[redacted]"))}
