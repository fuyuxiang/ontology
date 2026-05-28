"""老路由兼容层 — 给 deprecated router 添加 Deprecation / Sunset 响应头。

不改老路由的业务逻辑（避免破坏老前端），只在 ASGI 层标记 deprecated，
让前端/客户端看到迁移信号。退役时机由各路由的 sunset 字段记录。

与计划对齐：
- /datasources*        → Sunset: 2026-12-31（M4 删除）
- /business-documents* → Sunset: 2026-12-31
- /pipelines*          → Sunset: 2026-09-30（M2 起返回空 + 410）
"""
from __future__ import annotations

from typing import Iterable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


# (path_prefix, sunset_date)
DEPRECATED_PREFIXES: list[tuple[str, str]] = [
    ("/api/v1/datasources", "2026-12-31"),
    ("/api/v1/business-documents", "2026-12-31"),
    ("/api/v1/pipelines", "2026-09-30"),
]


def _match(path: str) -> str | None:
    for prefix, sunset in DEPRECATED_PREFIXES:
        if path == prefix or path.startswith(prefix + "/"):
            return sunset
    return None


class DeprecationHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        sunset = _match(request.url.path)
        if sunset is not None and 200 <= response.status_code < 400:
            response.headers["Deprecation"] = "true"
            response.headers["Sunset"] = sunset
            response.headers["Link"] = (
                '</api/v1/connections>; rel="successor-version"; '
                'title="Data Plane: Connection + Asset + /execute"'
            )
        return response


def install(app: FastAPI) -> None:
    app.add_middleware(DeprecationHeaderMiddleware)
