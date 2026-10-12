"""ORM 引擎 + 逻辑执行 + 动作执行 + 导出"""
from __future__ import annotations

import csv
import json
import logging
import os
import time
import asyncio
from uuid import uuid4
from typing import Any

from sqlalchemy.orm import Session

from app.models.action import EntityAction
from app.models.entity import OntologyEntity
from app.models.function import OntologyFunction
from app.models.shared_ref import OntologySharedRef
from app.services.action_executors import run_executor_sync
from app.services.function_executor import FunctionExecutor
from app.services.function_runtime.registry import FunctionRegistry
from app.services.function_runtime.sandbox import UnifiedSandbox
from app.services.mcp_tools.mcp_config import (
    PYTHON_RUNTIME_TIMEOUT_SEC,
    PYTHON_WORKSPACE_BASE,
)
from app.services.mcp_tools.registry import MCPTool, register
from app.services.mcp_tools.resolve import resolve_ontology_id

logger = logging.getLogger(__name__)


def _get_all_entity_ids_in_ontology(db: Session, ontology_id: str) -> set[str]:
    owned = {r[0] for r in db.query(OntologyEntity.id).filter(
        OntologyEntity.ontology_id == ontology_id
    ).all()}
    shared = {r[0] for r in db.query(OntologySharedRef.entity_id).filter(
        OntologySharedRef.target_ontology_id == ontology_id
    ).all()}
    return owned | shared


# ── ontology_service_execute ───────────────────────────────

@register
class ServiceExecuteTool(MCPTool):
    name = "ontology_service_execute"
    description = "平台核心 ORM 引擎。通过 ontology_name 和 code 参数执行 ORM 风格的数据查询。"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology_name": {"type": "string", "description": "本体英文标识"},
                "code": {"type": "string", "description": "要执行的 ORM 代码"},
                "page_size": {"type": "integer"},
            },
            "required": ["ontology_name", "code"],
            "additionalProperties": False,
        }

    async def execute(self, arguments: dict, **ctx: Any) -> Any:
        from app.services.mcp_tools.python_workspace import _ensure_workspace, RunPythonFileTool
        ontology_name = arguments["ontology_name"]
        code = arguments["code"]
        validation = UnifiedSandbox().validate(code.replace("__ontology_runtime__", "ontology_runtime"))
        if not validation.valid:
            return {"error": "ORM 代码安全检查失败: " + "; ".join(validation.errors)}

        from app.services.function_runtime.sandbox import RUNTIME_EXPORTS
        wrapped = f"import json\nfrom ontology_runtime import {', '.join(sorted(RUNTIME_EXPORTS))}\n{code}\nprint(json.dumps(result, ensure_ascii=False, default=str))"
        ws = _ensure_workspace(ontology_name)
        tmp_path = os.path.join(ws, f"_orm_exec_{uuid4().hex}.py")

        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(wrapped)

        try:
            request = ctx.get("request")
            execution = await RunPythonFileTool().execute({"ontology_name": ontology_name, "file_path": tmp_path,
                "user_id": str(getattr(request.state, "mcp_user_id", "") or "") if request else "",
                "timeout_sec": PYTHON_RUNTIME_TIMEOUT_SEC}, **ctx)
            if execution.get("error") or not execution.get("success"):
                return {"error": execution.get("error") or execution.get("stderr", "").strip() or "执行失败"}
            stdout = execution.get("stdout", "")
            try:
                return json.loads(stdout.strip() or "{}")
            except json.JSONDecodeError:
                return {"result": stdout.strip()}
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass


# ── ontology_run_logic ─────────────────────────────────────

