"""Resume the unexecuted suffix of a persisted graph after one-use approval."""
from datetime import datetime

from app.models.agent_runtime import AgentPendingAction, AgentRun
from app.models.agent_test_conversation import AgentTestConversation
from app.services.agent.graph_engine import GraphEngine
from app.services.agent_models import model_credentials
from app.utils.json import json_safe


def resume_confirmed_graph(db, pending, user, request):
    checkpoint = (pending.action_snapshot or {}).get("_graph_checkpoint")
    run = db.get(AgentRun, pending.run_id) if pending.run_id else None
    if not checkpoint or not run:
        return False
    if (pending.result or {}).get("graph_resume_started"):
        return False
    # Durable claim precedes resumption: a repeated confirmation can repair records,
    # but must never rerun already completed nodes or another effectful suffix.
    changed = db.query(AgentPendingAction).filter_by(id=pending.id, status="approved").filter(
        AgentPendingAction.result == pending.result).update(
        {"status": "resuming", "result": {**(pending.result or {}), "graph_resume_started": True,
            "continuation_status": "resuming"}}, synchronize_session=False)
    db.commit()
    db.refresh(pending)
    if not changed:
        return False
    context = dict(checkpoint.get("runtime_context") or {})
    context.update(user=user, run_id=run.id, agent_id=run.agent_id,
                   agent_snapshot=checkpoint.get("snapshot"))
    state = dict(checkpoint.get("context") or {})
    previous = state.get(checkpoint["node_id"])
    if isinstance(previous, dict) and previous.get("_loop_resume"):
        loop = previous["_loop_resume"]
        outputs = list(loop.get("outputs") or [])
        output = (pending.result or {}).get("output") or {}
        outputs[-1] = {"success": True, "value": output.get("result"), "outcome": output.get("outcome"),
            "committed_writes": output.get("committed_writes")}
        state[checkpoint["node_id"]] = {"_resume_loop": {**loop, "outputs": outputs}}
    else:
        state[checkpoint["node_id"]] = json_safe(pending.result)
    model_config = dict(checkpoint.get("model_config") or {})
    tools, proposed, steps, answer, errors = [], [], [], "", []
    complete = False
    uncertain = False
    try:
        if context.get("model_snapshot"):
            model_config["api_key"] = model_credentials(db, context["model_snapshot"])
        engine = GraphEngine(db, nodes_json=checkpoint["nodes"], edges_json=checkpoint["edges"],
            system_prompt=checkpoint.get("system_prompt", ""), model_name=checkpoint.get("model_name"),
            model_config=model_config, runtime_context=context,
            runtime_executor=getattr(request.app.state, "runtime_executor", None))
        if checkpoint.get("mode") == "scene":
            scene_checkpoint = {**checkpoint, "context": state}
            node_io = dict(checkpoint.get("node_io") or {})
            if checkpoint["node_id"] in node_io:
                node_io[checkpoint["node_id"]] = {**node_io[checkpoint["node_id"]], "output": json_safe(pending.result)}
            scene_checkpoint["node_io"] = node_io
            source = engine.run_for_scene(checkpoint=scene_checkpoint)
        else:
            source = engine.run(run.question, initial_context=state)
        for raw in source:
            event = json_safe(raw)
            steps.append(event)
            kind = event.get("type")
            if kind == "content":
                answer += event.get("content") or ""
            elif kind in {"error", "scene_failed"}:
                errors.append(event.get("message") or event.get("error") or "图恢复失败")
                failed = event.get("result") or {}
                uncertain = uncertain or failed.get("outcome") in {"unknown", "committed_unrecorded", "partial_committed"}
            elif kind == "action_pending":
                proposed.append({**event, "status": "pending"})
            elif kind == "tool_result":
                result = event.get("result") or {}
                if isinstance(result, dict):
                    nested = result.get("output") if isinstance(result.get("output"), dict) else {}
                    uncertain = uncertain or (result.get("outcome") or nested.get("outcome")) in {"unknown", "committed_unrecorded", "partial_committed"}
                success = not (isinstance(result, dict) and (result.get("error") or result.get("success") is False))
                tools.append({"tool": event.get("tool"), "result": result, "success": success,
                              "summary": event.get("summary"), "resultCount": event.get("resultCount", 0)})
                if not success:
                    errors.append(str(result.get("error") or result.get("message") or event.get("summary")))
            elif kind == "scene_finished":
                import json
                answer = json.dumps(event.get("final_output") or {}, ensure_ascii=False, default=str)
                complete = True
            elif kind == "scene_waiting_confirmation":
                answer = "业务行动已提出，等待有权限的用户确认后执行。"
                complete = True
            elif kind == "done":
                complete = True
        if not complete or not answer.strip():
            errors.append("图恢复未返回完整结果")
    except Exception as exc:
        errors.append(str(exc))
    run.steps = list(run.steps or []) + steps
    run.tool_runs = list(run.tool_runs or []) + tools
    run.pending_actions = list(run.pending_actions or []) + proposed
    run.status = "unknown" if uncertain else "failed" if errors else "pending_confirmation" if proposed else "completed"
    run.error = "\n".join(dict.fromkeys(errors)) or None
    run.answer = answer or run.answer
    run.finished_at = datetime.utcnow()
    pending.status = "approved"
    pending.result = {**(pending.result or {}), "continuation_status": run.status,
                      "continuation_error": run.error}
    db.add_all([run, pending])
    for conv in db.query(AgentTestConversation).filter_by(agent_id=pending.agent_id, user_id=pending.user_id):
        conv.messages = [{**message, "content": run.answer, "steps": run.steps,
                          "pending_actions": run.pending_actions}
                         if any(item.get("pending_id") == pending.id for item in message.get("pending_actions", []))
                         else message for message in conv.messages or []]
        db.add(conv)
    db.commit()
    return True
