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

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：建表 + 初始化管理员
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_admin(db)
    finally:
        db.close()

    # 初始化 Neo4j（可选，连不上不影响基础功能）
    try:
        from app.services.graph import get_driver, ensure_constraints
        driver = get_driver()
        ensure_constraints(driver)
        logger.info("Neo4j 连接成功")
    except Exception as e:
        logger.warning(f"Neo4j 未连接，图遍历功能不可用: {e}")

    yield

    # 关闭 Neo4j
    try:
        from app.services.graph import close_driver
        close_driver()
    except Exception:
        pass


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
app.include_router(auth_router, prefix="/api/v1")


@app.get("/api/health")
def health():
    return {"status": "ok"}
