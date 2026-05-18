from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import OntologyEntity
from app.models.rule import EntityAction
from app.schemas.action import (
    ActionCreate, ActionUpdate, ActionOut,
    ActionExecuteRequest, ActionExecuteResult,
)
from app.repositories.action_repo import ActionRepository
from app.core.deps import get_current_user
from app.models.user import User
from app.services.audit import write_audit

router = APIRouter(prefix="/actions", tags=["actions"])


def _action_to_out(a: EntityAction, entity_name: str) -> ActionOut:
    return ActionOut(
        id=a.id, entity_id=a.entity_id, entity_name=entity_name,
        name=a.name, type=a.type, status=a.status,
        impact_count=a.impact_count,
        parameters_json=a.parameters_json,
        preconditions_json=a.preconditions_json,
        effects_json=a.effects_json,
        action_meta_json=a.action_meta_json,
        created_at=a.created_at,
    )


@router.get("", response_model=list[ActionOut])
def list_actions(
    entity_id: str | None = None,
    status: str | None = None,
    type: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    repo = ActionRepository(db)
    actions = repo.list_with_filters(entity_id=entity_id, status=status, type=type, search=search)
    return [_action_to_out(a, repo.get_entity_name(a.entity_id)) for a in actions]


@router.get("/{action_id}", response_model=ActionOut)
def get_action(action_id: str, db: Session = Depends(get_db)):
    repo = ActionRepository(db)
    a = repo.get_by_id(action_id)
    if not a:
        raise HTTPException(status_code=404, detail="动作不存在")
    return _action_to_out(a, repo.get_entity_name(a.entity_id))


@router.post("", response_model=ActionOut, status_code=201)
def create_action(
    data: ActionCreate,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    repo = ActionRepository(db)
    entity = db.get(OntologyEntity, data.entity_id)
    if not entity:
        raise HTTPException(status_code=400, detail="关联实体不存在")

    action = EntityAction(
        entity_id=data.entity_id, name=data.name, type=data.type,
        status=data.status, parameters_json=data.parameters_json,
        preconditions_json=data.preconditions_json,
        effects_json=data.effects_json, action_meta_json=data.action_meta_json,
    )
    repo.create(action)

    write_audit(
        db, user_id=user.id if user else None,
        user_name=user.name if user else None,
        action="create", target_type="action",
        target_id=action.id, target_name=action.name,
    )
    repo.commit()
    return _action_to_out(action, entity.name)


@router.put("/{action_id}", response_model=ActionOut)
def update_action(
    action_id: str, data: ActionUpdate,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    repo = ActionRepository(db)
    action = repo.get_by_id(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="动作不存在")

    changes = []
    for field, value in data.model_dump(exclude_unset=True).items():
        old = getattr(action, field)
        if old != value:
            changes.append({"field": field, "oldValue": old, "newValue": value})
            setattr(action, field, value)

    if changes:
        write_audit(
            db, user_id=user.id if user else None,
            user_name=user.name if user else None,
            action="update", target_type="action",
            target_id=action.id, target_name=action.name, changes=changes,
        )
    repo.commit()
    return _action_to_out(action, repo.get_entity_name(action.entity_id))


@router.delete("/{action_id}", status_code=204)
def delete_action(
    action_id: str,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    repo = ActionRepository(db)
    action = repo.get_by_id(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="动作不存在")

    write_audit(
        db, user_id=user.id if user else None,
        user_name=user.name if user else None,
        action="delete", target_type="action",
        target_id=action.id, target_name=action.name,
    )
    repo.delete(action)
    repo.commit()


@router.post("/{action_id}/execute", response_model=ActionExecuteResult)
def execute_action(
    action_id: str,
    data: ActionExecuteRequest | None = None,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    repo = ActionRepository(db)
    action = repo.get_by_id(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="动作不存在")
    if action.status != "active":
        raise HTTPException(status_code=400, detail="动作未激活")

    from app.services.rule_engine import ActionExecutor
    executor = ActionExecutor(db)
    params = data.params if data else {}
    dry_run = data.dry_run if data else False
    result = executor.execute(action, params, dry_run=dry_run)

    if not dry_run:
        action.impact_count = (action.impact_count or 0) + 1
        write_audit(
            db, user_id=user.id if user else None,
            user_name=user.name if user else None,
            action="execute", target_type="action",
            target_id=action.id, target_name=action.name,
        )
        repo.commit()

    return ActionExecuteResult(
        success=result.success,
        message=result.message,
        effects=result.effects,
    )