@register
class RunLogicTool(MCPTool):
    name = "ontology_run_logic"
    description = "执行本体已注册的 logic 函数。"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology_name": {"type": "string"},
                "logic_name": {"type": "string", "description": "逻辑函数名"},
                "user_id": {"type": "string"},
                "params": {"type": "object", "description": "传给逻辑的参数字典"},
                "version_id": {"type": "string"},
            },
            "required": ["ontology_name", "logic_name", "user_id"],
            "additionalProperties": False,
        }

    async def execute(self, arguments: dict, **ctx: Any) -> Any:
        db: Session = ctx["db"]
        ontology_name = arguments["ontology_name"]
        logic_name = arguments["logic_name"]
        params = arguments.get("params") or {}

        ontology_id = resolve_ontology_id(db, ontology_name)
        if not ontology_id:
            return {"error": f"本体 '{ontology_name}' 不存在"}

        all_entity_ids = _get_all_entity_ids_in_ontology(db, ontology_id)

        # 查找函数：按 callable_name 或 name 匹配
        func = (
            db.query(OntologyFunction)
            .filter(
                (OntologyFunction.callable_name == logic_name) |
                (OntologyFunction.name == logic_name),
                (OntologyFunction.ontology_id == ontology_id) |
                (OntologyFunction.entity_id.in_(all_entity_ids)),
                OntologyFunction.status == "active",
            )
            .first()
        )

        from app.models.version import OntologyVersion
        from app.models.version_components import OntologyVersionFunction
        version_query = db.query(OntologyVersion).filter_by(ontology_id=ontology_id, status="published")
        version_query = version_query.filter_by(id=arguments["version_id"]) if arguments.get("version_id") else version_query.filter_by(is_active=True)
        version = version_query.first()
        executor = FunctionExecutor(db)
        from app.models.user import User
        from app.services.function_runtime.models import ExecContext
        request = ctx.get("request")
        user = db.get(User, getattr(request.state, "mcp_user_id", None)) if request else ctx.get("user")
        from app.core.permissions import has_permission
        if not (has_permission(user, "rule:execute", db) or has_permission(user, "rule:write", db)):
            return {"error": "业务函数执行需要已登录用户的执行权限"}
        execution_context = ExecContext(ontology_id=ontology_id, version_id=version.id if version else None,
            entity_ids=frozenset(all_entity_ids), user=user, action_mode="execute")
        if version:
            snapshots = [fn for fn in version.functions if logic_name in (fn.callable_name, fn.name, fn.source_function_id)]
            if len(snapshots) != 1:
                return {"error": "逻辑不在当前发布版本中"}
            result = executor.execute_snapshot(snapshots[0], params, context=execution_context)
        elif arguments.get("version_id"):
            return {"error": "指定发布版本不存在"}
        else:
            if not func:
                return {"error": f"逻辑函数 '{logic_name}' 不存在或无权访问"}
            result = executor.execute(func, params, context=execution_context)
        if result.success:
            return {
                "success": True,
                "result": result.value,
                "execution_ms": result.execution_ms,
                "outcome": result.outcome,
                "committed_writes": result.committed_writes,
            }
        return {
            "success": False,
            "error": result.error,
            "execution_ms": result.execution_ms,
            "outcome": result.outcome,
            "committed_writes": result.committed_writes,
        }


# ── ontology_run_action ────────────────────────────────────

