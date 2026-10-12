"""MCP Streamable HTTP 端点 — POST /mcp

实现 JSON-RPC 2.0 协议：
- initialize  — 握手
- tools/list  — 返回工具清单
- tools/call  — 执行工具调用
"""
from __future__ import annotations

import json
import logging
import time
import traceback

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.mcp_tools.auth import verify_mcp_auth
from app.services.mcp_tools.call_logger import log_mcp_call
from app.services.mcp_tools.mcp_config import MCP_SERVER_NAME, MCP_SERVER_VERSION
from app.services.mcp_tools.registry import TOOL_REGISTRY, get_tools_list

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.post("")
async def mcp_endpoint(request: Request, db: Session = Depends(get_db)):
    from app.services.mcp_tools.activity import track_request
    with track_request():
        return await _handle_mcp_request(request, db)


async def _handle_mcp_request(request, db):
    auth_error = verify_mcp_auth(request, db)
    if auth_error:
        return auth_error

    try:
        body = await request.json()
    except ValueError:
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "JSON 解析失败"}}
    if not isinstance(body, dict) or body.get("jsonrpc") != "2.0":
        return {"jsonrpc": "2.0", "id": body.get("id") if isinstance(body, dict) else None,
                "error": {"code": -32600, "message": "无效 JSON-RPC 请求"}}
    method = body.get("method", "")
    msg_id = body.get("id")
    params = body.get("params", {})

    try:
        if method == "initialize":
            result = _handle_initialize()
        elif method == "tools/list":
            result = _handle_tools_list()
        elif method == "tools/call":
            result = await _handle_tools_call(params, db, request)
        elif method == "notifications/initialized":
            result = {}
        else:
            result = {"error": {"code": -32601, "message": f"未知方法: {method}"}}
    except Exception as e:
        logger.error(f"MCP 调用失败: {method} — {e}\n{traceback.format_exc()}")
        result = {"error": {"code": -32603, "message": str(e)}}

    return {"jsonrpc": "2.0", "id": msg_id, **({"error": result["error"]} if isinstance(result, dict) and "error" in result else {"result": result})}


def _handle_initialize() -> dict:
    return {
        "protocolVersion": "2024-11-05",
        "serverInfo": {
            "name": MCP_SERVER_NAME,
            "version": MCP_SERVER_VERSION,
        },
        "capabilities": {"tools": {}},
    }


def _handle_tools_list() -> dict:
    return {"tools": get_tools_list()}


async def _handle_tools_call(params: dict, db: Session, request: Request) -> dict:
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    tool = TOOL_REGISTRY.get(tool_name)
    if not tool:
        return {"error": {"code": -32602, "message": f"未知工具: {tool_name}"}}
    permissions = getattr(request.state, "mcp_permissions", set())
    execute_tools = {"ontology_run_logic", "ontology_run_action", "run_python_file", "ontology_service_execute"}
    write_tools = {"write_python_file", "update_python_file", "delete_python_file", "export_to_minio"}
    if tool_name in execute_tools and not {"rule:execute", "rule:write"} & permissions:
        return {"error": {"code": -32003, "message": "缺少执行权限"}}
    if tool_name in write_tools and "rule:write" not in permissions:
        return {"error": {"code": -32003, "message": "缺少写入权限"}}
    if tool_name not in execute_tools | write_tools:
        permission = "rule:read" if tool_name in {"ontology_list_capabilities", "read_python_file", "list_python_files"} else "entity:read"
        if permission not in permissions:
            return {"error": {"code": -32003, "message": f"缺少读取权限: {permission}"}}
    if not isinstance(arguments, dict):
        return {"error": {"code": -32602, "message": "工具参数必须为对象"}}
    # The caller identity is authenticated; a model supplied user_id is never
    # an authorization grant and cannot impersonate another user in audit.
    if "user_id" in tool.input_schema().get("properties", {}):
        arguments = {**arguments, "user_id": getattr(request.state, "mcp_user_id", None)}

    start = time.perf_counter()
    is_error = False
    error_msg = None
    try:
        result = await tool.execute(arguments, db=db, request=request)
        is_error = isinstance(result, dict) and (result.get("success") is False or bool(result.get("error")) or result.get("exit_code", 0) != 0)
        if is_error:
            error_msg = str(result.get("error") or result.get("message") or result.get("stderr") or "工具返回业务失败")
    except Exception as e:
        is_error = True
        error_msg = str(e)
        logger.error(f"工具 {tool_name} 执行失败: {e}\n{traceback.format_exc()}")
        result = {"error": str(e)}
    finally:
        duration_ms = int((time.perf_counter() - start) * 1000)
        try:
            log_mcp_call(db, tool_name, duration_ms, is_error, error_msg)
        except Exception:
            db.rollback()
            logger.error("MCP调用记录保存失败，工具结果需核对: %s", tool_name)
            result = {"success": False, "error": "MCP调用记录保存失败，请核对实际工具回执，禁止盲目重发",
                      "outcome": "committed_unrecorded" if not is_error and tool_name in execute_tools | write_tools else "recording_failed",
                      "observed_result": result}
            is_error = True

    return {
        "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, default=str)}],
        "isError": is_error,
    }
