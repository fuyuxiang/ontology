import unittest

from app.database import SessionLocal
from app.models.agent_test_conversation import AgentTestConversation


class AgentTestConversationModelTests(unittest.TestCase):
    def test_create_and_defaults(self):
        db = SessionLocal()
        try:
            conv = AgentTestConversation(agent_id="a1", user_id="u1")
            db.add(conv)
            db.commit()
            db.refresh(conv)
            self.assertTrue(conv.id)
            self.assertEqual(conv.title, "新会话")
            self.assertEqual(conv.messages, [])
            self.assertIsNotNone(conv.created_at)
        finally:
            db.query(AgentTestConversation).filter_by(agent_id="a1").delete()
            db.commit()
            db.close()


if __name__ == "__main__":
    unittest.main()
