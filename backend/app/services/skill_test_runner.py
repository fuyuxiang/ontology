"""Run skill cases through the same scoped LLM/tool loop used by applications."""
import json

from app.database import SessionLocal
from app.services.agent.orchestrator import AgentService
from app.utils.json import json_safe


def run_skill_case(snapshot, case, user):
    with SessionLocal() as db:
        skill = {**snapshot, "skill_id": snapshot["id"], "version": "draft"}
        context = {"ontology_id": snapshot["ontology_id"], "ontology_version_id": snapshot["ontology_version_id"],
                   "entity_ids": snapshot["entity_ids"], "skills": [skill], "action_mode": "simulation",
                   "max_tool_rounds": 12, "restrict_to_skill_tools": True, "user": user}
        value = case["input"]
        question = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        answer, runs, errors = "", [], []
        skill_loaded = False
        try:
            svc = AgentService(db, runtime_context=context,
                system_prompt_prefix=f"请使用技能「{snapshot['name']}」完成任务，先 load_skill 加载该技能，再严格按其步骤执行。")
            complete = False
            for event in svc.ask(question):
                event = json_safe(event)
                kind = event.get("type")
                if kind == "content":
                    answer += event.get("content") or ""
                elif kind == "answer":
                    answer = event.get("content") or answer
                    complete = True
                elif kind == "done":
                    complete = True
                elif kind == "error":
                    errors.append(event.get("message") or "运行失败")
                elif kind == "skill_load" and event.get("skill_id") == snapshot["id"]:
                    skill_loaded = True
                elif kind == "tool_start":
                    runs.append({"tool": event["tool"], "arguments": event.get("arguments"), "success": False})
                elif kind == "tool_result":
                    result = event.get("result") or {}
                    success = not (isinstance(result, dict) and (result.get("error") or result.get("success") is False))
                    target = next((r for r in reversed(runs) if r["tool"] == event["tool"]), None)
                    if target:
                        target.update(success=success, summary=event.get("summary"), result=result)
                    if not success:
                        errors.append(str(result.get("error") or result.get("message") or event.get("summary")))
            if not complete:
                errors.append("运行未完成")
            if not skill_loaded:
                errors.append("本次运行未实际加载技能指引，不能作为该技能的测试证据")
        except Exception as exc:
            errors.append(str(exc))
        return {"answer": answer, "tool_runs": runs, "error": "\n".join(errors) or None}
