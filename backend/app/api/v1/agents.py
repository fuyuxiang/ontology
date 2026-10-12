import copy
import json
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.deps import require_user
from app.database import get_db
from app.models.agent import Agent, ModelRegistry
from app.models.agent_runtime import AgentPendingAction, AgentRun, AgentVersion
from app.models.agent_test_conversation import AgentTestConversation
from app.models.user import User
from app.schemas.action import ActionReconciliation
from app.services.agent.orchestrator import AgentService
from app.services.agent_management import (
    CONFIG_FIELDS,
    config_hash,
    config_snapshot,
    last_test,
    latest_version,
    normalize_tools_config,
    publish_agent_version,
    require_edit,
    runtime_context,
    validate_agent,
)
from app.utils.json import json_safe
from app.utils.time import utc_iso

router = APIRouter(prefix="/agents", tags=["agents"])
open_router = APIRouter(prefix="/open/agents", tags=["open-api"])

HISTORY_MAX_TURNS = 10  # 最近 N 轮（每轮 user+assistant 共 2 条）


def require_agent_user(user: User = Depends(require_user)) -> User:
    if not user.is_active:
        raise HTTPException(403, "账号已停用")
    return user


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = ""
    tags: list[str] | None = None
    model_id: str | None = None
    system_prompt: str | None = ""
    kb_ids: list[str] | None = None
    entity_ids: list[str] | None = None
    tools_config: dict | None = None
    nodes_json: list[dict] | None = None
    edges_json: list[dict] | None = None

    @field_validator("name")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("智能体名称不能为空")
        return value.strip()


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    tags: list[str] | None = None
    model_id: str | None = None
    system_prompt: str | None = None
    kb_ids: list[str] | None = None
    entity_ids: list[str] | None = None
    tools_config: dict | None = None
    nodes_json: list[dict] | None = None
    edges_json: list[dict] | None = None
    status: str | None = None

    @field_validator("name")
    @classmethod
    def nonblank(cls, value):
        if value is not None and not value.strip():
            raise ValueError("智能体名称不能为空")
        return value.strip() if value else value


class ChatRequest(BaseModel):
    messages: list[dict] | None = None
    question: str | None = Field(default=None, max_length=20000)
    stream: bool | None = True
    conversation_id: str | None = None


def _agent_out(a: Agent, db: Session, user: User | None = None) -> dict:
    from app.core.permissions import has_permission
    model_name = None
    if a.model_id:
        m = db.get(ModelRegistry, a.model_id)
        model_name = m.name if m else None
    release = latest_version(db, a.id)
    cfg = a.tools_config or {}
    referenced_ontology_ids = {cfg["ontology_id"]} if cfg.get("ontology_id") else set()
    for version in db.query(AgentVersion).filter_by(agent_id=a.id).all():
        oid = (version.config_snapshot.get("tools_config") or {}).get("ontology_id")
        if oid:
            referenced_ontology_ids.add(oid)
    return {
        "id": a.id,
        "name": a.name,
        "description": a.description,
        "tags": a.tags or [],
        "model_id": a.model_id,
        "model_name": model_name,
        "system_prompt": a.system_prompt,
        "kb_ids": a.kb_ids or [],
        "entity_ids": a.entity_ids or [],
        "nodes_json": a.nodes_json or [],
        "edges_json": a.edges_json or [],
        "tools_config": a.tools_config or {},
        "status": a.status,
        "api_key": a.api_key if a.status == "published" and user and has_permission(user, "rule:write", db) else None,
        "ontology_id": cfg.get("ontology_id"),
        "referenced_ontology_ids": sorted(referenced_ontology_ids),
        "ontology_version_id": cfg.get("ontology_version_id") or a.ontology_version_id,
        "skill_bindings": cfg.get("skill_bindings", []),
        "current_version": release.version if release else 0,
        "has_changes": not release or release.config_hash != config_hash(config_snapshot(a)),
        "last_test": last_test(db, a),
        "ontology_stale": a.ontology_stale,
        "ontology_stale_detail": a.ontology_stale_detail,
        "created_at": utc_iso(a.created_at),
        "updated_at": utc_iso(a.updated_at),
    }


@router.get("")
def list_agents(db: Session = Depends(get_db), user: User = Depends(require_agent_user)):
    return [_agent_out(a, db, user) for a in db.query(Agent).order_by(Agent.updated_at.desc()).all()]


