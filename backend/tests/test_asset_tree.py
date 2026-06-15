"""tests/test_asset_tree.py"""
import pytest
from unittest.mock import MagicMock, patch
from app.services.data_plane.asset_service import AssetService


def _make_asset(id, name, conn_id, schema_snapshot):
    a = MagicMock()
    a.id = id
    a.name = name
    a.connection_id = conn_id
    a.kind = "table"
    a.locator = {"table": name}
    a.schema_snapshot = schema_snapshot
    return a


def test_get_tree_groups_by_connection():
    db = MagicMock()
    svc = AssetService(db)

    assets = [
        _make_asset("a1", "t_customer", "c1",
                    [{"name": "id", "type": "bigint", "comment": "主键", "is_pk": True},
                     {"name": "name", "type": "varchar", "comment": "客户名"}]),
        _make_asset("a2", "t_order", "c1",
                    [{"name": "order_no", "type": "varchar", "comment": "订单号"}]),
        _make_asset("a3", "t_product", "c2",
                    [{"name": "sku", "type": "varchar", "comment": "SKU编码"}]),
    ]

    mock_conn1 = MagicMock()
    mock_conn1.name = "业务库"
    mock_conn1.type = "mysql"
    mock_conn1.database = "biz_db"

    mock_conn2 = MagicMock()
    mock_conn2.name = "数仓"
    mock_conn2.type = "postgresql"
    mock_conn2.database = "dw"

    def mock_get(cid):
        return {"c1": mock_conn1, "c2": mock_conn2}.get(cid)

    with patch.object(svc.repo, "list_active_structured", return_value=assets):
        db.query.return_value.get = mock_get
        tree = svc.get_tree()

    assert len(tree) == 2
    biz = next(n for n in tree if n["connection_id"] == "c1")
    assert len(biz["tables"]) == 2
    t_cust = next(t for t in biz["tables"] if t["asset_id"] == "a1")
    assert t_cust["table_name"] == "t_customer"
    assert len(t_cust["columns"]) == 2
    assert t_cust["columns"][0]["name"] == "id"
    assert t_cust["columns"][0]["is_pk"] is True


def test_get_tree_empty():
    db = MagicMock()
    svc = AssetService(db)
    with patch.object(svc.repo, "list_active_structured", return_value=[]):
        tree = svc.get_tree()
    assert tree == []


def test_get_tree_filters_by_connection():
    db = MagicMock()
    svc = AssetService(db)

    assets = [
        _make_asset("a1", "t_customer", "c1", [{"name": "id", "type": "bigint"}]),
        _make_asset("a3", "t_product", "c2", [{"name": "sku", "type": "varchar"}]),
    ]

    mock_conn1 = MagicMock()
    mock_conn1.name = "业务库"
    mock_conn1.type = "mysql"
    mock_conn1.database = "biz_db"

    def mock_get(cid):
        return {"c1": mock_conn1}.get(cid)

    with patch.object(svc.repo, "list_active_structured", return_value=assets):
        db.query.return_value.get = mock_get
        tree = svc.get_tree(connection_id="c1")

    assert len(tree) == 1
    assert tree[0]["connection_id"] == "c1"
