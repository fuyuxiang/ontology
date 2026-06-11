"""Test impact analysis endpoints exist and return correct structure"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_function_impact_endpoint():
    resp = client.get("/api/v1/impact-analysis/functions/nonexistent")
    assert resp.status_code == 200
    data = resp.json()
    assert "published_versions" in data
    assert "referencing_workflows" in data
    assert "referencing_skills" in data
    assert data["safe_to_delete"] is True


def test_rule_impact_endpoint():
    resp = client.get("/api/v1/impact-analysis/rules/nonexistent")
    assert resp.status_code == 200


def test_action_impact_endpoint():
    resp = client.get("/api/v1/impact-analysis/actions/nonexistent")
    assert resp.status_code == 200