@router.post("", status_code=201)
def create_agent(body: AgentCreate, db: Session = Depends(get_db), user: User = Depends(require_agent_user)):
    require_edit(user)
    data = body.model_dump()
    data["tools_config"] = normalize_tools_config(data.get("tools_config"))
    data["tools_config"]["owner_id"] = user.id
    a = Agent(**data)
    a.ontology_version_id = data["tools_config"].get("ontology_version_id")
    db.add(a)
    db.commit()
    db.refresh(a)
    return _agent_out(a, db, user)


@router.get("/{aid}")
def get_agent(aid: str, db: Session = Depends(get_db), user: User = Depends(require_agent_user)):
    a = db.get(Agent, aid)
    if not a:
        raise HTTPException(404, "Agent not found")
    return _agent_out(a, db, user)


@router.put("/{aid}")
def update_agent(aid: str, body: AgentUpdate, db: Session = Depends(get_db), user: User = Depends(require_agent_user)):
    require_edit(user)
    a = db.get(Agent, aid)
    if not a:
        raise HTTPException(404, "Agent not found")
    changes = body.model_dump(exclude_unset=True)
    if "status" in changes and changes["status"] != "draft":
        raise HTTPException(422, "请通过发布接口发布智能体")
    if "tools_config" in changes:
        cfg = normalize_tools_config(changes["tools_config"])
        cfg["owner_id"] = (a.tools_config or {}).get("owner_id") or user.id
        changes["tools_config"] = cfg
        a.ontology_version_id = cfg.get("ontology_version_id")
    for k, v in changes.items():
        if k == "name" and v is None:
            raise HTTPException(422, "智能体名称不能为空")
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return _agent_out(a, db, user)


@router.delete("/{aid}")
def delete_agent(aid: str, db: Session = Depends(get_db), user: User = Depends(require_agent_user)):
    require_edit(user)
    a = db.get(Agent, aid)
    if not a:
        raise HTTPException(404, "Agent not found")
    # Scene/workflow references are retained in other agents' canvas configurations.
    for other in db.query(Agent).filter(Agent.id != aid).all():
        if any((n.get("data") or {}).get("agent_id") == aid for n in other.nodes_json or []):
            raise HTTPException(409, "该智能体被其他流程引用，请先解除引用")
    for release in db.query(AgentVersion).filter(AgentVersion.agent_id != aid).all():
        nodes = (release.config_snapshot or {}).get("nodes_json") or []
        if any((n.get("data") or {}).get("agent_id") == aid for n in nodes):
            raise HTTPException(409, "该智能体被其他流程发布版本引用，不能删除")
    from app.models.eval import EvalCase, EvalResult, EvalRun, EvalSuite
    suite_ids = [s.id for s in db.query(EvalSuite).filter_by(agent_id=aid).all()]
    if suite_ids:
        run_ids = [r.id for r in db.query(EvalRun).filter(EvalRun.suite_id.in_(suite_ids)).all()]
        case_ids = [c.id for c in db.query(EvalCase).filter(EvalCase.suite_id.in_(suite_ids)).all()]
        db.query(EvalResult).filter((EvalResult.run_id.in_(run_ids)) | (EvalResult.case_id.in_(case_ids))).delete(synchronize_session=False)
        db.query(EvalRun).filter(EvalRun.suite_id.in_(suite_ids)).delete(synchronize_session=False)
        db.query(EvalCase).filter(EvalCase.suite_id.in_(suite_ids)).delete(synchronize_session=False)
        db.query(EvalSuite).filter(EvalSuite.id.in_(suite_ids)).delete(synchronize_session=False)
    db.query(AgentPendingAction).filter_by(agent_id=aid).delete()
    db.query(AgentRun).filter_by(agent_id=aid).delete()
    db.query(AgentVersion).filter_by(agent_id=aid).delete()
    db.query(AgentTestConversation).filter_by(agent_id=aid).delete()
    from app.models.trace import AgentTrace
    db.query(AgentTrace).filter_by(agent_id=aid).delete()
    db.delete(a)
    db.commit()
    return {"ok": True}


@router.post("/{aid}/publish")
def publish_agent(aid: str, db: Session = Depends(get_db), user: User = Depends(require_agent_user)):
    a = db.get(Agent, aid)
    if not a:
        raise HTTPException(404, "Agent not found")
    if not a.api_key:
        a.api_key = secrets.token_urlsafe(32)
    publish_agent_version(db, a, user)
    db.refresh(a)
    return _agent_out(a, db, user)


