"""
模块功能：
- OpenAI-compatible LLM client used by the supervisor agent。
- 该文件位于 `backend/app/agent/llm_client.py`，封装对 LLM 规划接口的访问，统一处理配置、超时和错误转换。
- 文件中定义的核心类包括：`LLMPlannerClient`。
"""

from __future__ import annotations

import json
import socket
from typing import Any
from urllib import error, parse, request

from app.config.settings import Settings


class LLMPlannerClient:
    """
    功能：
    - Minimal chat completions client for OpenAI-compatible APIs。
    - 该类定义在 `backend/app/agent/llm_client.py` 中，用于组织与 `LLMPlannerClient` 相关的数据或行为。
    """

    def __init__(
        self,
        *,
        base_url: str | None,
        api_key: str | None,
        model: str | None,
        timeout_seconds: float = 30,
    ) -> None:
        """
        功能：
        - 初始化当前对象并准备后续调用所需的依赖、状态和缓存。

        输入：
        - `base_url`: 函数执行所需的 `base_url` 参数。
        - `api_key`: 函数执行所需的 `api_key` 参数。
        - `model`: 函数执行所需的 `model` 参数。
        - `timeout_seconds`: 函数执行所需的 `timeout_seconds` 参数。

        输出：
        - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
        """
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_settings(cls, settings: Settings) -> "LLMPlannerClient":
        """
        功能：
        - 根据运行时配置构建当前对象实例。

        输入：
        - `settings`: 运行时配置对象，提供目录路径、命名空间和环境参数。

        输出：
        - 返回值: 返回 `'LLMPlannerClient'` 类型结果，供后续流程继续消费。
        """
        return cls(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )

    def is_configured(self) -> bool:
        """
        功能：
        - 检查当前客户端是否具备发起请求所需的配置。

        输入：
        - 无。

        输出：
        - 返回值: 返回布尔值，表示条件是否成立或当前操作是否允许。
        """
        return bool(self.base_url and self.api_key and self.model)

    def complete(self, messages: list[dict[str, Any]], *, tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """
        功能：
        - Call the configured chat completions endpoint and return one assistant message。

        输入：
        - `messages`: 发送给 LLM 的对话消息历史。
        - `tools`: 列表参数 `tools`，用于批量传入待处理的数据。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        if not self.is_configured():
            raise ValueError("llm_not_configured")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        endpoint = self._chat_completions_url()
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ValueError(f"llm_http_error:{exc.code}:{detail or exc.reason}") from exc
        except (TimeoutError, socket.timeout) as exc:
            raise ValueError("llm_timeout") from exc
        except error.URLError as exc:
            raise ValueError(f"llm_network_error:{exc.reason}") from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("llm_invalid_json") from exc

        choices = parsed.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("llm_missing_choice")
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise ValueError("llm_missing_message")
        return message

    def _chat_completions_url(self) -> str:
        """
        功能：
        - 处理与 `_chat_completions_url` 相关的逻辑。

        输入：
        - 无。

        输出：
        - 返回值: 返回字符串结果，供调用方继续展示、拼接或查询。
        """
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return parse.urljoin(f"{self.base_url}/", "chat/completions")
