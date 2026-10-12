"""
统一 LLM 客户端解析器

优先从 SystemConfig 的 ai.models JSON 中按场景查找模型配置，
回退到 settings.LLM_* 环境变量。

用法：
    from app.services.llm_resolver import get_llm_client
    client = get_llm_client(db, scene="ontology")
"""
import json
import logging
import time

import httpx
from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import settings

logger = logging.getLogger(__name__)

# 场景 → 默认模型配置的映射（用于无 DB 记录时的回退）
_SCENE_FALLBACKS = {
    "ontology": {"api_key": settings.LLM_API_KEY, "base_url": settings.LLM_BASE_URL, "model": settings.LLM_MODEL},
    "agent": {"api_key": settings.LLM_API_KEY, "base_url": settings.LLM_BASE_URL, "model": settings.LLM_MODEL},
    "data": {"api_key": settings.LLM_API_KEY, "base_url": settings.LLM_BASE_URL, "model": settings.LLM_MODEL},
    "general": {"api_key": settings.LLM_API_KEY, "base_url": settings.LLM_BASE_URL, "model": settings.LLM_MODEL},
}


def _resolve_model_from_db(db: Session, scene: str = "general") -> dict | None:
    """从 SystemConfig 的 ai.models JSON 中解析指定场景的模型配置"""
    try:
        from app.models.system_config import SystemConfig
        row = db.query(SystemConfig).filter(SystemConfig.key == "ai.models").first()
        models = json.loads(row.value) if row and row.value else []
        def options(model):
            return {"api_key": model["api_key"], "base_url": model.get("base_url", ""), "model": model.get("model_id", ""),
                    **{key: model[key] for key in ("temperature", "max_tokens", "top_p", "timeout_seconds") if model.get(key) is not None}}

        # 1. 先找该场景的默认模型
        for m in models:
            if scene in m.get("scenes", []) and m.get("is_default"):
                if m.get("api_key"):
                    return options(m)

        # 2. 再找该场景的任意模型
        for m in models:
            if scene in m.get("scenes", []) and m.get("api_key"):
                return options(m)

        # 3. 找通用场景的默认模型
        for m in models:
            if "general" in m.get("scenes", []) and m.get("is_default") and m.get("api_key"):
                return options(m)

        # 4. 找任意有 API Key 的模型
        for m in models:
            if m.get("api_key"):
                return options(m)

        from app.api.v1.system_config import _get_config_value
        api_key = _get_config_value(db, "ai.api_key")
        if api_key:
            resolved = {"api_key": api_key, "base_url": _get_config_value(db, "ai.base_url") or settings.LLM_BASE_URL,
                        "model": _get_config_value(db, "ai.model") or settings.LLM_MODEL}
            for key in ("temperature", "max_tokens", "top_p", "timeout_seconds"):
                value = _get_config_value(db, f"ai.{key}")
                if value is not None:
                    resolved[key] = int(value) if key == "max_tokens" else float(value)
            return resolved

        return None
    except Exception as e:
        logger.warning(f"从数据库解析模型配置失败: {e}")
        return None


def get_llm_client(
    db: Session | None = None,
    scene: str = "general",
    api_key: str | None = None,
    api_base: str | None = None,
) -> OpenAI:
    """
    获取 LLM 客户端

    优先级：
    1. 显式传入的 api_key/api_base
    2. 数据库中该场景的模型配置
    3. 环境变量 settings.LLM_*
    """
    # 如果显式传入了参数，直接使用
    if api_key and api_base:
        return _instrument_client(_create_client(api_key, api_base), db, scene)

    # 尝试从数据库解析
    if db:
        model_config = _resolve_model_from_db(db, scene)
        if model_config:
            logger.info(f"使用数据库模型配置 (场景: {scene}): {model_config.get('model', 'unknown')}")
            client = _create_client(model_config["api_key"], model_config["base_url"])
            if model_config.get("timeout_seconds") is not None:
                client = client.with_options(timeout=float(model_config["timeout_seconds"]))
            options = {key: model_config[key] for key in ("temperature", "max_tokens", "top_p") if key in model_config}
            if options:
                original_create = client.chat.completions.create
                def configured_create(*args, **kwargs):
                    kwargs.update(options)
                    return original_create(*args, **kwargs)
                client.chat.completions.create = configured_create
            return _instrument_client(client, db, scene)

    # 回退到环境变量
    fallback = _SCENE_FALLBACKS.get(scene, _SCENE_FALLBACKS["general"])
    logger.info(f"使用环境变量模型配置 (场景: {scene}): {fallback['model']}")
    return _instrument_client(_create_client(
        api_key or fallback["api_key"],
        api_base or fallback["base_url"],
    ), db, scene)


