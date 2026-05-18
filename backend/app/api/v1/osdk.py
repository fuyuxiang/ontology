"""
OSDK 生成服务 — 根据本体 Schema 生成 TypeScript/Python SDK 代码
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.osdk_generator import generate_sdk

router = APIRouter(prefix="/osdk", tags=["osdk"])


class GenerateRequest(BaseModel):
    language: str = "typescript"
    entity_ids: list[str] | None = None


class CodeFile(BaseModel):
    name: str
    content: str


class GenerateResponse(BaseModel):
    files: list[CodeFile]
    usage: str


@router.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest, db: Session = Depends(get_db)):
    result = generate_sdk(db, req.language, req.entity_ids)
    return result
