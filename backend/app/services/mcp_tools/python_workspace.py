"""Python 工作空间工具 — write/read/update/delete/list + run_python_file"""
from __future__ import annotations

import logging
import os
import re
import subprocess
import time
from typing import Any

from app.services.mcp_tools.mcp_config import (
    PYTHON_RUNTIME_MAX_TIMEOUT_SEC,
    PYTHON_RUNTIME_TIMEOUT_SEC,
    PYTHON_WORKSPACE_BASE,
)
from app.services.mcp_tools.registry import MCPTool, register

logger = logging.getLogger(__name__)


def _workspace_dir(ontology_name: str) -> str:
    return os.path.join(PYTHON_WORKSPACE_BASE, ontology_name)


def _ensure_workspace(ontology_name: str) -> str:
    ws = _workspace_dir(ontology_name)
    os.makedirs(ws, exist_ok=True)
    return ws


def _resolve_path(ontology_name: str, file_path: str) -> str:
    if os.path.isabs(file_path):
        return file_path
    return os.path.join(_ensure_workspace(ontology_name), file_path)


def _validate_filename(filename: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9_\-\.]+$', filename))


def _ensure_runtime_module(ontology_name: str):
    ws = _ensure_workspace(ontology_name)
    runtime_path = os.path.join(ws, "__ontology_runtime__.py")
    if not os.path.exists(runtime_path):
        content = RUNTIME_MODULE_TEMPLATE.format(ontology_name=ontology_name)
        with open(runtime_path, "w", encoding="utf-8") as f:
            f.write(content)


# ── write_python_file ──────────────────────────────────────

@register
class WritePythonFileTool(MCPTool):
    name = "write_python_file"
    description = "将 Python 代码写入到本体工作空间中的文件（仅创建新文件）。"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology_name": {"type": "string"},
                "python_code": {"type": "string", "description": "Python 代码"},
                "filename": {"type": "string", "description": "可选文件名"},
            },
            "required": ["ontology_name", "python_code"],
            "additionalProperties": False,
        }

    async def execute(self, arguments: dict, **ctx: Any) -> Any:
        ontology_name = arguments["ontology_name"]
        python_code = arguments["python_code"]
        filename = arguments.get("filename") or f"script_{int(time.time())}.py"

        if not _validate_filename(filename):
            return {"success": False, "message": f"非法文件名: {filename}"}

        ws = _ensure_workspace(ontology_name)
        file_path = os.path.join(ws, filename)

        if os.path.exists(file_path):
            return {"success": False, "file_path": file_path, "message": "文件已存在，请使用 update_python_file"}

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(python_code)

        _ensure_runtime_module(ontology_name)
        return {"success": True, "file_path": file_path, "filename": filename}


# ── read_python_file ───────────────────────────────────────

@register
class ReadPythonFileTool(MCPTool):
    name = "read_python_file"
    description = "读取本体工作空间中的 Python 文件内容。"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology_name": {"type": "string"},
                "file_path": {"type": "string", "description": "文件路径或文件名"},
            },
            "required": ["ontology_name", "file_path"],
            "additionalProperties": False,
        }

    async def execute(self, arguments: dict, **ctx: Any) -> Any:
        file_path = _resolve_path(arguments["ontology_name"], arguments["file_path"])
        if not os.path.exists(file_path):
            return {"success": False, "message": f"文件不存在: {file_path}"}

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"success": True, "content": content, "file_path": file_path}


# ── update_python_file ─────────────────────────────────────

@register
class UpdatePythonFileTool(MCPTool):
    name = "update_python_file"
    description = "更新本体工作空间中已存在的 Python 文件（覆盖写入）。"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology_name": {"type": "string"},
                "file_path": {"type": "string"},
                "python_code": {"type": "string"},
            },
            "required": ["ontology_name", "file_path", "python_code"],
            "additionalProperties": False,
        }

    async def execute(self, arguments: dict, **ctx: Any) -> Any:
        file_path = _resolve_path(arguments["ontology_name"], arguments["file_path"])
        if not os.path.exists(file_path):
            return {"success": False, "message": f"文件不存在: {file_path}，请使用 write_python_file 创建"}

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(arguments["python_code"])
        return {"success": True, "file_path": file_path, "filename": os.path.basename(file_path)}


# ── delete_python_file ─────────────────────────────────────

