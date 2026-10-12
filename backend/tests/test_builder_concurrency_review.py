"""Force two real HTTP workers to race on the same scoped new definition."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, local

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.security import create_access_token, hash_password
from app.database import Base, get_db
from app.main import app as production
from app.models import EntityAttribute, OntologyEntity, ScenarioDict, User


def test_concurrent_finalize_has_one_commit_and_recoverable_conflict(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'race.db'}", connect_args={"check_same_thread": False, "timeout": 10})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as db:
        db.add(User(id="owner", username="owner", name="Owner", role="admin", password_hash=hash_password("Fixture123!")))
        db.add(ScenarioDict(id="ontology", code="race", name="Race"))
        db.commit()
    app = FastAPI()
    app.include_router(production.router)
    def database():
        with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = database
    barrier, state = Barrier(2), local()
    def same_initial_read(conn, cursor, statement, parameters, context, executemany):
        if "ontology_entities.name =" in statement and not getattr(state, "passed", False):
            state.passed = True
            barrier.wait(timeout=10)
    event.listen(engine, "after_cursor_execute", same_initial_read)
    client = TestClient(app, raise_server_exceptions=False)
    payload = {"ontology_id": "ontology", "objects": [{"name": "Device", "properties": [{"name": "id", "type": "string"}]}]}
    headers = {"Authorization": "Bearer " + create_access_token("owner")}
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(lambda _: client.post("/api/v1/builder/finalize", headers=headers, json=payload), range(2)))
        assert sorted(row.status_code for row in responses) == [200, 409], [(r.status_code, r.text) for r in responses]
        assert "并发冲突" in next(row for row in responses if row.status_code == 409).json()["detail"]
        event.remove(engine, "after_cursor_execute", same_initial_read)
        retry = client.post("/api/v1/builder/finalize", headers=headers, json=payload)
        assert retry.status_code == 200 and retry.json()["created_entities"] == 0
        with sessions() as db:
            assert db.query(OntologyEntity).filter_by(ontology_id="ontology", name="Device").count() == 1
            assert db.query(EntityAttribute).count() == 1
    finally:
        if event.contains(engine, "after_cursor_execute", same_initial_read):
            event.remove(engine, "after_cursor_execute", same_initial_read)
        client.close()
        engine.dispose()
