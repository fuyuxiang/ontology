"""规则引擎测试。"""

import os

from app.config.settings import get_settings
from app.rules.engine import infer_record, load_ruleset


def test_ruleset_is_loaded_from_rules_directory():
    """验证默认规则集会从项目 rules 目录加载。"""
    os.environ["ONTOLOGY_IGNORE_ACTIVE_PROFILE"] = "1"
    settings = get_settings()
    ruleset = load_ruleset(settings)

    assert settings.rules_dir.name == "rules"
    assert settings.rules_path.name == "porting-risk.yaml"
    assert settings.ontology_domain_path.name == "telecom-porting.ttl"
    assert len(ruleset.factor_rules) == 11
    assert [rule.rule_label for rule in ruleset.decision_rules] == [
        "高风险携转预警",
        "中风险携转预警",
        "低风险携转预警",
        "低风险默认规则",
    ]


def test_infer_record_uses_external_decision_table():
    """验证推理逻辑会按外部决策表产出高风险结果。"""
    os.environ["ONTOLOGY_IGNORE_ACTIVE_PROFILE"] = "1"
    ruleset = load_ruleset(get_settings())
    record = {
        "metrics": {
            "hasActiveContract": False,
            "hasFusionBinding": False,
            "hasArrears": False,
            "hasRecentQuery7d": True,
            "hasRecentQuery30d": True,
            "queryAllowed": "1",
            "competitorCallCount7d": 2,
            "competitorCallCount30d": 2,
            "complaintCount30d": 2,
            "complaintCount60d": 2,
            "latestMaintainSuccess": "0",
            "innetMonths": 8,
        }
    }

    result = infer_record(record, ruleset)

    assert result["riskLevel"] == "HIGH"
    assert result["recommendedAction"] == "携转风险等级=高，触发紧急维系流程（例如：专属客服对接）"
    assert "高风险携转预警" in result["rules"]
    assert {factor.code for factor in result["factors"]} >= {
        "no_active_contract",
        "no_fusion_binding",
        "no_arrears",
        "recent_query_7d",
        "competitor_call",
        "complaint_30d",
        "retention_failed",
        "short_tenure",
    }