@router.get("/{aid}/api-info")
def get_api_info(aid: str, db: Session = Depends(get_db), user: User = Depends(require_agent_user)):
    require_edit(user)
    a = db.get(Agent, aid)
    if not a:
        raise HTTPException(404, "Agent not found")
    if a.status != "published":
        raise HTTPException(400, "Agent not published")
    endpoint = f"/api/v1/open/agents/{aid}/chat"
    curl = (
        f'curl -X POST "{endpoint}" \\\n'
        f'  -H "Content-Type: application/json" \\\n'
        f'  -H "X-Agent-Key: {a.api_key}" \\\n'
        f'  -d \'{{"messages": [{{"role": "user", "content": "你好"}}]}}\''
    )
    return {"endpoint": endpoint, "api_key": a.api_key, "curl": curl}


def _conv_out(conv: AgentTestConversation, with_messages: bool = False) -> dict:
    out = {
        "id": conv.id,
        "agent_id": conv.agent_id,
        "title": conv.title,
        "created_at": utc_iso(conv.created_at),
        "updated_at": utc_iso(conv.updated_at),
    }
    if with_messages:
        out["messages"] = conv.messages or []
    return out


def _get_owned_conv(db: Session, aid: str, cid: str, user: User) -> AgentTestConversation:
    conv = db.get(AgentTestConversation, cid)
    if not conv or conv.agent_id != aid or conv.user_id != user.id:
        raise HTTPException(404, "会话不存在")
    return conv


@router.get("/{aid}/conversations")
def list_conversations(aid: str, db: Session = Depends(get_db), user: User = Depends(require_agent_user)):
    rows = (
        db.query(AgentTestConversation)
        .filter_by(agent_id=aid, user_id=user.id)
        .order_by(AgentTestConversation.updated_at.desc())
        .all()
    )
    return [_conv_out(c, with_messages=False) for c in rows]


@router.post("/{aid}/conversations")
def create_conversation(aid: str, db: Session = Depends(get_db), user: User = Depends(require_agent_user)):
    if not db.get(Agent, aid):
        raise HTTPException(404, "Agent not found")
    conv = AgentTestConversation(agent_id=aid, user_id=user.id)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return _conv_out(conv, with_messages=True)


@router.get("/{aid}/conversations/{cid}")
def get_conversation(aid: str, cid: str, db: Session = Depends(get_db), user: User = Depends(require_agent_user)):
    conv = _get_owned_conv(db, aid, cid, user)
    return _conv_out(conv, with_messages=True)


@router.delete("/{aid}/conversations/{cid}")
def delete_conversation(aid: str, cid: str, db: Session = Depends(get_db), user: User = Depends(require_agent_user)):
    conv = _get_owned_conv(db, aid, cid, user)
    db.delete(conv)
    db.commit()
    return {"ok": True}


# 工具名 → (阶段, 中文名)。阶段用于前端思考过程时间线分组：
#   ontology 本体查询 / logic 逻辑计算 / action 执行动作
#   （intent 意图识别、answer 生成回答为前端合成阶段，不来自工具）
_TOOL_META: dict[str, tuple[str, str]] = {
    # ── 本体查询：读取模型/结构、取数、查实例 ──
    "describe_ontology_model": ("ontology", "读取本体模型"),
    "get_entity_detail": ("ontology", "读取实体详情"),
    "query_entity_data": ("ontology", "查询实体数据"),
    "ontology_query_instances": ("ontology", "查询实体实例"),
    "ontology_get_attr_mapping": ("ontology", "读取属性映射"),
    "ontology_complex_sql": ("ontology", "执行复杂查询"),
    "ontology_list_capabilities": ("ontology", "列出本体能力"),
    "query_datasource": ("ontology", "查询数据源"),
    "list_datasources": ("ontology", "查询数据源列表"),
    "get_table_schema": ("ontology", "读取表结构"),
    "list_business_datasources": ("ontology", "查询业务数据源"),
    "list_business_documents": ("ontology", "查询业务文档"),
    "analyze_assets_for_ontology": ("ontology", "分析资产生成本体"),
    # ── 逻辑计算：执行逻辑函数 ──
    "ontology_run_logic": ("logic", "执行逻辑函数"),
    "run_function": ("logic", "执行业务函数"),
    "load_skill": ("skill", "加载业务技能"),
    "run_action": ("action", "提出业务行动"),
    # ── 执行动作：有副作用的业务动作 ──
    "execute_action": ("action", "执行动作"),
    "ontology_run_action": ("action", "执行动作函数"),
}


