import os
import uuid as _uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.knowledge import KnowledgeBase, KnowledgeFile

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads", "knowledge")
os.makedirs(UPLOAD_DIR, exist_ok=True)

EXT_TYPE_MAP = {
    "pdf": "pdf", "doc": "word", "docx": "word",
    "xls": "excel", "xlsx": "excel",
    "png": "image", "jpg": "image", "jpeg": "image", "gif": "image", "webp": "image",
    "mp4": "video", "avi": "video", "mov": "video", "mkv": "video",
    "mp3": "audio", "wav": "audio", "m4a": "audio", "aac": "audio", "ogg": "audio",
    "txt": "text",
}


def _parse_file(path: str, file_type: str) -> str:
    try:
        if file_type == "pdf":
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                return "\n".join(p.extract_text() or "" for p in pdf.pages)
        elif file_type == "word":
            from docx import Document
            doc = Document(path)
            return "\n".join(p.text for p in doc.paragraphs)
        elif file_type == "excel":
            import openpyxl
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            lines = []
            for ws in wb.worksheets:
                for row in ws.iter_rows(values_only=True):
                    lines.append("\t".join(str(c) if c is not None else "" for c in row))
            return "\n".join(lines)
    except Exception as e:
        return f"[解析失败: {e}]"
    return ""


def _kb_dict(kb: KnowledgeBase, files: list[KnowledgeFile] | None = None) -> dict:
    d = {
        "id": kb.id, "name": kb.name, "description": kb.description or "",
        "tags": kb.tags or [], "status": kb.status,
        "created_at": kb.created_at.isoformat() if kb.created_at else "",
        "updated_at": kb.updated_at.isoformat() if kb.updated_at else "",
        "file_count": 0,
    }
    if files is not None:
        d["files"] = [_file_dict(f) for f in files]
        d["file_count"] = len(files)
    return d


def _file_dict(f: KnowledgeFile) -> dict:
    return {
        "id": f.id, "kb_id": f.kb_id, "name": f.name,
        "file_type": f.file_type, "size": f.size, "status": f.status,
        "created_at": f.created_at.isoformat() if f.created_at else "",
        "has_content": bool(f.parsed_content),
    }


# ── 知识库 CRUD ──────────────────────────────────────────────

@router.get("")
def list_kbs(q: str = Query(default=""), db: Session = Depends(get_db)):
    query = db.query(KnowledgeBase)
    if q:
        query = query.filter(KnowledgeBase.name.ilike(f"%{q}%"))
    kbs = query.order_by(KnowledgeBase.updated_at.desc()).all()
    result = []
    for kb in kbs:
        d = _kb_dict(kb)
        d["file_count"] = db.query(KnowledgeFile).filter(KnowledgeFile.kb_id == kb.id).count()
        result.append(d)
    return result


@router.post("", status_code=201)
def create_kb(name: str = Form(...), description: str = Form(""), tags: str = Form(""), db: Session = Depends(get_db)):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    kb = KnowledgeBase(name=name, description=description, tags=tag_list)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return _kb_dict(kb, [])


@router.get("/search")
def search_kbs(q: str = Query(...), db: Session = Depends(get_db)):
    if not q.strip():
        return []
    files = db.query(KnowledgeFile).filter(KnowledgeFile.parsed_content.ilike(f"%{q}%")).limit(50).all()
    results = []
    seen_kb = {}
    for f in files:
        if f.kb_id not in seen_kb:
            kb = db.get(KnowledgeBase, f.kb_id)
            seen_kb[f.kb_id] = kb.name if kb else f.kb_id
        idx = f.parsed_content.lower().find(q.lower()) if f.parsed_content else -1
        snippet = f.parsed_content[max(0, idx-60):idx+120] if idx >= 0 and f.parsed_content else ""
        results.append({"kb_id": f.kb_id, "kb_name": seen_kb[f.kb_id], "file_id": f.id, "file_name": f.name, "snippet": snippet})
    return results


@router.get("/{kb_id}")
def get_kb(kb_id: str, db: Session = Depends(get_db)):
    kb = db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(404, "知识库不存在")
    files = db.query(KnowledgeFile).filter(KnowledgeFile.kb_id == kb_id).order_by(KnowledgeFile.created_at.desc()).all()
    return _kb_dict(kb, files)


@router.put("/{kb_id}")
def update_kb(kb_id: str, name: str = Form(None), description: str = Form(None), tags: str = Form(None), db: Session = Depends(get_db)):
    kb = db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(404, "知识库不存在")
    if name is not None:
        kb.name = name
    if description is not None:
        kb.description = description
    if tags is not None:
        kb.tags = [t.strip() for t in tags.split(",") if t.strip()]
    kb.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(kb)
    files = db.query(KnowledgeFile).filter(KnowledgeFile.kb_id == kb_id).all()
    return _kb_dict(kb, files)


