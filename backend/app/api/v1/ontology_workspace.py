"""Persisted ontology object collections and actual action task history."""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import require_user
from app.database import get_db
from app.models import ActionExecution, AgentPendingAction, AuditLog, EntityAction, OntologyEntity, OntologyGroup, ScenarioDict, User
from app.services.audit import write_audit

router = APIRouter(prefix="/ontology", tags=["ontology-workspace"])


class GroupInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    entity_ids: list[str] = Field(default_factory=list)


class GroupOut(GroupInput):
    id: str
    ontology_id: str
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


def _ontology(db, ontology_id):
    if not db.get(ScenarioDict, ontology_id):
        raise HTTPException(404, "本体不存在")


def _validate(db, ontology_id, body, current_id=None):
    _ontology(db, ontology_id)
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "对象组名称不能为空")
    existing = db.query(OntologyGroup).filter_by(ontology_id=ontology_id, name=name).first()
    if existing and existing.id != current_id:
        raise HTTPException(409, "对象组名称已存在")
    ids = list(dict.fromkeys(body.entity_ids))
    valid = {row.id for row in db.query(OntologyEntity).filter(OntologyEntity.id.in_(ids), OntologyEntity.ontology_id == ontology_id).all()}
    if set(ids) != valid:
        raise HTTPException(422, "对象组只能包含当前本体内的对象")
    return name, ids


@router.get("/{ontology_id}/groups", response_model=list[GroupOut])
def groups(ontology_id: str, db: Session = Depends(get_db)):
    _ontology(db, ontology_id)
    return db.query(OntologyGroup).filter_by(ontology_id=ontology_id).order_by(OntologyGroup.created_at).all()


@router.post("/{ontology_id}/groups", response_model=GroupOut, status_code=201)
def create_group(ontology_id: str, body: GroupInput, db: Session = Depends(get_db), user: User = Depends(require_user)):
    name, ids = _validate(db, ontology_id, body)
    group = OntologyGroup(ontology_id=ontology_id, name=name, entity_ids=ids, created_by=user.id)
    db.add(group)
    db.flush()
    write_audit(db, user_id=user.id, user_name=user.name, action="create", target_type="object_group", target_id=group.id, target_name=group.name)
    db.commit()
    return group


@router.put("/{ontology_id}/groups/{group_id}", response_model=GroupOut)
def update_group(ontology_id: str, group_id: str, body: GroupInput, db: Session = Depends(get_db), user: User = Depends(require_user)):
    group = db.get(OntologyGroup, group_id)
    if not group or group.ontology_id != ontology_id:
        raise HTTPException(404, "对象组不存在")
    group.name, group.entity_ids = _validate(db, ontology_id, body, group_id)
    write_audit(db, user_id=user.id, user_name=user.name, action="update", target_type="object_group", target_id=group.id, target_name=group.name)
    db.commit()
    return group


@router.delete("/{ontology_id}/groups/{group_id}", status_code=204)
def delete_group(ontology_id: str, group_id: str, db: Session = Depends(get_db), user: User = Depends(require_user)):
    group = db.get(OntologyGroup, group_id)
    if not group or group.ontology_id != ontology_id:
        raise HTTPException(404, "对象组不存在")
    write_audit(db, user_id=user.id, user_name=user.name, action="delete", target_type="object_group", target_id=group.id, target_name=group.name)
    db.delete(group)
    db.commit()


@router.get("/{ontology_id}/tasks")
def tasks(ontology_id: str, limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db), user: User = Depends(require_user)):
    _ontology(db, ontology_id)
    entity_ids = db.query(OntologyEntity.id).filter_by(ontology_id=ontology_id)
    actions = db.query(EntityAction).filter((EntityAction.ontology_id == ontology_id) | EntityAction.entity_id.in_(entity_ids)).all()
    action_map = {a.id: a.name for a in actions}
    records = []
    query = db.query(ActionExecution).filter_by(ontology_id=ontology_id)
    if user.role != "admin":
        query = query.filter_by(user_id=user.id)
    ledger_ids = set()
    for row in query.order_by(ActionExecution.created_at.desc()).limit(limit):
        ledger_ids.add(row.id)
        records.append({"id": row.id, "action_id": row.action_id, "action_name": action_map.get(row.action_id, row.action_id),
                        "status": row.state, "params": row.params, "result": row.output,
                        "error": row.message if row.state in {"failed", "unknown"} else None,
                        "created_at": row.created_at, "source": "simulation" if row.dry_run else "direct"})
    query = db.query(AuditLog).filter(AuditLog.target_type == "action", AuditLog.action == "execute", AuditLog.target_id.in_(action_map))
    if user.role != "admin":
        query = query.filter(AuditLog.user_id == user.id)
    for row in query.order_by(AuditLog.timestamp.desc()).limit(limit):
        try:
            details = json.loads(row.details or "{}")
        except ValueError:
            details = {"message": row.details}
        if details.get("execution_id") in ledger_ids:
            continue
        records.append({"id": row.id, "action_id": row.target_id, "action_name": row.target_name,
                        "status": row.status, "params": details.get("params", {}), "result": details.get("output", details),
                        "error": details.get("message") if row.status != "success" else None,
                        "created_at": row.timestamp, "source": "direct"})
    query = db.query(AgentPendingAction).filter(AgentPendingAction.action_id.in_(action_map))
    if user.role != "admin":
        query = query.filter(AgentPendingAction.user_id == user.id)
    for row in query.order_by(AgentPendingAction.created_at.desc()).limit(limit):
        records.append({"id": row.id, "action_id": row.action_id, "action_name": (row.action_snapshot or {}).get("name", action_map.get(row.action_id)),
                        "status": row.status, "params": row.params, "result": row.result,
                        "error": (row.result or {}).get("message") if row.status in {"failed", "unknown", "expired", "stale"} else None,
                        "created_at": row.created_at, "source": "agent"})
    return sorted(records, key=lambda r: r["created_at"], reverse=True)[:limit]
