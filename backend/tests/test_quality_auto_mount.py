"""Test: binding creation auto-mounts quality rules."""
from unittest.mock import MagicMock, patch

from app.services.data_plane.object_binding_service import _auto_mount_quality_rules

_PATCH_TARGET = "app.services.data_plane.quality_rule_service.QualityRuleService"


def _make_entity_with_attrs(attrs):
    entity = MagicMock()
    entity.id = "entity-001"
    entity.name = "TestEntity"
    entity.attributes = []
    entity.config_json = {"primary_key": "user_id"}
    for a in attrs:
        attr = MagicMock()
        attr.name = a["name"]
        attr.required = a.get("required", False)
        attr.constraints_json = a.get("constraints_json")
        entity.attributes.append(attr)
    return entity


def test_auto_mount_creates_rules_for_required_attrs():
    db = MagicMock()
    entity = _make_entity_with_attrs([
        {"name": "email", "required": True},
        {"name": "nickname", "required": False},
    ])
    db.get.return_value = entity

    with patch(_PATCH_TARGET) as MockSvc:
        mock_svc = MockSvc.return_value
        mock_svc.list_rules.return_value = []
        _auto_mount_quality_rules(db, "asset-001", "entity-001")

        calls = mock_svc.create_rule.call_args_list
        kinds = [c.kwargs.get("kind") for c in calls]
        assert "row_count_min" in kinds
        assert "freshness" in kinds
        assert "null_ratio_max" in kinds
        assert "pk_uniqueness" in kinds
        assert len(calls) == 4  # row_count + freshness + pk_unique + email_null


def test_auto_mount_skips_existing_rules():
    db = MagicMock()
    entity = _make_entity_with_attrs([{"name": "email", "required": True}])
    db.get.return_value = entity

    with patch(_PATCH_TARGET) as MockSvc:
        mock_svc = MockSvc.return_value
        existing = MagicMock()
        existing.kind = "row_count_min"
        existing.column_name = None
        mock_svc.list_rules.return_value = [existing]
        _auto_mount_quality_rules(db, "asset-001", "entity-001")

        calls = mock_svc.create_rule.call_args_list
        kinds = [c.kwargs.get("kind") for c in calls]
        assert "row_count_min" not in kinds  # should skip existing


def test_auto_mount_handles_no_entity():
    db = MagicMock()
    db.get.return_value = None
    with patch(_PATCH_TARGET) as MockSvc:
        _auto_mount_quality_rules(db, "asset-001", "nonexistent")
        MockSvc.return_value.create_rule.assert_not_called()

