"""
模块功能：
- 监督式 agent 服务。
- 该文件位于 `backend/app/agent/__init__.py`，对外导出当前包的公共能力，便于上层模块以稳定接口进行导入。
"""

from app.agent.service import SupervisorAgentService

__all__ = ["SupervisorAgentService"]
