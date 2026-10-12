from datetime import datetime
from pathlib import Path
import json
import keyword
from contextlib import nullcontext

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import require_user
from app.database import get_db
from app.models import OntologyEntity
from app.models.function import OntologyFunction
from app.models.user import User
from app.models.scenario import ScenarioDict
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
        ontology_id=f.ontology_id,
        entity_name=entity_name,
        name=f.name, callable_name=f.callable_name or "",
        description=f.description, return_type=f.return_type,
        input_schema=f.input_schema, logic_type=f.logic_type,
        logic_body=f.logic_body,
        status=f.status, execution_count=f.execution_count,
        last_executed=f.last_executed, tags=f.tags,
        created_at=f.created_at, updated_at=f.updated_at,
    )


def _validate_scope(db, values, existing=None):
    entity_ids = set(values.get("entity_ids", existing.entity_ids if existing else []) or [])
    entity_id = values.get("entity_id", existing.entity_id if existing else None)
    if entity_id:
        entity_ids.add(entity_id)
    entities = [db.get(OntologyEntity, eid) for eid in entity_ids]
    if any(e is None for e in entities):
        raise HTTPException(422, "关联对象不存在")
    oid = values.get("ontology_id", existing.ontology_id if existing else None)
    owners = {e.ontology_id for e in entities if e.ontology_id}
    if oid and not db.get(ScenarioDict, oid):
        raise HTTPException(422, "关联本体不存在")
    if len(owners) > 1 or (oid and owners and owners != {oid}):
        raise HTTPException(422, "函数及关联对象必须属于同一本体")
    values["ontology_id"] = oid or (next(iter(owners)) if owners else None)
    from app.services.action_contracts import validate_parameter_references
    try:
        validate_parameter_references(db, values.get("input_schema", existing.input_schema if existing else None), values["ontology_id"])
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    callable_name = values.get("callable_name", existing.callable_name if existing else "")
    if callable_name:
        duplicate = db.query(OntologyFunction).filter(OntologyFunction.callable_name == callable_name,
            OntologyFunction.ontology_id == values["ontology_id"],
            OntologyFunction.id != (existing.id if existing else "")).first()
        if duplicate:
            raise HTTPException(409, "当前本体中 callable_name 已存在")
    return values


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

    values = _validate_scope(db, data.model_dump())
    func = OntologyFunction(
        entity_id=data.entity_id, entity_ids=data.entity_ids or [],
        ontology_id=values["ontology_id"],
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
    func_id: str, data: FunctionUpdate, request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    repo = FunctionRepository(db)
    func = repo.get_by_id(func_id)
    if not func:
        raise HTTPException(status_code=404, detail="函数不存在")

    values = _validate_scope(db, data.model_dump(exclude_unset=True), func)
    registry = getattr(request.app.state, "function_registry", None)
    with registry.mutation_lock() if registry else nullcontext():
        old_callable, old_owner = func.callable_name, func.ontology_id
        _update_workspace_contract(func, values)
        changes = []
        for field, value in values.items():
            old = getattr(func, field)
            if old != value:
                changes.append({"field": field, "oldValue": old, "newValue": value})
                setattr(func, field, value)
        if changes:
            write_audit(
                db, user_id=user.id, user_name=user.name, action="update", target_type="function",
                target_id=func.id, target_name=func.name, changes=changes,
            )
        repo.commit()
        if registry:
            registry.discard(old_callable, old_owner)
            registry.sync_from_db()
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
    func_name, ontology_id = func.func_name, func.ontology_id

    registry = getattr(request.app.state, "function_registry", None)
    with registry.mutation_lock() if registry else nullcontext():
        # Purge the registration source before removing its row. A failed file
        # mutation must not claim deletion and later recreate the function.
        _purge_function_runtime(request, callable_name, source_path, func_name, ontology_id)
        write_audit(db, user_id=user.id, user_name=user.name, action="delete", target_type="function",
                    target_id=func.id, target_name=func.name)
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
    from app.services.function_runtime.models import ExecContext
    executor = FunctionExecutor(db)
    params = data.params if data else {}
    from app.models.entity import OntologyEntity
    ontology_id = func.ontology_id or (func.entity.ontology_id if func.entity else None)
    entity_ids = frozenset(row.id for row in db.query(OntologyEntity).filter_by(ontology_id=ontology_id)) if ontology_id else frozenset()
    result = executor.execute(func, params, context=ExecContext(ontology_id=ontology_id,
        entity_ids=entity_ids, user=user, action_mode="simulation"))

    if result.success and not result.requested_write:
        func.execution_count += 1
        func.last_executed = datetime.utcnow()
        repo.commit()

    return FunctionTestResult(
        success=result.success,
        result=result.value,
        error=result.error,
        execution_ms=result.execution_ms,
        outcome=result.outcome,
        simulated=result.outcome == "simulated",
        requested_write=result.requested_write,
        execution_complete=not bool(result.requested_write),
    )


WORKSPACE_DIR = Path(getattr(settings, "WORKSPACE_ROOT", "") or Path(__file__).resolve().parents[3] / ".." / "workspace")


def _is_within_workspace(target: Path) -> bool:
    """确保待删除路径位于工作区目录内，避免误删工作区外的文件。"""
    try:
        root = WORKSPACE_DIR.resolve()
        target.resolve().relative_to(root)
        return True
    except (ValueError, OSError):
        return False


def _purge_function_runtime(
    request: Request, callable_name: str, source_path: str | None, func_name=None, ontology_id=None
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
            registry.discard(callable_name, ontology_id)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"清理 function registry 缓存失败 {callable_name}: {e}")

    # 2. 删除该函数登记来源的源文件
    if source_path:
        src = Path(source_path)
        if src.is_file() and _is_within_workspace(src):
            try:
                import ast
                code = src.read_text(encoding="utf-8")
                tree = ast.parse(code)
                functions = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
                selected = [node for node in functions if node.name == (func_name or callable_name)]
                siblings = [node for node in functions if node not in selected]
                if selected and siblings:
                    lines = code.splitlines(keepends=True)
                    for node in sorted(selected, key=lambda item: item.lineno, reverse=True):
                        first = min([node.lineno, *[d.lineno for d in node.decorator_list]]) - 1
                        del lines[first:node.end_lineno]
                    src.write_text("".join(lines), encoding="utf-8")
                else:
                    src.unlink()
            except (OSError, SyntaxError) as e:
                raise HTTPException(409, f"删除函数源文件失败，函数尚未删除: {e}") from e

    # 3. 删除工作区中以 callable_name 命名的函数目录（open_workspace 生成的）
    if callable_name:
        func_dir = WORKSPACE_DIR / callable_name
        if func_dir.is_dir() and _is_within_workspace(func_dir) and not (func_dir / "main.py").exists():
            try:
                shutil.rmtree(func_dir)
            except OSError as e:
                raise HTTPException(409, f"删除函数工作区目录失败，函数尚未删除: {e}") from e


def _update_workspace_contract(func, values):
    """Keep editable metadata and the watcher decorator as one contract."""
    import ast
    if not func.source_path:
        return
    fields = {"callable_name", "description", "input_schema", "return_type", "logic_type", "logic_body", "ontology_id"}
    if not fields.intersection(values):
        return
    path = Path(func.source_path)
    if not _is_within_workspace(path):
        raise HTTPException(409, "函数源文件不在配置工作区中，不能自动更新注册契约")
    try:
        code = path.read_text(encoding="utf-8")
        tree = ast.parse(code)
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == (func.func_name or func.callable_name))
        decorator = next((d for d in node.decorator_list if isinstance(d, ast.Call)
            and ((isinstance(d.func, ast.Name) and d.func.id == "Function") or
                 (isinstance(d.func, ast.Attribute) and d.func.attr == "Function"))), None)
    except (OSError, SyntaxError, StopIteration) as exc:
        raise HTTPException(409, "工作区源文件无法解析注册契约，请先修复代码") from exc
    new_decorator = decorator is None
    if new_decorator:
        decorator = ast.Call(func=ast.Name(id="Function", ctx=ast.Load()), args=[], keywords=[])
    detach = values.get("logic_type", func.logic_type) != "python" or ("logic_body" in values and values["logic_body"] != func.logic_body)
    if not detach:
        new_name = values.get("callable_name", func.callable_name)
        if not new_name or not new_name.isidentifier() or keyword.iskeyword(new_name):
            raise HTTPException(422, "工作区 callable_name 必须为有效 Python 标识符")
        if values.get("ontology_id", func.ontology_id) != func.ontology_id:
            siblings = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n is not node and n.decorator_list]
            if siblings:
                raise HTTPException(409, "共享源文件中的函数不能单独转移本体，请先拆分工作区文件")
        updates = {"name": new_name, "description": values.get("description", func.description or ""),
                   "params": values.get("input_schema", func.input_schema) or [],
                   "return_type": values.get("return_type", func.return_type)}
        existing = {kw.arg: kw for kw in decorator.keywords}
        for key, value in updates.items():
            literal = ast.parse(repr(value), mode="eval").body
            if key in existing:
                existing[key].value = literal
            else:
                decorator.keywords.append(ast.keyword(arg=key, value=literal))
        replacement = "@" + ast.unparse(decorator) + "\n"
        (path.parent / ".ontology.json").write_text(json.dumps({"ontology_id": values.get("ontology_id", func.ontology_id),
                                                              "function_id": func.id}), encoding="utf-8")
    else:
        # Retain the user's Python implementation as an ordinary function;
        # stripping only its registration prevents a rescan reverting type.
        replacement = ""
        func.source_path = func.checksum = None
        func.registered_by = "ui"
    lines = code.splitlines(keepends=True)
    first, last = (node.lineno - 1, node.lineno - 1) if new_decorator else (decorator.lineno - 1, decorator.end_lineno)
    lines[first:last] = [replacement]
    path.write_text("".join(lines), encoding="utf-8")


