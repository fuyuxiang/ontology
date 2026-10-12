"""AI suggestion errors must reach the registered HTTP caller, never empty success."""
from types import SimpleNamespace

import pytest

from test_builder_delivery import environment  # noqa: F401
from app.api.v1 import builder


@pytest.mark.parametrize("path,payload", [
    ("suggest-attributes", {"object_name": "Device", "existing_properties": []}),
    ("suggest-relations", {"objects": [{"name": "Device"}, {"name": "Ticket"}]}),
])
def test_invalid_suggestions_fail_and_explicit_empty_list_remains_valid(environment, monkeypatch, path, payload):
    client, _ = environment
    completion = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="not JSON"))])
    monkeypatch.setattr(builder, "get_llm_client", lambda **kwargs: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: completion))))
    for content in ("not JSON", "{}", "[broken]", '[{"name":"bad","source":"Device","target":"Unknown","type":"unsupported"}]',
                    '[{"name":"bad","type":[],"source":[],"target":"Ticket"}]'):
        completion.choices[0].message.content = content
        result = client.post(f"/builder/{path}", json=payload)
        assert result.status_code == 502, result.text
        assert "detail" in result.json()
    completion.choices[0].message.content = "[]"
    result = client.post(f"/builder/{path}", json=payload)
    assert result.status_code == 200 and next(iter(result.json().values())) == []
    valid = ('[{"name":"temperature","type":"number","required":false}]' if path == "suggest-attributes"
             else '[{"name":"repair","source":"Device","target":"Ticket","cardinality":"1:N"}]')
    completion.choices[0].message.content = "```json\n" + valid + "\n```"
    result = client.post(f"/builder/{path}", json=payload)
    assert result.status_code == 200 and len(next(iter(result.json().values()))) == 1
