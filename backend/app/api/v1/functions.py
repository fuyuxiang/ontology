from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import require_user
from app.database import get_db
from app.models import OntologyEntity
from app.models.function import OntologyFunction
from app.models.user import User
from app.repositories.function_repo import FunctionRepository
from app.schemas.function import (
    FunctionCreate,
    FunctionOut,
    FunctionTestRequest,
    FunctionTestResult,
    FunctionUpdate,
)
from app.services.audit import write_audit

router = APIRouter(prefix="/functions", tags=["functions"])


def _func_to_out(f: OntologyFunction, entity_name: str) -> FunctionOut:
    return FunctionOut(
        id=f.id, entity_id=f.entity_id, entity_ids=f.entity_ids or [],
        entity_name=entity_name,
        name=f.name, callable_name=f.callable_name or "",
        description=f.description, return_type=f.return_type,
        input_schema=f.input_schema, logic_type=f.logic_type,
        logic_body=f.logic_body,
        status=f.status, execution_count=f.execution_count,
        last_executed=f.last_executed, tags=f.tags,
        created_at=f.created_at, updated_at=f.updated_at,
    )


@router.get("", response_model=list[FunctionOut])
def list_functions(
    entity_id: str | None = None,
    status: str | None = None,
    search: str | None = None,
    ontology_id: str | None = None,
    db: Session = Depends(get_db),
):
    repo = FunctionRepository(db)
    funcs = repo.list_with_filters(
        entity_id=entity_id, status=status, search=search, ontology_id=ontology_id
    )
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
        logic_body=data.logic_body,
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
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    repo = FunctionRepository(db)
    func = repo.get_by_id(func_id)
    if not func:
        raise HTTPException(status_code=404, detail="函数不存在")

    callable_name = func.callable_name
    source_path = func.source_path

    write_audit(
        db, user_id=user.id,
        user_name=user.name,
        action="delete", target_type="function",
        target_id=func.id, target_name=func.name,
    )
    repo.delete(func)
    repo.commit()

    # 彻底删除：清运行时缓存 + 删掉工作区源文件，避免 scan_all/文件监听把函数重新登记回来
    _purge_function_runtime(request, callable_name, source_path)


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


WORKSPACE_DIR = Path(__file__).resolve().parents[3] / ".." / "workspace"
CODE_SERVER_PORT = int(__import__("os").environ.get("CODE_SERVER_PORT", "8443"))


def _is_within_workspace(target: Path) -> bool:
    """确保待删除路径位于工作区目录内，避免误删工作区外的文件。"""
    try:
        root = WORKSPACE_DIR.resolve()
        target.resolve().relative_to(root)
        return True
    except (ValueError, OSError):
        return False


def _purge_function_runtime(
    request: Request, callable_name: str, source_path: str | None
) -> None:
    """UI 删除函数后清理运行时痕迹：内存 registry 缓存 + 工作区源文件/目录。

    否则应用重启时 scan_all 会遍历工作区 .py 重新登记，或文件监听在文件被触碰时
    通过 _persist 把已删除的函数重建回数据库。
    """
    import logging
    import shutil

    logger = logging.getLogger(__name__)

    # 1. 清内存缓存，使执行器/能力列表立即反映删除
    registry = getattr(request.app.state, "function_registry", None)
    if registry is not None and callable_name:
        try:
            registry.discard(callable_name)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"清理 function registry 缓存失败 {callable_name}: {e}")

    # 2. 删除该函数登记来源的源文件
    if source_path:
        src = Path(source_path)
        if src.is_file() and _is_within_workspace(src):
            try:
                src.unlink()
            except OSError as e:
                logger.warning(f"删除函数源文件失败 {src}: {e}")

    # 3. 删除工作区中以 callable_name 命名的函数目录（open_workspace 生成的）
    if callable_name:
        func_dir = WORKSPACE_DIR / callable_name
        if func_dir.is_dir() and _is_within_workspace(func_dir):
            try:
                shutil.rmtree(func_dir)
            except OSError as e:
                logger.warning(f"删除函数工作区目录失败 {func_dir}: {e}")


def _generate_function_template(callable_name: str, description: str) -> str:
    return f'''from ontology_runtime import Function, call_function


@Function(
    name="{callable_name}",
    description="{description}",
    type="logic",
    params=[],
    return_type="object",
)
def {callable_name}(params):
    return {{}}
'''


class WorkspaceOut(BaseModel):
    url: str
    folder: str


@router.post("/{func_id}/workspace", response_model=WorkspaceOut)
def open_workspace(
    func_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    repo = FunctionRepository(db)
    func = repo.get_by_id(func_id)
    if not func:
        raise HTTPException(status_code=404, detail="函数不存在")

    func_dir = (WORKSPACE_DIR / func.callable_name).resolve()
    func_dir.mkdir(parents=True, exist_ok=True)

    main_file = func_dir / "main.py"
    if not main_file.exists():
        template = _generate_function_template(func.callable_name, func.description or "")
        main_file.write_text(template, encoding="utf-8")

    host = request.headers.get("host", "localhost").split(":")[0]
    folder_path = str(func_dir)
    url = f"http://{host}:{CODE_SERVER_PORT}/?folder={folder_path}"
    return WorkspaceOut(url=url, folder=folder_path)
