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
from functools import lru_cache

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
        if not row or not row.value:
            return None

        models = json.loads(row.value)
        if not models:
            return None

        # 1. 先找该场景的默认模型
        for m in models:
            if scene in m.get("scenes", []) and m.get("is_default"):
                if m.get("api_key"):
                    return {"api_key": m["api_key"], "base_url": m.get("base_url", ""), "model": m.get("model_id", "")}

        # 2. 再找该场景的任意模型
        for m in models:
            if scene in m.get("scenes", []) and m.get("api_key"):
                return {"api_key": m["api_key"], "base_url": m.get("base_url", ""), "model": m.get("model_id", "")}

        # 3. 找通用场景的默认模型
        for m in models:
            if "general" in m.get("scenes", []) and m.get("is_default") and m.get("api_key"):
                return {"api_key": m["api_key"], "base_url": m.get("base_url", ""), "model": m.get("model_id", "")}

        # 4. 找任意有 API Key 的模型
        for m in models:
            if m.get("api_key"):
                return {"api_key": m["api_key"], "base_url": m.get("base_url", ""), "model": m.get("model_id", "")}

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
        return _create_client(api_key, api_base)

    # 尝试从数据库解析
    if db:
        model_config = _resolve_model_from_db(db, scene)
        if model_config:
            logger.info(f"使用数据库模型配置 (场景: {scene}): {model_config.get('model', 'unknown')}")
            return _create_client(model_config["api_key"], model_config["base_url"])

    # 回退到环境变量
    fallback = _SCENE_FALLBACKS.get(scene, _SCENE_FALLBACKS["general"])
    logger.info(f"使用环境变量模型配置 (场景: {scene}): {fallback['model']}")
    return _create_client(
        api_key or fallback["api_key"],
        api_base or fallback["base_url"],
    )


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
    client_kwargs = {"api_key": api_key, "base_url": base_url}
    try:
        return OpenAI(**client_kwargs)
    except ImportError as exc:
        if "socksio" not in str(exc).lower():
            raise
        logger.warning("检测到 SOCKS 代理但未安装 socksio，改为忽略代理环境变量直连 LLM。")
        return OpenAI(**client_kwargs, http_client=httpx.Client(trust_env=False))
