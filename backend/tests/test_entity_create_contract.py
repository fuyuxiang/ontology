"""EntityCreate 请求契约测试。

前端 EntityCreatePayload（frontend/src/types/ontology.ts）声称与本 schema 对齐，
这里固化关键约定，避免字段再次漂移（历史上出现过 scenario_code、schema_json 两次漂移）。
"""

import pytest
from pydantic import ValidationError

from app.schemas.entity import EntityCreate


def _payload(**overrides):
    data = {"name": "Customer", "name_cn": "客户", "tier": 1, "ontology_id": "o1"}
    data.update(overrides)
    return data


def test_ontology_id_is_required():
    with pytest.raises(ValidationError) as exc:
        EntityCreate(**{k: v for k, v in _payload().items() if k != "ontology_id"})
    assert any(e["loc"] == ("ontology_id",) for e in exc.value.errors())


def test_minimal_payload_accepted():
    entity = EntityCreate(**_payload())
    assert entity.ontology_id == "o1"
    assert entity.attributes == []
    assert entity.status == "active"


def test_config_json_is_the_datasource_binding_field():
    # schema_json 已迁移重命名为 config_json（migrations/schema_compat.py），
    # 旧名不再落值，因此这里断言新名可用、旧名不进入模型字段
    entity = EntityCreate(**_payload(config_json={"datasource_id": "ds1", "table_name": "t"}))
    assert entity.config_json == {"datasource_id": "ds1", "table_name": "t"}

    legacy = EntityCreate(**_payload(schema_json={"datasource_id": "ds1"}))
    assert legacy.config_json is None
    assert "schema_json" not in EntityCreate.model_fields


def test_namespace_is_not_a_create_field():
    # NodeDetailPanel 曾发送 namespace，该字段不属于 EntityCreate，不会落值
    assert "namespace" not in EntityCreate.model_fields


def test_attributes_accept_frontend_shape():
    entity = EntityCreate(**_payload(attributes=[
        {"name": "phone", "type": "string", "description": "手机号", "required": True},
    ]))
    assert entity.attributes[0].name == "phone"
    assert entity.attributes[0].required is True
    # 前端不再发送 id，后端 AttributeBase 也不接收
    assert "id" not in type(entity.attributes[0]).model_fields
