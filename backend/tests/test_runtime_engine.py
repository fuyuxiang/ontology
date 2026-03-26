"""运营运行时集成测试。"""

from app.config.settings import get_settings
from app.services.semantic_service import SemanticService


def test_summary_exposes_operational_metrics():
    """验证首页概览包含运营层指标。"""
    service = SemanticService(get_settings())
    summary = service.get_summary()

    assert summary["operationalMetrics"]["caseCount"] == summary["primaryEntityCount"]
    assert summary["caseDistribution"]
    assert summary["taskDistribution"] is not None
    assert len(summary["actionCatalog"]) >= 6
    assert summary["operationsWorkbench"]["priorityBands"]
    assert summary["operationsWorkbench"]["queueLanes"]


def test_execute_action_advances_case_and_records_timeline():
    """验证执行动作会推进 case 状态并追加时间线记录。"""
    service = SemanticService(get_settings())
    case = next(item for item in service.list_cases() if item["availableActions"])
    action_id = case["availableActions"][0]["id"]

    before = service.get_case(case["caseId"])
    result = service.execute_action(
        action_id=action_id,
        actor_role="ops_manager",
        actor_id="test-user",
        actor_area_id=None,
        entity_id=case["entityId"],
        case_id=case["caseId"],
        parameters={},
    )
    after = service.get_case(case["caseId"])

    assert result["actionRun"]["action_id"] == action_id
    assert len(after["timeline"]) > len(before["timeline"])
    assert after["state"] != before["state"] or after["actionRuns"]
    assert result["workbench"]["focusCases"] is not None


def test_case_and_task_lists_are_enriched_for_workbench():
    """验证列表接口直接返回前端工作台可渲染字段。"""
    service = SemanticService(get_settings())

    case_item = service.list_cases()[0]
    task_item = service.list_tasks()[0]

    assert case_item["displayName"]
    assert "summaryFields" in case_item
    assert "recommendedAction" in case_item
    assert "nextAction" in case_item
    assert task_item["displayName"]
    assert "riskLevel" in task_item
    assert "summaryFields" in task_item
