"""
Agent 服务 — 向后兼容入口
实际实现已拆分至 app.services.agent 包
"""
from app.services.agent.orchestrator import AgentService  # noqa: F401

__all__ = ["AgentService"]
