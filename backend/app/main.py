from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config.settings import get_settings
from app.services.semantic_service import SemanticService


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    return {"name": "python-ontology-backend", "status": "ok"}

