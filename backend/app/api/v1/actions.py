import keyword
import re
import hashlib
import json
from datetime import datetime
from uuid import uuid4
from pathlib import Path
from contextlib import nullcontext

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.core.deps import require_user
from app.database import get_db
from app.models import OntologyEntity
from app.models.action import EntityAction
from app.models.action_execution import ActionExecution
from app.models.user import User
from app.models.scenario import ScenarioDict
from app.repositories.action_repo import ActionRepository
from app.schemas.action import (
    ActionCreate,
    ActionExecuteRequest,
    ActionExecuteResult,
    ActionOut,
    ActionTypeInfo,
    ActionUpdate,
    ActionReconciliation,
)
from app.services.action_executors import get_all_type_info, get_executor
from app.services.audit import write_audit

router = APIRouter(prefix="/actions", tags=["actions"])


@router.get("/types", response_model=list[ActionTypeInfo])
def list_action_types():
    return get_all_type_info()


def _validate_action_scope(db, values, action=None):
    category = values.get("category", action.category if action else "domain")
    eid = values.get("entity_id", action.entity_id if action else None)
    oid = values.get("ontology_id", action.ontology_id if action else None)
    if category == "domain" and not eid:
        raise HTTPException(422, "领域行动必须绑定对象")
    if category == "system" and eid:
        raise HTTPException(422, "系统行动不应绑定对象")
    entity = db.get(OntologyEntity, eid) if eid else None
    if eid and not entity:
        raise HTTPException(422, "行动关联对象不存在")
    if oid and not db.get(ScenarioDict, oid):
        raise HTTPException(422, "行动关联本体不存在")
    if entity and oid and entity.ontology_id != oid:
        raise HTTPException(422, "行动及关联对象必须属于同一本体")
    values["ontology_id"] = oid or (entity.ontology_id if entity else None)
    from app.services.action_contracts import validate_action_config, validate_parameter_references
    try:
        validate_parameter_references(db, values.get("parameters_json", action.parameters_json if action else None), values["ontology_id"])
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if values.get("type_config") is not None:
        config = dict(values["type_config"])
        if {"source_code", "version_id", "_version_entity_id"}.intersection(config):
            raise HTTPException(422, "发布快照字段由服务端管理")
        config["ontology_id"] = values["ontology_id"]
        if action and config.get("script") != (action.type_config or {}).get("script"):
            for key in ("source_path", "func_name"):
                config.pop(key, None)
        if config.get("source_path"):
            if not action:
                raise HTTPException(422, "请通过行动工作区入口创建源码绑定")
            try:
                Path(config["source_path"]).resolve().relative_to((WORKSPACE_DIR / ("action_" + action.id)).resolve())
            except ValueError as exc:
                raise HTTPException(422, "行动源码必须位于自身工作区") from exc
        values["type_config"] = config
    if values.get("status", action.status if action else "active") == "active":
        try:
            validate_action_config(db, values.get("action_type", action.action_type if action else None),
                values.get("type_config", action.type_config if action else None), values["ontology_id"], eid)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
    return values


@router.get("/notifications")
def list_notifications(db: Session = Depends(get_db), user: User = Depends(require_user)):
    from app.models.audit import AuditLog
    rows = db.query(AuditLog).filter_by(target_type="notification", user_id=user.id).order_by(AuditLog.timestamp.desc()).limit(100).all()
    return [{"id": row.target_id, "timestamp": row.timestamp, "channel": row.target_name,
             "status": row.status, "receipt": json.loads(row.details or "{}")} for row in rows]


