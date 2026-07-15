from unittest.mock import MagicMock, patch

import pytest

from app.services.function_runtime.models import FunctionMeta, ParamSchema
from app.services.function_runtime.registry import FunctionRegistry


def _make_meta(name="test_fn", type_="logic", ontology_id=1):
    return FunctionMeta(
        callable_name=name,
        description=f"desc for {name}",
        type=type_,
        params=[ParamSchema(name="x", type="number", required=True, description="")],
        return_type="object",
        source_path=f"/workspace/{ontology_id}/{name}/main.py",
        func_name=name,
        ontology_id=ontology_id,
        checksum="abc123",
    )


class TestRegistryInMemory:
    def test_register_and_get(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        registry = FunctionRegistry(db)
        meta = _make_meta("calc")
        registry.register(meta)
        assert registry.get("calc") == meta

    def test_unregister(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        registry = FunctionRegistry(db)
        registry.register(_make_meta("calc"))
        registry.unregister("calc")
        assert registry.get("calc") is None

    def test_discard_removes_from_cache(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        registry = FunctionRegistry(db)
        registry.register(_make_meta("calc"))
        registry.discard("calc")
        assert registry.get("calc") is None

    def test_discard_missing_is_noop(self):
        db = MagicMock()
        registry = FunctionRegistry(db)
        registry.discard("nonexistent")  # 不应抛异常
        assert registry.get("nonexistent") is None

    def test_get_nonexistent_returns_none(self):
        db = MagicMock()
        registry = FunctionRegistry(db)
        assert registry.get("nonexistent") is None

    def test_list_by_type(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        registry = FunctionRegistry(db)
        registry.register(_make_meta("fn1", "logic"))
        registry.register(_make_meta("fn2", "action"))
        registry.register(_make_meta("fn3", "logic"))

        logics = registry.list_by_type("logic")
        assert len(logics) == 2
        actions = registry.list_by_type("action")
        assert len(actions) == 1

    def test_list_by_type_with_ontology_filter(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        registry = FunctionRegistry(db)
        registry.register(_make_meta("fn1", "logic", ontology_id=1))
        registry.register(_make_meta("fn2", "logic", ontology_id=2))

        result = registry.list_by_type("logic", ontology_id=1)
        assert len(result) == 1
        assert result[0].callable_name == "fn1"

    def test_list_capabilities(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        registry = FunctionRegistry(db)
        registry.register(_make_meta("fn1", "logic"))
        registry.register(_make_meta("fn2", "action"))

        caps = registry.list_capabilities()
        assert len(caps) == 2
        assert caps[0]["name"] == "fn1"
        assert caps[0]["type"] == "logic"
        assert "params" in caps[0]

    def test_register_updates_existing(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        registry = FunctionRegistry(db)
        meta1 = _make_meta("calc")
        registry.register(meta1)
        meta2 = _make_meta("calc")
        meta2.description = "updated"
        registry.register(meta2)
        assert registry.get("calc").description == "updated"
