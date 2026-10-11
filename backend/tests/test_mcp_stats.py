"""工具健康表的空态、错误计数和七天窗口回归。"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.mcp_stats import get_tool_stats
from app.models.mcp_call_log import McpCallLog


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    McpCallLog.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_empty_tool_health_is_an_empty_list(db):
    assert get_tool_stats(db) == []


def test_tool_health_counts_errors_and_excludes_old_calls(db):
    now = datetime.utcnow()
    db.add_all([
        McpCallLog(tool_name="query", duration_ms=10, is_error=False, called_at=now),
        McpCallLog(tool_name="query", duration_ms=30, is_error=True, called_at=now),
        McpCallLog(tool_name="metadata", duration_ms=5, is_error=False, called_at=now),
        McpCallLog(tool_name="query", duration_ms=99, is_error=True, called_at=now - timedelta(days=8)),
    ])
    db.commit()
    stats = {row["tool_name"]: row for row in get_tool_stats(db)}
    assert stats["query"]["call_count"] == 2
    assert stats["query"]["error_count"] == 1
    assert stats["query"]["avg_ms"] == 20
    assert stats["query"]["percentage"] == 66.7
    assert stats["metadata"]["error_count"] == 0
    assert stats["metadata"]["percentage"] == 33.3
