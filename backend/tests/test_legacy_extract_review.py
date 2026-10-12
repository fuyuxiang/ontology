"""The registered extraction API must use effective config and reject empty output."""
from types import SimpleNamespace as N

from app.api.v1 import entities
from test_core_review import fixture, auth  # noqa: F401


def test_extraction_uses_configured_model_preserves_input_and_rejects_invalid_result(fixture, monkeypatch):
    client, db = fixture
    calls = []
    reply = [N(choices=[N(message=N(content='{"entities": [], "relations": []}'))])]
    def create(**kwargs):
        calls.append(kwargs)
        return reply[0]
    def resolve(**kwargs):
        assert kwargs['db'] is db and kwargs['scene'] == 'ontology'
        return N(chat=N(completions=N(create=create)))
    monkeypatch.setattr(entities, 'get_llm_client', resolve)
    monkeypatch.setattr('app.services.llm_resolver.get_model_name', lambda db, scene: 'saved-model')
    response = client.post('/api/v1/entities/ai-extract', headers=auth('admin'), data={'text': '设备温度告警'})
    assert response.status_code == 502
    assert calls[0]['model'] == 'saved-model'
    assert calls[0]['messages'][1]['content'] == '设备温度告警'
    response = client.post('/api/v1/entities/ai-extract', headers=auth('admin'), data={'text': 'a' * 8001})
    assert response.status_code == 413 and len(calls) == 1