def _generate_function_template(callable_name: str, description: str) -> str:
    return f'''from ontology_runtime import Function, call_function


@Function(
    name={callable_name!r},
    description={description!r},
    type="logic",
    params=[],
    return_type="object",
)
def {callable_name}(params):
    return {{}}
'''


class WorkspaceOut(BaseModel):
    folder: str
    port: int
    public_url: str = ""
    registration_error: str | None = None


@router.post("/{func_id}/workspace", response_model=WorkspaceOut)
def open_workspace(
    func_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    repo = FunctionRepository(db)
    func = repo.get_by_id(func_id)
    if not func:
        raise HTTPException(status_code=404, detail="函数不存在")

    if not func.callable_name or not func.callable_name.isidentifier() or keyword.iskeyword(func.callable_name):
        raise HTTPException(422, "工作区函数的 callable_name 必须为有效 Python 标识符")
    if func.source_path:
        main_file = Path(func.source_path).resolve()
        try:
            main_file.relative_to(WORKSPACE_DIR.resolve())
        except ValueError as exc:
            raise HTTPException(422, "源码必须位于配置的工作区") from exc
        func_dir = main_file.parent
    else:
        func_dir = (WORKSPACE_DIR / (func.id if func.ontology_id else func.callable_name)).resolve()
        main_file = func_dir / "main.py"
    func_dir.mkdir(parents=True, exist_ok=True)

    if not main_file.exists() and not func.source_path:
        template = _generate_function_template(func.callable_name, func.description or "")
        # Preserve the configured function contract in the generated decorator.
        template = template.replace("    params=[],", f"    params={func.input_schema or []!r},")
        main_file.write_text(template, encoding="utf-8")
    (func_dir / ".ontology.json").write_text(json.dumps({"ontology_id": func.ontology_id, "function_id": func.id}), encoding="utf-8")
    func.source_path = str(main_file)
    import ast
    registration_error = None
    try:
        tree = ast.parse(main_file.read_text(encoding="utf-8"))
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
        node = next((node for node in functions if node.name == (func.func_name or func.callable_name)), None)
        if node is None:
            registration_error = "工作区中未找到此函数的实现，请在编辑器修复后重新登记"
        else:
            func.func_name = node.name
    except (SyntaxError, OSError) as exc:
        registration_error = f"工作区源码无法登记，仍可打开编辑器修复: {exc}"
    func.logic_type = "python"
    if not registration_error:
        _update_workspace_contract(func, {"callable_name": func.callable_name, "input_schema": func.input_schema,
                                         "description": func.description, "return_type": func.return_type})
    repo.commit()
    from app.services.function_runtime.registry import FunctionRegistry
    from app.services.function_runtime.watcher import FunctionWatcher
    if not registration_error:
        FunctionWatcher(FunctionRegistry(db), str(WORKSPACE_DIR)).scan_all()

    # 只返回工作区路径与端口：编辑器 URL 的主机名必须由浏览器按当前访问地址推导。
    # 后端读到的 Host 头已被前端 dev server 代理（changeOrigin）重写，无法反映真实访问地址。
    return WorkspaceOut(
        folder=str(func_dir),
        port=settings.CODE_SERVER_PORT,
        public_url=settings.CODE_SERVER_PUBLIC_URL,
        registration_error=registration_error,
    )