def _tool_meta(tool: str) -> tuple[str, str]:
    """返回工具的 (阶段, 中文名)。画布节点工具名形如 "[节点标签]"。"""
    if tool.startswith("[") and tool.endswith("]"):
        return ("action", tool[1:-1])
    return _TOOL_META.get(tool, ("ontology", tool))


class _collect_steps:
    """把 chat 流中的 tool_start/tool_result 事件累积成结构化思考步骤。

    每一步形如 {category, tool, label, arguments, summary, resultCount, detail}，
    随流实时推入前端时间线，结束后整体写回会话记录以便历史回看。
    """

    def __init__(self) -> None:
        self._steps: list[dict] = []

    def feed(self, event: dict) -> None:
        etype = event.get("type")
        if etype == "tool_start":
            tool = event.get("tool", "")
            category, label = _tool_meta(tool)
            self._steps.append({
                "category": category,
                "tool": tool,
                "label": label,
                "arguments": event.get("arguments"),
                "summary": None,
                "resultCount": None,
                "detail": None,
            })
        elif etype == "tool_result":
            tool = event.get("tool", "")
            # 就近回填最后一个同名且未完成的步骤，否则补一条
            target = None
            for s in reversed(self._steps):
                if s["tool"] == tool and s["summary"] is None:
                    target = s
                    break
            if target is None:
                category, label = _tool_meta(tool)
                target = {
                    "category": category,
                    "tool": tool,
                    "label": label,
                    "arguments": None,
                }
                self._steps.append(target)
            target["summary"] = event.get("summary")
            target["resultCount"] = event.get("resultCount")
            target["detail"] = event.get("detail")

    def result(self) -> list[dict]:
        return self._steps


def _writeback_conversation(
    db: Session, conv, question: str, answer: str, steps: list | None = None,
    pending_actions: list | None = None,
) -> bool:
    """把本轮问答追加写回会话；返回是否完成持久化，调用者记录保存失败。

    steps 为本轮 assistant 的思考过程（工具调用链），一并存入 assistant 消息，
    便于历史会话回看时重现"使用本体、调用逻辑、执行动作"的过程。
    """
    if conv is None:
        return True
    try:
        msgs = list(conv.messages or [])
        msgs.append({"role": "user", "content": question})
        assistant_msg: dict = {"role": "assistant", "content": answer}
        if steps:
            assistant_msg["steps"] = steps
        if pending_actions:
            assistant_msg["pending_actions"] = pending_actions
        msgs.append(assistant_msg)
        conv.messages = msgs
        if not conv.title or conv.title == "新会话":
            conv.title = question.strip()[:30] or "新会话"
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(conv, "messages")
        db.add(conv)
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False


@router.post("/{aid}/chat")
async def chat_with_agent(aid: str, body: ChatRequest, request: Request,
                          db: Session = Depends(get_db), user: User = Depends(require_agent_user)):
    from app.services.agent_chat import execute_chat
    a = db.get(Agent, aid)
    if not a:
        raise HTTPException(404, "智能体不存在")
    if not user.is_active:
        raise HTTPException(403, "账号已停用")
    return execute_chat(db, a, config_snapshot(a), body, request, user,
                        AgentService, _collect_steps, _writeback_conversation)


def _public_agent(db, aid, key):
    a = db.get(Agent, aid)
    if not a:
        raise HTTPException(404, "智能体不存在")
    if a.status != "published":
        raise HTTPException(403, "智能体未发布")
    if not a.api_key or not key or not secrets.compare_digest(a.api_key, key):
        raise HTTPException(401, "无效或缺少 X-Agent-Key")
    release = latest_version(db, aid)
    if not release:
        raise HTTPException(409, "该旧版智能体尚无可用发布快照，请重新测试并发布")
    publisher = db.get(User, release.published_by)
    if not publisher or not publisher.is_active:
        raise HTTPException(403, "发布身份已不可用，请由有效用户重新发布")
    return a, release, publisher


