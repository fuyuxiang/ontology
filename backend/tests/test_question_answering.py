"""问答与 SPARQL 查询相关测试。"""

from app.config.settings import get_settings
from app.services.semantic_service import SemanticService


def test_default_question_query_returns_rows():
    """验证默认查询能够返回基础实体结果。"""
    service = SemanticService(get_settings())
    result = service.run_sparql(None)

    assert result["rowCount"] > 0
    assert {"userId", "deviceNumber", "riskLevel"}.issubset(set(result["variables"]))


def test_rule_query_can_join_user_and_inference_triples():
    """验证规则查询可以关联实体与推理生成的规则节点。"""
    service = SemanticService(get_settings())
    result = service.run_sparql(
        """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX telecom: <http://example.com/telecom#>
        SELECT ?userId ?ruleLabel
        WHERE {
          ?user a telecom:User ;
                telecom:userId ?userId ;
                <http://purl.org/doim/1.0#taggedByRule> ?rule .
          ?rule rdfs:label ?ruleLabel .
        }
        ORDER BY ?userId ?ruleLabel
        LIMIT 10
        """
    )

    assert result["rowCount"] > 0
    assert result["rows"][0]["userId"]
    assert result["rows"][0]["ruleLabel"]
