"""
Tests for OntologyVersionFunction, OntologyVersionRule, OntologyVersionAction snapshot models.
Verifies that models can be instantiated with correct fields and defaults.
"""
from datetime import datetime

import pytest


class TestOntologyVersionFunction:
    def test_import(self):
        from app.models.version_components import OntologyVersionFunction
        assert OntologyVersionFunction is not None

    def test_instantiate_minimal(self):
        from app.models.version_components import OntologyVersionFunction
        obj = OntologyVersionFunction(
            version_id="ver-001",
            source_function_id="fn-001",
            version_entity_id="ve-001",
            name="compute_age",
        )
        assert obj.name == "compute_age"
        assert obj.version_id == "ver-001"
        assert obj.source_function_id == "fn-001"
        assert obj.version_entity_id == "ve-001"

    def test_default_fields(self):
        from sqlalchemy import inspect as sa_inspect

        from app.models.version_components import OntologyVersionFunction
        mapper = sa_inspect(OntologyVersionFunction)
        col_defaults = {c.key: c.columns[0].default for c in mapper.mapper.column_attrs}
        # SQLAlchemy column defaults fire on INSERT, not on Python instantiation;
        # verify the default values are configured correctly on the column.
        assert col_defaults["description"].arg == ""
        assert col_defaults["return_type"].arg == "string"
        assert col_defaults["logic_type"].arg == "expression"
        assert col_defaults["logic_body"].arg == ""
        assert col_defaults["callable_name"].arg == ""

    def test_id_auto_generated(self):
        from sqlalchemy import inspect as sa_inspect

        from app.models.version_components import OntologyVersionFunction
        mapper = sa_inspect(OntologyVersionFunction)
        col_defaults = {c.key: c.columns[0].default for c in mapper.mapper.column_attrs}
        # id default should be the gen_uuid callable
        assert col_defaults["id"] is not None
        assert callable(col_defaults["id"].arg)

    def test_tablename(self):
        from app.models.version_components import OntologyVersionFunction
        assert OntologyVersionFunction.__tablename__ == "ontology_version_functions"


class TestOntologyVersionRule:
    def test_import(self):
        from app.models.version_components import OntologyVersionRule
        assert OntologyVersionRule is not None

    def test_instantiate_minimal(self):
        from app.models.version_components import OntologyVersionRule
        obj = OntologyVersionRule(
            version_id="ver-001",
            source_rule_id="rule-001",
            version_entity_id="ve-001",
            name="age_must_be_positive",
        )
        assert obj.name == "age_must_be_positive"
        assert obj.version_id == "ver-001"
        assert obj.source_rule_id == "rule-001"
        assert obj.version_entity_id == "ve-001"

    def test_default_fields(self):
        from sqlalchemy import inspect as sa_inspect

        from app.models.version_components import OntologyVersionRule
        mapper = sa_inspect(OntologyVersionRule)
        col_defaults = {c.key: c.columns[0].default for c in mapper.mapper.column_attrs}
        assert col_defaults["description"].arg == ""
        assert col_defaults["condition_expr"].arg == ""
        assert col_defaults["priority"].arg == "medium"

    def test_id_auto_generated(self):
        from sqlalchemy import inspect as sa_inspect

        from app.models.version_components import OntologyVersionRule
        mapper = sa_inspect(OntologyVersionRule)
        col_defaults = {c.key: c.columns[0].default for c in mapper.mapper.column_attrs}
        assert col_defaults["id"] is not None
        assert callable(col_defaults["id"].arg)

    def test_tablename(self):
        from app.models.version_components import OntologyVersionRule
        assert OntologyVersionRule.__tablename__ == "ontology_version_rules"


