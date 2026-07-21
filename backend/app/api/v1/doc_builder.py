"""文档构建 API — 上传文档 + 多轮对话抽取本体"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
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
async def upload_documents(files: list[UploadFile] = File(...)):
    parsed_files = []
    for f in files:
        content = await f.read()
        text = doc_builder.parse_file_content(f.filename or "unknown", content)
        parsed_files.append({
            "name": f.filename,
            "size": len(content),
            "type": f.content_type or "",
            "content": text,
            "content_preview": text[:200],
        })

    session = doc_builder.create_session(parsed_files)
    return {
        "session_id": session["id"],
        "files": [
            {"name": pf["name"], "size": pf["size"], "type": pf["type"], "content_preview": pf["content_preview"]}
            for pf in parsed_files
        ],
    }


class ChatRequest(BaseModel):
    session_id: str
    message: str = ""
    business_desc: str = ""


@router.post("/chat")
async def chat(req: ChatRequest):
    return StreamingResponse(
        doc_builder.chat_stream(req.session_id, req.message, req.business_desc),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class MappingPreviewRequest(BaseModel):
    session_id: str
    mapping_result: dict


class MappingApplyItem(BaseModel):
    entity_id: str | None = None
    asset_id: str | None = None
    conflict_action: str | None = None
    register_asset: bool = False
    table_name: str | None = None
    field_mappings: list[dict] = []


class MappingApplyRequest(BaseModel):
    session_id: str
    items: list[MappingApplyItem]


@router.post("/mapping/preview")
async def mapping_preview(req: MappingPreviewRequest, db: Session = Depends(get_db)):
    return doc_mapping_persist_service.preview_mappings(req.mapping_result, db)


@router.post("/mapping/apply")
async def mapping_apply(req: MappingApplyRequest, db: Session = Depends(get_db)):
    result = doc_mapping_persist_service.apply_mappings(
        [item.model_dump() for item in req.items], db
    )
    db.commit()
    return result
