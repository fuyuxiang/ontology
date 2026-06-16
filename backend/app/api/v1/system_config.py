"""
系统配置 API — 分组管理平台全局参数（支持多模型配置）
"""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.database import get_db
from app.models.system_config import SystemConfig
from app.models.user import User
from app.schemas.system_config import ConfigResponse, ConfigSaveRequest, TestResult

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
        groups.setdefault(r.group, []).append({
            "key": r.key,
            "value": _mask_value(r.key, r.value),
            "description": r.description,
            "is_sensitive": r.key in SENSITIVE_KEYS,
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
    # 如果 API Key 是脱敏的（以 •••• 开头），保留原值
    row = db.query(SystemConfig).filter(SystemConfig.key == "ai.models").first()
    old_models = []
    if row and row.value:
        try:
            old_models = json.loads(row.value)
        except Exception:
            pass

    old_key_map = {m.get("id"): m.get("api_key", "") for m in old_models}

    for m in models:
        if m.get("api_key", "").startswith("••••"):
            m["api_key"] = old_key_map.get(m.get("id"), "")

    value = json.dumps(models, ensure_ascii=False)
    if row:
        row.value = value
        row.updated_at = datetime.utcnow()
        row.updated_by = user.username
    else:
        db.add(SystemConfig(group="ai", key="ai.models", value=value, description="AI 模型列表", updated_by=user.username))
    db.commit()
    return {"message": "保存成功"}


@router.post("/ai/models/test")
def test_ai_model(data: dict, _user: User = Depends(require_admin)):
    """测试指定模型的连通性"""
    api_key = data.get("api_key", "")
    base_url = data.get("base_url", "https://api.anthropic.com")
    model_id = data.get("model_id", "")

    if not api_key or api_key.startswith("••••"):
        return TestResult(success=False, message="请先填写 API Key")
    if not model_id:
        return TestResult(success=False, message="请先选择模型")

    try:
        import httpx
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{base_url}/v1/models", headers={
                "Authorization": f"Bearer {api_key}",
                "x-api-key": api_key,
            })
            if resp.status_code < 400:
                return TestResult(success=True, message=f"连接成功，模型 {model_id} 可用")
            return TestResult(success=False, message=f"连接失败: HTTP {resp.status_code}")
    except Exception as e:
        return TestResult(success=False, message=f"连接失败: {str(e)}")


@router.get("/scenes")
def get_model_scenes(_user: User = Depends(require_admin)):
    """获取模型使用场景列表"""
    return MODEL_SCENES


@router.put("")
def save_config(data: ConfigSaveRequest, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    """批量保存某组配置"""
    for item in data.items:
        existing = db.query(SystemConfig).filter(SystemConfig.key == item.key).first()
        if existing:
            if item.key in SENSITIVE_KEYS and item.value and item.value.startswith("••••"):
                continue
            existing.value = item.value
            existing.updated_at = datetime.utcnow()
            existing.updated_by = user.username
        else:
            db.add(SystemConfig(
                group=data.group,
                key=item.key,
                value=item.value,
                updated_by=user.username,
            ))
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
            resp = client.get(f"{base_url}/v1/models", headers={
                "Authorization": f"Bearer {api_key}",
                "x-api-key": api_key,
            })
            if resp.status_code < 400:
                return TestResult(success=True, message=f"连接成功，模型 {model} 可用")
            return TestResult(success=False, message=f"连接失败: HTTP {resp.status_code}")
    except Exception as e:
        return TestResult(success=False, message=f"连接失败: {str(e)}")


@router.post("/test-email", response_model=TestResult)
def test_email(data: dict, db: Session = Depends(get_db), _user: User = Depends(require_admin)):
    """测试邮件发送"""
    recipient = data.get("recipient", "")
    if not recipient:
        return TestResult(success=False, message="请提供收件人邮箱")

    host = _get_config_value(db, "notification.smtp_host")
    port = int(_get_config_value(db, "notification.smtp_port") or "465")
    username = _get_config_value(db, "notification.smtp_username")
    password = _get_config_value(db, "notification.smtp_password")

    if not all([host, username, password]):
        return TestResult(success=False, message="邮件服务器配置不完整")

    try:
        import smtplib
        from email.mime.text import MIMEText
        msg = MIMEText("这是一封来自本体管理平台的测试邮件。", "plain", "utf-8")
        msg["Subject"] = "【本体管理平台】邮件测试"
        msg["From"] = username
        msg["To"] = recipient

        with smtplib.SMTP_SSL(host, port, timeout=10) as server:
            server.login(username, password)
            server.sendmail(username, [recipient], msg.as_string())
        return TestResult(success=True, message=f"测试邮件已发送至 {recipient}")
    except Exception as e:
        return TestResult(success=False, message=f"发送失败: {str(e)}")


def _get_config_value(db: Session, key: str) -> str | None:
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    return row.value if row else None
