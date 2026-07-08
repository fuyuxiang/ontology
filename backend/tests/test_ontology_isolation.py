"""本体数据隔离集成测试。

使用 SQLite 内存数据库覆盖 get_db 依赖，验证：
1. 实体按 ontology_id 隔离查询
2. 同名实体在不同本体中互不冲突
3. 共享实体在目标本体中可见并标记为 is_shared
4. 共享实体在目标本体中为只读（修改/删除返回 403）
5. 取消共享后实体不再可见
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import require_user
from app.core.security import create_access_token
from app.database import Base, get_db
from app.main import app
from app.models.entity import OntologyEntity
from app.models.scenario import ScenarioDict
from app.models.shared_ref import OntologySharedRef
from app.models.user import User

# ── SQLite in-memory test engine ──
TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=TEST_ENGINE, autoflush=False, autocommit=False)


def _override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Test user stub for auth ──
_TEST_USER = User(id=str(uuid.uuid4()), username="test_iso", password_hash="x", name="隔离测试用户", role="admin")


def _override_require_user():
    return _TEST_USER


app.dependency_overrides[get_db] = _override_get_db
app.dependency_overrides[require_user] = _override_require_user


def _auth_headers() -> dict:
    token = create_access_token(_TEST_USER.id)
    return {"Authorization": f"Bearer {token}"}


# ── Fixtures ──


@pytest.fixture(autouse=True)
def setup_db():
    """每个测试前创建全部表，测试后清除。"""
    Base.metadata.create_all(bind=TEST_ENGINE)
    # Insert test user
    db = TestSessionLocal()
    db.merge(_TEST_USER)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


# ── Helpers ──


def _create_ontology(db, code: str, name: str) -> str:
    """创建一个本体(ScenarioDict)并返回 id。"""
    ont_id = str(uuid.uuid4())
    ont = ScenarioDict(id=ont_id, code=code, name=name)
    db.add(ont)
    db.commit()
    return ont_id


def _create_entity(db, name: str, ontology_id: str) -> str:
    """创建一个实体并返回 id。"""
    entity_id = str(uuid.uuid4())
    entity = OntologyEntity(
        id=entity_id,
        name=name,
        name_cn=name,
        tier=1,
        ontology_id=ontology_id,
    )
    db.add(entity)
    db.commit()
    return entity_id


# ── Test Classes ──


class TestEntityIsolation:
    """验证实体按 ontology_id 隔离查询。"""

    def test_entities_filtered_by_ontology(self, client, db):
        """查询某本体实体时，其他本体的实体不可见。"""
        ont_a = _create_ontology(db, "iso_a", "本体A")
        ont_b = _create_ontology(db, "iso_b", "本体B")
        _create_entity(db, "entity_a", ont_a)
        _create_entity(db, "entity_b", ont_b)

        resp = client.get("/api/v1/entities", params={"ontology_id": ont_a})
        assert resp.status_code == 200
        names = [e["name"] for e in resp.json()]
        assert "entity_a" in names
        assert "entity_b" not in names

    def test_same_name_different_ontology(self, client, db):
        """不同本体可以有同名实体，互不冲突。"""
        ont_a = _create_ontology(db, "dup_a", "本体A")
        ont_b = _create_ontology(db, "dup_b", "本体B")
        _create_entity(db, "User", ont_a)
        _create_entity(db, "User", ont_b)

        resp_a = client.get("/api/v1/entities", params={"ontology_id": ont_a})
        resp_b = client.get("/api/v1/entities", params={"ontology_id": ont_b})
        assert resp_a.status_code == 200
        assert resp_b.status_code == 200
        assert len(resp_a.json()) == 1
        assert len(resp_b.json()) == 1


class TestSharing:
    """验证实体共享机制。"""

    def test_share_entity_visible_in_target(self, client, db):
        """共享后实体在目标本体中可见且标记 is_shared=True。"""
        ont_a = _create_ontology(db, "share_src", "源本体")
        ont_b = _create_ontology(db, "share_tgt", "目标本体")
        entity_id = _create_entity(db, "SharedEntity", ont_a)

        # 执行共享
        resp = client.post(f"/api/v1/ontology/{ont_a}/share", json={
            "target_ontology_id": ont_b,
            "entity_id": entity_id,
        })
        assert resp.status_code == 200

        # 在目标本体中查询
        resp = client.get("/api/v1/entities", params={"ontology_id": ont_b})
        assert resp.status_code == 200
        names = [e["name"] for e in resp.json()]
        assert "SharedEntity" in names

        # 验证 is_shared 标记
        shared_item = [e for e in resp.json() if e["name"] == "SharedEntity"][0]
        assert shared_item["is_shared"] is True

    def test_shared_entity_not_marked_in_source(self, client, db):
        """在源本体中实体不标记为 is_shared。"""
        ont_a = _create_ontology(db, "src_mark", "源本体")
        ont_b = _create_ontology(db, "tgt_mark", "目标本体")
        entity_id = _create_entity(db, "MarkTest", ont_a)

        client.post(f"/api/v1/ontology/{ont_a}/share", json={
            "target_ontology_id": ont_b,
            "entity_id": entity_id,
        })

        resp = client.get("/api/v1/entities", params={"ontology_id": ont_a})
        source_item = [e for e in resp.json() if e["name"] == "MarkTest"][0]
        assert source_item["is_shared"] is False

    def test_shared_entity_readonly_update(self, client, db):
        """从目标本体修改共享实体应返回 403。"""
        ont_a = _create_ontology(db, "ro_src", "源本体")
        ont_b = _create_ontology(db, "ro_tgt", "目标本体")
        entity_id = _create_entity(db, "ReadOnlyEntity", ont_a)

        client.post(f"/api/v1/ontology/{ont_a}/share", json={
            "target_ontology_id": ont_b,
            "entity_id": entity_id,
        })

        # 从目标本体尝试修改
        resp = client.put(
            f"/api/v1/entities/{entity_id}",
            params={"ontology_id": ont_b},
            json={"name_cn": "新名字"},
            headers=_auth_headers(),
        )
        assert resp.status_code == 403

    def test_shared_entity_readonly_delete(self, client, db):
        """从目标本体删除共享实体应返回 403。"""
        ont_a = _create_ontology(db, "del_src", "源本体")
        ont_b = _create_ontology(db, "del_tgt", "目标本体")
        entity_id = _create_entity(db, "DeleteTest", ont_a)

        client.post(f"/api/v1/ontology/{ont_a}/share", json={
            "target_ontology_id": ont_b,
            "entity_id": entity_id,
        })

        resp = client.delete(
            f"/api/v1/entities/{entity_id}",
            params={"ontology_id": ont_b},
            headers=_auth_headers(),
        )
        assert resp.status_code == 403

    def test_unshare_removes_visibility(self, client, db):
        """取消共享后实体在目标本体中不再可见。"""
        ont_a = _create_ontology(db, "unshr_src", "源本体")
        ont_b = _create_ontology(db, "unshr_tgt", "目标本体")
        entity_id = _create_entity(db, "UnshareEntity", ont_a)

        # 共享
        share_resp = client.post(f"/api/v1/ontology/{ont_a}/share", json={
            "target_ontology_id": ont_b,
            "entity_id": entity_id,
        })
        assert share_resp.status_code == 200
        ref_id = share_resp.json()["id"]

        # 取消共享
        del_resp = client.delete(f"/api/v1/ontology/{ont_a}/share/{ref_id}")
        assert del_resp.status_code == 200

        # 验证不可见
        resp = client.get("/api/v1/entities", params={"ontology_id": ont_b})
        names = [e["name"] for e in resp.json()]
        assert "UnshareEntity" not in names

    def test_cannot_share_to_self(self, client, db):
        """不能将实体共享给自身本体。"""
        ont_a = _create_ontology(db, "self_share", "本体A")
        entity_id = _create_entity(db, "SelfShare", ont_a)

        resp = client.post(f"/api/v1/ontology/{ont_a}/share", json={
            "target_ontology_id": ont_a,
            "entity_id": entity_id,
        })
        assert resp.status_code == 400

    def test_cannot_share_other_ontology_entity(self, client, db):
        """不能共享不属于自己本体的实体。"""
        ont_a = _create_ontology(db, "other_src", "本体A")
        ont_b = _create_ontology(db, "other_tgt", "本体B")
        ont_c = _create_ontology(db, "other_own", "本体C")
        entity_id = _create_entity(db, "OtherEntity", ont_c)

        resp = client.post(f"/api/v1/ontology/{ont_a}/share", json={
            "target_ontology_id": ont_b,
            "entity_id": entity_id,
        })
        assert resp.status_code == 403

    def test_duplicate_share_returns_409(self, client, db):
        """重复共享同一实体到同一目标本体应返回 409。"""
        ont_a = _create_ontology(db, "dup_share_s", "源本体")
        ont_b = _create_ontology(db, "dup_share_t", "目标本体")
        entity_id = _create_entity(db, "DupShare", ont_a)

        resp1 = client.post(f"/api/v1/ontology/{ont_a}/share", json={
            "target_ontology_id": ont_b,
            "entity_id": entity_id,
        })
        assert resp1.status_code == 200

        resp2 = client.post(f"/api/v1/ontology/{ont_a}/share", json={
            "target_ontology_id": ont_b,
            "entity_id": entity_id,
        })
        assert resp2.status_code == 409


class TestSharedRefsList:
    """验证共享引用列表 API。"""

    def test_list_shared_out(self, client, db):
        """查询出向共享列表。"""
        ont_a = _create_ontology(db, "list_out_s", "源本体")
        ont_b = _create_ontology(db, "list_out_t", "目标本体")
        entity_id = _create_entity(db, "ListOutEntity", ont_a)

        client.post(f"/api/v1/ontology/{ont_a}/share", json={
            "target_ontology_id": ont_b,
            "entity_id": entity_id,
        })

        resp = client.get(f"/api/v1/ontology/{ont_a}/shared", params={"direction": "out"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["shared_out"]) == 1
        assert data["shared_out"][0]["entity_id"] == entity_id

    def test_list_shared_in(self, client, db):
        """查询入向共享列表。"""
        ont_a = _create_ontology(db, "list_in_s", "源本体")
        ont_b = _create_ontology(db, "list_in_t", "目标本体")
        entity_id = _create_entity(db, "ListInEntity", ont_a)

        client.post(f"/api/v1/ontology/{ont_a}/share", json={
            "target_ontology_id": ont_b,
            "entity_id": entity_id,
        })

        resp = client.get(f"/api/v1/ontology/{ont_b}/shared", params={"direction": "in"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["shared_in"]) == 1
        assert data["shared_in"][0]["source_ontology_id"] == ont_a
