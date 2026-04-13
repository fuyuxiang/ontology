from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from app.database import get_db
from app.models import BusinessRule, OntologyEntity
from app.schemas.entity import RuleOut
from app.schemas.rule import RuleCreate, RuleUpdate, RuleExecuteResult
from app.core.deps import get_current_user
from app.models.user import User
from app.services.audit import write_audit

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=list[RuleOut])
def list_rules(
    entity_id: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(BusinessRule)
    if entity_id:
        q = q.filter(BusinessRule.entity_id == entity_id)
    if status:
        q = q.filter(BusinessRule.status == status)
    if priority:
        q = q.filter(BusinessRule.priority == priority)
    if search:
        pattern = f"%{search}%"
        q = q.filter(BusinessRule.name.ilike(pattern) | BusinessRule.condition_expr.ilike(pattern))

    rules = q.order_by(BusinessRule.priority.desc(), BusinessRule.name).all()
    result = []
    for r in rules:
        entity = db.get(OntologyEntity, r.entity_id)
        result.append(RuleOut(
            id=r.id, name=r.name, entity_id=r.entity_id,
            entity_name=entity.name if entity else "",
            condition_expr=r.condition_expr, action_desc=r.action_desc,
            status=r.status, priority=r.priority,
            trigger_count=r.trigger_count, last_triggered=r.last_triggered,
        ))
    return result


@router.get("/{rule_id}", response_model=RuleOut)
def get_rule(rule_id: str, db: Session = Depends(get_db)):
    r = db.get(BusinessRule, rule_id)
    if not r:
        raise HTTPException(status_code=404, detail="规则不存在")
    entity = db.get(OntologyEntity, r.entity_id)
    return RuleOut(
        id=r.id, name=r.name, entity_id=r.entity_id,
        entity_name=entity.name if entity else "",
        condition_expr=r.condition_expr, action_desc=r.action_desc,
        status=r.status, priority=r.priority,
        trigger_count=r.trigger_count, last_triggered=r.last_triggered,
    )


@router.post("", response_model=RuleOut, status_code=201)
def create_rule(
    data: RuleCreate,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    entity = db.get(OntologyEntity, data.entity_id)
    if not entity:
        raise HTTPException(status_code=400, detail="关联实体不存在")

    rule = BusinessRule(
        entity_id=data.entity_id, name=data.name,
        condition_expr=data.condition_expr, action_desc=data.action_desc,
        status=data.status, priority=data.priority,
    )
    db.add(rule)
    db.flush()

    write_audit(
        db, user_id=user.id if user else None,
        user_name=user.name if user else None,
        action="create", target_type="rule",
        target_id=rule.id, target_name=rule.name,
    )
    db.commit()
    return get_rule(rule.id, db)


@router.put("/{rule_id}", response_model=RuleOut)
def update_rule(
    rule_id: str, data: RuleUpdate,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    rule = db.get(BusinessRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    changes = []
    for field, value in data.model_dump(exclude_unset=True).items():
        old = getattr(rule, field)
        if old != value:
            changes.append({"field": field, "oldValue": old, "newValue": value})
            setattr(rule, field, value)

    if changes:
        write_audit(
            db, user_id=user.id if user else None,
            user_name=user.name if user else None,
            action="update", target_type="rule",
            target_id=rule.id, target_name=rule.name, changes=changes,
        )
    db.commit()
    return get_rule(rule.id, db)


@router.delete("/{rule_id}", status_code=204)
def delete_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    rule = db.get(BusinessRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    write_audit(
        db, user_id=user.id if user else None,
        user_name=user.name if user else None,
        action="delete", target_type="rule",
        target_id=rule.id, target_name=rule.name,
    )
    db.delete(rule)
    db.commit()


@router.post("/{rule_id}/execute", response_model=RuleExecuteResult)
def execute_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    rule = db.get(BusinessRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    rule.trigger_count += 1
    rule.last_triggered = datetime.utcnow()

    write_audit(
        db, user_id=user.id if user else None,
        user_name=user.name if user else None,
        action="execute", target_type="rule",
        target_id=rule.id, target_name=rule.name,
    )
    db.commit()

    return RuleExecuteResult(
        success=True,
        affected_count=rule.trigger_count,
        message=f"规则 {rule.name} 执行成功",
    )
