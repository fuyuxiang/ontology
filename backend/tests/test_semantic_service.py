from app.config.settings import get_settings
from app.services.semantic_service import SemanticService


def test_summary_contains_core_fields():
    service = SemanticService(get_settings())
    summary = service.get_summary()
    assert summary["primaryEntityCount"] > 0
    assert "riskDistribution" in summary
    assert "ontologyGraph" in summary
    assert summary["sourceCards"]


def test_summary_graph_only_contains_entity_nodes_and_relations():
    service = SemanticService(get_settings())
    summary = service.get_summary()
    graph = summary["ontologyGraph"]

    node_ids = {node["id"] for node in graph["nodes"]}
    node_types = {node["type"] for node in graph["nodes"]}
    non_user_nodes = [
        (node["type"], node["label"])
        for node in graph["nodes"]
        if node["type"] != "User"
    ]

    assert graph["displayedPrimaryEntities"] == summary["primaryEntityCount"]
    assert "RiskResult" not in node_types
    assert "Inference" not in node_types
    assert "Action" not in node_types
    assert len(non_user_nodes) == len(set(non_user_nodes))

    for edge in graph["edges"]:
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids
