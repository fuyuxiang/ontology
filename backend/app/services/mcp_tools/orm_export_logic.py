"""ORM 引擎 + 逻辑执行 + 动作执行 + 导出"""
from __future__ import annotations

import csv
import json
import logging
import os
import time
from typing import Any

from sqlalchemy.orm import Session

from app.models.action import EntityAction
from app.models.entity import OntologyEntity
from app.models.function import OntologyFunction
from app.models.shared_ref import OntologySharedRef
from app.services.action_executors import get_executor, run_executor_sync
from app.services.function_runtime import FunctionRuntimeExecutor
from app.services.function_runtime.models import ExecContext
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
        import subprocess
        ontology_name = arguments["ontology_name"]
        code = arguments["code"]

        wrapped = f"import json\n{code}\nprint(json.dumps(result, ensure_ascii=False, default=str))"
        ws = os.path.join(PYTHON_WORKSPACE_BASE, ontology_name)
        os.makedirs(ws, exist_ok=True)
        tmp_path = os.path.join(ws, f"_orm_exec_{int(time.time())}.py")

        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(wrapped)

        try:
            proc = subprocess.run(
                ["python3", tmp_path],
                capture_output=True, text=True,
                timeout=PYTHON_RUNTIME_TIMEOUT_SEC,
                env={**os.environ, "PYTHONPATH": ws},
            )
            if proc.returncode != 0:
                return {"error": proc.stderr.strip() or "执行失败"}
            try:
                return json.loads(proc.stdout.strip() or "{}")
            except json.JSONDecodeError:
                return {"result": proc.stdout.strip()}
        except subprocess.TimeoutExpired:
            return {"error": f"执行超时（{PYTHON_RUNTIME_TIMEOUT_SEC}s）"}
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
        if not func:
            return {"error": f"逻辑函数 '{logic_name}' 不存在或无权访问"}

        callable_name = func.callable_name or func.name

        # 使用 FunctionRuntimeExecutor 执行
        registry = FunctionRegistry(db)
        registry.sync_from_db()
        sandbox = UnifiedSandbox()
        executor = FunctionRuntimeExecutor(registry, sandbox, db)

        result = executor.execute(callable_name, params)
        if result.success:
            return {
                "success": True,
                "result": result.result,
                "execution_ms": result.execution_ms,
            }
        return {
            "success": False,
            "error": result.error,
            "execution_ms": result.execution_ms,
        }


# ── ontology_run_action ────────────────────────────────────

@register
class RunActionTool(MCPTool):
    name = "ontology_run_action"
    description = "在对象上执行已绑定的 action（写库/改数据，高风险）。仅在用户明确授权时调用。"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology_name": {"type": "string"},
                "object_name": {"type": "string"},
                "action_name": {"type": "string"},
                "user_id": {"type": "string"},
                "params": {"type": "object", "description": "action 入参字典"},
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
        if not entity:
            return {"error": f"对象 '{object_name}' 不存在"}

        # 查找 action
        action = (
            db.query(EntityAction)
            .filter(
                EntityAction.name == action_name,
                (EntityAction.entity_id == entity.id) | (EntityAction.ontology_id == ontology_id),
                EntityAction.status == "active",
            )
            .first()
        )
        if not action:
            return {"error": f"动作 '{action_name}' 不存在或无权访问"}

        # 通过 action_executors 执行
        type_config = action.type_config or {}
        try:
            exec_result = run_executor_sync(action.action_type, type_config, params)
            return {
                "success": exec_result.success,
                "message": exec_result.message,
                "output": exec_result.output,
            }
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

        if not data:
            return {"error": "数据为空，无法导出"}

        # 写 CSV 到临时目录
        ws = os.path.join(PYTHON_WORKSPACE_BASE, ontology_name)
        os.makedirs(ws, exist_ok=True)
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
                "success": True,
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

    return f"http://{endpoint}/{bucket}/{object_name}"