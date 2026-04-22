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
from app.api.v1.rules import router as rules_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.copilot import router as copilot_router
from app.api.v1.relations import router as relations_router
from app.api.v1.datasources import router as datasources_router
from app.api.v1.mnp import router as mnp_router
from app.api.v1.scenes import router as scenes_router
from app.api.v1.broadband import router as broadband_router
from app.api.v1.workflows import router as workflows_router
from app.api.v1.models import router as models_router
from app.api.v1.agents import router as agents_router, open_router as agents_open_router

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

    db = SessionLocal()
    try:
        seed_admin(db)
        _seed_agents(db)
    finally:
        db.close()

    # Neo4j 初始化暂时跳过（需要修复 numpy/pandas 版本冲突后启用）
    # 基础功能（实体CRUD、规则、看板）不依赖 Neo4j
    logger.info("服务启动完成（Neo4j 待配置）")

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
app.include_router(workflows_router, prefix="/api/v1")
app.include_router(models_router, prefix="/api/v1")
app.include_router(agents_router, prefix="/api/v1")
app.include_router(agents_open_router, prefix="/api/v1")


@app.get("/api/health")
def health():
    return {"status": "ok"}
