import json


def json_safe(value):
    """Normalize connector/function values for both SSE and JSON database columns."""
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))
