"""One observed execution path for draft debugging and immutable public releases."""
import json
import time
from datetime import datetime

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import sessionmaker

from app.models.agent_runtime import AgentRun
from app.models.agent_test_conversation import AgentTestConversation
from app.models.trace import AgentTrace
from app.models.user import User
from app.services.agent_management import config_hash, runtime_context
from app.utils.json import json_safe
from app.utils.time import utc_iso


def run_out(run):
    return {key: utc_iso(getattr(run, key))
            if key in ("started_at", "finished_at") else getattr(run, key)
            for key in ("id", "agent_id", "version", "status", "question", "answer", "steps",
                        "tool_runs", "pending_actions", "error", "started_at", "finished_at")}


def execute_chat(db, agent, snapshot, body, request, user, service_factory,
                 steps_factory, writeback, *, release=None, dependency_user=None):
    question = body.question or ""
    if not question and body.messages:
        question = next((m.get("content") for m in reversed(body.messages)
                         if isinstance(m, dict) and m.get("role") == "user" and m.get("content")), "")
    if not isinstance(question, str) or not question.strip():
        raise HTTPException(422, "请输入问题")
    question = question.strip()
    if len(question) > 20000:
        raise HTTPException(422, "问题不能超过 20000 字")
    cfg = snapshot.get("tools_config") or {}
    if cfg.get("ontology_id") or cfg.get("ontology_version_id") or snapshot.get("ontology_version_id"):
        context = runtime_context(db, snapshot, dependency_user or user, allow_archived=bool(release))
    else:
        # Existing unconfigured drafts can converse but receive no global data or tools.
        context = {"allow_empty": True, "entity_ids": [], "skills": [], "action_mode": "simulation",
                   "max_tool_rounds": 12, "config_hash": config_hash(snapshot)}
    context["user"] = user
    context["agent_id"] = agent.id
    conv, history = None, None
    if body.conversation_id and user and not release:
        candidate = db.get(AgentTestConversation, body.conversation_id)
        if candidate and candidate.agent_id == agent.id and candidate.user_id == user.id:
            conv = candidate
            history = [{"role": m["role"], "content": m["content"]}
                       for m in (candidate.messages or [])[-20:]
                       if m.get("role") in ("user", "assistant") and m.get("content")]
    elif body.messages:
        history = [{"role": m["role"], "content": m["content"]}
                   for m in body.messages[:-1][-20:] if isinstance(m, dict)
                   and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)]
    run = AgentRun(agent_id=agent.id, user_id=user.id if user else None,
                   version=release.version if release else None, config_hash=config_hash(snapshot),
                   question=question, steps=[], tool_runs=[], pending_actions=[])
    db.add(run)
    db.commit()
    context["run_id"] = run.id
    run_id, agent_id = run.id, agent.id
    user_id, conv_id = user.id if user else None, conv.id if conv else None
    session_factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)

    def events():
        # FastAPI may close request dependencies before consuming a streaming body.
        db = session_factory()
        run = db.get(AgentRun, run_id)
        conv = db.get(AgentTestConversation, conv_id) if conv_id else None
        context["user"] = db.get(User, user_id) if user_id else None
        t0 = time.monotonic()
        collector = steps_factory()
        answer = ""
        tools, pending, errors = [], [], []
        suggestions, actions = [], []
        complete, cancelled = False, False
        yield {"type": "run_started", "run_id": run.id, "version": run.version}
        try:
            from app.services.agent_models import model_credentials, model_snapshot
            pinned = snapshot.get("model_snapshot") or model_snapshot(db, snapshot.get("model_id"))
            model_name = pinned.get("model_name")
            model_config = dict(pinned.get("config_json") or {})
            model_config["api_key"] = model_credentials(db, pinned)
            model_config["api_base"] = pinned.get("api_base")
            for key in ("temperature", "max_tokens"):
                if key in cfg:
                    model_config.setdefault(key, cfg[key])
            if snapshot.get("nodes_json"):
                from app.services.agent.graph_engine import GraphEngine
                engine = GraphEngine(db, nodes_json=snapshot["nodes_json"],
                    edges_json=snapshot.get("edges_json") or [], system_prompt=snapshot.get("system_prompt") or "",
                    model_name=model_name, model_config=model_config,
                    runtime_executor=getattr(request.app.state, "runtime_executor", None), runtime_context=context)
                source = engine.run(question)
            else:
                svc = service_factory(db, system_prompt_prefix=snapshot.get("system_prompt") or None,
                    model_name=model_name, model_config=model_config,
                    runtime_executor=getattr(request.app.state, "runtime_executor", None), runtime_context=context)
                source = svc.ask(question, history=history)
            for event in source:
                event = json_safe(event)
                kind = event.get("type")
                if kind == "content":
                    answer += event.get("content") or ""
                elif kind == "answer":
                    answer = event.get("content") or answer
                    complete = True
                elif kind == "error":
                    errors.append(str(event.get("message") or "运行失败"))
                elif kind == "tool_start":
                    tools.append({"tool": event.get("tool"), "arguments": event.get("arguments"), "success": None})
                elif kind == "tool_result":
                    result = event.get("result")
                    success = not (isinstance(result, dict) and (result.get("error") or result.get("success") is False))
                    target = next((t for t in reversed(tools) if t["tool"] == event.get("tool") and t["success"] is None), None)
                    if target is None:
                        target = {"tool": event.get("tool"), "arguments": {}}
                        tools.append(target)
                    target.update(success=success, summary=event.get("summary"), result=result,
                                  resultCount=event.get("resultCount", 0))
                    if not success:
                        errors.append(str(result.get("error") or result.get("message") or event.get("summary")))
                elif kind == "action_pending":
                    pending.append({**event, "status": "pending"})
                elif kind == "done":
                    suggestions, actions = event.get("suggestions") or [], event.get("actions") or []
                    complete = True
                collector.feed(event)
                yield event
            if not complete or not answer.strip():
                errors.append("运行没有返回完整回答")
                yield {"type": "error", "message": errors[-1]}
        except GeneratorExit:
            cancelled = True
            raise
        except Exception as exc:
            errors.append(str(exc))
            yield {"type": "error", "message": str(exc)}
        finally:
            run.status = "cancelled" if cancelled else "failed" if errors else "pending_confirmation" if pending else "completed"
            run.answer, run.steps, run.tool_runs, run.pending_actions = answer, collector.result(), tools, pending
            run.error, run.finished_at = "\n".join(dict.fromkeys(errors)) or None, datetime.utcnow()
            db.add(run)
            db.add(AgentTrace(agent_id=agent_id, input_text=question, output_text=answer,
                latency_ms=int((time.monotonic() - t0) * 1000), status="ok" if not errors and not cancelled else "error"))
            db.commit()
            writeback(db, conv, question, answer, collector.result(), pending)
            db.close()
        yield {"type": "run_finished", "run_id": run.id, "status": run.status,
               "error": run.error, "suggestions": suggestions, "actions": actions}

    if body.stream is False:
        collected = list(events())
        db.refresh(run)
        finish = collected[-1] if collected else {}
        return {**run_out(run), "content": run.answer, "suggestions": finish.get("suggestions", []),
                "actions": finish.get("actions", [])}

    def stream():
        for event in events():
            yield f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "X-Agent-Run": run.id})
