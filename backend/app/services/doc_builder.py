"""文档构建服务 — 从上传文档中通过 LLM 多轮对话抽取本体"""
from __future__ import annotations

import io
import json
import logging
import re
import uuid
import copy

from sqlalchemy.orm import Session
from app.models.builder_document_session import BuilderDocumentSession
from collections.abc import Generator

from openai import OpenAI

from app.services.ontology_constraints import (
    build_constraint_prompt,
    validate_and_retry,
    validate_ontology_output,
)

logger = logging.getLogger(__name__)

_sessions: dict[str, dict] = {}


def _get_llm_client(db=None) -> OpenAI:
    from app.services.llm_resolver import get_llm_client
    return get_llm_client(db=db, scene="ontology")


def _get_model_name(db=None) -> str:
    from app.services.llm_resolver import get_model_name
    return get_model_name(db=db, scene="ontology")


def _extract_json(text: str) -> str:
    text = re.sub(r"<think>[\s\S]*?</think>", "", text).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return match.group(0)
    return text


def _sanitize_docx(data: bytes) -> bytes:
    """Remove broken relationship entries (e.g. Target='../NULL') from docx archive."""
    import zipfile
    from xml.etree import ElementTree as ET

    NS = "http://schemas.openxmlformats.org/package/2006/relationships"
    src = zipfile.ZipFile(io.BytesIO(data))
    names = set(src.namelist())

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            raw = src.read(item.filename)
            if item.filename.endswith(".rels"):
                tree = ET.fromstring(raw)
                dirty = False
                for rel in list(tree):
                    target = rel.get("Target", "")
                    if target.startswith("http"):
                        continue
                    # resolve relative path against rels parent dir
                    import posixpath
                    rels_dir = posixpath.dirname(item.filename)
                    parent_dir = posixpath.dirname(rels_dir)
                    resolved = posixpath.normpath(posixpath.join(parent_dir, target))
                    if resolved not in names and target not in names:
                        tree.remove(rel)
                        dirty = True
                if dirty:
                    ET.register_namespace("", NS)
                    raw = ET.tostring(tree, encoding="unicode", xml_declaration=True).encode("utf-8")
            dst.writestr(item, raw)
    src.close()
    return buf.getvalue()


def parse_file_content(filename: str, content: bytes) -> str:
    """Extract complete textual content; never silently cut off later business rules."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in ("doc", "xls", "ppt"):
        from app.services.office_conversion import convert_legacy_office
        content = convert_legacy_office(content, ext)
        ext = {"doc": "docx", "xls": "xlsx", "ppt": "pptx"}[ext]
    if ext in ("txt", "csv", "md"):
        try:
            return content.decode("utf-8-sig")
        except UnicodeDecodeError:
            return content.decode("gb18030")
    if ext == "pdf":
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    if ext == "docx":
        import docx
        from docx.table import Table
        from docx.text.paragraph import Paragraph
        doc = docx.Document(io.BytesIO(_sanitize_docx(content)))
        texts = []
        for element in doc.element.body:
            if element.tag.endswith("}p"):
                paragraph = Paragraph(element, doc)
                if paragraph.text.strip():
                    texts.append(paragraph.text)
            elif element.tag.endswith("}tbl"):
                table = Table(element, doc)
                texts.extend("\t".join(cell.text for cell in row.cells) for row in table.rows)
        return "\n".join(texts)
    if ext == "xlsx":
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        try:
            lines = []
            for ws in wb.worksheets:
                lines.append(f"## Sheet: {ws.title}")
                for row in ws.iter_rows(values_only=True):
                    line = "\t".join(str(cell) if cell is not None else "" for cell in row)
                    if line.strip():
                        lines.append(line)
            return "\n".join(lines)
        finally:
            wb.close()
    if ext == "pptx":
        from pptx import Presentation
        prs = Presentation(io.BytesIO(content))
        texts = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if shape.has_text_frame:
                    texts.extend(paragraph.text for paragraph in shape.text_frame.paragraphs if paragraph.text.strip())
                if shape.has_table:
                    texts.extend("\t".join(cell.text for cell in row.cells) for row in shape.table.rows)
        return "\n".join(texts)
    raise ValueError(f"不支持的文件格式: {ext}")


def create_session(files: list[dict], db: Session | None = None, user_id: str | None = None) -> dict:
    session_id = str(uuid.uuid4())
    payload = {"id": session_id, "files": files, "history": [], "current_ontology": None}
    if db is not None:
        db.add(BuilderDocumentSession(id=session_id, user_id=user_id, payload=payload))
        db.flush()
    else:
        _sessions[session_id] = payload
    return payload


def get_session(session_id: str, db: Session | None = None, user_id: str | None = None) -> dict | None:
    if db is None:
        return _sessions.get(session_id)
    record = db.get(BuilderDocumentSession, session_id)
    if not record or (record.user_id is not None and record.user_id != user_id):
        return None
    return copy.deepcopy(record.payload)


def _save_session(session: dict, db: Session | None) -> None:
    if db is not None:
        record = db.get(BuilderDocumentSession, session["id"])
        if record:
            record.payload = copy.deepcopy(session)
            db.commit()


_BASE_SYSTEM_PROMPT = """你是一名资深的业务建模与本体建模专家。你的任务是从用户提供的业务文档中提取本体（实体、属性、关系）。

