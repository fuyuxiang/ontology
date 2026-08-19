"""AI Builder V2 API — 基于已注册数据资产构建本体。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import ai_builder_v2, asset_catalog, minio_docs

router = APIRouter(prefix="/ai-builder", tags=["AI Builder V2"])


@router.get("/tables")
def list_tables(db: Session = Depends(get_db)):
    return {"tables": asset_catalog.get_tables(db)}


@router.get("/tables/{table_name}/schema")
def get_table_schema(table_name: str, db: Session = Depends(get_db)):
    return {"table_name": table_name, "fields": asset_catalog.get_table_schema(table_name, db)}


class RecommendTablesRequest(BaseModel):
    business_desc: str


@router.post("/recommend-tables")
def recommend_tables(req: RecommendTablesRequest, db: Session = Depends(get_db)):
    tables = asset_catalog.get_tables(db)
    recommended = ai_builder_v2.recommend_tables(req.business_desc, tables, db)
    return {"tables": tables, "recommended": recommended}


@router.get("/documents")
def list_documents(prefix: str = ""):
    return {"documents": minio_docs.list_documents(prefix)}


@router.get("/documents/content")
def get_document_content(key: str = Query(...)):
    content = minio_docs.get_document_content(key)
    return {"key": key, "content": content[:5000]}


class ExtractRequest(BaseModel):
    table_names: list[str]
    document_keys: list[str] = []
    business_desc: str


@router.post("/extract-ontology")
def extract_ontology(req: ExtractRequest, db: Session = Depends(get_db)):
    return StreamingResponse(
        ai_builder_v2.extract_ontology_stream(req.table_names, req.document_keys, req.business_desc, db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
