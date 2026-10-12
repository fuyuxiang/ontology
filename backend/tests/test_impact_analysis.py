"""Actual dependency endpoints, with platform authorization."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.core.security import create_access_token
from app.models.user import User
from app.models.skill import Skill

@pytest.fixture
def client():
    with SessionLocal() as db:
        user = User(username='impact-review', name='Impact review', password_hash='x', role='admin')
        db.add(user); db.commit(); user_id = user.id
    client = TestClient(app)
    client.headers.update({'Authorization':'Bearer ' + create_access_token(user_id)})
    yield client
    with SessionLocal() as db:
        db.query(User).filter_by(id=user_id).delete(); db.commit()


def test_function_impact_endpoint(client):
    response = client.get('/api/v1/impact-analysis/functions/nonexistent')
    assert response.status_code == 200, response.text
    assert response.json() == {'published_versions':[], 'referencing_workflows':[], 'referencing_skills':[], 'safe_to_delete':True}


def test_action_impact_endpoint(client):
    response = client.get('/api/v1/impact-analysis/actions/nonexistent')
    assert response.status_code == 200
    assert response.json()['safe_to_delete'] is True


def test_skill_reference_is_reported_as_unsafe_to_delete(client):
    with SessionLocal() as db:
        skill = Skill(name='Impact skill', tools=[{'type':'function','id':'referenced-fn'}])
        db.add(skill); db.commit(); sid = skill.id
    response = client.get('/api/v1/impact-analysis/functions/referenced-fn')
    assert response.status_code == 200
    assert response.json()['safe_to_delete'] is False
    assert response.json()['referencing_skills'][0]['id'] == sid
    with SessionLocal() as db:
        db.query(Skill).filter_by(id=sid).delete(); db.commit()
