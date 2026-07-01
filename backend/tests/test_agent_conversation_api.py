import unittest

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.database import SessionLocal
from app.main import app
from app.models.agent import Agent
from app.models.agent_test_conversation import AgentTestConversation
from app.models.user import User


def _auth(user_id):
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


class AgentConversationApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        cls.user_a = User(username="conv_user_a", password_hash="x", name="conv_user_a", role="admin")
        cls.user_b = User(username="conv_user_b", password_hash="x", name="conv_user_b", role="admin")
        db.add_all([cls.user_a, cls.user_b])
        cls.agent = Agent(name="会话测试智能体")
        db.add(cls.agent)
        db.commit()
        cls.uid_a, cls.uid_b, cls.aid = cls.user_a.id, cls.user_b.id, cls.agent.id
        db.close()

    @classmethod
    def tearDownClass(cls):
        db = SessionLocal()
        db.query(AgentTestConversation).filter_by(agent_id=cls.aid).delete()
        db.query(Agent).filter_by(id=cls.aid).delete()
        db.query(User).filter(User.id.in_([cls.uid_a, cls.uid_b])).delete(synchronize_session=False)
        db.commit()
        db.close()

    def test_crud_and_isolation(self):
        client = TestClient(app)
        # create
        r = client.post(f"/api/v1/agents/{self.aid}/conversations", headers=_auth(self.uid_a))
        self.assertEqual(r.status_code, 200)
        cid = r.json()["id"]
        # list sees it
        r = client.get(f"/api/v1/agents/{self.aid}/conversations", headers=_auth(self.uid_a))
        self.assertEqual(r.status_code, 200)
        self.assertIn(cid, [c["id"] for c in r.json()])
        self.assertNotIn("messages", r.json()[0])
        # get full
        r = client.get(f"/api/v1/agents/{self.aid}/conversations/{cid}", headers=_auth(self.uid_a))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["messages"], [])
        # user B cannot see A's conversation
        r = client.get(f"/api/v1/agents/{self.aid}/conversations", headers=_auth(self.uid_b))
        self.assertNotIn(cid, [c["id"] for c in r.json()])
        # user B cannot get A's conversation
        r = client.get(f"/api/v1/agents/{self.aid}/conversations/{cid}", headers=_auth(self.uid_b))
        self.assertEqual(r.status_code, 404)
        # delete
        r = client.delete(f"/api/v1/agents/{self.aid}/conversations/{cid}", headers=_auth(self.uid_a))
        self.assertEqual(r.status_code, 200)
        r = client.get(f"/api/v1/agents/{self.aid}/conversations/{cid}", headers=_auth(self.uid_a))
        self.assertEqual(r.status_code, 404)

    def test_requires_auth(self):
        client = TestClient(app)
        r = client.get(f"/api/v1/agents/{self.aid}/conversations")
        self.assertEqual(r.status_code, 401)


if __name__ == "__main__":
    unittest.main()
