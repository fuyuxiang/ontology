from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, SessionLocal
from app.models import *  # noqa: F401,F403 — 确保所有模型注册
from app.database import Base
from app.api.v1.entities import router as entities_router
from app.api.v1.auth import router as auth_router, seed_admin
from app.models.agent import Agent
from app.models.skill import Skill


def _seed_agents(db):
    if db.query(Agent).count() > 0:
        return
    import uuid, secrets
    from datetime import datetime
    presets = [
        {
            "name": "宽带退单稽核智能体",
            "description": "基于本体知识图谱，自动分析宽带退单原因，归因工程师责任，结合语音质检和规则引擎输出稽核结论",
            "tags": ["宽带", "退单", "稽核", "归因"],
            "system_prompt": "你是一名宽带退单稽核专家，基于本体知识图谱和业务规则，对宽带退单工单进行智能归因分析。请结合客户信息、工程师信息、工单记录和语音质检结果，给出准确的退单原因归因和责任判定。",
        },
        {
            "name": "携号转网预警智能体",
            "description": "实时监控高风险携号转网用户，结合用户行为、套餐偏好和竞品信息，输出预警等级和挽留策略建议",
            "tags": ["携号转网", "预警", "挽留"],
            "system_prompt": "你是一名携号转网预警分析专家，基于用户本体数据和行为特征，识别高风险用户并给出针对性的挽留策略。请综合分析用户的套餐使用情况、投诉记录、竞品偏好等多维度信息。",
        },
        {
            "name": "政企根因分析智能体",
            "description": "针对政企客户网络故障和服务投诉，基于本体关系图谱进行多维根因分析，快速定位问题根源",
            "tags": ["政企", "根因分析", "故障"],
            "system_prompt": "你是一名政企客户服务根因分析专家，基于网络拓扑本体和故障知识库，对政企客户的网络故障和服务问题进行深度根因分析。请给出清晰的故障链路和解决方案。",
        },
        {
            "name": "FTTR续约策划智能体",
            "description": "分析FTTR客户到期情况和使用行为，结合本体知识生成个性化续约方案和营销话术",
            "tags": ["FTTR", "续约", "营销"],
            "system_prompt": "你是一名FTTR业务续约策划专家，基于客户本体数据和历史使用记录，为即将到期的FTTR客户制定个性化续约方案。请结合客户价值、使用习惯和套餐偏好，给出最优续约建议和营销话术。",
        },
    ]
    for p in presets:
        a = Agent(
            id=str(uuid.uuid4()),
            name=p["name"],
            description=p["description"],
            tags=p["tags"],
            system_prompt=p["system_prompt"],
            kb_ids=[], entity_ids=[],
            tools_config={"temperature": 0.4, "max_tokens": 2048},
            status="published",
            api_key=secrets.token_urlsafe(32),
        )
        db.add(a)
    db.commit()


def _seed_skills(db):
    if db.query(Skill).count() > 0:
        return
    from app.utils.identifiers import gen_uuid
    presets = [
        {
            "name": "携号转网风险评估",
            "description": "基于本体实体和业务规则，对用户进行携号转网风险评估，输出风险等级、根因分析和挽留策略建议",
            "skill_type": "builtin",
            "code_ref": "mnp_risk_evaluate",
            "config_json": {
                "params": [
                    {"name": "user_id", "type": "string", "required": True, "description": "用户标识"}
                ]
            },
        },
        {
            "name": "宽带退单稽核",
            "description": "基于退单工单数据和稽核规则，自动分析退单根因，输出归因判定和稽核结论",
            "skill_type": "builtin",
            "code_ref": "broadband_audit",
            "config_json": {
                "params": [
                    {"name": "churn_id", "type": "string", "required": True, "description": "退单工单ID"}
                ]
            },
        },
    ]
    for p in presets:
        s = Skill(id=gen_uuid(), **p, status="active")
        db.add(s)
    db.commit()


