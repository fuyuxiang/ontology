"""MCP 工具注册表 — 工具基类 + 全局注册表"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class MCPTool(ABC):
    name: str = ""
    description: str = ""

    @abstractmethod
    def input_schema(self) -> dict:
        ...

    @abstractmethod
    async def execute(self, arguments: dict, **ctx: Any) -> Any:
        ...

    def to_mcp_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema(),
        }


TOOL_REGISTRY: dict[str, MCPTool] = {}


def register(tool_cls):
    instance = tool_cls()
    TOOL_REGISTRY[instance.name] = instance
    logger.info(f"MCP 工具注册: {instance.name}")
    return tool_cls


def get_tools_list() -> list[dict]:
    return [tool.to_mcp_schema() for tool in TOOL_REGISTRY.values()]
