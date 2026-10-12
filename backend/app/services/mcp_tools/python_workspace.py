"""Python 工作空间工具 — write/read/update/delete/list + run_python_file"""
from __future__ import annotations

import logging
import ast
import os
import re
import subprocess
import time
import asyncio
import sys
from pathlib import Path
from typing import Any

from app.services.mcp_tools.mcp_config import (
    PYTHON_RUNTIME_MAX_TIMEOUT_SEC,
    PYTHON_RUNTIME_TIMEOUT_SEC,
    PYTHON_WORKSPACE_BASE,
)
from app.services.mcp_tools.registry import MCPTool, register

logger = logging.getLogger(__name__)


def _restricted_program(source):
    """Keep the legacy workspace bridge while using only curated imports."""
    class WorkspaceNames(ast.NodeTransformer):
        def visit_ImportFrom(self, node):
            if node.module == "__ontology_runtime__":
                node.module = "ontology_runtime"
            return node
        def visit_Import(self, node):
            for alias in node.names:
                if alias.name == "__ontology_runtime__":
                    alias.name = "ontology_runtime"
            return node
        def visit_Name(self, node):
            if node.id == "__ontology_runtime__":
                node.id = "ontology_runtime"
            if node.id == "__name__" and isinstance(node.ctx, ast.Load):
                return ast.copy_location(ast.Constant("__main__"), node)
            return node
    tree = WorkspaceNames().visit(ast.parse(source))
    return ast.unparse(ast.fix_missing_locations(tree))


def _sandbox_bootstrap(ontology_name):
    # Only this trusted bootstrap uses host APIs. User code is validated and
    # executed by the same restricted environment as published functions.
    bridge = RUNTIME_MODULE_TEMPLATE.replace('__ONTOLOGY_NAME__', repr(ontology_name))
    return f'''import importlib.util
import sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("ontology_workspace_sandbox", sys.argv[1])
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
bridge = {{}}
exec({bridge!r}, bridge)
helpers = {{name: bridge[name] for name in module.RUNTIME_EXPORTS if name in bridge}}
source = sys.stdin.read()
source += "\\ndef workspace_complete(params): return None\\n"
module.UnifiedSandbox().execute(source, "workspace_complete", {{"params": {{}}}},
    timeout=int(sys.argv[2]), runtime_helpers=helpers)
'''


def _workspace_dir(ontology_name: str) -> str:
    if not isinstance(ontology_name, str) or not re.fullmatch(r"[\w-]+", ontology_name) or ontology_name in {".", ".."}:
        raise ValueError("非法本体工作区名称")
    root = Path(PYTHON_WORKSPACE_BASE).resolve()
    target = (root / ontology_name).resolve()
    target.relative_to(root)
    return str(target)


def _ensure_workspace(ontology_name: str) -> str:
    ws = _workspace_dir(ontology_name)
    os.makedirs(ws, exist_ok=True)
    return ws


def _resolve_path(ontology_name: str, file_path: str) -> str:
    root = Path(_ensure_workspace(ontology_name)).resolve()
    target = (Path(file_path) if os.path.isabs(file_path) else root / file_path).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("文件必须位于指定本体工作区内") from exc
    if target.suffix != ".py" or target == root or target.name.startswith("__"):
        raise ValueError("仅支持工作区内 Python 文件")
    return str(target)


def _validate_filename(filename: str) -> bool:
    return bool(re.fullmatch(r'[a-zA-Z0-9_\-]+\.py', filename)) and not filename.startswith('__')


