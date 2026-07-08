"""MCP 工具包 — 导入时自动注册所有 15 个工具"""
from app.services.mcp_tools.metadata import GetAttrMappingTool, ListCapabilitiesTool  # noqa: F401
from app.services.mcp_tools.data_query import QueryInstancesTool, ComplexSqlTool, ObjectFindTool  # noqa: F401
from app.services.mcp_tools.python_workspace import (  # noqa: F401
    WritePythonFileTool, ReadPythonFileTool, UpdatePythonFileTool,
    DeletePythonFileTool, ListPythonFilesTool, RunPythonFileTool,
)
from app.services.mcp_tools.orm_export_logic import (  # noqa: F401
    ServiceExecuteTool, RunLogicTool, RunActionTool, ExportToMinioTool,
)
