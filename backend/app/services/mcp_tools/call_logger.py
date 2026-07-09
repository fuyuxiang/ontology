from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.mcp_call_log import McpCallLog


def log_mcp_call(
    db: Session,
    tool_name: str,
    duration_ms: int,
    is_error: bool = False,
    error_message: str | None = None,
):
    record = McpCallLog(
        tool_name=tool_name,
        duration_ms=duration_ms,
        is_error=is_error,
        error_message=error_message,
    )
    db.add(record)
    db.commit()
