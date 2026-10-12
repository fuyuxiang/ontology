"""Published SDKs retain business id fields and use the mapped instance key."""
import importlib.util
import sys
from types import SimpleNamespace

from app.services.osdk_generator import _generate_python, _generate_typescript


def entity():
    return SimpleNamespace(id="snapshot-device", source_entity_id="device", version_id="published-v1", name="Device",
        attributes=[SimpleNamespace(name="id", type="integer", required=True, source_attribute_id="business-id"),
                    SimpleNamespace(name="serial", type="string", required=False, source_attribute_id="instance-key")],
        binding_snapshot={"id_column": "serial_number", "field_mappings": [
            {"attribute_id": "business-id", "source_column": "status_code"},
            {"attribute_id": "instance-key", "source_column": "serial_number"}]})


def test_generated_python_uses_primary_property_without_losing_business_id(tmp_path):
    for file in _generate_python([entity()], {})["files"]:
        (tmp_path / file["name"]).write_text(file["content"])
    spec = importlib.util.spec_from_file_location("identity_review_sdk", tmp_path / "__init__.py",
                                                submodule_search_locations=[str(tmp_path)])
    package = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = package
    try:
        spec.loader.exec_module(package)
        class Client:
            def __init__(self):
                self.calls = []
            def query(self, name, **params):
                self.calls.append(("list", name, params))
                return [{"id": 7, "serial": "S-001"}, {"id": 7, "serial": "S-002"}]
            def get_by_id(self, name, record_id, **params):
                self.calls.append(("get", name, record_id, params))
                return {"id": 7, "serial": record_id}
            def get_relations(self, *args, **pagination):
                self.calls.append(("relations", *args, pagination))
                return []
        client = Client()
        rows = package.Device.list(client)
        assert [row.id for row in rows] == ["S-001", "S-002"]
        assert all(row.id_ == 7 for row in rows)
        assert package.Device.get(client, "S-001").id == "S-001"
        rows[1].relations(client, limit=1, offset=2, relation_id="r1")
        assert client.calls[-1] == ("relations", "device", "S-002", 1, None, "published-v1",
                                    {"limit": 1, "offset": 2, "relation_id": "r1"})
        assert client.calls[0][2]["version_id"] == "published-v1"
    finally:
        for name in list(sys.modules):
            if name == spec.name or name.startswith(spec.name + "."):
                sys.modules.pop(name, None)


def test_generated_typescript_keeps_id_type_and_uses_primary_property():
    files = _generate_typescript([entity()], {})["files"]
    device = next(file["content"] for file in files if file["name"] == "Device.ts")
    assert '"id": number;' in device and '"serial": string;' in device
    assert 'String(d["serial"])' in device and 'String(data["serial"])' in device
    assert 'this.id, depth, relType, "published-v1", pagination' in device
