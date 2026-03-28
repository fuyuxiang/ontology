"""语义服务测试。"""

from app.config.settings import get_settings
from app.services.semantic_service import SemanticService


def test_summary_contains_core_fields():
    """验证概览接口包含前端依赖的核心字段。"""
    service = SemanticService(get_settings())
    summary = service.get_summary()
    assert summary["primaryEntityCount"] > 0
    assert "riskDistribution" in summary
    assert "ontologyGraph" in summary
    assert summary["sourceCards"]


def test_summary_graph_only_contains_entity_nodes_and_relations():
    """验证概览图只保留实体节点和实体间关系。"""
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


def test_ontology_workspace_contains_resource_collections():
    """验证本体工作台接口包含核心资源集合。"""
    service = SemanticService(get_settings())
    workspace = service.get_ontology_workspace()

    assert workspace["metrics"]["objectTypeCount"] > 0
    assert workspace["metrics"]["sharedPropertyCount"] > 0
    assert workspace["metrics"]["objectTypeGroupCount"] > 0
    assert workspace["objectTypes"]
    assert len({item["id"] for item in workspace["objectTypes"]}) == len(workspace["objectTypes"])
    assert workspace["sharedProperties"]
    assert workspace["objectTypeGroups"]
    assert workspace["linkTypes"]
    assert workspace["actionTypes"]
    assert workspace["interfaces"]
    assert workspace["rules"]
    assert any(item["name"] == "CoreEntity" for item in workspace["interfaces"])
    assert any(item["name"] == "identifier" for item in workspace["sharedProperties"])


def test_ontology_governance_change_and_publish():
    """验证本体草稿变更可以保存并发布。"""
    service = SemanticService(get_settings())
    workspace = service.get_ontology_workspace()
    object_type = workspace["objectTypes"][0]

    governance = service.save_ontology_draft_change(
        resource_type="objectTypes",
        resource_id=object_type["id"],
        changes={"description": "测试草稿描述", "capabilityTags": ["edited-tag"]},
        actor_id="pytest",
    )
    assert governance["status"] == "draft"
    refreshed = service.get_ontology_workspace()
    refreshed_object = next(item for item in refreshed["objectTypes"] if item["id"] == object_type["id"])
    assert refreshed_object["description"] == "测试草稿描述"
    assert "edited-tag" in refreshed_object["capabilityTags"]

    published = service.publish_ontology_draft(actor_id="pytest")
    assert published["status"] == "published"
    assert published["changeCount"] == 0


def test_ontology_governance_revert_single_change():
    """验证回退单条草稿变更后，会恢复到上一条有效状态。"""
    service = SemanticService(get_settings())
    workspace = service.get_ontology_workspace()
    object_type = workspace["objectTypes"][0]
    original_description = object_type["description"]

    first = service.save_ontology_draft_change(
        resource_type="objectTypes",
        resource_id=object_type["id"],
        changes={"description": "第一版描述"},
        actor_id="pytest",
    )
    assert first["changeCount"] == 1
    second = service.save_ontology_draft_change(
        resource_type="objectTypes",
        resource_id=object_type["id"],
        changes={"description": "第二版描述"},
        actor_id="pytest",
    )
    latest_change = second["changes"][-1]
    assert latest_change["oldValue"] == "第一版描述"

    reverted = service.revert_ontology_draft_change(latest_change["id"])
    assert reverted["status"] == "draft"
    assert reverted["changeCount"] == 1

    refreshed = service.get_ontology_workspace()
    refreshed_object = next(item for item in refreshed["objectTypes"] if item["id"] == object_type["id"])
    assert refreshed_object["description"] == "第一版描述"

    final_change_id = reverted["changes"][0]["id"]
    cleaned = service.revert_ontology_draft_change(final_change_id)
    assert cleaned["status"] == "clean"
    assert cleaned["changeCount"] == 0

    restored = service.get_ontology_workspace()
    restored_object = next(item for item in restored["objectTypes"] if item["id"] == object_type["id"])
    assert restored_object["description"] == original_description


def test_ontology_governance_discard_restores_last_published_state():
    """验证丢弃草稿后会回到最近一次发布的本体状态。"""
    service = SemanticService(get_settings())
    workspace = service.get_ontology_workspace()
    object_type = workspace["objectTypes"][0]

    service.save_ontology_draft_change(
        resource_type="objectTypes",
        resource_id=object_type["id"],
        changes={"description": "已发布描述"},
        actor_id="pytest",
    )
    service.publish_ontology_draft(actor_id="pytest")

    draft = service.save_ontology_draft_change(
        resource_type="objectTypes",
        resource_id=object_type["id"],
        changes={"description": "待丢弃描述"},
        actor_id="pytest",
    )
    assert draft["status"] == "draft"
    assert draft["changeCount"] == 1

    discarded = service.discard_ontology_draft()
    assert discarded["status"] == "published"
    assert discarded["changeCount"] == 0

    refreshed = service.get_ontology_workspace()
    refreshed_object = next(item for item in refreshed["objectTypes"] if item["id"] == object_type["id"])
    assert refreshed_object["description"] == "已发布描述"