class TestOntologyVersionAction:
    def test_import(self):
        from app.models.version_components import OntologyVersionAction
        assert OntologyVersionAction is not None

    def test_instantiate_minimal(self):
        from app.models.version_components import OntologyVersionAction
        obj = OntologyVersionAction(
            version_id="ver-001",
            source_action_id="act-001",
            name="send_notification",
            action_type="http",
        )
        assert obj.name == "send_notification"
        assert obj.version_id == "ver-001"
        assert obj.source_action_id == "act-001"
        assert obj.action_type == "http"

    def test_default_fields(self):
        from sqlalchemy import inspect as sa_inspect

        from app.models.version_components import OntologyVersionAction
        mapper = sa_inspect(OntologyVersionAction)
        col_defaults = {c.key: c.columns[0].default for c in mapper.mapper.column_attrs}
        assert col_defaults["category"].arg == "domain"

    def test_system_action_no_entity(self):
        from app.models.version_components import OntologyVersionAction
        # System actions have no version_entity_id
        obj = OntologyVersionAction(
            version_id="ver-001",
            source_action_id="act-sys-001",
            name="global_audit",
            action_type="audit",
            category="system",
        )
        assert obj.version_entity_id is None
        assert obj.category == "system"

    def test_id_auto_generated(self):
        from sqlalchemy import inspect as sa_inspect

        from app.models.version_components import OntologyVersionAction
        mapper = sa_inspect(OntologyVersionAction)
        col_defaults = {c.key: c.columns[0].default for c in mapper.mapper.column_attrs}
        assert col_defaults["id"] is not None
        assert callable(col_defaults["id"].arg)

    def test_tablename(self):
        from app.models.version_components import OntologyVersionAction
        assert OntologyVersionAction.__tablename__ == "ontology_version_actions"


class TestRegistration:
    def test_models_in_init(self):
        from app.models import (
            OntologyVersionAction,
            OntologyVersionFunction,
            OntologyVersionRule,
        )
        assert OntologyVersionFunction is not None
        assert OntologyVersionRule is not None
        assert OntologyVersionAction is not None

    def test_version_has_relationships(self):
        from app.models.version import OntologyVersion
        mapper = OntologyVersion.__mapper__
        rel_keys = [r.key for r in mapper.relationships]
        assert "functions" in rel_keys
        assert "rules" in rel_keys
        assert "actions" in rel_keys


# ---------------------------------------------------------------------------
# Snapshot service tests
# ---------------------------------------------------------------------------

class _Attr:
    """Minimal stand-in for OntologyVersionAttribute."""
    def __init__(self, source_attribute_id: str, id: str):
        self.source_attribute_id = source_attribute_id
        self.id = id


class _VersionEntity:
    """Minimal stand-in for OntologyVersionEntity."""
    def __init__(self, id: str, source_entity_id: str, attributes=None):
        self.id = id
        self.source_entity_id = source_entity_id
        self.attributes = attributes or []


class _Version:
    """Minimal stand-in for OntologyVersion."""
    def __init__(self, id: str, entities=None):
        self.id = id
        self.entities = entities or []


class _Function:
    """Minimal stand-in for OntologyFunction."""
    def __init__(self, id, name, description="", return_type="string",
                 input_schema=None, logic_type="expression", logic_body="",
                 callable_name="", tags=None):
        self.id = id
        self.name = name
        self.description = description
        self.return_type = return_type
        self.input_schema = input_schema
        self.logic_type = logic_type
        self.logic_body = logic_body
        self.callable_name = callable_name
        self.tags = tags


class _Rule:
    """Minimal stand-in for BusinessRule."""
    def __init__(self, id, name, description="", condition_expr="",
                 conditions_json=None, priority="medium", input_params=None,
                 output_schema=None, tags=None):
        self.id = id
        self.name = name
        self.description = description
        self.condition_expr = condition_expr
        self.conditions_json = conditions_json
        self.priority = priority
        self.input_params = input_params
        self.output_schema = output_schema
        self.tags = tags


class _Action:
    """Minimal stand-in for EntityAction."""
    def __init__(self, id, name, action_type, category="domain",
                 type_config=None, description=None, parameters_json=None,
                 output_schema=None):
        self.id = id
        self.name = name
        self.action_type = action_type
        self.category = category
        self.type_config = type_config
        self.description = description
        self.parameters_json = parameters_json
        self.output_schema = output_schema