@router.delete("/{kb_id}")
def delete_kb(kb_id: str, db: Session = Depends(get_db)):
    kb = db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(404, "知识库不存在")
    db.query(KnowledgeFile).filter(KnowledgeFile.kb_id == kb_id).delete()
    db.delete(kb)
    db.commit()
    return {"ok": True}


# ── 文件操作 ──────────────────────────────────────────────────

@router.post("/{kb_id}/files", status_code=201)
async def upload_file(kb_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    kb = db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(404, "知识库不存在")

    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    file_type = EXT_TYPE_MAP.get(ext, "other")
    save_name = f"{_uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(UPLOAD_DIR, save_name)

    content = await file.read()
    with open(save_path, "wb") as fp:
        fp.write(content)

    parsed = ""
    if file_type in ("pdf", "word", "excel"):
        parsed = _parse_file(save_path, file_type)

    kf = KnowledgeFile(
        kb_id=kb_id,
        name=file.filename or save_name,
        file_type=file_type,
        file_path=save_path,
        size=len(content),
        parsed_content=parsed[:100000] if parsed else None,
        status="ready",
    )
    db.add(kf)
    kb.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(kf)
    return _file_dict(kf)


@router.delete("/{kb_id}/files/{fid}")
def delete_file(kb_id: str, fid: str, db: Session = Depends(get_db)):
    kf = db.get(KnowledgeFile, fid)
    if not kf or kf.kb_id != kb_id:
        raise HTTPException(404, "文件不存在")
    if kf.file_path and os.path.exists(kf.file_path):
        os.remove(kf.file_path)
    db.delete(kf)
    db.commit()
    return {"ok": True}


@router.get("/{kb_id}/files/{fid}/content")
def get_file_content(kb_id: str, fid: str, db: Session = Depends(get_db)):
    kf = db.get(KnowledgeFile, fid)
    if not kf or kf.kb_id != kb_id:
        raise HTTPException(404, "文件不存在")
    return {"content": kf.parsed_content or "", "file_type": kf.file_type, "name": kf.name}


from pydantic import BaseModel

class AsrUpdateReq(BaseModel):
    asr_text: str

@router.put("/{kb_id}/files/{fid}/asr")
def update_asr(kb_id: str, fid: str, req: AsrUpdateReq, db: Session = Depends(get_db)):
    kf = db.get(KnowledgeFile, fid)
    if not kf or kf.kb_id != kb_id:
        raise HTTPException(404, "文件不存在")
    kf.parsed_content = req.asr_text[:100000]
    db.commit()
    return {"ok": True}


class VoiceAuditReq(BaseModel):
    asr_text: str
    scenario: str = "broadband"  # broadband / general

@router.post("/{kb_id}/files/{fid}/voice-audit")
def voice_audit_file(kb_id: str, fid: str, req: VoiceAuditReq, db: Session = Depends(get_db)):
    from openai import OpenAI
    from app.config import settings
    import json as _json

    kf = db.get(KnowledgeFile, fid)
    if not kf or kf.kb_id != kb_id:
        raise HTTPException(404, "文件不存在")

    asr = req.asr_text.strip() or (kf.parsed_content or "").strip()
    if not asr:
        raise HTTPException(400, "无可质检的文本内容")

    scenario_hint = "宽带装机服务工程师" if req.scenario == "broadband" else "客服/服务人员"
    prompt = f"""你是{scenario_hint}话术质检专家。请对以下通话文本进行质检分析。

通话文本：
{asr}

请从以下5个维度逐一评分并给出简短说明：
1. 自我介绍：是否进行了规范的自我介绍（姓名、工号、来意）
2. 问题确认：是否清晰确认了客户问题或诉求
3. 操作规范：是否按规范流程操作，有无违规承诺或误导性表述
4. 情绪处理：面对客户投诉/不满时是否妥善安抚
5. 结果告知：是否明确告知处理结果或后续安排

返回JSON格式：
{{
  "overall": "pass" | "fail" | "warning",
  "score": 0-100,
  "summary": "一句话总结",
  "dimensions": [
    {{"name": "自我介绍", "result": "pass"|"fail"|"na", "comment": "..."}},
    {{"name": "问题确认", "result": "pass"|"fail"|"na", "comment": "..."}},
    {{"name": "操作规范", "result": "pass"|"fail"|"na", "comment": "..."}},
    {{"name": "情绪处理", "result": "pass"|"fail"|"na", "comment": "..."}},
    {{"name": "结果告知", "result": "pass"|"fail"|"na", "comment": "..."}}
  ],
  "risk_flags": ["..."]
}}
只返回JSON，不要其他内容。"""

    client = OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_API_BASE)
    try:
        resp = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=800,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return _json.loads(raw)
    except Exception as e:
        raise HTTPException(500, f"质检失败: {e}")
