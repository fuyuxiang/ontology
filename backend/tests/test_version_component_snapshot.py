"""
Tests for OntologyVersionFunction, OntologyVersionRule, OntologyVersionAction snapshot models.
Verifies that models can be instantiated with correct fields and defaults.
"""
import pytest
from datetime import datetime


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
        from app.models.version_components import OntologyVersionFunction
        from sqlalchemy import inspect as sa_inspect
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
        from app.models.version_components import OntologyVersionFunction
        from sqlalchemy import inspect as sa_inspect
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
        from app.models.version_components import OntologyVersionRule
        from sqlalchemy import inspect as sa_inspect
        mapper = sa_inspect(OntologyVersionRule)
        col_defaults = {c.key: c.columns[0].default for c in mapper.mapper.column_attrs}
        assert col_defaults["description"].arg == ""
        assert col_defaults["condition_expr"].arg == ""
        assert col_defaults["priority"].arg == "medium"

    def test_id_auto_generated(self):
        from app.models.version_components import OntologyVersionRule
        from sqlalchemy import inspect as sa_inspect
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
        from app.models.version_components import OntologyVersionAction
        from sqlalchemy import inspect as sa_inspect
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
        from app.models.version_components import OntologyVersionAction
        from sqlalchemy import inspect as sa_inspect
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
            OntologyVersionFunction,
            OntologyVersionRule,
            OntologyVersionAction,
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
