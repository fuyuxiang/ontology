"""Agent configuration contracts and immutable release management."""
import copy
import hashlib
import json

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, object_session

from app.models.agent import ModelRegistry
from app.models.agent_runtime import AgentRun, AgentVersion
from app.models.version import OntologyVersion
from app.services.audit import write_audit
from app.utils.time import utc_iso

CONFIG_FIELDS = ("name", "description", "tags", "model_id", "system_prompt", "kb_ids",
                 "entity_ids", "tools_config", "nodes_json", "edges_json", "ontology_version_id")


def config_snapshot(agent):
    from app.services.agent_models import model_snapshot
    snap = copy.deepcopy({key: getattr(agent, key) for key in CONFIG_FIELDS})
    snap["model_snapshot"] = model_snapshot(object_session(agent), agent.model_id)
    return snap


def config_hash(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=False,
                                     default=str, separators=(",", ":")).encode()).hexdigest()


def latest_version(db, aid):
    return db.query(AgentVersion).filter_by(agent_id=aid).order_by(AgentVersion.version.desc()).first()


def require_edit(user):
    from app.core.permissions import has_permission
    if not has_permission(user, "rule:write"):
        raise HTTPException(403, "需要管理员或编辑者权限")


def normalize_tools_config(raw):
    if raw is not None and not isinstance(raw, dict):
        raise HTTPException(422, "工具配置必须为对象")
    cfg = copy.deepcopy(raw or {})
    cfg.setdefault("action_mode", "simulation")
    cfg.setdefault("skill_bindings", [])
    cfg.setdefault("max_tool_rounds", 12)
    if cfg["action_mode"] not in ("simulation", "confirm"):
        raise HTTPException(422, "动作模式只能为 simulation 或 confirm")
    rounds = cfg["max_tool_rounds"]
    if isinstance(rounds, bool) or not isinstance(rounds, int) or not 2 <= rounds <= 20:
        raise HTTPException(422, "推理轮次应为 2–20 的整数")
    if not isinstance(cfg["skill_bindings"], list):
        raise HTTPException(422, "挂载技能必须为列表")
    seen = set()
    for binding in cfg["skill_bindings"]:
        if not isinstance(binding, dict) or not isinstance(binding.get("skill_id"), str) or not binding.get("skill_id") or not isinstance(binding.get("version"), int) or isinstance(binding.get("version"), bool) or binding["version"] < 1:
            raise HTTPException(422, "技能必须绑定已发布的固定版本")
        if binding["skill_id"] in seen:
            raise HTTPException(422, "不能重复挂载同一技能")
        seen.add(binding["skill_id"])
    if "allowed_tools" in cfg and (not isinstance(cfg["allowed_tools"], list) or any(not isinstance(x, str) for x in cfg["allowed_tools"])):
        raise HTTPException(422, "工具范围必须为名称列表")
    return cfg


def runtime_context(db: Session, snapshot: dict, user, *, allow_archived=False):
    from app.services.skill_service import SkillService
    cfg = normalize_tools_config(snapshot.get("tools_config"))
    ontology_id = cfg.get("ontology_id")
    vid = cfg.get("ontology_version_id") or snapshot.get("ontology_version_id")
    version = db.get(OntologyVersion, vid) if vid else None
    if not version or version.status != "published" or version.ontology_id != ontology_id:
        raise HTTPException(409, "请选择属于当前本体的已发布版本")
    entity_ids = set(snapshot.get("entity_ids") or [])
    if not entity_ids:
        raise HTTPException(409, "请至少选择一个业务对象")
    version_entity_ids = {e.source_entity_id for e in version.entities}
    if not entity_ids <= version_entity_ids:
        raise HTTPException(409, "对象范围包含当前发布版本以外的对象")
    svc = SkillService(db)
    skill_snapshots = []
    for binding in cfg["skill_bindings"]:
        skill = svc.get_published_snapshot(binding["skill_id"], binding["version"], user, allow_archived=allow_archived)
        if skill.get("ontology_id") != ontology_id or skill.get("ontology_version_id") != vid:
            raise HTTPException(409, f"技能「{skill.get('name', '')}」与当前本体版本不匹配")
        if not set(skill.get("entity_ids") or []) <= entity_ids:
            raise HTTPException(409, f"技能「{skill.get('name', '')}」需要当前对象范围以外的对象")
        skill_snapshots.append(skill)
    if snapshot.get("model_id"):
        model = db.get(ModelRegistry, snapshot["model_id"])
        if not model or model.status != "active":
            raise HTTPException(409, "所选模型不可用")
    return {"ontology_id": ontology_id, "ontology_version_id": vid, "entity_ids": sorted(entity_ids),
            "skills": skill_snapshots, "action_mode": cfg["action_mode"],
            "max_tool_rounds": cfg["max_tool_rounds"], "allowed_tools": cfg.get("allowed_tools"),
            "user": user, "config_hash": config_hash(snapshot)}


def validate_agent(db, agent, user):
    errors = []
    snap = config_snapshot(agent)
    if not (agent.name or "").strip():
        errors.append("请输入智能体名称")
    try:
        context = runtime_context(db, snap, user)
    except HTTPException as exc:
        errors.append(str(exc.detail))
        context = None
    return {"valid": not errors, "errors": errors, "warnings": [],
            "config_hash": config_hash(snap), "dependencies": {
                "ontology_version_id": context["ontology_version_id"],
                "skills": [{"skill_id": s["skill_id"], "version": s.get("version")} for s in context["skills"]]
            } if context else {}}


def last_test(db, agent):
    digest = config_hash(config_snapshot(agent))
    run = db.query(AgentRun).filter_by(agent_id=agent.id, config_hash=digest, version=None).order_by(AgentRun.started_at.desc()).first()
    if not run:
        return None
    return {"passed": run.status in ("completed", "pending_confirmation"), "status": run.status,
            "tested_at": utc_iso(run.finished_at),
            "config_hash": run.config_hash, "run_id": run.id}


def publish_agent_version(db, agent, user, description=""):
    require_edit(user)
    check = validate_agent(db, agent, user)
    if not check["valid"]:
        raise HTTPException(409, detail=check)
    test = last_test(db, agent)
    if not test or not test["passed"]:
        raise HTTPException(409, "当前草稿尚未通过对话测试，请保存并完成测试后发布")
    snap = config_snapshot(agent)
    previous = latest_version(db, agent.id)
    if previous and previous.config_hash == config_hash(snap) and previous.published_by == user.id:
        agent.status = "published"
        db.commit()
        return previous
    release = AgentVersion(agent_id=agent.id, version=(previous.version + 1) if previous else 1,
                           config_snapshot=snap, config_hash=config_hash(snap),
                           description=description, published_by=user.id)
    db.add(release)
    agent.status = "published"
    write_audit(db, user_id=user.id, user_name=user.name, action="publish", target_type="agent",
                target_id=agent.id, target_name=agent.name, details=f"发布版本 {release.version}")
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "该草稿已由其他用户发布，请刷新版本记录") from exc
    return release