def _seed_aip_scenes(db):
    """从 backend/app/data/aip_scenes_seed.json 把内置场景导入数据库（仅当表空时）。"""
    from app.models.scene import AipScene, AipSceneTrigger
    if db.query(AipScene).count() > 0:
        return
    import json as _json
    import os as _os
    from app.utils.identifiers import gen_uuid as _gen
    seed_path = _os.path.join(_os.path.dirname(__file__), "data", "aip_scenes_seed.json")
    if not _os.path.exists(seed_path):
        return
    try:
        with open(seed_path, "r", encoding="utf-8") as f:
            data = _json.load(f)
    except Exception:
        return

    meta_map = {
        "fttr_renewal": {
            "name": "包头 FTTR 或组网到期续约",
            "group": "FTTR续约策划",
            "description": "FTTR 到期客户续约智能策划 v1.3：⓪ 本体查询 → ① 客群洞察 → ② 产品推荐 → ③ 触点选择 → ④ 八段式话术 → ⑤ 续约策略执行包",
            "ontology_bindings": ["Customer", "Segment", "Contract", "FTTRSubscription", "Product", "Strategy", "Script", "Channel", "TouchEvent", "WorkOrder", "RenewalStrategyPackage", "Order"],
            "stats": {"users": 40929, "conversion": "4.64%", "strategies": 7},
            "trigger": {"type": "schedule", "enabled": False, "schedule": {"frequency": "daily", "hour": 8, "minute": 0, "timezone": "Asia/Shanghai"}},
        },
        "refund_attribution": {
            "name": "宽带装机退单智能归因",
            "group": "退单智能归因",
            "description": "基于装机工单和 4 类外呼通话记录，37 条证据抽取配合分层归因推理，识别资源 / 施工 / 用户 / 业务四类根因，驱动自动归档 / 现场核实 / 强制回访 / 营销外呼 4 条动作闭环",
            "ontology_bindings": ["InstallOrder", "InstallChurn", "Customer", "Product", "Channel", "DispatchRecord", "Engineer", "Address", "PendingPool", "EngineerCall", "CallbackCall", "MarketingCall", "CompetitorCall"],
            "stats": {"orders": 8536, "accuracy": "90%+", "functions": 37, "reasons": 23},
            "trigger": {"type": "schedule", "enabled": False, "schedule": {"frequency": "daily", "hour": 10, "minute": 0, "timezone": "Asia/Shanghai"}},
        },
        "ge_insight_qa": {
            "name": "政企智能问数及归因分析",
            "group": "政企智能问数",
            "description": "4 节点流水线：本体语义理解 → 政企数据分析 Agent → 政企归因推理 Agent → 业务规则分支 → 5 个动作执行",
            "ontology_bindings": ["KPIIndicatorDef", "GeCustomerSegment", "GeProject", "GeOpportunity", "Contract", "GeProductService", "GeAccountManager", "GeBusinessEvent", "GeRegionOrg"],
            "stats": {"queries": 1247, "branches": 5, "actions": 5},
            "trigger": {"type": "schedule", "enabled": False, "schedule": {"frequency": "daily", "hour": 9, "minute": 0, "timezone": "Asia/Shanghai"}},
        },
    }

    for slug, payload in data.items():
        meta = meta_map.get(slug, {
            "name": slug, "group": "自定义", "description": "",
            "ontology_bindings": [], "stats": {}, "trigger": {"type": "manual", "enabled": False},
        })
        s = AipScene(
            id=_gen(),
            name=meta["name"],
            description=meta["description"],
            group_name=meta["group"],
            nodes_json=payload.get("nodes", []),
            edges_json=payload.get("edges", []),
            ontology_bindings=meta.get("ontology_bindings", []),
            datasource_bindings=[],
            stats_json=meta.get("stats", {}),
            trigger_config=meta.get("trigger", {}),
            status="published",
            version=1,
        )
        db.add(s)
        db.flush()
        # 若有 schedule 配置，写入触发器表（默认 disabled，避免误触发）
        cfg = meta.get("trigger", {}) or {}
        if cfg.get("type"):
            trg = AipSceneTrigger(
                id=_gen(),
                scene_id=s.id,
                type=cfg.get("type", "manual"),
                enabled=False,
                schedule_payload=cfg.get("schedule") or {},
                cron_expr=_seed_cron(cfg.get("schedule") or {}),
                timezone=(cfg.get("schedule") or {}).get("timezone") or "Asia/Shanghai",
            )
            db.add(trg)
    db.commit()


