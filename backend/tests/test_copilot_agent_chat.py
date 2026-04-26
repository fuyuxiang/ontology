import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.v1 import copilot as copilot_api
from app.main import app
from app.services import copilot as copilot_service


class CopilotAgentChatTests(unittest.TestCase):
    def test_agent_chat_init_failure_returns_sse_error(self):
        class BrokenAgentService:
            def __init__(self, db):
                raise RuntimeError("boom")

        with patch.object(copilot_api, "AgentService", BrokenAgentService):
            with TestClient(app) as client:
                response = client.post("/api/v1/copilot/agent-chat", json={"question": "test"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("服务异常: boom", response.text)
        self.assertIn("data: [DONE]", response.text)

    def test_get_llm_client_retries_without_proxy_env(self):
        calls: list[dict] = []
        created_http_clients: list[SimpleNamespace] = []

        def fake_httpx_client(*, trust_env):
            client = SimpleNamespace(trust_env=trust_env)
            created_http_clients.append(client)
            return client

        def fake_openai(**kwargs):
            calls.append(kwargs)
            if "http_client" not in kwargs:
                raise ImportError("Using SOCKS proxy, but the 'socksio' package is not installed.")
            return SimpleNamespace(kwargs=kwargs)

        with patch.object(copilot_service.httpx, "Client", side_effect=fake_httpx_client):
            with patch.object(copilot_service, "OpenAI", side_effect=fake_openai):
                client = copilot_service.get_llm_client()

        self.assertEqual(len(calls), 2)
        self.assertNotIn("http_client", calls[0])
        self.assertEqual(len(created_http_clients), 1)
        self.assertIs(created_http_clients[0].trust_env, False)
        self.assertIs(client.kwargs["http_client"], created_http_clients[0])


if __name__ == "__main__":
    unittest.main()
