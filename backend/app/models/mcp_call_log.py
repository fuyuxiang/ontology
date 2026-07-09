from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text

from app.database import Base


class McpCallLog(Base):
    __tablename__ = "t_mcp_call_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tool_name = Column(String(100), nullable=False)
    duration_ms = Column(Integer, nullable=False)
    is_error = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    called_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_mcp_call_log_called_at", "called_at"),
        Index("ix_mcp_call_log_tool_name", "tool_name"),
    )