@open_router.post("/{aid}/chat")
async def open_chat(aid: str, body: ChatRequest, request: Request,
                    x_agent_key: str | None = Header(None, alias="X-Agent-Key"),
                    db: Session = Depends(get_db)):
    from app.services.agent_chat import execute_chat
    a, release, publisher = _public_agent(db, aid, x_agent_key)
    return execute_chat(db, a, copy.deepcopy(release.config_snapshot), body, request, None,
                        AgentService, _collect_steps, _writeback_conversation,
                        release=release, dependency_user=publisher)


@open_router.get("/{aid}/info")
def open_agent_info(aid: str, x_agent_key: str | None = Header(None, alias="X-Agent-Key"),
                    db: Session = Depends(get_db)):
    a, release, _ = _public_agent(db, aid, x_agent_key)
    snap = release.config_snapshot
    return {"id": a.id, "name": snap["name"], "description": snap.get("description"),
            "tags": snap.get("tags") or [], "version": release.version}


@router.post("/{aid}/validate")
def check_agent(aid: str, db: Session = Depends(get_db), user: User = Depends(require_agent_user)):
    a = db.get(Agent, aid)
    if not a:
        raise HTTPException(404, "智能体不存在")
    return validate_agent(db, a, user)


@router.get("/{aid}/versions")
def list_versions(aid: str, db: Session = Depends(get_db), user: User = Depends(require_agent_user)):
    from app.services.agent_models import public_snapshot
    if not db.get(Agent, aid):
        raise HTTPException(404, "智能体不存在")
    return [{"id": v.id, "version": v.version, "description": v.description,
             "published_at": utc_iso(v.published_at), "config_snapshot": public_snapshot(v.config_snapshot)}
            for v in db.query(AgentVersion).filter_by(agent_id=aid).order_by(AgentVersion.version.desc()).all()]


class RollbackRequest(BaseModel):
    version: int = Field(ge=1)


@router.post("/{aid}/rollback")
def rollback_agent(aid: str, body: RollbackRequest, db: Session = Depends(get_db),
                   user: User = Depends(require_agent_user)):
    require_edit(user)
    a = db.get(Agent, aid)
    release = db.query(AgentVersion).filter_by(agent_id=aid, version=body.version).first()
    if not a or not release:
        raise HTTPException(404, "发布版本不存在")
    snap = copy.deepcopy(release.config_snapshot)
    runtime_context(db, snap, user, allow_archived=True)
    for key in CONFIG_FIELDS:
        if key in snap:
            setattr(a, key, snap[key])
    # Restore a reviewable draft; the current public version remains pinned.
    from app.services.audit import write_audit
    write_audit(db, user_id=user.id, user_name=user.name, action="rollback", target_type="agent",
                target_id=a.id, target_name=a.name, details=f"恢复版本 {body.version} 为草稿")
    db.commit()
    return _agent_out(a, db, user)


@router.get("/{aid}/runs")
def list_runs(aid: str, db: Session = Depends(get_db), user: User = Depends(require_agent_user)):
    from app.services.agent_chat import run_out
    if not db.get(Agent, aid):
        raise HTTPException(404, "智能体不存在")
    rows = db.query(AgentRun).filter_by(agent_id=aid)
    if user.role != "admin":
        rows = rows.filter_by(user_id=user.id)
    return [run_out(run) for run in rows.order_by(AgentRun.started_at.desc()).limit(100).all()]


@router.get("/{aid}/runs/{rid}")
def get_run(aid: str, rid: str, db: Session = Depends(get_db), user: User = Depends(require_agent_user)):
    from app.services.agent_chat import run_out
    run = db.get(AgentRun, rid)
    if not run or run.agent_id != aid or (user.role != "admin" and run.user_id != user.id):
        raise HTTPException(404, "运行记录不存在")
    return run_out(run)


class ActionDecisionRequest(BaseModel):
    approve: bool