def _seed_cron(schedule: dict) -> str:
    if not schedule:
        return ""
    freq = schedule.get("frequency", "daily")
    h = int(schedule.get("hour", 9))
    m = int(schedule.get("minute", 0))
    if freq == "daily":
        return f"{m} {h} * * *"
    if freq == "weekly":
        return f"{m} {h} * * 1"
    if freq == "monthly":
        return f"{m} {h} 1 * *"
    return schedule.get("cron", f"{m} {h} * * *")

from app.api.v1.rules import router as rules_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.copilot import router as copilot_router
from app.api.v1.relations import router as relations_router
from app.api.v1.datasources import router as datasources_router
from app.api.v1.mnp import router as mnp_router
from app.api.v1.scenes import router as scenes_router
from app.api.v1.broadband import router as broadband_router
from app.api.v1.models import router as models_router
from app.api.v1.agents import router as agents_router, open_router as agents_open_router
from app.api.v1.skills import router as skills_router
from app.api.v1.skill_gen import router as skill_gen_router
from app.api.v1.resolution import router as resolution_router
from app.api.v1.governance import router as governance_router
from app.api.v1.prompt_templates import router as prompt_templates_router
from app.api.v1.ai_ontology import router as ai_ontology_router
from app.api.v1.builder import router as builder_router
from app.api.v1.business_documents import router as business_documents_router
from app.api.v1.ontology_api import router as ontology_api_router
from app.api.v1.osdk import router as osdk_router
from app.api.v1.ontology_publish import router as ontology_publish_router
from app.api.v1.traces import router as traces_router
from app.api.v1.evals import router as evals_router
from app.api.v1.actions import router as actions_router
from app.api.v1.functions import router as functions_router
from app.api.v1.monitor import router as monitor_router
from app.api.v1.studio import router as studio_router
from app.api.v1.pipelines import router as pipelines_router, start_worker as start_pipeline_worker
from app.api.v1.aip_scenes import router as aip_scenes_router
from app.api.v1.aip_executions import router as aip_executions_router
from app.api.v1.ai_builder_v2 import router as ai_builder_v2_router
from app.api.v1.aip_webhooks import router as aip_webhooks_router
from app.api.v1.doc_builder import router as doc_builder_router
from app.api.v1.ontology_mapping import router as ontology_mapping_router

