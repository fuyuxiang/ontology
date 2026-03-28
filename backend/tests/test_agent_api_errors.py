"""监督式 agent API 错误映射测试。"""

import socket
from urllib import error

import pytest
from fastapi import HTTPException

from app.agent.llm_client import LLMPlannerClient
from app.api.routes import _raise_agent_http_error


@pytest.mark.parametrize(
    ("raw_error", "status_code", "detail"),
    [
        ("llm_not_configured", 503, "智能问答模型未配置"),
        ("llm_timeout", 504, "智能问答模型响应超时，请稍后重试"),
        ("llm_network_error:timed out", 502, "智能问答模型网络异常，请稍后重试"),
        ("llm_http_error:500:upstream", 502, "智能问答模型服务异常，请稍后重试"),
        ("llm_invalid_json", 502, "智能问答模型返回异常响应"),
        ("question_required", 400, "question_required"),
    ],
)
def test_raise_agent_http_error_maps_value_error_to_expected_response(
    raw_error: str,
    status_code: int,
    detail: str,
):
    """监督式 agent 的异常应映射为稳定且可读的 HTTP 错误。"""
    with pytest.raises(HTTPException) as exc_info:
        _raise_agent_http_error(ValueError(raw_error))

    assert exc_info.value.status_code == status_code
    assert exc_info.value.detail == detail


def test_llm_client_converts_timeout_to_llm_timeout(monkeypatch: pytest.MonkeyPatch):
    """底层 HTTP 超时应统一转换成 llm_timeout。"""
    client = LLMPlannerClient(
        base_url="https://example.com/v1",
        api_key="test-key",
        model="test-model",
        timeout_seconds=1,
    )

    def fake_urlopen(*args, **kwargs):
        raise socket.timeout("timed out")

    monkeypatch.setattr("app.agent.llm_client.request.urlopen", fake_urlopen)

    with pytest.raises(ValueError, match="llm_timeout"):
        client.complete([{"role": "user", "content": "hello"}])


def test_llm_client_converts_http_error_to_llm_http_error(monkeypatch: pytest.MonkeyPatch):
    """上游 HTTP 错误应保留为 llm_http_error，便于 API 层统一映射。"""
    client = LLMPlannerClient(
        base_url="https://example.com/v1",
        api_key="test-key",
        model="test-model",
        timeout_seconds=1,
    )

    class FakeHttpError(error.HTTPError):
        def __init__(self) -> None:
            super().__init__(
                url="https://example.com/v1/chat/completions",
                code=429,
                msg="Too Many Requests",
                hdrs=None,
                fp=None,
            )

        def read(self) -> bytes:
            return b'{"error":"rate_limited"}'

    def fake_urlopen(*args, **kwargs):
        raise FakeHttpError()

    monkeypatch.setattr("app.agent.llm_client.request.urlopen", fake_urlopen)

    with pytest.raises(ValueError, match=r"llm_http_error:429:"):
        client.complete([{"role": "user", "content": "hello"}])