@router.post("/{aid}/actions/{pending_id}/confirm")
def confirm_action(aid: str, pending_id: str, body: ActionDecisionRequest, request: Request,
                   db: Session = Depends(get_db), user: User = Depends(require_agent_user)):
    from app.services.agent_actions import execute_action_snapshot
    from app.services.audit import write_audit
    from app.core.permissions import has_permission
    if not (has_permission(user, "rule:execute", db) or has_permission(user, "rule:write", db)):
        raise HTTPException(403, "需要行动执行权限")
    pending = db.get(AgentPendingAction, pending_id)
    if not pending or pending.agent_id != aid or (user.role != "admin" and pending.user_id != user.id):
        raise HTTPException(404, "待确认行动不存在")
    if pending.status == "pending" and pending.expires_at <= datetime.utcnow():
        db.query(AgentPendingAction).filter_by(id=pending.id, status="pending").update({"status": "expired"})
        db.commit()
        db.refresh(pending)
        _sync_pending_status(db, pending)
    if pending.status == "pending":
        agent = db.get(Agent, aid)
        release = latest_version(db, aid)
        approved_hashes = {config_hash(config_snapshot(agent))} if agent else set()
        if agent and agent.status == "published" and release:
            approved_hashes.add(release.config_hash)
        if pending.config_hash not in approved_hashes:
            raise HTTPException(409, "智能体配置已变更，请重新运行后授权")
        target_status = "executing" if body.approve else "rejected"
        changed = db.query(AgentPendingAction).filter_by(id=pending.id, status="pending").update(
            {"status": target_status, "confirmed_at": datetime.utcnow()}, synchronize_session=False)
        db.commit()
        db.refresh(pending)
        if changed and body.approve:
            _sync_pending_status(db, pending)
            action = pending.action_snapshot
            try:
                from app.services.agent_actions import action_execution_context
                result = execute_action_snapshot(db, action, pending.params, dry_run=False,
                    context=action_execution_context(action, user=user))
                pending.result = json_safe({"success": result.success, "message": result.message, "output": result.output})
                uncertain = isinstance(result.output, dict) and result.output.get("outcome") in {"unknown", "committed_unrecorded", "partial_committed"}
                pending.status = "unknown" if uncertain else "approved" if result.success else "failed"
            except (TimeoutError, ConnectionError) as exc:
                pending.result, pending.status = {"success": False, "message": str(exc),
                    "outcome": getattr(exc, "outcome", "unknown"),
                    "observed_result": getattr(exc, "observed_result", None)}, "unknown"
            except Exception as exc:
                pending.result, pending.status = {"success": False, "message": str(exc)}, "failed"
            db.add(pending)
            observed_result = pending.result
            try:
                if pending.status == "approved":
                    _increment_action_impact(db, pending.action_id)
                write_audit(db, user_id=user.id, user_name=user.name, action="execute", target_type="agent_action",
                            target_id=pending.id, target_name=action.get("name", ""), details=pending.status,
                            status="success" if pending.status == "approved" else pending.status)
                db.commit()
            except Exception as exc:
                db.rollback()
                _record_uncertain_pending(db, pending.id, observed_result,
                    "行动执行已返回，但结果记录失败；请核查业务回执，原授权不会重发")
                raise HTTPException(503, detail={"status": "unknown", "result": observed_result,
                    "message": "行动执行已返回，但结果记录失败；不要重新执行，请核查业务数据和运行记录"}) from exc
            if pending.status == "approved" and action.get("_graph_checkpoint"):
                from app.services.agent_graph_resume import resume_confirmed_graph
                try:
                    resume_confirmed_graph(db, pending, user, request)
                except Exception as exc:
                    db.rollback()
                    _record_uncertain_pending(db, pending.id, observed_result,
                        "行动已完成，但后续图执行或记录未确认；请核查后续结果，原检查点不可重放", continuation=True)
                    raise HTTPException(503, detail={"status": "unknown", "result": observed_result,
                        "message": "行动已完成，但后续图执行或记录未确认；不要重复执行，请核查业务回执和运行记录"}) from exc
        if changed:
            _sync_pending_status(db, pending)
    elif pending.status != "pending":
        # Repair an interrupted projection write without replaying the external action.
        _sync_pending_status(db, pending)
    summaries = {"approved": "行动已授权并执行", "rejected": "行动已拒绝，未执行", "expired": "授权已过期，未执行",
                 "executing": "行动正在执行，请稍后刷新", "failed": "行动执行失败，请查看原因"}
    summaries["unknown"] = "行动结果未知，请核查业务回执；该授权不会重复执行"
    summaries["resuming"] = "行动已完成，后续图执行正在处理；请刷新运行记录"
    return {"status": pending.status, "result": pending.result, "summary": summaries.get(pending.status, pending.status)}


