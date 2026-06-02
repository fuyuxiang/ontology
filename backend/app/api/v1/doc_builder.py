"""文档构建 API — 上传文档 + 多轮对话抽取本体"""
from __future__ import annotations

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services import doc_builder

router = APIRouter(prefix="/doc-builder", tags=["doc-builder"])


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
