"""MCP Streamable HTTP 端点 — POST /mcp

实现 JSON-RPC 2.0 协议：
- initialize  — 握手
- tools/list  — 返回工具清单
- tools/call  — 执行工具调用
"""
from __future__ import annotations

import json
import logging
import traceback

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.mcp_tools.auth import verify_mcp_auth
from app.services.mcp_tools.mcp_config import MCP_SERVER_NAME, MCP_SERVER_VERSION
from app.services.mcp_tools.registry import TOOL_REGISTRY, get_tools_list

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.post("")
async def mcp_endpoint(request: Request, db: Session = Depends(get_db)):
    auth_error = verify_mcp_auth(request)
    if auth_error:
        return auth_error

    body = await request.json()
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

    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


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

    try:
        result = await tool.execute(arguments, db=db, request=request)
    except Exception as e:
        logger.error(f"工具 {tool_name} 执行失败: {e}\n{traceback.format_exc()}")
        return {
            "content": [{"type": "text", "text": json.dumps({"error": str(e)}, ensure_ascii=False)}],
            "isError": True,
        }

    return {
        "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, default=str)}],
    }
