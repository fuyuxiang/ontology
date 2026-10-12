"""Recover interrupted local runs without retrying any business side effect."""
from datetime import datetime

from app.models.agent_runtime import AgentPendingAction, AgentRun
from app.models.trace import AgentTrace


def recover_interrupted_runs(db):
    from app.api.v1.agents import _sync_pending_status
    pending = db.query(AgentPendingAction).filter(AgentPendingAction.status.in_(["executing", "resuming"])).all()
    for action in pending:
        resuming = action.status == "resuming"
        action.status = "unknown"
        action.result = {**(action.result or {}), "success": False, "outcome": "unknown",
                         "message": "行动已执行成功，但图后续恢复期间服务重启；请核查后续结果，授权不会重放" if resuming else
                                    "服务在行动执行期间重启，无法确认外部结果，请回读业务数据；授权不会重放"}
        if resuming:
            action.result.update(graph_resume_started=True, continuation_status="unknown",
                                 continuation_error="图后续执行期间服务重启，请核查后续结果；不可重放原检查点")
        db.add(action)
    for run in db.query(AgentRun).filter_by(status="running").all():
        run.status, run.error = "interrupted", "服务在执行期间重启，请重新发起查询；先核查任何已提出行动"
        run.finished_at = datetime.utcnow()
        trace = db.get(AgentTrace, run.id)
        if trace:
            trace.status = "error"
    db.commit()
    for action in db.query(AgentPendingAction).filter(
            AgentPendingAction.status.in_(["approved", "failed", "unknown", "rejected", "expired"])).all():
        _sync_pending_status(db, action)
    return len(pending)