规则：
1. 每次回复必须包含完整的本体 JSON
2. 在 JSON 之外可用自然语言解释你的分析思路
"""


def _build_system_prompt() -> str:
    return _BASE_SYSTEM_PROMPT + "\n" + build_constraint_prompt()


def _document_contract(result: dict) -> dict:
    """Convert the validated extraction schema into the document/mapping UI schema."""
    return {
        "entities": [{"name": entity["name"], "displayName": entity["name_cn"], "tier": entity["tier"], "description": entity["description"],
                      "properties": [{**attribute, "displayName": attribute["display_name"]} for attribute in entity["attributes"]]} for entity in result["entities"]],
        "relations": [{**relation, "source": relation["from_entity"], "target": relation["to_entity"], "displayName": relation["name"]} for relation in result["relations"]],
    }


def _validate_document_output(raw: str):
    # Existing document callers also supplied properties/displayName; normalize
    # aliases before the same strict structural validator used by other builders.
    try:
        candidate = json.loads(raw)
        if isinstance(candidate, dict):
            for entity in candidate.get("entities", []):
                if "attributes" not in entity and "properties" in entity:
                    entity["attributes"] = entity["properties"]
                    entity.setdefault("name_cn", entity.get("displayName", entity.get("name", "")))
                    entity.setdefault("tier", 3)
                    entity.setdefault("description", "")
                    for attribute in entity["attributes"]:
                        attribute.setdefault("display_name", attribute.get("displayName", attribute.get("name", "")))
                        attribute.setdefault("required", False)
                        attribute.setdefault("description", "")
            for relation in candidate.get("relations", []):
                relation.setdefault("from_entity", relation.get("source"))
                relation.setdefault("to_entity", relation.get("target"))
                relation.setdefault("rel_type", {"1:1":"has_one", "1:N":"has_many", "N:1":"belongs_to", "N:N":"many_to_many"}.get(relation.get("cardinality"), "has_many"))
        return validate_ontology_output(json.dumps(candidate))
    except (ValueError, TypeError, AttributeError):
        return None, "文档抽取结果格式无效"


def chat_stream(session_id: str, message: str, business_desc: str, db: Session | None = None, user_id: str | None = None) -> Generator[str, None, None]:
    try:
        yield from _chat_stream(session_id, message, business_desc, db, user_id)
    except Exception as exc:
        if db is not None:
            db.rollback()
        session = get_session(session_id, db, user_id)
        if session:
            session["current_ontology"] = None
            _save_session(session, db)
        yield f"data: {json.dumps({'event':'error', 'message':str(exc)})}\n\n"
        yield "data: [DONE]\n\n"


def _chat_stream(
    session_id: str,
    message: str,
    business_desc: str,
    db: Session | None = None,
    user_id: str | None = None,
) -> Generator[str, None, None]:
    session = get_session(session_id, db, user_id)
    if not session:
        yield f"data: {json.dumps({'event': 'error', 'message': 'session not found'})}\n\n"
        return

    yield f"data: {json.dumps({'event': 'thinking', 'message': '正在分析文档内容...'})}\n\n"

    messages = [{"role": "system", "content": _build_system_prompt()}]

    if not session["history"]:
        doc_contents = "\n\n".join(
            f"### 文件: {f['name']}\n{f['content']}" for f in session["files"]
        )
        first_user_msg = f"""业务需求：{business_desc}