# ── Data Plane（M1 新增 7 个 router）──
from app.api.v1.data_plane.connections import router as dp_connections_router
from app.api.v1.data_plane.assets import router as dp_assets_router
from app.api.v1.data_plane.execute import router as dp_execute_router
from app.api.v1.data_plane.probes import router as dp_probes_router
from app.api.v1.data_plane.lineage import router as dp_lineage_router
from app.api.v1.data_plane.events import router as dp_events_router
from app.api.v1.data_plane.audit import router as dp_audit_router
from app.api.v1.data_plane.object_bindings import router as dp_bindings_router
from app.api.v1.data_plane.quality import router as dp_quality_router
from app.api.v1.data_plane.mapping import router as dp_mapping_router
from app.api.v1.data_plane.compat import install as install_compat_middleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：建表 + 初始化管理员
    Base.metadata.create_all(bind=engine)

    # SQLite 迁移：datasources 表增加 table_name / record_count 列
    with engine.connect() as conn:
        from sqlalchemy import text, inspect as sa_inspect
        inspector = sa_inspect(engine)
        if "datasources" in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns("datasources")}
            if "table_name" not in cols:
                conn.execute(text("ALTER TABLE datasources ADD COLUMN table_name VARCHAR(200) DEFAULT ''"))
            if "record_count" not in cols:
                conn.execute(text("ALTER TABLE datasources ADD COLUMN record_count INTEGER DEFAULT 0"))
                if "table_count" in cols:
                    conn.execute(text("UPDATE datasources SET record_count = table_count"))
            # 旧 table_count 列有 NOT NULL 约束，需保留默认值以兼容
            if "table_count" in cols:
                try:
                    conn.execute(text("UPDATE datasources SET table_count = 0 WHERE table_count IS NULL"))
                except Exception:
                    pass
            if "enabled" not in cols:
                conn.execute(text("ALTER TABLE datasources ADD COLUMN enabled TINYINT(1) DEFAULT 0"))
            if "source_category" not in cols:
                conn.execute(text("ALTER TABLE datasources ADD COLUMN source_category VARCHAR(20) DEFAULT 'database'"))
            if "file_path" not in cols:
                conn.execute(text("ALTER TABLE datasources ADD COLUMN file_path VARCHAR(500)"))
            if "file_type" not in cols:
                conn.execute(text("ALTER TABLE datasources ADD COLUMN file_type VARCHAR(20)"))
            if "api_url" not in cols:
                conn.execute(text("ALTER TABLE datasources ADD COLUMN api_url VARCHAR(500)"))
            if "api_method" not in cols:
                conn.execute(text("ALTER TABLE datasources ADD COLUMN api_method VARCHAR(10) DEFAULT 'GET'"))
            if "api_headers" not in cols:
                conn.execute(text("ALTER TABLE datasources ADD COLUMN api_headers JSON"))
            if "api_body" not in cols:
                conn.execute(text("ALTER TABLE datasources ADD COLUMN api_body TEXT"))
            if "mq_topic" not in cols:
                conn.execute(text("ALTER TABLE datasources ADD COLUMN mq_topic VARCHAR(200)"))
            if "mq_group" not in cols:
                conn.execute(text("ALTER TABLE datasources ADD COLUMN mq_group VARCHAR(200)"))
            if "poll_interval" not in cols:
                conn.execute(text("ALTER TABLE datasources ADD COLUMN poll_interval INTEGER DEFAULT 60"))
            if "parsed_content" not in cols:
                conn.execute(text("ALTER TABLE datasources ADD COLUMN parsed_content TEXT"))
            conn.commit()

        # business_rules 表增加结构化列
        if "business_rules" in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns("business_rules")}
            if "conditions_json" not in cols:
                conn.execute(text("ALTER TABLE business_rules ADD COLUMN conditions_json JSON"))
            if "rule_meta_json" not in cols:
                conn.execute(text("ALTER TABLE business_rules ADD COLUMN rule_meta_json JSON"))
            conn.commit()

        # entity_actions 表增加结构化列
        if "entity_actions" in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns("entity_actions")}
            for col in ("parameters_json", "preconditions_json", "effects_json", "action_meta_json"):
                if col not in cols:
                    conn.execute(text(f"ALTER TABLE entity_actions ADD COLUMN {col} JSON"))
            conn.commit()

        # entity_attributes 表增加映射字段
        if "entity_attributes" in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns("entity_attributes")}
            if "source_table" not in cols:
                conn.execute(text("ALTER TABLE entity_attributes ADD COLUMN source_table VARCHAR(200)"))
            if "source_field" not in cols:
                conn.execute(text("ALTER TABLE entity_attributes ADD COLUMN source_field VARCHAR(200)"))
            if "data_status" not in cols:
                conn.execute(text("ALTER TABLE entity_attributes ADD COLUMN data_status VARCHAR(20) DEFAULT '未确认来源'"))
            conn.commit()

        # agents 表增加 nodes_json / edges_json 列
        if "agents" in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns("agents")}
            if "nodes_json" not in cols:
                conn.execute(text("ALTER TABLE agents ADD COLUMN nodes_json JSON"))
            if "edges_json" not in cols:
                conn.execute(text("ALTER TABLE agents ADD COLUMN edges_json JSON"))
            if "ontology_version_id" not in cols:
                conn.execute(text("ALTER TABLE agents ADD COLUMN ontology_version_id VARCHAR(36)"))
            if "ontology_stale" not in cols:
                conn.execute(text("ALTER TABLE agents ADD COLUMN ontology_stale TINYINT(1) NOT NULL DEFAULT 0"))
            if "ontology_stale_detail" not in cols:
                conn.execute(text("ALTER TABLE agents ADD COLUMN ontology_stale_detail JSON"))
            conn.commit()

        # aip_scenes 表增加 ontology_stale 相关列
        if "aip_scenes" in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns("aip_scenes")}
            if "ontology_version_id" not in cols:
                conn.execute(text("ALTER TABLE aip_scenes ADD COLUMN ontology_version_id VARCHAR(36)"))
            if "ontology_stale" not in cols:
                conn.execute(text("ALTER TABLE aip_scenes ADD COLUMN ontology_stale TINYINT(1) NOT NULL DEFAULT 0"))
            if "ontology_stale_detail" not in cols:
                conn.execute(text("ALTER TABLE aip_scenes ADD COLUMN ontology_stale_detail JSON"))
            conn.commit()

        # audit_log 表补充 details / status 列
        if "audit_log" in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns("audit_log")}
            if "details" not in cols:
                conn.execute(text("ALTER TABLE audit_log ADD COLUMN details TEXT"))
            if "status" not in cols:
                conn.execute(text("ALTER TABLE audit_log ADD COLUMN status VARCHAR(16) DEFAULT 'success'"))
            conn.commit()

        # skills 表增加技能平台扩展列
        if "skills" in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns("skills")}
            if "current_version" not in cols:
                conn.execute(text("ALTER TABLE skills ADD COLUMN current_version INTEGER DEFAULT 0"))
            if "input_schema" not in cols:
                conn.execute(text("ALTER TABLE skills ADD COLUMN input_schema JSON"))
            if "output_schema" not in cols:
                conn.execute(text("ALTER TABLE skills ADD COLUMN output_schema JSON"))
            if "prompt_template" not in cols:
                conn.execute(text("ALTER TABLE skills ADD COLUMN prompt_template TEXT"))
            if "tools" not in cols:
                conn.execute(text("ALTER TABLE skills ADD COLUMN tools JSON"))
            if "test_cases" not in cols:
                conn.execute(text("ALTER TABLE skills ADD COLUMN test_cases JSON"))
            if "asset_refs" not in cols:
                conn.execute(text("ALTER TABLE skills ADD COLUMN asset_refs JSON"))
            if "created_by" not in cols:
                conn.execute(text("ALTER TABLE skills ADD COLUMN created_by VARCHAR(100) DEFAULT ''"))
            if "reviewed_by" not in cols:
                conn.execute(text("ALTER TABLE skills ADD COLUMN reviewed_by VARCHAR(100) DEFAULT ''"))
            conn.commit()

        # ontology_entities 表增加 publish_config 列
        if "ontology_entities" in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns("ontology_entities")}
            if "publish_config" not in cols:
                conn.execute(text("ALTER TABLE ontology_entities ADD COLUMN publish_config JSON"))
            conn.commit()

    db = SessionLocal()
    try:
        seed_admin(db)
        _seed_agents(db)
        _seed_skills(db)
        _seed_aip_scenes(db)
    finally:
        db.close()

    # Neo4j 初始化暂时跳过（需要修复 numpy/pandas 版本冲突后启用）
    # 基础功能（实体CRUD、规则、看板）不依赖 Neo4j
    logger.info("服务启动完成（Neo4j 待配置）")

    # 启动 AIP 调度器（schedule 触发器轮询）
    try:
        from app.services.aip.scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        logger.warning(f"AIP 调度器启动失败: {e}")

    # 注册 Data Plane 跨模块事件 handler
    try:
        from app.services.data_plane.event_handlers import register_event_handlers
        register_event_handlers()
        logger.info("Data Plane 事件 handler 已注册")
    except Exception as e:
        logger.warning(f"Data Plane 事件 handler 注册失败: {e}")

    # 注册业务侧 sql_view Asset（mnp / scenes / broadband）
    try:
        from scripts.seed_business_assets import seed as seed_business_assets
        bs_stats = seed_business_assets()
        logger.info(f"业务资产 seed 完成: {bs_stats}")
    except Exception as e:
        logger.warning(f"业务资产 seed 失败: {e}")

    # 预热携号转网案例用户缓存（后台执行，不阻塞启动）
    import asyncio

    def _preheat_sync():
        try:
            from app.api.v1.scenes import list_mnp_case_users, execute_mnp_flow
            db = SessionLocal()
            try:
                case_users = list_mnp_case_users(db)
                logger.info(f"预热案例用户缓存完成，共 {len(case_users)} 个用户")
                for u in case_users:
                    try:
                        execute_mnp_flow(user_id=u.user_id, db=db)
                    except Exception:
                        pass
                logger.info("预热案例用户执行数据缓存完成")
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"预热案例用户缓存失败: {e}")

    asyncio.create_task(asyncio.to_thread(_preheat_sync))

    start_pipeline_worker()

    # 启动监控采集器
    try:
        from app.services.monitor.collector import start_collector
        await start_collector()
        logger.info("监控采集器已启动")
    except Exception as e:
        logger.warning(f"监控采集器启动失败: {e}")

    yield