@register
class RunActionTool(MCPTool):
    name = "ontology_run_action"
    description = "在对象上执行已绑定的 action（会写库或改数据）。仅在用户明确授权时调用。"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology_name": {"type": "string"},
                "object_name": {"type": "string"},
                "action_name": {"type": "string"},
                "user_id": {"type": "string"},
                "params": {"type": "object", "description": "action 入参字典"},
                "version_id": {"type": "string"},
                "idempotency_key": {"type": "string"},
            },
            "required": ["ontology_name", "object_name", "action_name", "user_id"],
            "additionalProperties": False,
        }

    async def execute(self, arguments: dict, **ctx: Any) -> Any:
        db: Session = ctx["db"]
        ontology_name = arguments["ontology_name"]
        object_name = arguments["object_name"]
        action_name = arguments["action_name"]
        params = arguments.get("params") or {}

        ontology_id = resolve_ontology_id(db, ontology_name)
        if not ontology_id:
            return {"error": f"本体 '{ontology_name}' 不存在"}

        all_entity_ids = _get_all_entity_ids_in_ontology(db, ontology_id)

        # 查找实体
        entity = (
            db.query(OntologyEntity)
            .filter(OntologyEntity.name == object_name, OntologyEntity.id.in_(all_entity_ids))
            .first()
        )

        # 查找 action
        action = (
            db.query(EntityAction)
            .filter(
                EntityAction.name == action_name,
                (EntityAction.entity_id == (entity.id if entity else None)) | (EntityAction.ontology_id == ontology_id),
                EntityAction.status == "active",
            )
            .first()
        )

        from app.models.version import OntologyVersion
        version_query = db.query(OntologyVersion).filter_by(ontology_id=ontology_id, status="published")
        version_query = version_query.filter_by(id=arguments["version_id"]) if arguments.get("version_id") else version_query.filter_by(is_active=True)
        version = version_query.first()
        if arguments.get("version_id") and not version:
            return {"error": "指定发布版本不存在"}
        if version:
            version_entities = [e for e in version.entities if e.name == object_name]
            if len(version_entities) != 1:
                return {"error": "对象不在当前发布版本中"}
            snapshots = [a for a in version.actions if a.name == action_name and a.version_entity_id in (None, version_entities[0].id)]
            if len(snapshots) != 1:
                return {"error": "行动不在当前发布版本中"}
            action_id = snapshots[0].source_action_id
        elif action and entity:
            action_id = action.id
        else:
            return {"error": f"动作 '{action_name}' 不存在或无权访问"}
        try:
            from app.api.v1.actions import execute_action
            from app.schemas.action import ActionExecuteRequest
            from app.models.user import User
            user = db.get(User, getattr(ctx.get("request").state, "mcp_user_id", None))
            if not user:
                return {"error": "真实行动执行需要已登录用户"}
            result = await execute_action(action_id, ActionExecuteRequest(params=params,
                version_id=version.id if version else None, idempotency_key=arguments.get("idempotency_key")), db, user)
            return result.model_dump()
        except Exception as e:
            return {"error": str(e)}


# ── export_to_minio ────────────────────────────────────────

@register
class ExportToMinioTool(MCPTool):
    name = "export_to_minio"
    description = "将数据导出为 CSV 并上传到 MinIO，返回下载链接。"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology_name": {"type": "string"},
                "data": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "要导出的数据（字典数组）",
                },
                "filename": {"type": "string", "description": "可选文件名"},
                "user_id": {"type": "string"},
            },
            "required": ["ontology_name", "data", "user_id"],
            "additionalProperties": False,
        }

    async def execute(self, arguments: dict, **ctx: Any) -> Any:
        ontology_name = arguments["ontology_name"]
        data = arguments["data"]
        filename = arguments.get("filename") or f"export_{ontology_name}_{int(time.time())}.csv"
        from app.services.mcp_tools.python_workspace import _ensure_workspace
        import re
        if not re.fullmatch(r"[\w-]+\.csv", filename):
            return {"error": "非法导出文件名"}

        if not data:
            return {"error": "数据为空，无法导出"}

        # 写 CSV 到临时目录
        ws = _ensure_workspace(ontology_name)
        csv_path = os.path.join(ws, filename)

        headers = list(data[0].keys())
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)

        # 尝试上传 MinIO
        try:
            download_url = _upload_to_minio(csv_path, ontology_name, filename)
            return {
                "success": True,
                "download_url": download_url,
                "filename": filename,
                "records_count": len(data),
            }
        except Exception as e:
            logger.warning(f"MinIO 上传失败，返回本地路径: {e}")
            return {
                "success": False,
                "local_path": csv_path,
                "filename": filename,
                "records_count": len(data),
                "message": f"MinIO 不可用，文件保存在 {csv_path}",
            }


def _upload_to_minio(local_path: str, ontology_name: str, filename: str) -> str:
    from app.config import settings

    endpoint = settings.MINIO_ENDPOINT
    access_key = settings.MINIO_ACCESS_KEY
    secret_key = settings.MINIO_SECRET_KEY
    bucket = settings.MINIO_BUCKET or "ontology-exports"

    if not endpoint or not access_key:
        raise RuntimeError("MinIO 未配置（MINIO_ENDPOINT / MINIO_ACCESS_KEY）")

    from minio import Minio

    client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=False)

    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)

    object_name = f"ontology/{ontology_name}/tempdata/{filename}"
    client.fput_object(bucket, object_name, local_path)

    from datetime import timedelta
    return client.presigned_get_object(bucket, object_name, expires=timedelta(hours=1))
