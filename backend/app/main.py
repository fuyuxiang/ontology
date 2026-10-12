import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.actions import router as actions_router
from app.api.v1.agents import open_router as agents_open_router
from app.api.v1.agents import router as agents_router
from app.api.v1.ai_builder_v2 import router as ai_builder_v2_router
from app.api.v1.ai_code import router as ai_code_router
from app.api.v1.ai_ontology import router as ai_ontology_router
from app.api.v1.auth import router as auth_router
from app.api.v1.auth import seed_admin
from app.api.v1.builder import router as builder_router
from app.api.v1.business_documents import router as business_documents_router
from app.api.v1.copilot import router as copilot_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.data_plane.assets import router as dp_assets_router
from app.api.v1.data_plane.audit import router as dp_audit_router
from app.api.v1.data_plane.compat import install as install_compat_middleware
from app.api.v1.data_plane.connections import router as dp_connections_router
from app.api.v1.data_plane.events import router as dp_events_router
from app.api.v1.data_plane.execute import router as dp_execute_router
from app.api.v1.data_plane.lineage import router as dp_lineage_router
from app.api.v1.data_plane.mapping import router as dp_mapping_router
from app.api.v1.data_plane.object_bindings import router as dp_bindings_router
from app.api.v1.data_plane.probes import router as dp_probes_router
from app.api.v1.data_plane.quality import router as dp_quality_router
from app.api.v1.doc_builder import router as doc_builder_router
from app.api.v1.entities import router as entities_router
from app.api.v1.evals import router as evals_router
from app.api.v1.functions import router as functions_router
from app.api.v1.governance import router as governance_router
from app.api.v1.impact_analysis import router as impact_analysis_router
from app.api.v1.mcp import router as mcp_router
from app.api.v1.mcp_stats import router as mcp_stats_router
from app.api.v1.models import router as models_router
from app.api.v1.monitor import router as monitor_router
from app.api.v1.ontology_api import router as ontology_api_router
from app.api.v1.ontology_mapping import router as ontology_mapping_router
from app.api.v1.ontology_publish import router as ontology_publish_router
from app.api.v1.ontology_workspace import router as ontology_workspace_router
from app.api.v1.osdk import router as osdk_router
from app.api.v1.prompt_templates import router as prompt_templates_router
from app.api.v1.registry import router as registry_router
from app.api.v1.relations import router as relations_router
from app.api.v1.resolution import router as resolution_router
from app.api.v1.scenarios import router as scenarios_router
from app.api.v1.shared_attributes import router as shared_attrs_router
from app.api.v1.shared_refs import router as shared_refs_router
from app.api.v1.skills import router as skills_router
from app.api.v1.system_config import router as system_config_router
from app.api.v1.sso import router as sso_router
from app.api.v1.traces import router as traces_router
from app.config import settings
from app.core.permissions import require_platform_access
from app.database import Base, SessionLocal, engine
from app.db_compat import ensure_legacy_schema_compat
from app.models import *  # noqa: F401,F403 — 确保所有模型注册
from app.models.system_config import SystemConfig
from app.services.mcp_tools import (  # noqa: F401  — 触发工具注册
    data_query,
    metadata,  # noqa: F401
    orm_export_logic,
    python_workspace,
)
from app.services.skill_test_runner import run_skill_case

logger = logging.getLogger(__name__)