@router.get("", response_model=list[ActionOut])
def list_actions(
    entity_id: str | None = Query(None),
    status: str | None = Query(None),
    action_type: str | None = Query(None),
    category: str | None = Query(None),
    search: str | None = Query(None),
    ontology_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    repo = ActionRepository(db)
    actions = repo.list_with_filters(
        entity_id=entity_id, status=status,
        action_type=action_type, category=category,
        search=search, ontology_id=ontology_id,
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
    action = EntityAction(**_validate_action_scope(db, data.model_dump()))
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
    for field, value in _validate_action_scope(db, data.model_dump(exclude_unset=True), action).items():
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
    action_id: str, request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    repo = ActionRepository(db)
    action = repo.get_by_id(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="动作不存在")

    registry = getattr(request.app.state, "function_registry", None)
    with registry.mutation_lock() if registry else nullcontext():
        config = action.type_config or {}
        if config.get("source_path"):
            from app.api.v1.functions import _purge_function_runtime
            from app.models.function import OntologyFunction
            _purge_function_runtime(request, config.get("callable_name"), config["source_path"], config.get("func_name"), action.ontology_id)
            db.query(OntologyFunction).filter_by(source_path=config["source_path"], ontology_id=action.ontology_id).delete(synchronize_session=False)
        write_audit(db, user_id=user.id, user_name=user.name, action="delete", target_type="action", target_id=action.id, target_name=action.name)
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
    if not action and data and data.version_id:
        from app.models.version import OntologyVersion
        from app.models.version_components import OntologyVersionAction
        frozen = db.query(OntologyVersionAction).filter_by(version_id=data.version_id, source_action_id=action_id).first()
        version = db.get(OntologyVersion, data.version_id)
        if frozen and version and version.status == "published":
            action = EntityAction(id=action_id, name=frozen.name, action_type=frozen.action_type,
                                  ontology_id=version.ontology_id, status="active", parameters_json=frozen.parameters_json,
                                  type_config=frozen.type_config, impact_count=0)
    if not action:
        raise HTTPException(status_code=404, detail="动作不存在")
    if action.status != "active" and not (data and data.version_id):
        raise HTTPException(status_code=400, detail="动作未激活")
    version_action = None
    if data and data.version_id:
        from app.models.version import OntologyVersion
        from app.models.version_components import OntologyVersionAction
        version = db.get(OntologyVersion, data.version_id)
        version_action = db.query(OntologyVersionAction).filter_by(version_id=data.version_id, source_action_id=action.id).first()
        if not version or version.status != "published" or not version_action:
            raise HTTPException(404, "动作不在指定已发布版本中")

    execution_ontology_id = action.ontology_id or (action.entity.ontology_id if action.entity else None)
    execution_entity_id = action.entity_id
    if version_action:
        from app.models.version import OntologyVersionEntity
        execution_ontology_id = version.ontology_id
        frozen_entity = db.get(OntologyVersionEntity, version_action.version_entity_id) if version_action.version_entity_id else None
        execution_entity_id = frozen_entity.source_entity_id if frozen_entity else None

    from app.services.agent_actions import validate_parameters
    try:
        params = validate_parameters(version_action.parameters_json if version_action else action.parameters_json, data.params if data else {})
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    dry_run = data.dry_run if data else False
    key = data.idempotency_key if data and data.idempotency_key else str(uuid4())
    if len(key) > 120:
        raise HTTPException(422, "幂等键不得超过 120 字符")
    digest = hashlib.sha256(json.dumps({"action_id": action_id, "params": params, "dry_run": dry_run, "version_id": data.version_id if data else None}, sort_keys=True, default=str).encode()).hexdigest()
    record = db.query(ActionExecution).filter_by(user_id=user.id, idempotency_key=key).first()
    if not record:
        record = ActionExecution(action_id=action.id, ontology_id=execution_ontology_id,
                                 user_id=user.id, idempotency_key=key, request_hash=digest, params=params, dry_run=dry_run)
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            record = db.query(ActionExecution).filter_by(user_id=user.id, idempotency_key=key).one()
    if record.request_hash != digest:
        raise HTTPException(409, "幂等键已用于不同的行动或参数")
    if record.state != "pending":
        return ActionExecuteResult(success=record.state == "succeeded", message=record.message or "执行正在进行或结果待核对，不会重复提交",
                                   output=record.output, execution_id=record.id, state=record.state)
    claimed = db.query(ActionExecution).filter_by(id=record.id, state="pending").update({"state": "executing", "started_at": datetime.utcnow()})
    db.commit()
    if not claimed:
        db.refresh(record)
        return ActionExecuteResult(success=record.state == "succeeded", message=record.message or "执行已被其他请求接管", output=record.output,
                                   execution_id=record.id, state=record.state)
    config = dict(action.type_config or {})
    config["ontology_id"] = record.ontology_id
    from app.services.agent_actions import action_execution_context
    execution_context = action_execution_context({"ontology_id": record.ontology_id,
        "entity_id": execution_entity_id, "version_id": data.version_id if data else None}, user=user, dry_run=dry_run)
    if action.action_type in {"custom_script", "call_function"}:
        config["_exec_context"] = execution_context
    if not version_action and action.action_type == "modify_attribute" and action.entity_id and config.get("target_entity_id") != action.entity_id:
        invalid_target = True
    else:
        invalid_target = False
    from app.services.action_executors.base import ExecutionResult
    try:
        if invalid_target:
            result = ExecutionResult(False, "修改属性目标必须为行动所属对象", {"outcome": "failed"})
        elif version_action:
            from app.services.version_action_executor import execute_version_action
            result = await execute_version_action(db, version_action, params, dry_run, context=execution_context)
        else:
            executor = get_executor(action.action_type, db=db)
            result = await executor.execute(config, params, dry_run)
    except Exception as exc:
        result = ExecutionResult(False, str(exc), {"outcome": "unknown"})
    record.state = "succeeded" if result.success else ("unknown" if (result.output or {}).get("outcome") in {"unknown", "committed_unrecorded", "partial_committed"} else "failed")
    record.message, record.output, record.finished_at = result.message, result.output, datetime.utcnow()
    if not dry_run:
        if result.success:
            action.impact_count = (action.impact_count or 0) + 1
        write_audit(
            db, user_id=user.id if user else None,
            user_name=user.name if user else None,
            action="execute", target_type="action",
            target_id=action.id, target_name=action.name,
            details=json.dumps({"execution_id": record.id, "ontology_id": record.ontology_id, "params": params,
                                "output": result.output, "message": result.message, "success": result.success,
                                "dry_run": dry_run}, ensure_ascii=False, default=str),
            status="success" if result.success else record.state,
        )
    execution_id = record.id
    try:
        repo.commit()
    except Exception as exc:
        db.rollback()
        # A dispatched side effect cannot be classified as safely failed just
        # because its ledger/audit transaction failed after the source commit.
        try:
            interrupted = db.get(ActionExecution, execution_id)
            interrupted.state = "unknown"
            interrupted.message = "业务执行后结果记录失败，请核对源数据或外部回执"
            interrupted.output = {"outcome": "committed_unrecorded" if result.success else "unknown"}
            db.commit()
        except Exception:
            db.rollback()
        return ActionExecuteResult(success=False, message="执行结果记录失败，请核对业务回执；原幂等键不会重发",
                                   output={"outcome": "committed_unrecorded" if result.success else "unknown"}, execution_id=execution_id, state="unknown")
    return ActionExecuteResult(success=result.success, message=result.message, output=result.output, execution_id=execution_id, state=record.state)


@router.get("/{action_id}/executions/by-key")
def action_execution_by_key(action_id: str, key: str = Query(..., max_length=120),
                            db: Session = Depends(get_db), user: User = Depends(require_user)):
    """Read an account's durable receipt without dispatching its side effect."""
    record = db.query(ActionExecution).filter_by(action_id=action_id, user_id=user.id, idempotency_key=key).first()
    if not record:
        raise HTTPException(404, "执行记录尚未登记或不属于当前账户")
    return {"execution_id": record.id, "action_id": record.action_id, "params": record.params,
            "state": record.state, "success": record.state == "succeeded",
            "message": record.message or "执行正在进行或结果待核对，不会重复提交", "output": record.output,
            "created_at": record.created_at, "finished_at": record.finished_at}


@router.post("/{action_id}/executions/{execution_id}/reconcile", response_model=ActionExecuteResult)
def reconcile_action_execution(action_id: str, execution_id: str, data: ActionReconciliation,
                               db: Session = Depends(get_db), user: User = Depends(require_user)):
    from app.core.permissions import role_permissions
    if not user.is_active or not {"rule:execute", "rule:write"}.intersection(role_permissions(db, user.role)):
        raise HTTPException(403, "人工核查需要执行权限")
    record = db.query(ActionExecution).filter_by(id=execution_id, action_id=action_id).first()
    if not record or (record.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "执行记录不存在或不属于当前账户")
    if record.state not in {"unknown", "committed_unrecorded"}:
        raise HTTPException(409, "仅结果未知的执行可以人工核查；执行中请等待，终态不会再次变更")
    if len(data.evidence.strip()) < 10:
        raise HTTPException(422, "请填写实际核查的源数据或外部回执证据")
    previous_output = dict(record.output or {})
    verification = {"resolution": data.resolution, "evidence": data.evidence.strip(),
                    "receipt_id": data.receipt_id, "user_id": user.id, "user_name": user.name,
                    "verified_at": datetime.utcnow().isoformat(), "method": "manual"}
    output = {**previous_output, "observed_outcome": previous_output.get("outcome", "unknown"),
              "outcome": "manually_reconciled", "manual_reconciliation": verification}
    message = "经人工核查确认为" + ("成功" if data.resolution == "succeeded" else "失败") + "；原幂等键保留，不会重新执行"
    claimed = db.query(ActionExecution).filter(ActionExecution.id == execution_id,
        ActionExecution.state.in_(["unknown", "committed_unrecorded"])).update(
            {"state": data.resolution, "output": output, "message": message, "finished_at": datetime.utcnow()},
            synchronize_session=False)
    if not claimed:
        db.rollback()
        raise HTTPException(409, "该执行已被其他核查请求更新，请重新读取结果")
    if data.resolution == "succeeded" and not record.dry_run:
        from sqlalchemy import func
        db.query(EntityAction).filter_by(id=action_id).update(
            {"impact_count": func.coalesce(EntityAction.impact_count, 0) + 1}, synchronize_session=False)
    write_audit(db, user_id=user.id, user_name=user.name, action="manual_reconciliation", target_type="action",
        target_id=action_id, target_name=(db.get(EntityAction, action_id).name if db.get(EntityAction, action_id) else action_id),
        details=json.dumps({"execution_id": execution_id, "ontology_id": record.ontology_id,
                            "previous_state": record.state, "previous_output": previous_output, **verification}, ensure_ascii=False),
        status="success" if data.resolution == "succeeded" else "failed")
    db.commit()
    return ActionExecuteResult(success=data.resolution == "succeeded", message=message, output=output,
                               execution_id=execution_id, state=data.resolution)


WORKSPACE_DIR = Path(getattr(settings, "WORKSPACE_ROOT", "") or Path(__file__).resolve().parents[3] / ".." / "workspace")


def _sanitize_dirname(name: str) -> str:
    return re.sub(r'[^\w\-.]', '_', name)


def _generate_action_template(name: str, description: str) -> str:
    safe_name = re.sub(r'\W', '_', name)
    if not safe_name.isidentifier() or keyword.iskeyword(safe_name):
        safe_name = f"action_{safe_name}"
    return f'''from ontology_runtime import Function, call_function


@Function(
    name={safe_name!r},
    description={description!r},
    type="action",
    params=[],
    return_type="object",
)
def {safe_name}(params):
    return {{}}
'''


class WorkspaceOut(BaseModel):
    folder: str
    port: int
    public_url: str = ""
    registration_error: str | None = None


@router.post("/{action_id}/workspace", response_model=WorkspaceOut)
def open_action_workspace(
    action_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    repo = ActionRepository(db)
    action = repo.get_by_id(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="动作不存在")

    if getattr(action, "action_type", "custom_script") != "custom_script":
        raise HTTPException(422, "此行动使用类型配置执行；仅 custom_script 支持 Python 工作区")
    # Display names may be Chinese; new actions retain their callable identifier
    # in type_config without changing the existing action contract.
    configured_name = (action.type_config or {}).get("callable_name")
    callable_name = configured_name if isinstance(configured_name, str) and configured_name else action.name
    dir_name = "action_" + action.id if getattr(action, "id", None) else _sanitize_dirname(callable_name)
    action_dir = (WORKSPACE_DIR / dir_name).resolve()
    action_dir.mkdir(parents=True, exist_ok=True)

    main_file = action_dir / "main.py"
    registration_error = None
    if not main_file.exists() and not (action.type_config or {}).get("source_path"):
        template = _generate_action_template(callable_name, action.description or "")
        template = template.replace("    params=[],", f"    params={getattr(action, 'parameters_json', None) or []!r},")
        main_file.write_text(template, encoding="utf-8")
    if db is not None and getattr(action, "id", None):
        import ast
        config = dict(action.type_config or {})
        node = None
        try:
            tree = ast.parse(main_file.read_text(encoding="utf-8"))
            functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
            preferred = config.get("func_name") or configured_name
            node = next((node for node in functions if node.name == preferred), None)
            if node is None and not config.get("func_name") and len(functions) == 1:
                node = functions[0]
            if node is None:
                registration_error = "行动工作区缺少已关联的入口，请修复源码后重新登记"
        except (SyntaxError, OSError) as exc:
            registration_error = f"工作区源码无法登记，仍可打开编辑器修复: {exc}"
        from app.models.function import OntologyFunction
        if node:
            conflict = db.query(OntologyFunction).filter_by(callable_name=node.name, ontology_id=action.ontology_id).first()
            if conflict and conflict.source_path != str(main_file):
                raise HTTPException(409, "工作区 callable_name 与当前本体的其他函数冲突")
            config.update(func_name=node.name, callable_name=node.name)
        config.update(source_path=str(main_file), ontology_id=action.ontology_id)
        action.type_config = config
        (action_dir / ".ontology.json").write_text(json.dumps({"ontology_id": action.ontology_id, "action_id": action.id}), encoding="utf-8")
        db.commit()
        from app.services.function_runtime.registry import FunctionRegistry
        from app.services.function_runtime.watcher import FunctionWatcher
        if not registration_error:
            FunctionWatcher(FunctionRegistry(db), str(WORKSPACE_DIR)).scan_all()

    # 同 functions.open_workspace：主机名交由浏览器推导，后端只提供路径与端口。
    return WorkspaceOut(
        folder=str(action_dir),
        port=settings.CODE_SERVER_PORT,
        public_url=settings.CODE_SERVER_PUBLIC_URL,
        registration_error=registration_error,
    )
