"""MCP 认证 — 复用项目已有的 JWT 体系 + X-API-Key 备用"""
from __future__ import annotations

import os

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.security import decode_token


def verify_mcp_auth(request: Request) -> JSONResponse | None:
    """验证 MCP 请求认证。返回 None = 通过，返回 JSONResponse = 拒绝"""

    # 1. JWT Bearer Token（复用项目 core.security.decode_token）
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        user_id = decode_token(token)
        if user_id:
            request.state.mcp_user_id = user_id
            return None
        return JSONResponse(
            status_code=401,
            content={"jsonrpc": "2.0", "error": {"code": -32001, "message": "JWT 令牌无效或过期"}},
        )

    # 2. X-API-Key
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        valid_keys_str = os.getenv("MCP_API_KEYS", "")
        valid_keys = {k.strip() for k in valid_keys_str.split(",") if k.strip()}
        if api_key in valid_keys:
            request.state.mcp_user_id = None
            return None
        return JSONResponse(
            status_code=401,
            content={"jsonrpc": "2.0", "error": {"code": -32001, "message": "API Key 无效"}},
        )

    # 3. 无认证 — 开发模式放行
    if os.getenv("MCP_REQUIRE_AUTH", "false").lower() == "true":
        return JSONResponse(
            status_code=401,
            content={"jsonrpc": "2.0", "error": {"code": -32001, "message": "缺少认证凭据"}},
        )

    request.state.mcp_user_id = None
    return None
