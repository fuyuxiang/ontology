"""文档构建 API — 上传文档 + 多轮对话抽取本体"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import require_user
from app.models.user import User
from app.services import doc_builder, doc_mapping_persist_service

router = APIRouter(prefix="/doc-builder", tags=["doc-builder"])

_TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "static", "templates", "ontology_doc_template.md"
)


@router.get("/template")
async def download_template():
    return FileResponse(
        path=os.path.abspath(_TEMPLATE_PATH),
        filename="本体建模业务文档模板.md",
        media_type="text/markdown",
    )


@router.post("/upload")
async def upload_documents(files: list[UploadFile] = File(...), db: Session = Depends(get_db), user: User = Depends(require_user)):
    from app.services.data_plane.storage_policy import storage_policy
    policy = storage_policy(db)
    parsed_files = []
    for f in files:
        filename = f.filename or "unknown"
        extension = filename.rsplit(".", 1)[-1].lower()
        if extension not in policy["allowed"]:
            raise HTTPException(422, f"存储配置不允许 .{extension} 文件")
        content = await f.read(policy["max_bytes"] + 1)
        if len(content) > policy["max_bytes"]:
            raise HTTPException(413, "文档超过配置的上传大小限制")
        try:
            from starlette.concurrency import run_in_threadpool
            text = await run_in_threadpool(doc_builder.parse_file_content, filename, content)
        except Exception as exc:
            raise HTTPException(422, f"文档 {filename} 无法解析: {exc}") from exc
        if not text.strip():
            raise HTTPException(422, f"文档 {filename} 未包含可提取文本，请检查文件或提供文本版本")
        parsed_files.append({
            "name": f.filename,
            "size": len(content),
            "type": f.content_type or "",
            "content": text,
            "content_preview": text[:200],
        })

    if not parsed_files:
        raise HTTPException(422, "没有有效文档")
    session = doc_builder.create_session(parsed_files, db, user.id)
    db.commit()
    return {
        "session_id": session["id"],
        "files": [
            {"name": pf["name"], "size": pf["size"], "type": pf["type"], "content_preview": pf["content_preview"]}
            for pf in parsed_files
        ],
    }


@router.get("/sessions/{session_id}")
async def read_document_session(session_id: str, db: Session = Depends(get_db), user: User = Depends(require_user)):
    session = doc_builder.get_session(session_id, db, user.id)
    if not session:
        raise HTTPException(404, "文档构建会话不存在或不可访问")
    return {"session_id": session_id, "history": session["history"], "current_ontology": session["current_ontology"]}


class ChatRequest(BaseModel):
    session_id: str
    message: str = ""
    business_desc: str = ""


@router.post("/chat")
async def chat(req: ChatRequest, db: Session = Depends(get_db), user: User = Depends(require_user)):
    return StreamingResponse(
        doc_builder.chat_stream(req.session_id, req.message, req.business_desc, db, user.id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class MappingPreviewRequest(BaseModel):
    session_id: str
    mapping_result: dict
    ontology_id: str | None = None


class MappingApplyItem(BaseModel):
    entity_name: str | None = None
    entity_id: str | None = None
    asset_id: str | None = None
    conflict_action: str | None = None
    field_mappings: list[dict] = []


class MappingApplyRequest(BaseModel):
    session_id: str
    items: list[MappingApplyItem]
    ontology_id: str | None = None
    mapping_result: dict | None = None


@router.post("/mapping/preview")
async def mapping_preview(req: MappingPreviewRequest, db: Session = Depends(get_db)):
    return doc_mapping_persist_service.preview_mappings(req.mapping_result, db, req.ontology_id)


@router.post("/mapping/apply")
async def mapping_apply(req: MappingApplyRequest, db: Session = Depends(get_db), user: User = Depends(require_user)):
    try:
        from app.models.builder_document_session import BuilderDocumentSession
        session = db.get(BuilderDocumentSession, req.session_id)
        if session and session.user_id != user.id:
            raise HTTPException(404, "文档映射会话不存在或不可访问")
        # Legacy mapping clients used their own session IDs before uploads were
        # persisted. Record their confirmation under the authenticated owner too.
        if not session:
            session = BuilderDocumentSession(id=req.session_id, user_id=user.id,
                payload={"id": req.session_id, "files": [], "history": [], "current_ontology": None})
            db.add(session)
        items = [item.model_dump() for item in req.items]
        kept_entities = set()
        from app.models.entity import OntologyEntity
        from app.repositories.object_binding_repo import ObjectBindingRepository
        for item in items:
            entity = (db.get(OntologyEntity, item["entity_id"]) if item.get("entity_id") else
                      db.query(OntologyEntity).filter_by(name=item.get("entity_name"), ontology_id=req.ontology_id).first())
            if entity and entity.ontology_id != req.ontology_id:
                raise ValueError("实体不属于目标本体")
            if entity and item.get("conflict_action") != "overwrite" and ObjectBindingRepository(db).list(object_type_id=entity.id, role="primary"):
                kept_entities.add(entity.id)
        if req.mapping_result:
            from app.api.v1.builder import FinalizeRequest, finalize_draft
            entities = req.mapping_result.get("entities", [])
            # 创建对象和属性后才解析属性 ID。所有结构、映射在同一事务内提交。
            draft = FinalizeRequest(
                ontology_id=req.ontology_id,
                objects=[{
                    "name": e["name"], "displayName": e.get("displayName"),
                    "description": e.get("description"), "tier": e.get("tier", 2),
                    "primaryKey": e.get("primaryKey", "id"),
                    "properties": [{
                        "name": p["name"], "displayName": p.get("displayName"),
                        "type": p.get("type", "string"), "required": p.get("required", False),
                    } for p in e.get("properties", [])],
                } for e in entities],
                relations=req.mapping_result.get("relations", []),
            )
            finalize_draft(draft, db, sync_bindings=False, preserve_entity_ids=kept_entities, preserve_definitions=True)
            preview = doc_mapping_persist_service.preview_mappings(req.mapping_result, db, req.ontology_id)
            by_name = {row["entity_name"]: row for row in preview["items"]}
            for item in items:
                resolved = by_name.get(item.get("entity_name"))
                if not resolved:
                    raise ValueError("提交映射与预览不一致")
                if item.get("entity_id") and item["entity_id"] != resolved["entity_id"]:
                    raise ValueError("实体不属于目标本体")
                if item.get("asset_id") != resolved["asset_id"]:
                    raise ValueError("资产与当前映射结果不一致，请重新预览")
                item["entity_id"] = resolved["entity_id"]
                # 首次创建的字段由名称解析，禁止向另一对象属性写入映射。
                item["field_mappings"] = [{
                    "attribute_id": fm["attribute_id"], "source_column": fm["source_column"],
                } for fm in resolved["field_mappings"] if fm["attribute_id"] and fm["source_column"]]
        for item in items:
            entity = db.get(OntologyEntity, item.get("entity_id"))
            if not entity or entity.ontology_id != req.ontology_id:
                raise ValueError("实体不属于目标本体")
        result = doc_mapping_persist_service.apply_mappings(items, db)
        result["items"] = [doc_mapping_persist_service.effective_mapping_item(
            db, item["entity_id"], "keep" if item["entity_id"] in kept_entities else item.get("conflict_action"))
            for item in items]
        session.payload = {**(session.payload or {}), "mapping_receipt": {
            "ontology_id": req.ontology_id,
            "kept_entities": {entity_id: doc_mapping_persist_service.binding_fingerprint(db, entity_id)
                              for entity_id in kept_entities},
        }}
        db.commit()
        return result
    except (ValueError, LookupError) as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    except Exception:
        db.rollback()
        raise