def _increment_action_impact(db, action_id):
    from sqlalchemy import func
    from app.models.action import EntityAction
    db.query(EntityAction).filter_by(id=action_id).update(
        {"impact_count": func.coalesce(EntityAction.impact_count, 0) + 1}, synchronize_session=False)


def _record_uncertain_pending(db, pending_id, observed_result, message, *, continuation=False):
    """Best-effort durable recovery after a failed projection commit, with no replay."""
    try:
        pending = db.get(AgentPendingAction, pending_id)
        if not pending:
            return
        result = {**(observed_result or {}), "success": False, "message": message,
                  "outcome": "committed_unrecorded" if (observed_result or {}).get("success") else "unknown",
                  "observed_result": observed_result}
        if continuation:
            result.update(graph_resume_started=True, continuation_status="unknown", continuation_error=message)
        pending.status, pending.result = "unknown", json_safe(result)
        db.commit()
        _sync_pending_status(db, pending)
    except Exception:
        db.rollback()


def _owned_pending(db, aid, pending_id, user):
    from app.core.permissions import has_permission
    if not (has_permission(user, "rule:execute", db) or has_permission(user, "rule:write", db)):
        raise HTTPException(403, "需要行动执行权限")
    pending = db.get(AgentPendingAction, pending_id)
    if not pending or pending.agent_id != aid or (user.role != "admin" and pending.user_id != user.id):
        raise HTTPException(404, "待确认行动不存在")
    return pending


@router.post("/{aid}/actions/{pending_id}/reconcile")
def reconcile_pending_action(aid: str, pending_id: str, body: ActionReconciliation,
                             db: Session = Depends(get_db), user: User = Depends(require_agent_user)):
    """Record independently checked evidence; never dispatch the original action."""
    from app.services.audit import write_audit
    pending = _owned_pending(db, aid, pending_id, user)
    if pending.status not in {"unknown", "committed_unrecorded"}:
        raise HTTPException(409, "仅结果未知的行动可以人工核查；执行中请等待，终态不会再次变更")
    if len(body.evidence.strip()) < 10:
        raise HTTPException(422, "请填写实际核查的源数据或外部回执证据")
    previous = copy.deepcopy(pending.result or {})
    verification = {"resolution": body.resolution, "evidence": body.evidence.strip(),
                    "receipt_id": body.receipt_id, "user_id": user.id, "user_name": user.name,
                    "verified_at": datetime.utcnow().isoformat(), "method": "manual"}
    result = {**previous, "success": body.resolution == "succeeded", "outcome": "manually_reconciled",
              "observed_result": previous, "manual_reconciliation": verification,
              "message": "经人工核查确认为" + ("成功" if body.resolution == "succeeded" else "失败") + "；原授权保留，不会重新执行"}
    if body.resolution == "succeeded" and (pending.action_snapshot or {}).get("_graph_checkpoint"):
        if previous.get("graph_resume_started"):
            # A crashed suffix may already have effects. The original checkpoint cannot
            # replay it, even when the first action is independently confirmed successful.
            result["continuation_status"] = previous.get("continuation_status") or "unknown"
            result["continuation_error"] = previous.get("continuation_error") or "图后续执行已开始但结果未知；请核查后续运行记录，不可重放该检查点"
        else:
            result["continuation_status"] = "awaiting_resume"
            result["continuation_error"] = None
    status = "approved" if body.resolution == "succeeded" else "failed"
    changed = db.query(AgentPendingAction).filter(AgentPendingAction.id == pending.id,
        AgentPendingAction.status.in_(["unknown", "committed_unrecorded"])).update(
            {"status": status, "result": json_safe(result), "confirmed_at": datetime.utcnow()}, synchronize_session=False)
    if not changed:
        db.rollback()
        raise HTTPException(409, "该行动已被其他核查请求更新，请重新读取结果")
    if status == "approved":
        _increment_action_impact(db, pending.action_id)
    write_audit(db, user_id=user.id, user_name=user.name, action="manual_reconciliation", target_type="agent_action",
                target_id=pending.id, target_name=(pending.action_snapshot or {}).get("name", ""),
                details=json.dumps({"run_id": pending.run_id, "previous_state": pending.status,
                                               "previous_result": previous, **verification}, ensure_ascii=False),
                status="success" if status == "approved" else "failed")
    db.commit()
    db.refresh(pending)
    _sync_pending_status(db, pending)
    return {"status": pending.status, "result": pending.result, "summary": result["message"]}


