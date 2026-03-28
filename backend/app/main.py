"""
模块功能：
- FastAPI 应用入口，负责初始化语义服务并挂载路由。
- 该文件位于 `backend/app/main.py`，组装应用入口、生命周期和根路由，是后端服务启动时的首个加载点。
- 文件中对外暴露或复用的主要函数包括：`lifespan`, `root`。
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.platform import PlatformContext


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    功能：
    - 在应用生命周期内创建共享的语义服务实例。

    输入：
    - `app`: FastAPI 应用实例。

    输出：
    - 返回值: 返回 `Any` 类型结果，供后续流程继续消费。
    """
    app.state.platform_context = PlatformContext()
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
    """
    功能：
    - 提供最小健康检查响应，便于本地联调与部署探活。

    输入：
    - 无。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
    context = app.state.platform_context
    summary = context.platform_summary()
    return {
        "name": "python-ontology-platform",
        "status": "ok",
        "activeScenarioKey": summary["activeScenarioKey"],
    }
