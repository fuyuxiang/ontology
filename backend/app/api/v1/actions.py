from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import OntologyEntity
from app.models.rule import EntityAction
from app.schemas.action import (
    ActionCreate, ActionUpdate, ActionOut,
    ActionExecuteRequest, ActionExecuteResult, ActionTypeInfo,
)
from app.repositories.action_repo import ActionRepository
from app.core.deps import require_user
from app.models.user import User
from app.services.audit import write_audit
from app.services.action_executors import get_executor, get_all_type_info

router = APIRouter(prefix="/actions", tags=["actions"])


@router.get("/types", response_model=list[ActionTypeInfo])
def list_action_types():
    return get_all_type_info()


@router.get("", response_model=list[ActionOut])
def list_actions(
    entity_id: str | None = Query(None),
    status: str | None = Query(None),
    action_type: str | None = Query(None),
    category: str | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
):
    repo = ActionRepository(db)
    actions = repo.list_with_filters(
        entity_id=entity_id, status=status,
        action_type=action_type, category=category, search=search,
    )
    results = []
    for a in actions:
        out = ActionOut.model_validate(a)
        if a.entity_id:
            out.entity_name = repo.get_entity_name(a.entity_id)
        results.append(out)
    return results


@router.get("/{action_id}", response_model=ActionOut)
def get_action(action_id: str, db: Session = Depends(get_db)):
    repo = ActionRepository(db)
    a = repo.get_by_id(action_id)
    if not a:
        raise HTTPException(status_code=404, detail="动作不存在")
    out = ActionOut.model_validate(a)
    if a.entity_id:
        out.entity_name = repo.get_entity_name(a.entity_id)
    return out


@router.post("", response_model=ActionOut, status_code=201)
def create_action(
    data: ActionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    if data.category == "domain" and not data.entity_id:
        raise HTTPException(status_code=400, detail="领域行动必须绑定实体")
    if data.category == "system" and data.entity_id:
        raise HTTPException(status_code=400, detail="系统行动不应绑定实体")

    if data.entity_id:
        entity = db.get(OntologyEntity, data.entity_id)
        if not entity:
            raise HTTPException(status_code=400, detail="关联实体不存在")

    repo = ActionRepository(db)
    action = EntityAction(**data.model_dump())
    repo.create(action)

    write_audit(
        db, user_id=user.id,
        user_name=user.name,
        action="create", target_type="action",
        target_id=action.id, target_name=action.name,
    )
    repo.commit()

    out = ActionOut.model_validate(action)
    if action.entity_id:
        out.entity_name = repo.get_entity_name(action.entity_id)
    return out


@router.put("/{action_id}", response_model=ActionOut)
def update_action(
    action_id: str, data: ActionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
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

    out = ActionOut.model_validate(action)
    if action.entity_id:
        out.entity_name = repo.get_entity_name(action.entity_id)
    return out


@router.delete("/{action_id}", status_code=204)
def delete_action(
    action_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    repo = ActionRepository(db)
    action = repo.get_by_id(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="动作不存在")

    write_audit(
        db, user_id=user.id,
        user_name=user.name,
        action="delete", target_type="action",
        target_id=action.id, target_name=action.name,
    )
    repo.delete(action)
    repo.commit()


@router.post("/{action_id}/execute", response_model=ActionExecuteResult)
async def execute_action(
    action_id: str,
    data: ActionExecuteRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    repo = ActionRepository(db)
    action = repo.get_by_id(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="动作不存在")
    if action.status != "active":
        raise HTTPException(status_code=400, detail="动作未激活")

    params = data.params if data else {}
    dry_run = data.dry_run if data else False

    executor = get_executor(action.action_type)
    result = await executor.execute(action.type_config or {}, params, dry_run)

    if not dry_run:
        action.impact_count = (action.impact_count or 0) + 1
        write_audit(
            db, user_id=user.id if user else None,
            user_name=user.name if user else None,
            action="execute", target_type="action",
            target_id=action.id, target_name=action.name,
        )
        repo.commit()

    return ActionExecuteResult(success=result.success, message=result.message, output=result.output)
