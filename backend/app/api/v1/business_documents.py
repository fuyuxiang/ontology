"""业务文档库 CRUD — 上传、列表、删除、按 id 取详情/正文。"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BusinessDocument

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/business-documents", tags=["business-documents"])


class _DocOut(BaseModel):
    id: str
    name: str
    file_type: str
    size_bytes: int
    domain_tags: list[str]
    summary: str | None
    uploaded_at: str

    @classmethod
    def from_db(cls, d: BusinessDocument) -> _DocOut:
        return cls(
            id=d.id, name=d.name, file_type=d.file_type or "",
            size_bytes=d.size_bytes or 0,
            domain_tags=list(d.domain_tags or []),
            summary=d.summary or "",
            uploaded_at=d.uploaded_at.isoformat() if d.uploaded_at else "",
        )


def _parse_to_text(filename: str, raw: bytes) -> str:
    """复用 builder.extract 里同款解析。"""
    from app.api.v1.builder import _parse_text
    return _parse_text(filename, raw)


@router.get("", response_model=list[_DocOut])
def list_documents(
    domain: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(BusinessDocument).order_by(BusinessDocument.uploaded_at.desc())
    if search:
        q = q.filter(BusinessDocument.name.ilike(f"%{search}%"))
    docs = q.all()
    if domain:
        docs = [d for d in docs if domain in (d.domain_tags or [])]
    return [_DocOut.from_db(d) for d in docs]


@router.post("/upload", response_model=_DocOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    domain_tags: str = Form(""),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(400, "文件名为空")
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "文件内容为空")

    ext = (file.filename.rsplit(".", 1)[-1] or "").lower()
    text = _parse_to_text(file.filename, raw)
    summary = (text or "")[:500]
    tags = [t.strip() for t in (domain_tags or "").split(",") if t.strip()]

    doc = BusinessDocument(
        name=file.filename,
        file_type=ext,
        size_bytes=len(raw),
        parsed_text=text,
        summary=summary,
        domain_tags=tags,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _DocOut.from_db(doc)


@router.delete("/{doc_id}", status_code=204)
def delete_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.get(BusinessDocument, doc_id)
    if not doc:
        raise HTTPException(404, "文档不存在")
    db.delete(doc)
    db.commit()


@router.get("/{doc_id}/text")
def get_document_text(doc_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    doc = db.get(BusinessDocument, doc_id)
    if not doc:
        raise HTTPException(404, "文档不存在")
    return {"id": doc.id, "name": doc.name, "text": doc.parsed_text or ""}
