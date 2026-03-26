"""FastAPI 应用入口，负责初始化语义服务并挂载路由。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config.settings import get_settings
from app.services.semantic_service import SemanticService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """在应用生命周期内创建共享的语义服务实例。"""
    app.state.semantic_service = SemanticService(get_settings())
    yield


app = FastAPI(
    title="Python Ontology Semantic Layer",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/")
def root() -> dict[str, str]:
    """提供最小健康检查响应，便于本地联调与部署探活。"""
    return {"name": "python-ontology-backend", "status": "ok"}
