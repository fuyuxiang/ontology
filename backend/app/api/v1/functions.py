from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models import OntologyEntity
from app.models.function import OntologyFunction
from app.schemas.function import (
    FunctionCreate, FunctionUpdate, FunctionOut,
    FunctionTestRequest, FunctionTestResult,
)
from app.repositories.function_repo import FunctionRepository
from app.core.deps import require_user
from app.models.user import User
from app.services.audit import write_audit

router = APIRouter(prefix="/functions", tags=["functions"])


def _func_to_out(f: OntologyFunction, entity_name: str) -> FunctionOut:
    return FunctionOut(
        id=f.id, entity_id=f.entity_id, entity_ids=f.entity_ids or [],
        entity_name=entity_name,
        name=f.name, callable_name=f.callable_name or "",
        description=f.description, return_type=f.return_type,
        input_schema=f.input_schema, logic_type=f.logic_type,
        logic_body=f.logic_body, is_derived_property=f.is_derived_property,
        status=f.status, execution_count=f.execution_count,
        last_executed=f.last_executed, tags=f.tags,
        created_at=f.created_at, updated_at=f.updated_at,
    )


@router.get("", response_model=list[FunctionOut])
def list_functions(
    entity_id: str | None = None,
    status: str | None = None,
    is_derived: bool | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    repo = FunctionRepository(db)
    funcs = repo.list_with_filters(entity_id=entity_id, status=status, is_derived=is_derived, search=search)
    return [_func_to_out(f, repo.get_entity_name(f.entity_id)) for f in funcs]


@router.get("/{func_id}", response_model=FunctionOut)
def get_function(func_id: str, db: Session = Depends(get_db)):
    repo = FunctionRepository(db)
    f = repo.get_by_id(func_id)
    if not f:
        raise HTTPException(status_code=404, detail="函数不存在")
    return _func_to_out(f, repo.get_entity_name(f.entity_id))


@router.post("", response_model=FunctionOut, status_code=201)
def create_function(
    data: FunctionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    repo = FunctionRepository(db)
    if data.entity_id:
        entity = db.get(OntologyEntity, data.entity_id)
        if not entity:
            raise HTTPException(status_code=400, detail="关联实体不存在")

    func = OntologyFunction(
        entity_id=data.entity_id, entity_ids=data.entity_ids or [],
        name=data.name,
        callable_name=data.callable_name,
        description=data.description, return_type=data.return_type,
        input_schema=data.input_schema, logic_type=data.logic_type,
        logic_body=data.logic_body, is_derived_property=data.is_derived_property,
        status=data.status, tags=data.tags,
    )
    repo.create(func)

    write_audit(
        db, user_id=user.id,
        user_name=user.name,
        action="create", target_type="function",
        target_id=func.id, target_name=func.name,
    )
    repo.commit()
    return _func_to_out(func, repo.get_entity_name(func.entity_id))


@router.put("/{func_id}", response_model=FunctionOut)
def update_function(
    func_id: str, data: FunctionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    repo = FunctionRepository(db)
    func = repo.get_by_id(func_id)
    if not func:
        raise HTTPException(status_code=404, detail="函数不存在")

    changes = []
    for field, value in data.model_dump(exclude_unset=True).items():
        old = getattr(func, field)
        if old != value:
            changes.append({"field": field, "oldValue": old, "newValue": value})
            setattr(func, field, value)

    if changes:
        write_audit(
            db, user_id=user.id if user else None,
            user_name=user.name if user else None,
            action="update", target_type="function",
            target_id=func.id, target_name=func.name, changes=changes,
        )
    repo.commit()
    return _func_to_out(func, repo.get_entity_name(func.entity_id))


@router.delete("/{func_id}", status_code=204)
def delete_function(
    func_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    repo = FunctionRepository(db)
    func = repo.get_by_id(func_id)
    if not func:
        raise HTTPException(status_code=404, detail="函数不存在")

    write_audit(
        db, user_id=user.id,
        user_name=user.name,
        action="delete", target_type="function",
        target_id=func.id, target_name=func.name,
    )
    repo.delete(func)
    repo.commit()


@router.post("/{func_id}/test", response_model=FunctionTestResult)
def test_function(
    func_id: str,
    data: FunctionTestRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    repo = FunctionRepository(db)
    func = repo.get_by_id(func_id)
    if not func:
        raise HTTPException(status_code=404, detail="函数不存在")

    from app.services.function_executor import FunctionExecutor
    executor = FunctionExecutor(db)
    params = data.params if data else {}
    result = executor.execute(func, params)

    if result.success:
        func.execution_count += 1
        func.last_executed = datetime.utcnow()
        repo.commit()

    return FunctionTestResult(
        success=result.success,
        result=result.value,
        error=result.error,
        execution_ms=result.execution_ms,
    )
