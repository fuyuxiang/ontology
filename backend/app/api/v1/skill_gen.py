"""技能生成 API — 向导式生成流程"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.skill import Skill
from app.models.skill_tool import SkillTool
from app.services import skill_generator
from app.services.skill_sandbox import execute_in_sandbox, validate_code
from app.services.skill_version_service import publish_skill

router = APIRouter(prefix="/skill-gen", tags=["skill-gen"])


class SessionCreate(BaseModel):
    asset_ids: dict


class ChatRequest(BaseModel):
    session_id: str
    message: str = ""


class GenerateRequest(BaseModel):
    session_id: str


class DraftUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    input_schema: dict | None = None
    output_schema: dict | None = None
    prompt_template: str | None = None
    tools: list | None = None
    test_cases: list | None = None


class RegenerateRequest(BaseModel):
    session_id: str
    section: str
    current_draft: dict


class TestRequest(BaseModel):
    skill_def: dict
    test_input: dict


class PublishRequest(BaseModel):
    session_id: str
    change_log: str = ""
    published_by: str = ""


@router.post("/session")
def create_session(body: SessionCreate, db: Session = Depends(get_db)):
    session = skill_generator.create_session(body.asset_ids, db)
    return {"session_id": session["id"], "assets_context": session["assets_context"]}


@router.post("/chat")
async def chat(req: ChatRequest):
    return StreamingResponse(
        skill_generator.chat_stream(req.session_id, req.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/generate")
def generate(req: GenerateRequest):
    try:
        skill_def = skill_generator.generate_skill(req.session_id)
        return {"skill_def": skill_def}
    except Exception as e:
        raise HTTPException(500, str(e)) from e


@router.get("/draft/{session_id}")
def get_draft(session_id: str):
    session = skill_generator._sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return {"draft": session.get("draft"), "summary": session.get("summary")}


@router.put("/draft/{session_id}")
def update_draft(session_id: str, body: DraftUpdate):
    session = skill_generator._sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if "draft" not in session:
        session["draft"] = {}
    for k, v in body.model_dump(exclude_none=True).items():
        session["draft"][k] = v
    return {"ok": True, "draft": session["draft"]}


@router.post("/draft/{session_id}/regenerate")
def regenerate_section(session_id: str, body: RegenerateRequest):
    try:
        result = skill_generator.regenerate_section(body.session_id, body.section, body.current_draft)
        return {"section": body.section, "result": result}
    except Exception as e:
        raise HTTPException(500, str(e)) from e


@router.post("/test")
def test_skill(body: TestRequest):
    tools = body.skill_def.get("tools", [])
    results = []
    for tool in tools:
        code = tool.get("code", "")
        func_name = tool.get("name", "")
        violations = validate_code(code)
        if violations:
            results.append({"tool": func_name, "success": False, "error": "; ".join(violations)})
            continue
        try:
            output = execute_in_sandbox(code, func_name, body.test_input)
            results.append({"tool": func_name, "success": True, "output": output})
        except Exception as e:
            results.append({"tool": func_name, "success": False, "error": str(e)})
    return {"results": results}


@router.post("/publish")
def publish(body: PublishRequest, db: Session = Depends(get_db)):
    session = skill_generator._sessions.get(body.session_id)
    if not session or "draft" not in session:
        raise HTTPException(400, "No draft to publish")

    draft = session["draft"]

    skill = Skill(
        name=draft.get("name", ""),
        description=draft.get("description", ""),
        skill_type="generated",
        status="draft",
        input_schema=draft.get("input_schema"),
        output_schema=draft.get("output_schema"),
        prompt_template=draft.get("prompt_template", ""),
        tools=draft.get("tools"),
        test_cases=draft.get("test_cases"),
        asset_refs=session.get("asset_ids"),
        created_by=body.published_by,
    )
    db.add(skill)
    db.flush()

    for tool_def in draft.get("tools", []):
        tool = SkillTool(
            skill_id=skill.id,
            name=tool_def.get("name", ""),
            description=tool_def.get("description", ""),
            parameters=tool_def.get("parameters"),
            code=tool_def.get("code", ""),
            code_type="generated",
        )
        db.add(tool)

    version = publish_skill(skill, body.change_log or "Initial release", body.published_by, db)

    del skill_generator._sessions[body.session_id]

    return {"skill_id": skill.id, "version": version.version}
