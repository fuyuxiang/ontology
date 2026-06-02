"""AI Builder V2 API — 主题域下钻式本体构建"""
from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services import dwd_catalog, minio_docs, ai_builder_v2

router = APIRouter(prefix="/ai-builder", tags=["AI Builder V2"])


@router.get("/domains")
def list_domains():
    return {"domains": dwd_catalog.get_domains()}


@router.get("/domains/{domain1}/sub-domains")
def list_sub_domains(domain1: str):
    return {"sub_domains": dwd_catalog.get_sub_domains(domain1)}


@router.get("/domains/{domain1}/{domain2}/themes")
def list_themes(domain1: str, domain2: str):
    return {"themes": dwd_catalog.get_themes(domain1, domain2)}


@router.get("/tables")
def list_tables(domain1: str = Query(...), domain2: str = Query(...), domain3: str = Query(None)):
    return {"tables": dwd_catalog.get_tables(domain1, domain2, domain3)}


@router.get("/tables/{table_name}/schema")
def get_table_schema(table_name: str):
    return {"table_name": table_name, "fields": dwd_catalog.get_table_schema(table_name)}


class MatchDomainRequest(BaseModel):
    business_desc: str


@router.post("/match-domain")
def match_domain(req: MatchDomainRequest):
    return ai_builder_v2.match_domain(req.business_desc)


class RecommendTablesRequest(BaseModel):
    business_desc: str
    domains: list[str]
    sub_domains: list[str] = []
    themes: list[str] = []


@router.post("/recommend-tables")
def recommend_tables(req: RecommendTablesRequest):
    tables = dwd_catalog.get_tables_by_domains(
        req.domains,
        req.sub_domains if req.sub_domains else None,
        req.themes if req.themes else None,
    )
    recommended = ai_builder_v2.recommend_tables(req.business_desc, tables)
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
def extract_ontology(req: ExtractRequest):
    return StreamingResponse(
        ai_builder_v2.extract_ontology_stream(req.table_names, req.document_keys, req.business_desc),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
