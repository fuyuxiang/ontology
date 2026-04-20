"""
工作流服务 — 发布编译 + 审批状态机
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.workflow import WorkflowApp, ApprovalTask
from app.services.agent_tools import AGENT_TOOL_SPECS


def compile_canvas_to_runtime(app: WorkflowApp) -> dict[str, Any]:
    """将设计态 canvas_json 编译为运行态 published_json"""
    canvas = app.canvas_json or {"nodes": [], "edges": []}
    nodes = canvas.get("nodes", [])
    edges = canvas.get("edges", [])

    agent_nodes = [n for n in nodes if n.get("data", {}).get("nodeType") == "agent"]
    copilot_nodes = [n for n in nodes if n.get("data", {}).get("nodeType") == "copilot"]
    approval_nodes = [n for n in nodes if n.get("data", {}).get("nodeType") == "approval"]

    # 提取默认 Agent 配置 (取第一个 agent 节点)
    default_agent = None
    if agent_nodes:
        cfg = agent_nodes[0].get("data", {}).get("config", {})
        default_agent = {
            "nodeId": agent_nodes[0]["id"],
            "persona": cfg.get("persona", ""),
            "objective": cfg.get("objective", ""),
            "maxSteps": cfg.get("maxSteps", 8),
            "boundTools": cfg.get("boundTools", []),
        }

    # 收集所有绑定的工具
    all_bound_tools: list[str] = []
    for an in agent_nodes:
        tools = an.get("data", {}).get("config", {}).get("boundTools", [])
        all_bound_tools.extend(tools)
    all_bound_tools = list(set(all_bound_tools))

    # 构建工具绑定详情
    spec_map = {s.name: s for s in AGENT_TOOL_SPECS}
    tool_bindings = []
    for tname in all_bound_tools:
        spec = spec_map.get(tname)
        if spec:
            tool_bindings.append({
                "name": spec.name,
                "description": spec.description,
                "sensitive": getattr(spec, "sensitive", False),
                "parameters": spec.parameters,
                "required": list(spec.required),
            })

    # 审批策略
    sensitive_tools = []
    for an in approval_nodes:
        st = an.get("data", {}).get("config", {}).get("sensitiveTools", [])
        sensitive_tools.extend(st)
    sensitive_tools = list(set(sensitive_tools))

    approval_policy = {
        "sensitiveTools": sensitive_tools,
        "requireApproval": len(sensitive_tools) > 0,
    }

    # Widget 绑定 (copilot → agent)
    edge_map: dict[str, str] = {}
    for e in edges:
        edge_map[e.get("source", "")] = e.get("target", "")

    widget_bindings = []
    for cn in copilot_nodes:
        cfg = cn.get("data", {}).get("config", {})
        bound_agent_id = cfg.get("boundAgentNodeId") or edge_map.get(cn["id"])
        widget_bindings.append({
            "widgetType": "copilot",
            "nodeId": cn["id"],
            "label": cn.get("data", {}).get("label", "Copilot"),
            "boundAgentNodeId": bound_agent_id,
        })

    # 本体范围
    ontology_scope = []
    for n in nodes:
        scope = n.get("data", {}).get("config", {}).get("ontologyScope", [])
        ontology_scope.extend(scope)
    ontology_scope = list(set(ontology_scope))

    return {
        "appId": app.id,
        "appCode": app.code,
        "appName": app.name,
        "sceneCode": app.scene_code,
        "ontologyScope": ontology_scope,
        "defaultAgent": default_agent,
        "toolBindings": tool_bindings,
        "approvalPolicy": approval_policy,
        "widgetBindings": widget_bindings,
        "version": (app.published_version or 0) + 1,
    }


def publish_app(db: Session, app_id: str) -> WorkflowApp:
    app = db.query(WorkflowApp).filter(WorkflowApp.id == app_id).first()
    if not app:
        raise ValueError(f"App {app_id} not found")
    published = compile_canvas_to_runtime(app)
    app.published_json = published
    app.published_version = published["version"]
    app.status = "published"
    db.commit()
    db.refresh(app)
    return app


def create_approval_task(
    db: Session, *, app_id: str, session_id: str,
    tool_name: str, tool_args: dict, created_by: str = "system",
) -> ApprovalTask:
    task = ApprovalTask(
        id=str(uuid.uuid4()),
        app_id=app_id,
        session_id=session_id,
        tool_name=tool_name,
        tool_args=tool_args,
        status="pending",
        created_by=created_by,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def resolve_approval(db: Session, task_id: str, action: str, resolved_by: str = "admin") -> ApprovalTask:
    task = db.query(ApprovalTask).filter(ApprovalTask.id == task_id).first()
    if not task:
        raise ValueError(f"Approval task {task_id} not found")
    if task.status != "pending":
        raise ValueError(f"Task already resolved: {task.status}")
    task.status = action  # "approved" or "rejected"
    task.resolved_by = resolved_by
    task.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task
