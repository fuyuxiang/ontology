import os

from app.config.settings import get_settings
from app.rules.engine import infer_record, load_ruleset


def test_ruleset_is_loaded_from_rules_directory():
    os.environ["ONTOLOGY_IGNORE_ACTIVE_PROFILE"] = "1"
    settings = get_settings()
    ruleset = load_ruleset(settings)

    assert settings.rules_dir.name == "rules"
    assert settings.rules_path.name == "porting-risk.yaml"
    assert settings.ontology_domain_path.name == "telecom-porting.ttl"
    assert len(ruleset.factor_rules) == 7
    assert [rule.rule_label for rule in ruleset.decision_rules] == [
        "高风险组合规则",
        "中风险组合规则",
        "低风险默认规则",
    ]


def test_infer_record_uses_external_decision_table():
    os.environ["ONTOLOGY_IGNORE_ACTIVE_PROFILE"] = "1"
    ruleset = load_ruleset(get_settings())
    record = {
        "metrics": {
            "complaintCount30d": 4,
            "dataUsageDropPct": 35,
            "competitorContactCount30d": 1,
            "contractRemainingDays": 30,
            "portingCodeRequestCount30d": 1,
            "overdueDays": 0,
            "retentionOfferRejected": 0,
        }
    }

    result = infer_record(record, ruleset)

    assert result["riskLevel"] == "HIGH"
    assert result["recommendedAction"] == "48小时内外呼挽留+定向权益补贴"
    assert "高风险组合规则" in result["rules"]
    assert {factor.code for factor in result["factors"]} >= {
        "complaint_spike",
        "data_drop",
        "competitor_contact",
        "contract_expiring",
        "porting_intent",
    }