class TestSnapshotService:
    """Tests for snapshot_components_for_version."""

    def _make_db(self, functions=None, rules=None, actions=None, system_actions=None):
        """Return a mock Session whose .query().filter().all() returns configured lists.

        ``actions`` is returned for entity-scoped EntityAction queries.
        ``system_actions`` (default: []) is returned for the system-level query
        that runs after the per-entity loop.
        """
        from unittest.mock import MagicMock

        from app.models.function import OntologyFunction
        from app.models.rule import BusinessRule, EntityAction

        _system_actions = system_actions if system_actions is not None else []
        # Track how many times EntityAction has been queried to distinguish
        # domain (per-entity) calls from the trailing system-actions call.
        entity_action_call_count = {"n": 0}

        db = MagicMock()
        added = []
        db.add.side_effect = added.append
        db.flush = MagicMock()

        def query_side_effect(model):
            q = MagicMock()

            def filter_side_effect(*args, **kwargs):
                fq = MagicMock()

                def all_side_effect():
                    if model is OntologyFunction:
                        return functions or []
                    elif model is BusinessRule:
                        return rules or []
                    elif model is EntityAction:
                        entity_action_call_count["n"] += 1
                        # The system-level query is always the last one; we
                        # use the call count to differentiate.  For tests with
                        # a single entity the first call is domain, second is
                        # system.  For tests with no entities the first (only)
                        # call is the system query.
                        n_entities = sum(1 for _ in (actions or []))  # noqa
                        # Simpler: the system query is chained differently
                        # (three filters), but Mock can't see that.  Instead,
                        # return domain actions on the first call per entity
                        # and system_actions on the very last call.
                        # Since we can't know the total entity count here, we
                        # rely on the caller to pass separate lists.
                        # Return ``actions`` unless this is clearly a system
                        # query — indicated by system_actions being non-empty
                        # and call count > number of entities already seen.
                        # For simplicity: first call → domain, subsequent → system.
                        if entity_action_call_count["n"] == 1 and actions is not None:
                            return actions
                        return _system_actions
                    return []

                fq.all.side_effect = all_side_effect

                def filter2(*a, **kw):
                    fq2 = MagicMock()
                    fq2.all.side_effect = all_side_effect
                    return fq2

                fq.filter.side_effect = filter2
                return fq

            q.filter.side_effect = filter_side_effect
            return q

        db.query.side_effect = query_side_effect
        db._added = added
        return db

    def test_import(self):
        from app.services.version_component_snapshot import snapshot_components_for_version
        assert callable(snapshot_components_for_version)

    def test_empty_version_returns_zeros(self):
        from app.services.version_component_snapshot import snapshot_components_for_version
        version = _Version(id="v1", entities=[])
        db = self._make_db()
        result = snapshot_components_for_version(db, version)
        assert result == {"functions_count": 0, "rules_count": 0, "actions_count": 0}
        db.flush.assert_called_once()

    def test_function_snapshot_with_attr_remapping(self):
        from unittest.mock import MagicMock, patch

        from app.models.version_components import OntologyVersionFunction
        from app.services.version_component_snapshot import snapshot_components_for_version

        attr = _Attr(source_attribute_id="src-attr-1", id="ver-attr-1")
        ve = _VersionEntity(id="ve-1", source_entity_id="ent-1", attributes=[attr])
        version = _Version(id="v1", entities=[ve])

        func = _Function(
            id="fn-1",
            name="compute_age",
            input_schema=[{"attribute_id": "src-attr-1", "type": "integer"}],
        )

        db = self._make_db(functions=[func], rules=[], actions=[])
        result = snapshot_components_for_version(db, version)

        assert result["functions_count"] == 1
        assert result["rules_count"] == 0
        assert result["actions_count"] == 0
        db.flush.assert_called_once()

        # Find the added OntologyVersionFunction
        added_fns = [o for o in db._added if isinstance(o, OntologyVersionFunction)]
        assert len(added_fns) == 1
        snap = added_fns[0]
        assert snap.version_id == "v1"
        assert snap.source_function_id == "fn-1"
        assert snap.version_entity_id == "ve-1"
        assert snap.name == "compute_age"
        # attribute_id remapped to version_attribute_id
        assert snap.input_schema[0].get("attribute_id") is None or "attribute_id" not in snap.input_schema[0]
        assert snap.input_schema[0]["version_attribute_id"] == "ver-attr-1"

    def test_function_unknown_attr_becomes_none(self):
        from app.models.version_components import OntologyVersionFunction
        from app.services.version_component_snapshot import snapshot_components_for_version

        attr = _Attr(source_attribute_id="src-attr-1", id="ver-attr-1")
        ve = _VersionEntity(id="ve-1", source_entity_id="ent-1", attributes=[attr])
        version = _Version(id="v1", entities=[ve])

        func = _Function(
            id="fn-1",
            name="compute_x",
            input_schema=[{"attribute_id": "unknown-attr", "type": "string"}],
        )
        db = self._make_db(functions=[func], rules=[], actions=[])
        snapshot_components_for_version(db, version)

        added_fns = [o for o in db._added if isinstance(o, OntologyVersionFunction)]
        snap = added_fns[0]
        assert snap.input_schema[0]["version_attribute_id"] is None

    def test_rule_snapshot_with_conditions_and_params_remapping(self):
        from app.models.version_components import OntologyVersionRule
        from app.services.version_component_snapshot import snapshot_components_for_version

        attr = _Attr(source_attribute_id="src-attr-2", id="ver-attr-2")
        ve = _VersionEntity(id="ve-1", source_entity_id="ent-1", attributes=[attr])
        version = _Version(id="v1", entities=[ve])

        rule = _Rule(
            id="rule-1",
            name="age_positive",
            conditions_json=[{"attribute_id": "src-attr-2", "op": "gt", "value": 0}],
            input_params=[{"attribute_id": "src-attr-2", "required": True}],
        )
        db = self._make_db(functions=[], rules=[rule], actions=[])
        result = snapshot_components_for_version(db, version)

        assert result["rules_count"] == 1
        added_rules = [o for o in db._added if isinstance(o, OntologyVersionRule)]
        snap = added_rules[0]
        assert snap.source_rule_id == "rule-1"
        assert snap.version_entity_id == "ve-1"
        assert snap.conditions_json[0]["version_attribute_id"] == "ver-attr-2"
        assert snap.input_params[0]["version_attribute_id"] == "ver-attr-2"

    def test_action_snapshot_with_params_remapping(self):
        from app.models.version_components import OntologyVersionAction
        from app.services.version_component_snapshot import snapshot_components_for_version

        attr = _Attr(source_attribute_id="src-attr-3", id="ver-attr-3")
        ve = _VersionEntity(id="ve-1", source_entity_id="ent-1", attributes=[attr])
        version = _Version(id="v1", entities=[ve])

        action = _Action(
            id="act-1",
            name="send_notification",
            action_type="http",
            parameters_json=[{"attribute_id": "src-attr-3", "in": "body"}],
        )
        db = self._make_db(functions=[], rules=[], actions=[action])
        result = snapshot_components_for_version(db, version)

        assert result["actions_count"] == 1
        added_acts = [o for o in db._added if isinstance(o, OntologyVersionAction)]
        snap = added_acts[0]
        assert snap.source_action_id == "act-1"
        assert snap.version_entity_id == "ve-1"
        assert snap.parameters_json[0]["version_attribute_id"] == "ver-attr-3"

    def test_system_actions_are_snapshotted(self):
        from unittest.mock import MagicMock

        from app.models.rule import EntityAction
        from app.models.version_components import OntologyVersionAction
        from app.services.version_component_snapshot import snapshot_components_for_version

        version = _Version(id="v1", entities=[])

        sys_action = _Action(
            id="sys-act-1",
            name="global_audit",
            action_type="audit",
            category="system",
        )

        # Need a special db that returns system_actions for entity_id=None query
        db = MagicMock()
        added = []
        db.add.side_effect = added.append
        db.flush = MagicMock()

        def query_se(model):
            q = MagicMock()

            def filter_se(*args, **kw):
                fq = MagicMock()
                fq.all.return_value = [sys_action] if model is EntityAction else []

                def filter2(*a, **kw2):
                    fq2 = MagicMock()
                    fq2.all.return_value = [sys_action] if model is EntityAction else []
                    return fq2

                fq.filter.side_effect = filter2
                return fq

            q.filter.side_effect = filter_se
            return q

        db.query.side_effect = query_se
        db._added = added

        result = snapshot_components_for_version(db, version)
        assert result["actions_count"] == 1

        added_acts = [o for o in added if isinstance(o, OntologyVersionAction)]
        assert len(added_acts) == 1
        assert added_acts[0].version_entity_id is None
        assert added_acts[0].category == "system"

    def test_null_json_fields_are_preserved(self):
        from app.models.version_components import OntologyVersionFunction
        from app.services.version_component_snapshot import snapshot_components_for_version

        ve = _VersionEntity(id="ve-1", source_entity_id="ent-1", attributes=[])
        version = _Version(id="v1", entities=[ve])

        func = _Function(id="fn-2", name="no_schema", input_schema=None)
        db = self._make_db(functions=[func], rules=[], actions=[])
        snapshot_components_for_version(db, version)

        added_fns = [o for o in db._added if isinstance(o, OntologyVersionFunction)]
        assert added_fns[0].input_schema is None
