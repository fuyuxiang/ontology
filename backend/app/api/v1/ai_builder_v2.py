"""AI Builder V2 API — 基于已注册数据资产构建本体。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import require_user
from app.models.user import User
from app.services import ai_builder_v2, asset_catalog, minio_docs

router = APIRouter(prefix="/ai-builder", tags=["AI Builder V2"])


@router.get("/tables")
def list_tables(db: Session = Depends(get_db)):
    return {"tables": asset_catalog.get_tables(db)}


@router.get("/tables/{table_name}/schema")
def get_table_schema(table_name: str, db: Session = Depends(get_db)):
    try:
        return {"table_name": table_name, "fields": asset_catalog.get_table_schema(table_name, db)}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


class RecommendTablesRequest(BaseModel):
    business_desc: str


@router.post("/recommend-tables")
def recommend_tables(req: RecommendTablesRequest, db: Session = Depends(get_db)):
    tables = asset_catalog.get_tables(db)
    try:
        recommended = ai_builder_v2.recommend_tables(req.business_desc, tables, db)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"tables": tables, "recommended": recommended}


@router.get("/documents")
def list_documents(prefix: str = "", db: Session = Depends(get_db)):
    from app.models.asset import Asset
    assets = db.query(Asset).filter(Asset.kind == "document", Asset.status == "active").all()
    documents = [{"key": f"asset:{asset.id}", "title": asset.name, "size": int((asset.locator or {}).get("file_size") or 0),
                  "last_modified": asset.updated_at.isoformat() if asset.updated_at else None}
                 for asset in assets if not prefix or prefix.lower() in asset.name.lower()]
    warning = None
    try:
        documents.extend(minio_docs.list_documents(prefix, db=db))
    except Exception as exc:
        # Catalog documents remain independently usable when the optional
        # unregistered MinIO library has no configuration or cannot be reached.
        warning = f"MinIO 文档库不可用: {exc}"
    return {"documents": documents, "warning": warning}


@router.get("/documents/content")
def get_document_content(key: str = Query(...), db: Session = Depends(get_db), user: User = Depends(require_user)):
    try:
        content = ai_builder_v2.read_document_content(key, db, user.id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"key": key, "content": content[:5000], "truncated": len(content) > 5000, "total_chars": len(content)}


class ExtractRequest(BaseModel):
    table_names: list[str]
    document_keys: list[str] = []
    business_desc: str


@router.post("/extract-ontology")
def extract_ontology(req: ExtractRequest, db: Session = Depends(get_db), user: User = Depends(require_user)):
    return StreamingResponse(
        ai_builder_v2.extract_ontology_stream(req.table_names, req.document_keys, req.business_desc, db, user.id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
