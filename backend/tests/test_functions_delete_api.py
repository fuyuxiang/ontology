import unittest

from fastapi.testclient import TestClient

from app.api.v1.functions import WORKSPACE_DIR
from app.core.security import create_access_token
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models.audit import AuditLog
from app.models.function import OntologyFunction
from app.models.user import User


def _auth(user_id):
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


class FunctionDeleteApiTests(unittest.TestCase):
    """验证 UI 删除函数会连带清理工作区文件与运行时缓存，避免删除后被扫描重建。"""

    CALLABLE = "fn_delete_api_test"

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        cls.user = User(
            username="fn_delete_test_user", password_hash="x",
            name="fn_delete_test_user", role="admin",
        )
        db.add(cls.user)
        db.commit()
        cls.uid = cls.user.id
        db.close()

    @classmethod
    def tearDownClass(cls):
        db = SessionLocal()
        db.query(OntologyFunction).filter(OntologyFunction.callable_name == cls.CALLABLE).delete()
        db.query(AuditLog).filter(AuditLog.target_type == "function").delete()
        db.query(User).filter_by(id=cls.uid).delete()
        db.commit()
        db.close()
        # 兜底清理测试残留文件
        import shutil
        func_dir = WORKSPACE_DIR / cls.CALLABLE
        if func_dir.exists():
            shutil.rmtree(func_dir, ignore_errors=True)

    def test_delete_removes_row_file_dir_and_cache(self):
        # 准备：工作区目录 + 源文件（模拟 open_workspace 生成 + watcher 登记）
        func_dir = WORKSPACE_DIR / self.CALLABLE
        func_dir.mkdir(parents=True, exist_ok=True)
        main_file = func_dir / "main.py"
        main_file.write_text("# stub\n", encoding="utf-8")

        db = SessionLocal()
        func = OntologyFunction(
            name="删除接口测试函数",
            callable_name=self.CALLABLE,
            logic_type="python",
            source_path=str(main_file),
            status="active",
        )
        db.add(func)
        db.commit()
        func_id = func.id
        db.close()

        # 往运行时 registry 塞一个同名缓存项，验证删除后被清掉
        registry = getattr(app.state, "function_registry", None)
        if registry is not None:
            registry._cache[self.CALLABLE] = object()

        client = TestClient(app)
        r = client.delete(f"/api/v1/functions/{func_id}", headers=_auth(self.uid))
        self.assertEqual(r.status_code, 204, r.text)

        # DB 行已删除
        db = SessionLocal()
        self.assertIsNone(db.get(OntologyFunction, func_id))
        db.close()

        # 工作区文件与目录已删除，scan_all 不会再扫到它
        self.assertFalse(main_file.exists(), "源文件应被删除")
        self.assertFalse(func_dir.exists(), "函数工作区目录应被删除")

        # 运行时缓存已清
        if registry is not None:
            self.assertIsNone(registry.get(self.CALLABLE))

    def test_delete_missing_returns_404(self):
        client = TestClient(app)
        r = client.delete("/api/v1/functions/nonexistent-id", headers=_auth(self.uid))
        self.assertEqual(r.status_code, 404, r.text)


if __name__ == "__main__":
    unittest.main()