def _ensure_runtime_module(ontology_name: str):
    ws = _ensure_workspace(ontology_name)
    runtime_path = os.path.join(ws, "__ontology_runtime__.py")
    content = RUNTIME_MODULE_TEMPLATE.replace('__ONTOLOGY_NAME__', repr(ontology_name))
    if not os.path.exists(runtime_path) or Path(runtime_path).read_text(encoding="utf-8") != content:
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
        from app.services.mcp_tools.resolve import resolve_ontology_id
        import json
        ontology_id = resolve_ontology_id(ctx["db"], ontology_name)
        if not ontology_id:
            return {"success": False, "message": "指定本体不存在"}
        (Path(ws) / ".ontology.json").write_text(json.dumps({"ontology_id": ontology_id}), encoding="utf-8")
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

        with open(file_path, encoding="utf-8") as f:
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
        from app.services.function_runtime.sandbox import UnifiedSandbox
        source = Path(file_path).read_text(encoding="utf-8")
        try:
            source = _restricted_program(source)
        except SyntaxError as exc:
            return {"error": f"工作区代码语法错误: {exc}"}
        validation = UnifiedSandbox().validate(source)
        if not validation.valid:
            return {"error": "工作区代码安全检查失败: " + "; ".join(validation.errors)}

        requested_timeout = arguments.get("timeout_sec", PYTHON_RUNTIME_TIMEOUT_SEC)
        if isinstance(requested_timeout, bool) or not isinstance(requested_timeout, int) or requested_timeout <= 0:
            return {"error": "timeout_sec 必须为正整数"}
        timeout = min(requested_timeout, PYTHON_RUNTIME_MAX_TIMEOUT_SEC)
        ws = _ensure_workspace(ontology_name)
        _ensure_runtime_module(ontology_name)

        try:
            request = ctx.get("request")
            proc = await asyncio.to_thread(subprocess.run,
                [sys.executable, "-I", "-c", _sandbox_bootstrap(ontology_name),
                 str(Path(__file__).resolve().parents[1] / "function_runtime" / "sandbox.py"), str(timeout)],
                input=source, capture_output=True, text=True,
                timeout=timeout,
                cwd=ws,
                env={
                    "PATH": os.environ.get("PATH", ""),
                    "PYTHONPATH": ws,
                    "ONTOLOGY_RUNTIME_USER_ID": arguments["user_id"],
                    "ONTOLOGY_RUNTIME_URL": str(request.base_url).rstrip('/') + '/api/v1/mcp' if request else '',
                    "ONTOLOGY_RUNTIME_AUTH": request.headers.get('Authorization', '') if request else '',
                },
            )
            return {
                "success": proc.returncode == 0,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "exit_code": proc.returncode,
                "file_path": file_path,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"执行超时（{timeout}s）",
                "exit_code": -1,
                "file_path": file_path,
            }


# ── 运行时模块模板 ─────────────────────────────────────────

RUNTIME_MODULE_TEMPLATE = '''# -*- coding: utf-8 -*-
"""Authenticated MCP protocol bridge for workspace scripts."""
import json
import os
import urllib.request

ONTOLOGY_NAME = __ONTOLOGY_NAME__

def _call(name, arguments):
    arguments = dict(arguments, ontology_name=ONTOLOGY_NAME, user_id=os.environ.get("ONTOLOGY_RUNTIME_USER_ID"))
    url = os.environ.get("ONTOLOGY_RUNTIME_URL")
    if not url:
        raise RuntimeError("Run this file through the authenticated run_python_file tool")
    data = json.dumps({"jsonrpc":"2.0", "id":1, "method":"tools/call", "params":{"name":name,"arguments":arguments}}).encode()
    request = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json", "Authorization":os.environ.get("ONTOLOGY_RUNTIME_AUTH", "")})
    with urllib.request.urlopen(request, timeout=30) as response:
        envelope = json.load(response)
    if envelope.get("error"):
        raise RuntimeError(envelope["error"])
    result = envelope["result"]
    payload = json.loads(result["content"][0]["text"])
    if result.get("isError"):
        raise RuntimeError(payload)
    return payload

def get_object(class_name):
    return class_name

def call_find(obj, **kwargs):
    return _call("ontology_object_find", dict(kwargs, object_name=obj))

def call_check_attr_mapping(object_names):
    return _call("ontology_get_attr_mapping", {"object_names":object_names})

def call_complex_sql(sql, **kwargs):
    return _call("ontology_complex_sql_execute", dict(kwargs, sql=sql))

def execute_logic(logic_name, params=None):
    return _call("ontology_run_logic", {"logic_name":logic_name, "params":params or {}})

def execute_action(obj_name, action_name, params=None):
    return _call("ontology_run_action", {"object_name":obj_name, "action_name":action_name, "params":params or {}})

def export_to_minio(data, filename=None):
    return _call("export_to_minio", {"data":data, "filename":filename})
'''
