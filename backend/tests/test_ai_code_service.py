import pytest
from unittest.mock import MagicMock, patch
from app.services.ai_code_service import AiCodeService


class TestContextBuilding:
    def setup_method(self):
        self.db = MagicMock()
        self.service = AiCodeService(self.db)

    def test_build_context_for_function(self):
        mock_func = MagicMock()
        mock_func.name = "calculate_total"
        mock_func.description = "计算总金额"
        mock_func.return_type = "number"
        mock_func.input_schema = [
            {"name": "customer_id", "type": "string", "required": True, "description": "客户ID", "entity_id": "ent-1"}
        ]
        mock_func.entity_id = "ent-2"
        mock_func.logic_type = "python"

        mock_entity = MagicMock()
        mock_entity.name = "Customer"
        mock_entity.name_cn = "客户"
        mock_entity.description = "客户实体"
        mock_attr = MagicMock()
        mock_attr.name = "total_amount"
        mock_attr.type = "number"
        mock_attr.description = "消费总额"
        mock_entity.attributes = [mock_attr]

        with patch.object(self.service, "_load_entity", return_value=mock_entity):
            context = self.service._build_function_context(mock_func, extra_entity_ids=[])

        assert "calculate_total" in context
        assert "customer_id" in context
        assert "Customer" in context

    def test_build_context_deduplicates_entities(self):
        mock_func = MagicMock()
        mock_func.name = "test"
        mock_func.description = ""
        mock_func.return_type = "string"
        mock_func.input_schema = [
            {"name": "id", "type": "string", "entity_id": "ent-1"}
        ]
        mock_func.entity_id = "ent-1"
        mock_func.logic_type = "python"

        mock_entity = MagicMock()
        mock_entity.name = "Order"
        mock_entity.name_cn = "订单"
        mock_entity.description = ""
        mock_entity.attributes = []

        with patch.object(self.service, "_load_entity", return_value=mock_entity) as mock_load:
            self.service._build_function_context(mock_func, extra_entity_ids=["ent-1"])

        mock_load.assert_called_once_with("ent-1")
