from app.config.settings import get_settings
from app.services.semantic_service import SemanticService


def test_summary_contains_core_fields():
    service = SemanticService(get_settings())
    summary = service.get_summary()
    assert summary["primaryEntityCount"] > 0
    assert "riskDistribution" in summary
    assert "ontologyGraph" in summary
    assert summary["sourceCards"]
