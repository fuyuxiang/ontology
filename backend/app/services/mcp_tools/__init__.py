"""MCP 工具包 — 导入时自动注册所有 15 个工具"""
from app.services.mcp_tools.data_query import (  # noqa: F401
    ComplexSqlTool,
    ObjectFindTool,
    QueryInstancesTool,
)
from app.services.mcp_tools.metadata import GetAttrMappingTool, ListCapabilitiesTool  # noqa: F401
from app.services.mcp_tools.orm_export_logic import (  # noqa: F401
    ExportToMinioTool,
    RunActionTool,
    RunLogicTool,
    ServiceExecuteTool,
)
from app.services.mcp_tools.python_workspace import (  # noqa: F401
    DeletePythonFileTool,
    ListPythonFilesTool,
    ReadPythonFileTool,
    RunPythonFileTool,
    UpdatePythonFileTool,
    WritePythonFileTool,
)
