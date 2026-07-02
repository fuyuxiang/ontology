import unittest

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import ScenarioDict
from app.models.audit import AuditLog
from app.models.user import User


def _auth(user_id):
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


class ScenarioApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        cls.user = User(username="scenario_test_user", password_hash="x", name="scenario_test_user", role="admin")
        db.add(cls.user)
        db.commit()
        cls.uid = cls.user.id
        db.close()

    @classmethod
    def tearDownClass(cls):
        db = SessionLocal()
        db.query(ScenarioDict).filter(ScenarioDict.code == "scenario-api-test").delete()
        db.query(AuditLog).filter(AuditLog.target_type == "scenario").delete()
        db.query(User).filter_by(id=cls.uid).delete()
        db.commit()
        db.close()

    def test_create_scenario(self):
        client = TestClient(app)
        r = client.post(
            "/api/v1/scenarios",
            headers=_auth(self.uid),
            json={"code": "scenario-api-test", "name": "接口测试场景"},
        )
        self.assertEqual(r.status_code, 201, r.text)
        body = r.json()
        self.assertEqual(body["code"], "scenario-api-test")
        self.assertTrue(body["id"])
        # 审计日志的 target_id 必须指向新建场景，不能为空
        db = SessionLocal()
        entry = (
            db.query(AuditLog)
            .filter(AuditLog.target_type == "scenario", AuditLog.target_id == body["id"])
            .first()
        )
        db.close()
        self.assertIsNotNone(entry)


if __name__ == "__main__":
    unittest.main()
