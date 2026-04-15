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
from app.api.v1.rules import router as rules_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.copilot import router as copilot_router
from app.api.v1.relations import router as relations_router
from app.api.v1.datasources import router as datasources_router

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

    db = SessionLocal()
    try:
        seed_admin(db)
    finally:
        db.close()

    # Neo4j 初始化暂时跳过（需要修复 numpy/pandas 版本冲突后启用）
    # 基础功能（实体CRUD、规则、看板）不依赖 Neo4j
    logger.info("服务启动完成（Neo4j 待配置）")

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


@app.get("/api/health")
def health():
    return {"status": "ok"}
