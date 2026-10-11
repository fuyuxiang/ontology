"""Pin model behavior in releases while keeping rotatable credentials outside them."""
import copy
import json

from app.config import settings
from app.models.agent import ModelRegistry
from app.models.system_config import SystemConfig
from app.services.llm_resolver import _resolve_model_from_db


def public_snapshot(snapshot):
    # Keep runtime definitions intact in storage; mask credentials in inspection APIs.
    from app.api.v1.models import _redact_base, _redact_config
    visible = _redact_config(copy.deepcopy(snapshot))
    if visible.get("model_snapshot"):
        visible["model_snapshot"]["api_base"] = _redact_base(visible["model_snapshot"].get("api_base"))
    return visible


def model_snapshot(db, model_id):
    if model_id:
        model = db.get(ModelRegistry, model_id) if db else None
        if not model:
            return {"source": "registry", "model_id": model_id, "unavailable": True}
        config = model.config_json or {}
        return {"source": "registry", "model_id": model_id, "model_name": model.model_name,
                "provider": model.provider, "api_base": model.api_base or settings.LLM_BASE_URL,
                "config_json": {k: copy.deepcopy(config[k]) for k in ("temperature", "max_tokens") if k in config}}
    configured = _resolve_model_from_db(db, "agent") if db else None
    return {"source": "system" if configured else "environment", "model_id": None,
            "model_name": configured["model"] if configured else settings.LLM_MODEL,
            "api_base": configured["base_url"] if configured else settings.LLM_BASE_URL, "config_json": {}}


def model_credentials(db, pinned):
    if pinned["source"] == "registry":
        model = db.get(ModelRegistry, pinned["model_id"])
        if not model or model.status != "active":
            raise ValueError("发布版本所需的模型已不可用")
        return model.api_key or settings.LLM_API_KEY
    if pinned["source"] == "system":
        row = db.query(SystemConfig).filter(SystemConfig.key == "ai.models").first()
        entries = json.loads(row.value) if row and row.value else []
        for entry in entries:
            if entry.get("model_id") == pinned["model_name"] and entry.get("base_url", "") == pinned["api_base"] and entry.get("api_key"):
                return entry["api_key"]
        raise ValueError("发布版本模型凭证已不可用，请配置对应模型或重新测试发布")
    if pinned["api_base"] != settings.LLM_BASE_URL:
        raise ValueError("发布版本原模型地址已变更，请添加对应模型后重新测试发布")
    return settings.LLM_API_KEY
