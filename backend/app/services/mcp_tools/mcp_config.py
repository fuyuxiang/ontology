"""MCP 全局配置常量"""
from pathlib import Path
from app.config import settings

PYTHON_WORKSPACE_BASE = str(Path(settings.WORKSPACE_ROOT) / "mcp") if settings.WORKSPACE_ROOT else "/tmp/ontology_python_workspace"
PYTHON_WORKSPACE_TTL_SEC = 3600
PYTHON_RUNTIME_TIMEOUT_SEC = 60
PYTHON_RUNTIME_MAX_TIMEOUT_SEC = 300

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 5000
MAX_RETURN_ROWS = 5000

MCP_SERVER_NAME = "元枢 Ontology MCP Server"
MCP_SERVER_VERSION = "1.0.0"