@register
class DeletePythonFileTool(MCPTool):
    name = "delete_python_file"
    description = "删除本体工作空间中的 Python 文件。"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology_name": {"type": "string"},
                "file_path": {"type": "string"},
            },
            "required": ["ontology_name", "file_path"],
            "additionalProperties": False,
        }

    async def execute(self, arguments: dict, **ctx: Any) -> Any:
        file_path = _resolve_path(arguments["ontology_name"], arguments["file_path"])
        if not os.path.exists(file_path):
            return {"success": False, "message": f"文件不存在: {file_path}"}

        os.remove(file_path)
        return {"success": True, "message": f"已删除 {os.path.basename(file_path)}"}


# ── list_python_files ──────────────────────────────────────

@register
class ListPythonFilesTool(MCPTool):
    name = "list_python_files"
    description = "列出本体工作空间中的所有 Python 文件。"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology_name": {"type": "string"},
            },
            "required": ["ontology_name"],
            "additionalProperties": False,
        }

    async def execute(self, arguments: dict, **ctx: Any) -> Any:
        ws = _workspace_dir(arguments["ontology_name"])
        if not os.path.isdir(ws):
            return {"files": []}

        files = []
        for f in sorted(os.listdir(ws)):
            if f.endswith(".py") and not f.startswith("__"):
                fp = os.path.join(ws, f)
                files.append({
                    "filename": f,
                    "file_path": fp,
                    "size_bytes": os.path.getsize(fp),
                })
        return {"files": files, "total": len(files)}


# ── run_python_file ────────────────────────────────────────

@register
class RunPythonFileTool(MCPTool):
    name = "run_python_file"
    description = "运行本体工作空间中的 Python 文件。代码在独立子进程中运行，辅助函数已自动注入。"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology_name": {"type": "string"},
                "file_path": {"type": "string"},
                "user_id": {"type": "string"},
                "timeout_sec": {"type": "integer"},
            },
            "required": ["ontology_name", "file_path", "user_id"],
            "additionalProperties": False,
        }

    async def execute(self, arguments: dict, **ctx: Any) -> Any:
        ontology_name = arguments["ontology_name"]
        file_path = _resolve_path(ontology_name, arguments["file_path"])
        if not os.path.exists(file_path):
            return {"error": f"文件不存在: {file_path}"}

        timeout = min(
            arguments.get("timeout_sec") or PYTHON_RUNTIME_TIMEOUT_SEC,
            PYTHON_RUNTIME_MAX_TIMEOUT_SEC,
        )
        ws = _ensure_workspace(ontology_name)
        _ensure_runtime_module(ontology_name)

        try:
            proc = subprocess.run(
                ["python3", file_path],
                capture_output=True, text=True,
                timeout=timeout,
                cwd=ws,
                env={
                    **os.environ,
                    "PYTHONPATH": ws,
                    "ONTOLOGY_RUNTIME_USER_ID": arguments["user_id"],
                },
            )
            return {
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "exit_code": proc.returncode,
                "file_path": file_path,
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"执行超时（{timeout}s）",
                "exit_code": -1,
                "file_path": file_path,
            }


# ── 运行时模块模板 ─────────────────────────────────────────

RUNTIME_MODULE_TEMPLATE = '''# -*- coding: utf-8 -*-
"""本体运行时辅助模块 — 自动注入"""
import json

ONTOLOGY_NAME = "{ontology_name}"


def get_object(class_name: str):
    """获取本体对象（桩实现，实际查询调用 MCP 工具）"""
    return class_name


def call_find(obj, **kwargs):
    """执行对象查询（桩实现）"""
    raise NotImplementedError("请在 MCP 工具中调用 ontology_query_instances")


def call_check_attr_mapping(object_names):
    """获取属性映射（桩实现）"""
    raise NotImplementedError("请在 MCP 工具中调用 ontology_get_attr_mapping")


def call_complex_sql(sql, **kwargs):
    """执行复杂 SQL（桩实现）"""
    raise NotImplementedError("请在 MCP 工具中调用 ontology_complex_sql_execute")


def execute_logic(logic_name, params=None):
    """执行逻辑（桩实现）"""
    raise NotImplementedError("请在 MCP 工具中调用 ontology_run_logic")


def execute_action(obj_name, action_name, params=None):
    """执行动作（桩实现）"""
    raise NotImplementedError("请在 MCP 工具中调用 ontology_run_action")


def export_to_minio(data, filename=None):
    """导出到 MinIO（桩实现）"""
    raise NotImplementedError("请在 MCP 工具中调用 export_to_minio")
'''