app = FastAPI(
    title="本体驱动智能策略平台 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data Plane 兼容层：给 deprecated 路由添加 Deprecation / Sunset / Link 响应头
install_compat_middleware(app)

app.include_router(entities_router, prefix="/api/v1")
app.include_router(rules_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(copilot_router, prefix="/api/v1")
app.include_router(relations_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(datasources_router, prefix="/api/v1")
app.include_router(mnp_router, prefix="/api/v1")
app.include_router(scenes_router, prefix="/api/v1")
app.include_router(broadband_router, prefix="/api/v1")
app.include_router(models_router, prefix="/api/v1")
app.include_router(agents_router, prefix="/api/v1")
app.include_router(agents_open_router, prefix="/api/v1")
app.include_router(skills_router, prefix="/api/v1")
app.include_router(resolution_router, prefix="/api/v1")
app.include_router(governance_router, prefix="/api/v1")
app.include_router(prompt_templates_router, prefix="/api/v1")
app.include_router(ai_ontology_router, prefix="/api/v1")
app.include_router(ontology_api_router, prefix="/api/v1")
app.include_router(osdk_router, prefix="/api/v1")
app.include_router(ontology_publish_router, prefix="/api/v1")
app.include_router(traces_router, prefix="/api/v1")
app.include_router(evals_router, prefix="/api/v1")
app.include_router(actions_router, prefix="/api/v1")
app.include_router(functions_router, prefix="/api/v1")
app.include_router(monitor_router, prefix="/api/v1")
app.include_router(studio_router, prefix="/api/v1")
app.include_router(pipelines_router, prefix="/api/v1")
app.include_router(aip_scenes_router, prefix="/api/v1")
app.include_router(aip_executions_router, prefix="/api/v1")
app.include_router(aip_webhooks_router, prefix="/api/v1")
app.include_router(builder_router, prefix="/api/v1")
app.include_router(business_documents_router, prefix="/api/v1")

# ── Data Plane router 挂载 ──
app.include_router(dp_connections_router, prefix="/api/v1")
app.include_router(dp_assets_router, prefix="/api/v1")
app.include_router(dp_execute_router, prefix="/api/v1")
app.include_router(dp_probes_router, prefix="/api/v1")
app.include_router(dp_lineage_router, prefix="/api/v1")
app.include_router(dp_events_router, prefix="/api/v1")
app.include_router(dp_audit_router, prefix="/api/v1")
app.include_router(dp_bindings_router, prefix="/api/v1")
app.include_router(dp_quality_router, prefix="/api/v1")
app.include_router(dp_mapping_router, prefix="/api/v1")
app.include_router(ai_builder_v2_router, prefix="/api/v1")
app.include_router(doc_builder_router, prefix="/api/v1")
app.include_router(ontology_mapping_router, prefix="/api/v1")
app.include_router(skill_gen_router, prefix="/api/v1")


@app.get("/api/health")
def health():
    return {"status": "ok"}