def _seed_system_config(db):
    """初始化默认系统配置项（幂等：已存在则跳过）"""
    defaults = [
        # basic
        ("basic", "system_name", "本体管理平台", "系统名称"),
        ("basic", "language", "zh-CN", "界面语言"),
        ("basic", "timezone", "Asia/Shanghai", "系统时区"),
        # auth
        ("auth", "password_min_length", "8", "密码最小长度"),
        ("auth", "password_complexity", "upper,lower,digit", "密码复杂度要求"),
        ("auth", "session_timeout", "30", "会话超时（分钟）"),
        ("auth", "sso_enabled", "false", "是否启用 SSO"),
        ("auth", "sso_provider", "oidc", "SSO 提供商（oidc/saml/ldap）"),
        ("auth", "client_id", "", "SSO Client ID"),
        ("auth", "client_secret", "", "SSO Client Secret"),
        ("auth", "issuer_url", "", "OIDC Issuer URL"),
        ("auth", "redirect_uri", "", "OIDC 回调完整地址 /api/v1/auth/sso/callback"),
        # storage
        ("storage", "backend", "local", "存储后端（local/minio/oss）"),
        ("storage", "local_path", "./uploads", "本地文件存储路径"),
        ("storage", "max_upload_mb", "50", "最大上传大小（MB）"),
        ("storage", "allowed_types", ".owl,.rdf,.ttl,.csv,.xlsx,.xls,.json,.docx,.doc,.pptx,.ppt,.pdf,.txt,.md", "允许的文件类型"),
        ("storage", "endpoint", "", "MinIO/OSS 服务地址"),
        ("storage", "bucket", "", "MinIO/OSS 存储桶"),
        ("storage", "access_key", "", "MinIO/OSS Access Key"),
        ("storage", "secret_key", "", "MinIO/OSS Secret Key"),
        # ai
        ("ai", "model", "claude-sonnet-4-20250514", "LLM 模型"),
        ("ai", "api_key", "", "API Key"),
        ("ai", "api_secret", "", "API Secret（部分模型需要）"),
        ("ai", "base_url", "https://api.anthropic.com", "API Base URL"),
        ("ai", "temperature", "0.7", "Temperature（0.0-2.0）"),
        ("ai", "max_tokens", "4096", "最大 Token 数"),
        ("ai", "top_p", "1.0", "Top P 采样"),
        ("ai", "timeout_seconds", "60", "请求超时（秒）"),
        # notification
        ("notification", "smtp_host", "", "SMTP 服务器地址"),
        ("notification", "smtp_port", "465", "SMTP 端口"),
        ("notification", "smtp_encryption", "ssl", "加密方式（ssl/tls/none）"),
        ("notification", "smtp_username", "", "SMTP 用户名"),
        ("notification", "smtp_password", "", "SMTP 密码"),
        ("notification", "smtp_from_name", "本体管理平台", "发件人名称"),
        ("notification", "webhook_url", "", "Webhook URL"),
        ("notification", "webhook_secret", "", "Webhook 签名密钥"),
    ]
    existing = {r.key for r in db.query(SystemConfig.key).all()}
    added = 0
    for group, key, value, desc in defaults:
        if key not in existing:
            db.add(SystemConfig(group=group, key=key, value=value, description=desc))
            added += 1

    if added:
        db.commit()
        logger.info(f"系统配置初始化完成：新增 {added} 项")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.startup_components = {"database": False, "migrations": False, "events": False, "function_runtime": False, "monitor": False}
    # 启动：建表 + schema 迁移
    Base.metadata.create_all(bind=engine)
    ensure_legacy_schema_compat(engine)

    from app.migrations import run_startup_migrations
    run_startup_migrations(engine)
    app.state.startup_components.update(database=True, migrations=True)

    db = SessionLocal()
    try:
        seed_admin(db)
        _seed_system_config(db)
        from app.services.agent_recovery import recover_interrupted_runs
        recover_interrupted_runs(db)
        from app.models.action_execution import recover_interrupted_actions
        recover_interrupted_actions(db)
    finally:
        db.close()

    # Neo4j 初始化暂时跳过（需要修复 numpy/pandas 版本冲突后启用）
    # 基础功能（实体CRUD、规则、看板）不依赖 Neo4j
    logger.info("服务启动完成（Neo4j 待配置）")

    # 注册 Data Plane 跨模块事件 handler
    try:
        from app.services.data_plane.event_handlers import register_event_handlers
        register_event_handlers()
        app.state.startup_components["events"] = True
        logger.info("Data Plane 事件 handler 已注册")
    except Exception as e:
        raise RuntimeError("Data Plane 事件 handler 初始化失败") from e

    from app.services.data_plane.refresh_service import start_refresher, stop_refresher
    app.state.startup_components["data_refresh"] = await start_refresher(db_factory=SessionLocal)

    # 启动监控采集器
    try:
        from app.services.monitor.collector import start_collector
        await start_collector()
        app.state.startup_components["monitor"] = settings.MONITOR_ENABLED
        logger.info("监控采集器已启动")
    except Exception as e:
        await stop_refresher()
        raise RuntimeError("监控采集器初始化失败") from e

    # Function Runtime 初始化
    _function_watcher = None
    rt_db = None
    try:
        from pathlib import Path

        from app.services.function_runtime.executor import FunctionRuntimeExecutor
        from app.services.function_runtime.registry import FunctionRegistry
        from app.services.function_runtime.sandbox import UnifiedSandbox
        from app.services.function_runtime.watcher import FunctionWatcher

        workspace_root = str(Path(settings.WORKSPACE_ROOT).resolve())
        Path(workspace_root).mkdir(parents=True, exist_ok=True)
        rt_db = SessionLocal()
        registry = FunctionRegistry(rt_db)
        registry.sync_from_db()
        sandbox = UnifiedSandbox()
        runtime_executor = FunctionRuntimeExecutor(registry=registry, sandbox=sandbox, db=rt_db, session_factory=SessionLocal)
        _function_watcher = FunctionWatcher(registry=registry, workspace_root=workspace_root)
        _function_watcher.scan_all()
        _function_watcher.start()
        app.state.runtime_executor = runtime_executor
        app.state.function_registry = registry
        app.state.startup_components["function_runtime"] = True
        logger.info(f"Function Runtime 初始化完成，workspace={workspace_root}")
    except Exception as e:
        if rt_db:
            rt_db.close()
        from app.services.monitor.collector import stop_collector
        await stop_collector()
        await stop_refresher()
        raise RuntimeError("Function Runtime 初始化失败") from e

    yield

    # Shutdown: stop function watcher
    if _function_watcher:
        _function_watcher.stop()
    if rt_db:
        rt_db.close()
    from app.services.monitor.collector import stop_collector
    await stop_collector()
    await stop_refresher()


