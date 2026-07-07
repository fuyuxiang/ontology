"""AIP 场景平台 — 场景 CRUD / 校验 / 发布 / 回滚 / 执行 API"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models.scene import (
    AipScene,
    AipSceneExecution,
    AipSceneTrigger,
    AipSceneVersion,
)
from app.repositories import (
    AipSceneRepository,
    AipSceneTriggerRepository,
    AipSceneVersionRepository,
)
from app.services.aip.scene_runner import (
    create_execution_row,
    run_scene_stream,
    sse_format,
)
from app.utils.identifiers import gen_uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/aip/scenes", tags=["aip-scenes"])


# ── Pydantic Schemas ────────────────────────────────────────────

class SceneCreate(BaseModel):
    name: str
    description: str = ""
    group_name: str = "自定义"
    ontology_bindings: list[str] = []
    datasource_bindings: list[str] = []
    nodes_json: list = []
    edges_json: list = []
    trigger_config: dict = {}


class SceneUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    group_name: str | None = None
    nodes_json: list | None = None
    edges_json: list | None = None
    ontology_bindings: list[str] | None = None
    datasource_bindings: list[str] | None = None
    input_schema: dict | None = None
    output_schema: dict | None = None
    stats_json: dict | None = None
    trigger_config: dict | None = None


class SceneExecuteRequest(BaseModel):
    input_params: dict[str, Any] = {}


class SceneTriggerUpdate(BaseModel):
    type: str  # schedule / event / webhook / manual
    enabled: bool = False
    cron_expr: str | None = None
    timezone: str = "Asia/Shanghai"
    schedule_payload: dict | None = None
    event_entity: str | None = None
    event_action: str | None = None
    webhook_secret: str | None = None


# ── Helpers ─────────────────────────────────────────────────────

def _brief(s: AipScene) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "description": s.description or "",
        "group_name": s.group_name or "自定义",
        "status": s.status,
        "version": s.version or 0,
        "node_count": len(s.nodes_json or []),
        "edge_count": len(s.edges_json or []),
        "ontology_bindings": s.ontology_bindings or [],
        "datasource_bindings": s.datasource_bindings or [],
        "stats": s.stats_json or {},
        "trigger_config": s.trigger_config or {},
        "created_at": s.created_at.isoformat() if s.created_at else "",
        "updated_at": s.updated_at.isoformat() if s.updated_at else "",
        "created_by": s.created_by or "",
    }


def _full(s: AipScene) -> dict:
    d = _brief(s)
    d["nodes_json"] = s.nodes_json or []
    d["edges_json"] = s.edges_json or []
    d["input_schema"] = s.input_schema or {}
    d["output_schema"] = s.output_schema or {}
    d["published_version_id"] = s.published_version_id or ""
    return d


def _validate_scene_payload(s: AipScene) -> dict:
    """场景校验：循环依赖 / 节点引用是否存在 / 数据流是否合理。"""
    errors: list[str] = []
    warnings: list[str] = []
    nodes = s.nodes_json or []
    edges = s.edges_json or []
    node_ids = {n.get("id") for n in nodes}

    # 1. 边的 source/target 必须存在
    for e in edges:
        if e.get("source") not in node_ids:
            errors.append(f"连线 {e.get('id')} 的源节点不存在: {e.get('source')}")
        if e.get("target") not in node_ids:
            errors.append(f"连线 {e.get('id')} 的目标节点不存在: {e.get('target')}")

    # 2. 拓扑环检测
    in_deg = {nid: 0 for nid in node_ids}
    for e in edges:
        if e.get("target") in in_deg:
            in_deg[e["target"]] += 1
    queue = [nid for nid, d in in_deg.items() if d == 0]
    visited = 0
    children: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for e in edges:
        if e.get("source") in children and e.get("target") in in_deg:
            children[e["source"]].append(e["target"])
    while queue:
        cur = queue.pop(0)
        visited += 1
        for ch in children.get(cur, []):
            in_deg[ch] -= 1
            if in_deg[ch] == 0:
                queue.append(ch)
    if visited < len(node_ids):
        errors.append("画布存在循环依赖")

    # 3. 节点引用校验
    from app.models.agent import Agent
    from app.models.entity import OntologyEntity
    from app.models.function import OntologyFunction
    from app.models.action import EntityAction
    from app.models.skill import Skill

    db = SessionLocal()
    try:
        for n in nodes:
            ntype = n.get("type", "")
            data = n.get("data", {}) or {}
            label = data.get("label") or n.get("id")
            if ntype in ("ontologyQuery", "ontology-query"):
                ref = data.get("objectType") or (data.get("objectTypes") or [None])[0]
                if not ref:
                    warnings.append(f"节点 {label} 未指定本体对象")
                elif not db.query(OntologyEntity).filter(OntologyEntity.name == ref).first():
                    errors.append(f"节点 {label} 引用的本体 {ref} 不存在")
            elif ntype in ("skill", "skillNode"):
                sid = data.get("skill_id")
                if sid and not db.get(Skill, sid):
                    errors.append(f"节点 {label} 引用的 Skill {sid} 不存在")
            elif ntype in ("agent", "agentNode"):
                aid = data.get("agent_id")
                if aid and not db.get(Agent, aid):
                    errors.append(f"节点 {label} 引用的 Agent {aid} 不存在")
            elif ntype in ("action", "actionSystem"):
                aid = data.get("action_id")
                if aid and not db.get(EntityAction, aid):
                    errors.append(f"节点 {label} 引用的动作 {aid} 不存在")
            elif ntype == "function":
                fid = data.get("function_id") or data.get("func_id")
                if fid and not db.get(OntologyFunction, fid):
                    errors.append(f"节点 {label} 引用的函数 {fid} 不存在")
            elif ntype == "subscene":
                sid = data.get("scene_id")
                if sid and not db.get(AipScene, sid):
                    errors.append(f"节点 {label} 引用的子场景 {sid} 不存在")
    finally:
        db.close()

    return {"ok": not errors, "errors": errors, "warnings": warnings}


def _sync_trigger(db: Session, scene_id: str, cfg: dict | None) -> AipSceneTrigger | None:
    """根据 trigger_config 同步 aip_scene_triggers 行（不变 enabled，不调度）。"""
    if not cfg:
        return None
    repo = AipSceneTriggerRepository(db)
    trg = repo.get_by_scene(scene_id)
    if not trg:
        trg = AipSceneTrigger(id=gen_uuid(), scene_id=scene_id, type=cfg.get("type", "manual"))
        db.add(trg)
    trg.type = cfg.get("type", trg.type or "manual")
    trg.enabled = bool(cfg.get("enabled", trg.enabled))
    schedule = cfg.get("schedule") or {}
    if schedule:
        trg.schedule_payload = schedule
        trg.cron_expr = schedule.get("cron") or _build_cron(schedule)
        trg.timezone = schedule.get("timezone") or trg.timezone or "Asia/Shanghai"
    event = cfg.get("event") or {}
    if event:
        trg.event_entity = event.get("objectType") or trg.event_entity
        trg.event_action = event.get("trigger") or trg.event_action
    webhook = cfg.get("webhook") or {}
    if webhook:
        trg.webhook_secret = webhook.get("secret") or trg.webhook_secret
    if trg.type == "webhook" and not trg.webhook_path:
        trg.webhook_path = secrets.token_urlsafe(16)
    db.commit()

    # 同步 APScheduler
    try:
        from app.services.aip.scheduler import sync_trigger_job
        sync_trigger_job(trg)
    except Exception as e:
        logger.warning(f"[aip] 同步调度任务失败: {e}")
    return trg


def _build_cron(schedule: dict) -> str:
    freq = schedule.get("frequency", "daily")
    h = int(schedule.get("hour", 9))
    m = int(schedule.get("minute", 0))
    if freq == "daily":
        return f"{m} {h} * * *"
    if freq == "weekly":
        return f"{m} {h} * * 1"
    if freq == "monthly":
        return f"{m} {h} 1 * *"
    return schedule.get("cron", f"{m} {h} * * *")


# ── CRUD ────────────────────────────────────────────────────────

@router.get("")
def list_scenes(
    status: str = Query(default=""),
    group: str = Query(default=""),
    keyword: str = Query(default=""),
    db: Session = Depends(get_db),
):
    repo = AipSceneRepository(db)
    items = repo.list_with_filters(
        status=status or None, group=group or None, keyword=keyword or None,
    )
    return [_brief(s) for s in items]


@router.post("", status_code=201)
def create_scene(body: SceneCreate, db: Session = Depends(get_db)):
    repo = AipSceneRepository(db)
    s = AipScene(
        id=gen_uuid(),
        name=body.name,
        description=body.description,
        group_name=body.group_name,
        nodes_json=body.nodes_json or [],
        edges_json=body.edges_json or [],
        ontology_bindings=body.ontology_bindings or [],
        datasource_bindings=body.datasource_bindings or [],
        trigger_config=body.trigger_config or {},
        status="draft",
        version=0,
    )
    repo.create(s)
    repo.commit()
    repo.refresh(s)
    if body.trigger_config:
        _sync_trigger(db, s.id, body.trigger_config)
    return _full(s)


@router.get("/{sid}")
def get_scene(sid: str, db: Session = Depends(get_db)):
    repo = AipSceneRepository(db)
    s = repo.get_by_id(sid)
    if not s:
        raise HTTPException(404, "场景不存在")
    return _full(s)


@router.put("/{sid}")
def update_scene(sid: str, body: SceneUpdate, db: Session = Depends(get_db)):
    repo = AipSceneRepository(db)
    s = repo.get_by_id(sid)
    if not s:
        raise HTTPException(404, "场景不存在")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(s, field, val)
    s.updated_at = datetime.utcnow()
    repo.commit()
    repo.refresh(s)
    if body.trigger_config is not None:
        _sync_trigger(db, s.id, body.trigger_config)
    return _full(s)


@router.delete("/{sid}")
def delete_scene(sid: str, db: Session = Depends(get_db)):
    repo = AipSceneRepository(db)
    s = repo.get_by_id(sid)
    if not s:
        raise HTTPException(404, "场景不存在")
    # 级联清理触发器（执行历史保留以便审计）
    trg_repo = AipSceneTriggerRepository(db)
    trg = trg_repo.get_by_scene(sid)
    if trg:
        try:
            from app.services.aip.scheduler import remove_trigger_job
            remove_trigger_job(trg)
        except Exception:
            pass
        db.delete(trg)
    repo.delete(s)
    repo.commit()
    return {"ok": True}


@router.post("/{sid}/validate")
def validate_scene(sid: str, db: Session = Depends(get_db)):
    repo = AipSceneRepository(db)
    s = repo.get_by_id(sid)
    if not s:
        raise HTTPException(404, "场景不存在")
    return _validate_scene_payload(s)


# ── 版本 / 发布 / 回滚 ────────────────────────────────────────

@router.get("/{sid}/versions")
def list_versions(sid: str, db: Session = Depends(get_db)):
    vrepo = AipSceneVersionRepository(db)
    items = vrepo.list_by_scene(sid)
    return [{
        "id": v.id, "scene_id": v.scene_id, "version": v.version, "note": v.note,
        "status": v.status,
        "published_at": v.published_at.isoformat() if v.published_at else "",
        "published_by": v.published_by,
    } for v in items]


@router.post("/{sid}/publish")
def publish_scene(sid: str, db: Session = Depends(get_db)):
    repo = AipSceneRepository(db)
    s = repo.get_by_id(sid)
    if not s:
        raise HTTPException(404, "场景不存在")
    val = _validate_scene_payload(s)
    if not val["ok"]:
        raise HTTPException(400, {"message": "校验失败", "errors": val["errors"]})
    new_version = (s.version or 0) + 1
    snap = AipSceneVersion(
        id=gen_uuid(),
        scene_id=s.id,
        version=new_version,
        snapshot_json={
            "nodes_json": s.nodes_json or [],
            "edges_json": s.edges_json or [],
            "ontology_bindings": s.ontology_bindings or [],
            "datasource_bindings": s.datasource_bindings or [],
            "trigger_config": s.trigger_config or {},
            "input_schema": s.input_schema or {},
            "output_schema": s.output_schema or {},
        },
        note=f"v{new_version}",
        status="published",
        published_by="admin",
    )
    db.add(snap)
    s.version = new_version
    s.published_version_id = snap.id
    s.status = "published"
    s.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "status": s.status, "version": new_version, "version_id": snap.id}


@router.post("/{sid}/rollback")
def rollback_scene(sid: str, version_id: str = Query(...), db: Session = Depends(get_db)):
    s = db.get(AipScene, sid)
    if not s:
        raise HTTPException(404, "场景不存在")
    v = db.get(AipSceneVersion, version_id)
    if not v or v.scene_id != sid:
        raise HTTPException(404, "版本不存在")
    snap = v.snapshot_json or {}
    s.nodes_json = snap.get("nodes_json", [])
    s.edges_json = snap.get("edges_json", [])
    s.ontology_bindings = snap.get("ontology_bindings", [])
    s.datasource_bindings = snap.get("datasource_bindings", [])
    s.trigger_config = snap.get("trigger_config", {})
    s.input_schema = snap.get("input_schema", {})
    s.output_schema = snap.get("output_schema", {})
    s.status = "draft"  # 回滚后变回草稿，需重新发布
    s.updated_at = datetime.utcnow()
    v.status = "rolled_back"
    db.commit()
    return _full(s)


# ── 执行 ────────────────────────────────────────────────────────

@router.post("/{sid}/execute")
async def execute_scene(
    sid: str,
    body: SceneExecuteRequest = SceneExecuteRequest(),
    db: Session = Depends(get_db),
):
    s = db.get(AipScene, sid)
    if not s:
        raise HTTPException(404, "场景不存在")
    if not s.nodes_json:
        raise HTTPException(400, "画布为空，请先添加节点")
    execution = create_execution_row(db, s, "manual", None, body.input_params)

    # 用 SessionLocal 隔离 SSE 生成器的会话
    def event_stream():
        local_db = SessionLocal()
        try:
            scene = local_db.get(AipScene, sid)
            exc = local_db.get(AipSceneExecution, execution.id)
            for ev in run_scene_stream(local_db, scene, exc, body.input_params):
                yield sse_format(ev)
            yield "data: [DONE]\n\n"
        finally:
            local_db.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{sid}/test")
def test_node(
    sid: str,
    node_id: str = Query(...),
    db: Session = Depends(get_db),
):
    """单节点试跑（沙箱）— 仅执行指定节点，不影响其它。"""
    s = db.get(AipScene, sid)
    if not s:
        raise HTTPException(404, "场景不存在")
    target_node = next((n for n in (s.nodes_json or []) if n.get("id") == node_id), None)
    if not target_node:
        raise HTTPException(404, "节点不存在")

    from app.services.agent.graph_engine import GraphEngine
    from app.services.aip.scene_runner import _resolve_model_config

    model_name, model_config = _resolve_model_config(db)
    engine = GraphEngine(
        db,
        nodes_json=[target_node],
        edges_json=[],
        system_prompt=s.description or "",
        model_name=model_name,
        model_config=model_config,
        emit_node_io=True,
    )
    out: dict = {}
    for ev in engine.run_for_scene({}):
        if ev.get("type") == "scene_finished":
            out = ev.get("final_output", {})
        if ev.get("type") == "scene_failed":
            return {"ok": False, "error": ev.get("error")}
    return {"ok": True, "node_id": node_id, "output": out, "node_io": engine.node_io.get(node_id)}


# ── 触发器 CRUD ─────────────────────────────────────────────────

@router.get("/{sid}/trigger")
def get_trigger(sid: str, db: Session = Depends(get_db)):
    trg = AipSceneTriggerRepository(db).get_by_scene(sid)
    if not trg:
        return {"scene_id": sid, "type": "manual", "enabled": False}
    return {
        "id": trg.id, "scene_id": trg.scene_id, "type": trg.type, "enabled": trg.enabled,
        "cron_expr": trg.cron_expr, "timezone": trg.timezone,
        "schedule_payload": trg.schedule_payload or {},
        "event_entity": trg.event_entity, "event_action": trg.event_action,
        "webhook_path": trg.webhook_path, "webhook_secret": trg.webhook_secret,
        "last_fired_at": trg.last_fired_at.isoformat() if trg.last_fired_at else None,
        "fire_count": trg.fire_count or 0,
    }


@router.put("/{sid}/trigger")
def upsert_trigger(sid: str, body: SceneTriggerUpdate, db: Session = Depends(get_db)):
    s = db.get(AipScene, sid)
    if not s:
        raise HTTPException(404, "场景不存在")
    cfg = {
        "type": body.type,
        "enabled": body.enabled,
        "schedule": (body.schedule_payload or {}) if body.type == "schedule" else {},
        "event": ({"objectType": body.event_entity, "trigger": body.event_action}
                  if body.type == "event" else {}),
        "webhook": ({"secret": body.webhook_secret} if body.type == "webhook" else {}),
    }
    if body.cron_expr:
        cfg["schedule"]["cron"] = body.cron_expr
    if body.timezone:
        cfg["schedule"]["timezone"] = body.timezone
    s.trigger_config = cfg
    db.commit()
    trg = _sync_trigger(db, sid, cfg)
    return {
        "ok": True,
        "trigger": {
            "id": trg.id, "type": trg.type, "enabled": trg.enabled,
            "cron_expr": trg.cron_expr, "timezone": trg.timezone,
            "webhook_path": trg.webhook_path, "webhook_secret": trg.webhook_secret,
        },
    }


@router.post("/{sid}/trigger/test-fire")
def test_fire_trigger(sid: str, db: Session = Depends(get_db)):
    """手动触发一次 — 走调度通路（不阻塞返回）。"""
    s = db.get(AipScene, sid)
    if not s:
        raise HTTPException(404, "场景不存在")
    import threading

    from app.services.aip.scene_runner import run_scene_in_thread
    eid_holder = {"id": ""}

    def _run():
        try:
            eid_holder["id"] = run_scene_in_thread(sid, "manual", {}, {})
        except Exception as e:
            logger.warning(f"[test_fire] 失败: {e}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=0.1)
    return {"ok": True, "scheduled": True}


@router.post("/{scene_id}/acknowledge-stale")
def acknowledge_stale(scene_id: str, db: Session = Depends(get_db)):
    scene = db.query(AipScene).filter(AipScene.id == scene_id).first()
    if not scene:
        raise HTTPException(404, "场景不存在")
    if not scene.ontology_stale:
        return {"message": "该场景没有过期标记"}

    from app.models.version import OntologyVersion
    active_version = db.query(OntologyVersion).filter(OntologyVersion.is_active == True).first()
    scene.ontology_stale = False
    scene.ontology_stale_detail = None
    scene.ontology_version_id = active_version.id if active_version else None
    db.commit()
    return {"message": "已确认，过期标记已清除"}
