import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.agent import orchestrator as orch_mod


def _fake_stream_no_tool(text):
    chunk = SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=text, tool_calls=None), finish_reason="stop")]
    )
    return [chunk]


class OrchestratorHistoryTests(unittest.TestCase):
    def _build_service(self, captured):
        fake_client = MagicMock()

        def create(**kwargs):
            captured["messages"] = kwargs["messages"]
            return _fake_stream_no_tool('{"answer": "hi", "suggestions": []}')

        fake_client.chat.completions.create.side_effect = create
        with patch.object(orch_mod, "get_llm_client", return_value=fake_client), \
             patch.object(orch_mod, "build_system_prompt", return_value="SYS"):
            from app.database import SessionLocal
            db = SessionLocal()
            self.addCleanup(db.close)
            return orch_mod.AgentService(db)

    def test_history_injected_between_system_and_user(self):
        captured = {}
        svc = self._build_service(captured)
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
        ]
        list(svc.ask("Q2", history=history))
        roles = [m["role"] for m in captured["messages"]]
        self.assertEqual(roles, ["system", "user", "assistant", "user"])
        self.assertEqual(captured["messages"][1]["content"], "Q1")
        self.assertEqual(captured["messages"][-1]["content"], "Q2")

    def test_no_history_is_backward_compatible(self):
        captured = {}
        svc = self._build_service(captured)
        list(svc.ask("Q1"))
        roles = [m["role"] for m in captured["messages"]]
        self.assertEqual(roles, ["system", "user"])

    def test_truncated_stream_never_emits_done_or_executes_partial_tools(self):
        svc = self._build_service({})
        truncated = SimpleNamespace(choices=[SimpleNamespace(
            delta=SimpleNamespace(content='{"answer":"partial', tool_calls=None), finish_reason=None)])
        svc.client.chat.completions.create.side_effect = None
        svc.client.chat.completions.create.return_value = [truncated]
        events = list(svc.ask("Q"))
        self.assertTrue(any(e["type"] == "error" for e in events))
        self.assertFalse(any(e["type"] == "done" for e in events))
        partial_tool = SimpleNamespace(index=0, id="t", function=SimpleNamespace(name="run_action", arguments="{}"))
        truncated.choices[0].delta = SimpleNamespace(content=None, tool_calls=[partial_tool])
        events = list(svc.ask("Q"))
        self.assertFalse(any(e["type"] in ("tool_start", "done") for e in events))


if __name__ == "__main__":
    unittest.main()
