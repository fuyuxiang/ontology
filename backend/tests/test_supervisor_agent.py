"""监督式 agent 与 object/tool 层测试。"""

import pytest

from app.agent import SupervisorAgentService
from app.config.settings import get_settings
from app.services.semantic_service import SemanticService


class FakePlanner:
    """按预置响应顺序返回 assistant message，模拟 LLM tool calling。"""

    def __init__(self, responses: list[dict]) -> None:
        self.responses = list(responses)

    def complete(self, messages: list[dict], *, tools: list[dict] | None = None) -> dict:
        assert messages
        assert tools
        if not self.responses:
            raise AssertionError("missing_fake_planner_response")
        return self.responses.pop(0)


def test_summary_exposes_object_model_and_tool_catalog():
    """概览接口应暴露对象模型与工具目录。"""
    service = SemanticService(get_settings())
    summary = service.get_summary()

    object_keys = {item["key"] for item in summary["ontologyObjects"]}
    tool_names = {item["name"] for item in summary["toolCatalog"]}

    assert "User" in object_keys
    assert "RetentionCase" in object_keys
    assert "query_objects" in tool_names
    assert summary["agentProfile"]["mode"] == "supervised"
    assert summary["agentProfile"]["planner"] == "llm-tool-router"


def test_query_objects_can_filter_high_risk_users():
    """统一对象查询应支持风险过滤。"""
    service = SemanticService(get_settings())
    result = service.query_objects("User", filters={"riskLevel": "HIGH"}, limit=5)

    assert result["total"] > 0
    assert result["rows"]
    assert all(row["riskLevel"] == "HIGH" for row in result["rows"])


def test_supervisor_agent_requires_llm_configuration(monkeypatch: pytest.MonkeyPatch):
    """未配置 LLM 环境变量时应直接报错，而不是回退到硬编码规则。"""
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    service = SemanticService(get_settings())
    agent = SupervisorAgentService(service)

    with pytest.raises(ValueError, match="llm_not_configured"):
        agent.ask("哪些规则被命中最多？")


def test_supervisor_agent_answers_rule_question_with_tools():
    """监督 agent 应通过 LLM 规划工具调用来回答规则命中问题。"""
    service = SemanticService(get_settings())
    planner = FakePlanner(
        [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "query_objects",
                            "arguments": '{"object_type":"RuleHit","limit":5}',
                        },
                    }
                ],
            },
            {
                "role": "assistant",
                "content": (
                    '{"answer":"规则命中排行已经整理完成。","primaryObjectType":"RuleHit",'
                    '"requiresConfirmation":false,"pendingAction":null,'
                    '"suggestions":["看看高风险用户","查看最近交互事件","查看开放 Case"]}'
                ),
            },
        ]
    )
    agent = SupervisorAgentService(service, planner=planner)

    result = agent.ask("帮我看看命中最多的规则")

    assert result["primaryObjectType"] == "RuleHit"
    assert result["toolRuns"]
    assert result["toolRuns"][0]["tool"] == "query_objects"
    assert "规则" in result["answer"]
