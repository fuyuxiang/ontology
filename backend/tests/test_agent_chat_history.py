import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.v1 import agents as agents_api
from app.core.security import create_access_token
from app.database import SessionLocal
from app.main import app
from app.models.agent import Agent
from app.models.agent_test_conversation import AgentTestConversation
from app.models.user import User


def _auth(uid):
    return {"Authorization": f"Bearer {create_access_token(uid)}"}


class FakeAgentService:
    last_history = None

    def __init__(self, *a, **k):
        pass

    def ask(self, question, entity_id=None, history=None):
        FakeAgentService.last_history = history
        yield {"type": "content", "content": "答复正文"}
        yield {"type": "done", "suggestions": []}


class AgentChatHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        cls.user = User(username="chat_hist_user", password_hash="x", name="chat_hist_user", role="admin")
        db.add(cls.user)
        cls.agent = Agent(name="历史测试智能体")  # 无 nodes_json → 非画布，走 orchestrator
        db.add(cls.agent)
        db.commit()
        cls.uid, cls.aid = cls.user.id, cls.agent.id
        db.close()

    @classmethod
    def tearDownClass(cls):
        db = SessionLocal()
        db.query(AgentTestConversation).filter_by(agent_id=cls.aid).delete()
        db.query(Agent).filter_by(id=cls.aid).delete()
        db.query(User).filter_by(id=cls.uid).delete()
        db.commit()
        db.close()

    def _make_conv(self, messages):
        db = SessionLocal()
        conv = AgentTestConversation(agent_id=self.aid, user_id=self.uid, messages=messages)
        db.add(conv)
        db.commit()
        cid = conv.id
        db.close()
        return cid

    def test_history_loaded_and_writeback(self):
        cid = self._make_conv([
            {"role": "user", "content": "第一问"},
            {"role": "assistant", "content": "第一答"},
        ])
        with patch.object(agents_api, "AgentService", FakeAgentService):
            client = TestClient(app)
            r = client.post(
                f"/api/v1/agents/{self.aid}/chat",
                json={"question": "第二问", "conversation_id": cid},
                headers=_auth(self.uid),
            )
        self.assertEqual(r.status_code, 200)
        # history passed to ask
        self.assertEqual(FakeAgentService.last_history,
                         [{"role": "user", "content": "第一问"},
                          {"role": "assistant", "content": "第一答"}])
        # writeback: 4 messages now
        db = SessionLocal()
        conv = db.get(AgentTestConversation, cid)
        contents = [(m["role"], m["content"]) for m in conv.messages]
        db.close()
        self.assertEqual(contents, [
            ("user", "第一问"), ("assistant", "第一答"),
            ("user", "第二问"), ("assistant", "答复正文"),
        ])

    def test_truncates_to_last_10_turns(self):
        msgs = []
        for i in range(12):
            msgs.append({"role": "user", "content": f"u{i}"})
            msgs.append({"role": "assistant", "content": f"a{i}"})
        cid = self._make_conv(msgs)  # 24 条 = 12 轮
        with patch.object(agents_api, "AgentService", FakeAgentService):
            client = TestClient(app)
            client.post(
                f"/api/v1/agents/{self.aid}/chat",
                json={"question": "new", "conversation_id": cid},
                headers=_auth(self.uid),
            )
        # 只保留最近 10 轮 = 20 条
        self.assertEqual(len(FakeAgentService.last_history), 20)
        self.assertEqual(FakeAgentService.last_history[0]["content"], "u2")

    def test_no_conversation_id_still_works(self):
        with patch.object(agents_api, "AgentService", FakeAgentService):
            client = TestClient(app)
            r = client.post(
                f"/api/v1/agents/{self.aid}/chat",
                json={"question": "无会话"},
                headers=_auth(self.uid),
            )
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(FakeAgentService.last_history)

    def test_title_generated_on_first_writeback(self):
        cid = self._make_conv([])
        with patch.object(agents_api, "AgentService", FakeAgentService):
            client = TestClient(app)
            client.post(
                f"/api/v1/agents/{self.aid}/chat",
                json={"question": "这是一个很长的第一句问题用来生成标题内容", "conversation_id": cid},
                headers=_auth(self.uid),
            )
        db = SessionLocal()
        conv = db.get(AgentTestConversation, cid)
        title = conv.title
        db.close()
        self.assertNotEqual(title, "新会话")
        self.assertTrue(title.startswith("这是一个"))


if __name__ == "__main__":
    unittest.main()