app = FastAPI(
    title="本体驱动智能策略平台 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.skill_test_runner = run_skill_case

_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()] if settings.CORS_ORIGINS else ["http://localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data Plane 兼容层：给 deprecated 路由添加 Deprecation / Sunset / Link 响应头
install_compat_middleware(app)

app.include_router(entities_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(dashboard_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(copilot_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(relations_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(auth_router, prefix="/api/v1")
app.include_router(sso_router, prefix="/api/v1")
# app.include_router(datasources_router, prefix="/api/v1")  # 已废弃
app.include_router(scenarios_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(models_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(agents_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(agents_open_router, prefix="/api/v1")
app.include_router(skills_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(resolution_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(governance_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(impact_analysis_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(prompt_templates_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(ai_ontology_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(ontology_api_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(osdk_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(ontology_publish_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(ontology_workspace_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(traces_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(evals_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(actions_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(functions_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(monitor_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(builder_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(business_documents_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(shared_refs_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(shared_attrs_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])

# ── Data Plane router 挂载 ──
app.include_router(dp_connections_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(dp_assets_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(dp_execute_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(dp_probes_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(dp_lineage_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(dp_events_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(dp_audit_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(dp_bindings_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(dp_quality_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(dp_mapping_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(ai_builder_v2_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(doc_builder_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(ontology_mapping_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(registry_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(system_config_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])
app.include_router(ai_code_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])

# ── MCP 端点 ──
app.include_router(mcp_router, prefix="/api/v1")
app.include_router(mcp_stats_router, prefix="/api/v1", dependencies=[Depends(require_platform_access)])


@app.get("/api/health")
def health():
    components = getattr(app.state, "startup_components", {})
    required = ["database", "migrations", "events", "function_runtime"]
    if settings.MONITOR_ENABLED:
        required.append("monitor")
    if settings.DATA_PLANE_REFRESH_ENABLED:
        required.append("data_refresh")
    if not all(components.get(key) for key in required):
        raise HTTPException(503, detail={"status": "starting_or_failed", "components": components})
    return {"status": "ok", "components": components}