以下是上传的业务文档内容：

{doc_contents}

请从以上文档中提取本体的实体、属性和关系。"""
        messages.append({"role": "user", "content": first_user_msg})
        session["history"].append({"role": "user", "content": first_user_msg})
    else:
        for h in session["history"]:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": message})
        session["history"].append({"role": "user", "content": message})

    session["current_ontology"] = None
    client = _get_llm_client(db)
    try:
        resp = client.chat.completions.create(
            model=_get_model_name(db),
            messages=messages,
            temperature=0.3,
            stream=True,
        )
    except Exception as e:
        _save_session(session, db)
        yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
        yield "data: [DONE]\n\n"
        return

    full_content = ""
    in_think = False
    buffer = ""
    think_notified = False

    for chunk in resp:
        delta = chunk.choices[0].delta
        if delta.content:
            full_content += delta.content
            buffer += delta.content

            while buffer:
                if in_think:
                    end_idx = buffer.find("</think>")
                    if end_idx == -1:
                        buffer = ""
                        break
                    else:
                        buffer = buffer[end_idx + 8:]
                        in_think = False
                else:
                    start_idx = buffer.find("<think>")
                    if start_idx == -1:
                        if "<" in buffer and not buffer.endswith(">"):
                            safe = buffer[:buffer.rfind("<")]
                            if safe:
                                yield f"data: {json.dumps({'event': 'token', 'content': safe})}\n\n"
                            buffer = buffer[len(safe):]
                        else:
                            yield f"data: {json.dumps({'event': 'token', 'content': buffer})}\n\n"
                            buffer = ""
                        break
                    else:
                        if start_idx > 0:
                            yield f"data: {json.dumps({'event': 'token', 'content': buffer[:start_idx]})}\n\n"
                        buffer = buffer[start_idx + 7:]
                        in_think = True
                        if not think_notified:
                            think_notified = True
                            yield f"data: {json.dumps({'event': 'thinking', 'message': 'AI 正在深度思考...'})}\n\n"

    session["history"].append({"role": "assistant", "content": full_content})

    ontology_json = _extract_json(full_content)
    if ontology_json:
        result, errors = _validate_document_output(ontology_json)
        if result is not None:
            session["current_ontology"] = _document_contract(result)
            yield f"data: {json.dumps({'event': 'ontology', 'data': session['current_ontology']})}\n\n"
        else:
            yield f"data: {json.dumps({'event': 'validating', 'message': '正在校验修正输出...'})}\n\n"
            client = _get_llm_client(db)

            def retry_caller(retry_prompt: str) -> str:
                resp = client.chat.completions.create(
                    model=_get_model_name(db),
                    messages=[
                        {"role": "system", "content": retry_prompt},
                        {"role": "user", "content": "请输出修正后的完整JSON。"},
                    ],
                    temperature=0,
                )
                return resp.choices[0].message.content or ""

            result, warnings = validate_and_retry(retry_caller, full_content, max_retries=5)
            if result is not None:
                # The shared historical helper may return an unvalidated JSON
                # fallback after exhausting retries; it is not usable output.
                result, validation_error = _validate_document_output(json.dumps(result))
                warnings = validation_error or warnings
            if result is not None:
                session["current_ontology"] = _document_contract(result)
                yield f"data: {json.dumps({'event': 'ontology', 'data': session['current_ontology']})}\n\n"
                if warnings:
                    yield f"data: {json.dumps({'event': 'validation_warning', 'message': warnings})}\n\n"
            else:
                _save_session(session, db)
                yield f"data: {json.dumps({'event':'error','message':'文档抽取结果未通过校验，请重试或调整文档'})}\n\n"
                yield "data: [DONE]\n\n"
                return

    if not session["current_ontology"]:
        _save_session(session, db)
        yield f"data: {json.dumps({'event':'error','message':'文档抽取未生成有效本体，请重试'})}\n\n"
        yield "data: [DONE]\n\n"
        return

    _save_session(session, db)
    yield "data: [DONE]\n\n"