def _instrument_client(client, db, scene):
    """Record actual completions without committing the caller's transaction.

    A stream is successful only after a provider finish_reason. Cancellation,
    transport errors and EOF without that terminal marker count as failures.
    No prompts, credentials or response text are retained.
    """
    from sqlalchemy import event
    from sqlalchemy.orm import sessionmaker
    from app.database import SessionLocal
    from app.repositories.monitor_repo import MonitorRepository
    factory = sessionmaker(bind=db.get_bind()) if isinstance(db, Session) else SessionLocal
    original = client.chat.completions.create

    def persist(values):
        try:
            with factory() as metrics_db:
                MonitorRepository(metrics_db).save_llm_call(**values)
        except Exception:
            logger.exception("LLM 调用统计持久化失败")

    def persist_or_defer(values):
        # SQLite permits one writer. AI conversations can already hold a write
        # transaction, so flush metrics after its outer commit OR rollback.
        if isinstance(db, Session) and db.get_bind().dialect.name == "sqlite" and db.in_transaction():
            db.info.setdefault("llm_metrics_pending", []).append(values)
            if not db.info.get("llm_metrics_listener"):
                db.info["llm_metrics_listener"] = True
                def after_transaction(session, transaction):
                    if transaction.parent is None:
                        for item in session.info.pop("llm_metrics_pending", []):
                            persist(item)
                event.listen(db, "after_transaction_end", after_transaction)
        else:
            persist(values)

    def create(*args, **kwargs):
        started = time.monotonic()
        model = kwargs.get("model")
        def record(success, usage=None):
            persist_or_defer(dict(caller_module=scene, model_name=model,
                prompt_tokens=getattr(usage, "prompt_tokens", None),
                completion_tokens=getattr(usage, "completion_tokens", None),
                latency_ms=(time.monotonic() - started) * 1000, success=success))
        try:
            result = original(*args, **kwargs)
        except BaseException:
            record(False)
            raise
        if not kwargs.get("stream"):
            choices = getattr(result, "choices", [])
            success = bool(choices) and all(getattr(c, "finish_reason", None) in {"stop", "tool_calls", "function_call"} for c in choices)
            record(success, getattr(result, "usage", None))
            if not success:
                raise ValueError("模型输出未完整结束，请调整参数或重试")
            return result
        def tracked_stream():
            terminal, completed, usage = False, False, None
            try:
                for chunk in result:
                    usage = getattr(chunk, "usage", None) or usage
                    for choice in getattr(chunk, "choices", []):
                        reason = getattr(choice, "finish_reason", None)
                        if reason is not None:
                            terminal = reason in {"stop", "tool_calls", "function_call"}
                    yield chunk
                completed = True
                if not terminal:
                    raise ValueError("模型流输出未完整结束，请重试")
            finally:
                try:
                    close = getattr(result, "close", None)
                    if close:
                        close()
                finally:
                    record(completed and terminal, usage)
        return tracked_stream()
    client.chat.completions.create = create
    return client


def get_model_name(db: Session | None = None, scene: str = "general") -> str:
    """获取指定场景的模型名称（用于 API 调用的 model 参数）"""
    if db:
        model_config = _resolve_model_from_db(db, scene)
        if model_config and model_config.get("model"):
            return model_config["model"]

    fallback = _SCENE_FALLBACKS.get(scene, _SCENE_FALLBACKS["general"])
    return fallback["model"]


def _create_client(api_key: str, base_url: str) -> OpenAI:
    """创建 OpenAI 客户端，处理代理兼容性"""
    from urllib.parse import urlsplit
    parsed = urlsplit(base_url)
    if parsed.hostname in {"api.anthropic.com", "api.openai.com"} and parsed.path in ("", "/"):
        base_url = base_url.rstrip("/") + "/v1"
    client_kwargs = {"api_key": api_key, "base_url": base_url}
    try:
        return OpenAI(**client_kwargs)
    except ImportError as exc:
        if "socksio" not in str(exc).lower():
            raise
        logger.warning("检测到 SOCKS 代理但未安装 socksio，改为忽略代理环境变量直连 LLM。")
        return OpenAI(**client_kwargs, http_client=httpx.Client(trust_env=False))
