"""
系统配置 API — 分组管理平台全局参数（支持多模型配置）
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.database import get_db
from app.models.system_config import SystemConfig
from app.models.user import User
from app.schemas.system_config import ConfigResponse, ConfigSaveRequest, TestResult
from app.services.audit import write_audit
from app.models.audit import AuditLog

router = APIRouter(prefix="/system-config", tags=["system-config"])

# 敏感字段列表（返回时脱敏）
SENSITIVE_KEYS = {"ai.api_key", "ai.api_secret", "notification.smtp_password", "notification.webhook_secret", "auth.client_secret", "storage.secret_key"}

# 多模型场景定义
MODEL_SCENES = [
    {"key": "ontology", "label": "本体构建", "desc": "用于本体自动构建、实体抽取、关系推理"},
    {"key": "agent", "label": "智能体", "desc": "用于智能体对话、问答、任务执行"},
    {"key": "data", "label": "数据处理", "desc": "用于数据清洗、转换、质量检测"},
    {"key": "general", "label": "通用", "desc": "默认模型，未指定场景时使用"},
]


def _mask_value(key: str, value: str | None) -> str | None:
    """对敏感字段脱敏：显示前4位 + **** + 后4位"""
    if key == "ai.models" and value:
        import json
        models = json.loads(value)
        for model in models:
            model["api_key"] = _mask_model_api_key(model.get("api_key"))
        return json.dumps(models, ensure_ascii=False)
    if not value or key not in SENSITIVE_KEYS:
        return value
    if len(value) <= 8:
        return "••••••••"
    return value[:4] + "****" + value[-4:]


def _mask_model_api_key(key: str | None) -> str | None:
    """对模型 API Key 脱敏"""
    if not key:
        return ""
    if len(key) <= 8:
        return "••••••••"
    return key[:4] + "****" + key[-4:]


@router.get("", response_model=ConfigResponse)
def get_all_config(db: Session = Depends(get_db), _user: User = Depends(require_admin)):
    """获取全部配置（按分组返回）"""
    rows = db.query(SystemConfig).order_by(SystemConfig.group, SystemConfig.key).all()
    groups: dict[str, list[dict]] = {}
    for r in rows:
        sensitive_key = r.key if "." in r.key else f"{r.group}.{r.key}"
        groups.setdefault(r.group, []).append({
            "key": r.key,
            "value": _mask_value(sensitive_key, r.value),
            "description": r.description,
            "is_sensitive": sensitive_key in SENSITIVE_KEYS,
        })
    return ConfigResponse(groups=groups)


@router.get("/ai/models")
def get_ai_models(db: Session = Depends(get_db), _user: User = Depends(require_admin)):
    """获取 AI 模型列表（JSON 存储在 ai.models 这个 key 中）"""
    row = db.query(SystemConfig).filter(SystemConfig.key == "ai.models").first()
    if not row or not row.value:
        return {"models": [], "scenes": MODEL_SCENES}
    try:
        import json
        models = json.loads(row.value)
        # 脱敏 API Key
        for m in models:
            m["api_key"] = _mask_model_api_key(m.get("api_key", ""))
        return {"models": models, "scenes": MODEL_SCENES}
    except Exception:
        return {"models": [], "scenes": MODEL_SCENES}


@router.put("/ai/models")
def save_ai_models(data: dict, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    """保存 AI 模型列表"""
    import json
    models = data.get("models", [])
    if not isinstance(models, list) or not all(isinstance(m, dict) and isinstance(m.get("id"), str) and m["id"] for m in models):
        raise HTTPException(422, "models 必须为带唯一 id 的模型列表")
    if len({m["id"] for m in models}) != len(models):
        raise HTTPException(422, "模型 id 不能重复")
    for model in models:
        for key, low, high in (("temperature", 0, 2), ("top_p", 0, 1), ("max_tokens", 1, 1000000), ("timeout_seconds", 1, 300)):
            if key in model:
                val = model[key]
                if isinstance(val, bool) or not isinstance(val, (int, float)) or not low <= val <= high or (key in {"max_tokens", "timeout_seconds"} and int(val) != val):
                    raise HTTPException(422, f"模型参数 {key} 无效")
        if "scenes" in model and (not isinstance(model["scenes"], list) or not set(model["scenes"]).issubset({s["key"] for s in MODEL_SCENES})):
            raise HTTPException(422, "模型使用场景无效")
    # 读取时返回的长、短密钥掩码都必须还原为已有值。
    row = db.query(SystemConfig).filter(SystemConfig.key == "ai.models").first()
    old_models = []
    if row and row.value:
        try:
            old_models = json.loads(row.value)
        except Exception:
            pass

    old_key_map = {m.get("id"): m.get("api_key", "") for m in old_models}

    for m in models:
        old_key = old_key_map.get(m.get("id"), "")
        submitted_key = m.get("api_key", "")
        if old_key and submitted_key == _mask_model_api_key(old_key):
            m["api_key"] = old_key

    value = json.dumps(models, ensure_ascii=False)
    if row:
        row.value = value
        row.updated_at = datetime.utcnow()
        row.updated_by = user.username
    else:
        db.add(SystemConfig(group="ai", key="ai.models", value=value, description="AI 模型列表", updated_by=user.username))
    write_audit(db, user_id=getattr(user, "id", None), user_name=user.username,
                action="update", target_type="system_config", target_id="ai.models", target_name="AI 模型配置",
                details="更新模型列表、场景和运行参数")
    db.commit()
    return {"message": "保存成功"}


@router.post("/ai/models/test")
def test_ai_model(data: dict, db: Session = Depends(get_db), _user: User = Depends(require_admin)):
    """测试指定模型的连通性"""
    api_key = data.get("api_key", "")
    base_url = data.get("base_url", "https://api.anthropic.com")
    model_id = data.get("model_id", "")

    # 列表只包含脱敏密钥；测试已保存模型时按其 ID 在服务端取真实凭据。
    if data.get("id"):
        import json
        row = db.query(SystemConfig).filter(SystemConfig.key == "ai.models").first()
        try:
            saved_models = json.loads(row.value) if row and row.value else []
            saved = next((m for m in saved_models if m.get("id") == data["id"]), None)
            saved_key = saved.get("api_key", "") if saved else ""
            if saved_key and api_key == _mask_model_api_key(saved_key):
                api_key = saved_key
        except (ValueError, TypeError):
            pass

    if not api_key or api_key.startswith("••••"):
        return TestResult(success=False, message="请先填写 API Key")
    if not model_id:
        return TestResult(success=False, message="请先选择模型")

    try:
        import httpx
        with httpx.Client(timeout=10) as client:
            resp = client.post(_models_url(base_url).removesuffix("/models") + "/chat/completions", json={
                "model": model_id, "messages": [{"role": "user", "content": "Reply OK."}], "max_tokens": 8,
            }, headers={
                "Authorization": f"Bearer {api_key}",
                "x-api-key": api_key,
            })
            if resp.status_code < 400 and resp.json().get("choices"):
                return TestResult(success=True, message=f"连接成功，模型 {model_id} 可用")
            if resp.status_code < 400:
                return TestResult(success=False, message="模型未返回有效 completion")
            return TestResult(success=False, message=f"连接失败: HTTP {resp.status_code}")
    except Exception as e:
        return TestResult(success=False, message=f"连接失败: {str(e)}")


@router.get("/scenes")
def get_model_scenes(_user: User = Depends(require_admin)):
    """获取模型使用场景列表"""
    return MODEL_SCENES


@router.get("/history")
def config_history(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db),
                   _user: User = Depends(require_admin)):
    rows = db.query(AuditLog).filter_by(target_type="system_config").order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [{"id": row.id, "user": row.user_name or "系统", "time": row.timestamp.isoformat(),
             "desc": row.details or row.target_name, "type": row.action} for row in rows]


@router.put("")
def save_config(data: ConfigSaveRequest, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    """批量保存某组配置"""
    # Validate the complete request before touching any persistent row. Reject a
    # dotted key in the wrong group, including previously unseen keys.
    if data.group == "auth":
        submitted = {item.key.removeprefix("auth."): item.value for item in data.items}
        provider = submitted.get("sso_provider", _get_config_value(db, "auth.sso_provider") or "oidc")
        enabled = submitted.get("sso_enabled", _get_config_value(db, "auth.sso_enabled") or "false")
        if "sso_provider" in submitted and provider != "oidc":
            raise HTTPException(422, "当前仅支持 OIDC 单点登录")
        if enabled == "true" and provider != "oidc":
            raise HTTPException(422, "请先选择受支持的 OIDC 单点登录协议")
    normalized = {}
    unchanged = set()
    keys = [item.key.removeprefix(data.group + ".") for item in data.items]
    if len(keys) != len(set(keys)):
        raise HTTPException(422, "同一配置字段不能重复提交")
    for item in data.items:
        if "." in item.key and item.key.split(".", 1)[0] != data.group:
            raise HTTPException(422, "配置字段不属于当前分组")
        if data.group == "basic":
            bare = item.key.removeprefix("basic.")
            if bare == "system_name" and (not item.value or not item.value.strip() or len(item.value) > 100):
                raise HTTPException(422, "系统名称必须为1到100个字符")
            if bare == "language" and item.value not in {"zh-CN", "en"}:
                raise HTTPException(422, "界面语言必须为 zh-CN 或 en")
            if bare == "timezone" and item.value not in {"Asia/Shanghai", "UTC"}:
                raise HTTPException(422, "时区必须为 Asia/Shanghai 或 UTC")
    for item in data.items:
        bare = item.key.split(".")[-1]
        if item.key.startswith("auth.role_permissions."):
            raise HTTPException(422, "请通过角色权限接口修改权限")
        if item.key == "ai.models":
            existing = db.query(SystemConfig).filter_by(key=item.key).first()
            if existing and item.value == _mask_value(item.key, existing.value):
                unchanged.add(item.key)
                continue
            raise HTTPException(422, "请通过模型配置接口修改模型列表")
        bounds = {"password_min_length": (6, 72), "session_timeout": (5, 1440), "smtp_port": (1, 65535),
                  "max_upload_mb": (1, 1024), "timeout_seconds": (1, 300), "max_tokens": (1, 1000000),
                  "temperature": (0, 2), "top_p": (0, 1)}
        if bare in bounds:
            try:
                value = float(item.value)
            except (ValueError, TypeError):
                raise HTTPException(422, f"{bare} 必须是有效数值") from None
            low, high = bounds[bare]
            if not low <= value <= high or (bare not in {"temperature", "top_p"} and not value.is_integer()):
                raise HTTPException(422, f"{bare} 必须在 {low} 到 {high} 范围内")
            normalized[item.key] = str(value) if bare in {"temperature", "top_p"} else str(int(value))
    # Validate group ownership before mutating any persistent row.
    for item in data.items:
        existing = db.query(SystemConfig).filter_by(key=item.key).first()
        if existing and existing.group != data.group:
            raise HTTPException(422, "配置字段不属于当前分组")
    for item in data.items:
        if item.key in unchanged:
            continue
        bare = item.key.split(".")[-1]
        value = normalized.get(item.key, item.value)
        existing = db.query(SystemConfig).filter(SystemConfig.key == item.key).first()
        # Match the reader's precedence without creating aliases that silently
        # override settings edited through the legacy bare key.
        qualified = db.query(SystemConfig).filter_by(key=f"{data.group}.{bare}").first()
        legacy = db.query(SystemConfig).filter_by(group=data.group, key=bare).first()
        existing = qualified or legacy or existing
        if existing:
            if existing.group != data.group:
                raise HTTPException(422, "配置字段不属于当前分组")
            sensitive_key = existing.key if "." in existing.key else f"{existing.group}.{existing.key}"
            if sensitive_key in SENSITIVE_KEYS and existing.value and item.value == _mask_value(sensitive_key, existing.value):
                continue
            existing.value = value
            existing.updated_at = datetime.utcnow()
            existing.updated_by = user.username
        else:
            db.add(SystemConfig(
                group=data.group,
                key=item.key,
                value=value,
                updated_by=user.username,
            ))
    write_audit(db, user_id=getattr(user, "id", None), user_name=user.username,
                action="update", target_type="system_config", target_id=data.group,
                target_name=f"{data.group} 配置", details=f"修改 {data.group} 配置字段：" + ", ".join(item.key for item in data.items))
    db.commit()
    return {"message": "保存成功"}


@router.post("/test-ai", response_model=TestResult)
def test_ai_connection(db: Session = Depends(get_db), _user: User = Depends(require_admin)):
    """测试默认 AI 连通性"""
    api_key = _get_config_value(db, "ai.api_key")
    base_url = _get_config_value(db, "ai.base_url") or "https://api.anthropic.com"
    model = _get_config_value(db, "ai.model") or "claude-sonnet-4-20250514"

    if not api_key:
        return TestResult(success=False, message="未配置 API Key")

    try:
        import httpx
        with httpx.Client(timeout=10) as client:
            resp = client.post(_models_url(base_url).removesuffix("/models") + "/chat/completions", json={
                "model": model, "messages": [{"role": "user", "content": "Reply OK."}], "max_tokens": 8,
            }, headers={
                "Authorization": f"Bearer {api_key}",
                "x-api-key": api_key,
            })
            if resp.status_code < 400 and resp.json().get("choices"):
                return TestResult(success=True, message=f"连接成功，模型 {model} 可用")
            if resp.status_code < 400:
                return TestResult(success=False, message="模型未返回有效 completion")
            return TestResult(success=False, message=f"连接失败: HTTP {resp.status_code}")
    except Exception as e:
        return TestResult(success=False, message=f"连接失败: {str(e)}")


@router.post("/test-email", response_model=TestResult)
async def test_email(data: dict, db: Session = Depends(get_db), _user: User = Depends(require_admin)):
    """测试邮件发送"""
    recipient = data.get("recipient", "")
    if not recipient:
        return TestResult(success=False, message="请提供收件人邮箱")

    from app.services.action_executors import get_executor
    result = await get_executor("notification", db).execute({
        "channel": "email", "recipient": recipient,
        "subject": "【本体管理平台】邮件测试", "message_template": "这是一封来自本体管理平台的测试邮件。",
    }, {})
    return TestResult(success=result.success, message=result.message)


def _models_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    return f"{base}/models" if base.endswith("/v1") else f"{base}/v1/models"


def _get_config_value(db: Session, key: str) -> str | None:
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not row and "." in key:
        group, bare_key = key.split(".", 1)
        row = db.query(SystemConfig).filter(SystemConfig.group == group, SystemConfig.key == bare_key).first()
    value = row.value if row else None
    # Earlier releases accepted integer-valued decimal spellings ("5.0").
    # Normalize legacy rows at the shared read boundary as well as on save.
    integer_keys = {"password_min_length", "session_timeout", "smtp_port", "max_upload_mb", "timeout_seconds", "max_tokens"}
    if value and key.split(".")[-1] in integer_keys:
        from decimal import Decimal, InvalidOperation
        try:
            number = Decimal(value)
            if not number.is_finite() or number != number.to_integral_value():
                raise InvalidOperation
            return str(int(number))
        except (InvalidOperation, ValueError, OverflowError):
            raise HTTPException(503, f"配置 {key} 不是有效整数，请在系统配置中修正") from None
    return value
