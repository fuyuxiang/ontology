"""ontology_mapping_service 单元测试"""
import json
from unittest.mock import MagicMock, patch

import pytest

SAMPLE_ONTOLOGY = {
    "entities": [
        {
            "name": "Customer",
            "displayName": "客户",
            "properties": [
                {"name": "customerName", "displayName": "客户名称", "type": "string", "required": True},
                {"name": "phone", "displayName": "手机号", "type": "string", "required": False},
            ],
        }
    ],
    "relations": [
        {"name": "belongsTo", "displayName": "属于", "source": "Order", "target": "Customer", "cardinality": "N:1"}
    ],
}


def test_build_ontology_summary():
    from app.services.ontology_mapping_service import _build_ontology_summary
    summary = _build_ontology_summary(SAMPLE_ONTOLOGY)
    assert "客户" in summary
    assert "Customer" in summary
    assert "客户名称" in summary
    assert "属于" in summary


def test_merge_mapping_into_ontology():
    import copy

    from app.services.ontology_mapping_service import _merge_mapping_into_ontology

    ontology = copy.deepcopy(SAMPLE_ONTOLOGY)
    mapping = {
        "entities": [
            {
                "name": "Customer",
                "table": "dwd_crm_customer",
                "confidence": 0.92,
                "properties": [
                    {"name": "customerName", "field": "cust_name", "fieldType": "varchar", "confidence": 0.95},
                    {"name": "phone", "field": "mobile", "fieldType": "varchar", "confidence": 0.72},
                ],
            }
        ],
        "relations": [
            {
                "name": "belongsTo",
                "source": "Order",
                "target": "Customer",
                "sourceField": "cust_id",
                "sourceTable": "dwd_order_main",
                "targetField": "id",
                "targetTable": "dwd_crm_customer",
                "confidence": 0.88,
            }
        ],
    }

    result = _merge_mapping_into_ontology(ontology, mapping)

    assert result["entities"][0]["table"] == "dwd_crm_customer"
    assert result["entities"][0]["confidence"] == 0.92
    assert result["entities"][0]["properties"][0]["field"] == "cust_name"
    assert result["entities"][0]["properties"][1]["field"] == "mobile"
    assert result["relations"][0]["sourceField"] == "cust_id"
    assert result["relations"][0]["targetTable"] == "dwd_crm_customer"
    assert result["relations"][0]["confidence"] == 0.88


def test_merge_mapping_missing_entity():
    import copy

    from app.services.ontology_mapping_service import _merge_mapping_into_ontology

    ontology = copy.deepcopy(SAMPLE_ONTOLOGY)
    mapping = {"entities": [], "relations": []}

    result = _merge_mapping_into_ontology(ontology, mapping)

    assert result["entities"][0]["table"] is None
    assert result["entities"][0]["confidence"] == 0
    assert result["entities"][0]["properties"][0]["field"] is None


@patch("app.services.ontology_mapping_service.get_all_tables_summary")
@patch("app.services.ontology_mapping_service._get_llm_client")
@patch("app.services.ontology_mapping_service.map_entities_and_relations")
def test_map_ontology_stream_success(mock_map, mock_client, mock_tables):
    from app.services.ontology_mapping_service import map_ontology_stream

    mock_tables.return_value = [
        {"table_name": "dwd_crm_customer", "table_desc": "客户主表"},
    ]

    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = json.dumps({
        "candidates": [{"entity": "Customer", "tables": ["dwd_crm_customer"]}]
    })
    mock_client.return_value.chat.completions.create.return_value = mock_resp

    mock_map.return_value = {
        "entities": [{"name": "Customer", "table": "dwd_crm_customer", "confidence": 0.9, "properties": []}],
        "relations": [],
    }

    events = list(map_ontology_stream(SAMPLE_ONTOLOGY))
    result_events = [e for e in events if "result" in e]
    assert len(result_events) == 1
    assert "dwd_crm_customer" in result_events[0]


@patch("app.services.ontology_mapping_service.get_all_tables_summary")
def test_map_ontology_stream_db_error(mock_tables):
    from app.services.ontology_mapping_service import map_ontology_stream

    mock_tables.side_effect = Exception("Connection refused")

    events = list(map_ontology_stream(SAMPLE_ONTOLOGY))
    error_events = [e for e in events if "error" in e]
    assert len(error_events) == 1
    # The SSE stream may unicode-escape Chinese characters; decode to verify
    error_text = error_events[0].encode().decode("unicode_escape") if "\\u" in error_events[0] else error_events[0]
    assert "数据资产服务不可用" in error_text