@router.post("/{aid}/actions/{pending_id}/resume")
def resume_reconciled_action(aid: str, pending_id: str, request: Request,
                             db: Session = Depends(get_db), user: User = Depends(require_agent_user)):
    pending = _owned_pending(db, aid, pending_id, user)
    if pending.status != "approved" or (pending.result or {}).get("continuation_status") != "awaiting_resume":
        raise HTTPException(409, "该行动没有可安全恢复的未执行图后缀，请读取运行记录")
    from app.services.agent_graph_resume import resume_confirmed_graph
    if not resume_confirmed_graph(db, pending, user, request):
        raise HTTPException(409, "图后缀已被其他请求恢复，请读取运行记录")
    _sync_pending_status(db, pending)
    return {"status": pending.status, "result": pending.result, "summary": "已恢复未执行图后缀；原行动未重新执行"}


def _sync_pending_status(db, pending):
    def updated(items):
        return [{**item, "status": pending.status, "result": pending.result}
                if item.get("pending_id") == pending.id else item for item in items or []]
    run = db.get(AgentRun, pending.run_id) if pending.run_id else None
    if run:
        projected_errors = {str((item.get("result") or {}).get("message") or "行动执行失败")
                            for item in run.pending_actions or [] if item.get("status") in {"failed", "unknown", "committed_unrecorded"}}
        projected_errors.update(str((item.get("result") or {}).get("continuation_error"))
                                for item in run.pending_actions or [] if (item.get("result") or {}).get("continuation_error"))
        independent_errors = [error for error in (run.error or "").splitlines() if error and error not in projected_errors]
        run.pending_actions = updated(run.pending_actions)
        if run.status in {"pending_confirmation", "unknown", "failed"}:
            failures = [item for item in run.pending_actions if item.get("status") in {"failed", "unknown", "committed_unrecorded"}]
            continuations = [item.get("result") or {} for item in run.pending_actions]
            tools = [item for item in run.tool_runs or [] if item.get("success") is False]
            def uncertain_tool(item):
                result = item.get("result") if isinstance(item.get("result"), dict) else {}
                output = result.get("output") if isinstance(result.get("output"), dict) else {}
                return (result.get("outcome") or output.get("outcome")) in {"unknown", "committed_unrecorded", "partial_committed"}
            unknown = any(i.get("status") in {"unknown", "committed_unrecorded"} for i in failures) or any(
                i.get("continuation_status") == "unknown" for i in continuations) or any(
                uncertain_tool(i) for i in tools)
            errors = independent_errors + [str((item.get("result") or {}).get("message") or "行动执行失败") for item in failures]
            errors += [str(i.get("continuation_error")) for i in continuations if i.get("continuation_error")]
            errors += [str((i.get("result") or {}).get("error") or (i.get("result") or {}).get("message") or "工具执行失败") for i in tools]
            waiting = any(item.get("status") in {"pending", "executing", "resuming"} for item in run.pending_actions) or any(
                i.get("continuation_status") == "awaiting_resume" for i in continuations)
            run.status = "unknown" if unknown else "failed" if errors else "pending_confirmation" if waiting else "completed"
            run.finished_at = None if waiting else datetime.utcnow()
            run.error = "\n".join(dict.fromkeys(errors)) or None
        db.add(run)
        from app.models.trace import AgentTrace
        trace = db.get(AgentTrace, run.id)
        if trace:
            trace.status = "pending" if run.status == "pending_confirmation" else "ok" if run.status == "completed" else "error"
            trace.output_text = run.answer
            db.add(trace)
    for conv in db.query(AgentTestConversation).filter_by(agent_id=pending.agent_id, user_id=pending.user_id).all():
        conv.messages = [{**m, "pending_actions": updated(m["pending_actions"])}
                         if "pending_actions" in m else m for m in conv.messages or []]
        db.add(conv)
    db.commit()


@router.post("/{agent_id}/acknowledge-stale")
def acknowledge_stale(agent_id: str, db: Session = Depends(get_db), user: User = Depends(require_agent_user)):
    require_edit(user)
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, "智能体不存在")
    agent.ontology_stale = False
    agent.ontology_stale_detail = None
    db.commit()
    return {"message": "已确认提醒；更新本体版本后需重新选择对象、测试并发布"}
