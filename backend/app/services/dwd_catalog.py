"""DWD 数据目录查询服务 — 通过已注册的 Asset 查询 dwd_table_list / dwd_table_details。

前置条件：用户需在前端"数据接入"页面将 dwd_table_list 和 dwd_table_details
两张表注册为 Asset（kind=table）。本服务通过 Asset 名称查找并走 ExecuteService 执行查询。
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.services.data_plane.execute_service import (
    ExecuteRequest,
    ExecuteService,
)

logger = logging.getLogger(__name__)

_TABLE_LIST_ASSET_NAME = "dwd_table_list"
_TABLE_DETAILS_ASSET_NAME = "dwd_table_details"


def _find_asset(db: Session, name: str) -> Asset | None:
    asset = (
        db.query(Asset)
        .filter(Asset.status == "active", Asset.kind == "table")
        .filter(
            (Asset.name == name)
            | (Asset.alias == name)
            | (Asset.locator["table"].as_string() == name)
        )
        .first()
    )
    return asset


def _execute(db: Session, asset: Asset, sql: str, params: dict | None = None) -> list[list]:
    svc = ExecuteService(db)
    result = svc.execute(ExecuteRequest(
        asset_id=asset.id,
        sql=sql,
        params=params or {},
        purpose="dwd_catalog",
    ))
    return result.rows


def _expand_in_params(key_prefix: str, values: list) -> tuple[str, dict]:
    """展开 IN 查询的参数列表为 :k_0, :k_1, ... 格式"""
    placeholders = []
    params = {}
    for i, v in enumerate(values):
        k = f"{key_prefix}_{i}"
        placeholders.append(f":{k}")
        params[k] = v
    return ", ".join(placeholders), params


def get_domains(db: Session) -> list[str]:
    asset = _find_asset(db, _TABLE_LIST_ASSET_NAME)
    if not asset:
        logger.warning("未找到资产 '%s'，请先在数据接入页面注册", _TABLE_LIST_ASSET_NAME)
        return []
    sql = (
        "SELECT DISTINCT theme_domain_1 FROM dwd_table_list "
        "WHERE theme_domain_1 IS NOT NULL AND theme_domain_1 != '' "
        "ORDER BY theme_domain_1"
    )
    rows = _execute(db, asset, sql)
    return [r[0] for r in rows]


def get_sub_domains(domain1: str, db: Session) -> list[str]:
    asset = _find_asset(db, _TABLE_LIST_ASSET_NAME)
    if not asset:
        return []
    sql = (
        "SELECT DISTINCT theme_domain_2 FROM dwd_table_list "
        "WHERE theme_domain_1 = :d1 AND theme_domain_2 IS NOT NULL AND theme_domain_2 != '' "
        "ORDER BY theme_domain_2"
    )
    rows = _execute(db, asset, sql, {"d1": domain1})
    return [r[0] for r in rows]


def get_themes(domain1: str, domain2: str, db: Session) -> list[str]:
    asset = _find_asset(db, _TABLE_LIST_ASSET_NAME)
    if not asset:
        return []
    sql = (
        "SELECT DISTINCT theme_domain_3 FROM dwd_table_list "
        "WHERE theme_domain_1 = :d1 AND theme_domain_2 = :d2 "
        "AND theme_domain_3 IS NOT NULL AND theme_domain_3 != '' "
        "ORDER BY theme_domain_3"
    )
    rows = _execute(db, asset, sql, {"d1": domain1, "d2": domain2})
    return [r[0] for r in rows]


def get_tables(domain1: str, domain2: str, domain3: str | None = None, db: Session = None) -> list[dict]:
    asset = _find_asset(db, _TABLE_LIST_ASSET_NAME)
    if not asset:
        return []
    sql = (
        "SELECT table_name, table_desc, layering, cycle FROM dwd_table_list "
        "WHERE theme_domain_1 = :d1 AND theme_domain_2 = :d2"
    )
    params: dict = {"d1": domain1, "d2": domain2}
    if domain3:
        sql += " AND theme_domain_3 = :d3"
        params["d3"] = domain3
    sql += " ORDER BY serial_number"
    rows = _execute(db, asset, sql, params)
    return [{"table_name": r[0], "table_desc": r[1], "layering": r[2], "cycle": r[3]} for r in rows]


def get_table_schema(table_name: str, db: Session) -> list[dict]:
    asset = _find_asset(db, _TABLE_DETAILS_ASSET_NAME)
    if not asset:
        logger.warning("未找到资产 '%s'，请先在数据接入页面注册", _TABLE_DETAILS_ASSET_NAME)
        return []
    sql = (
        "SELECT field_name, field_desc, field_type, field_length, "
        "is_partition, field_handle, field_source_desc "
        "FROM dwd_table_details WHERE table_name = :tn ORDER BY field_serial_number"
    )
    rows = _execute(db, asset, sql, {"tn": table_name})
    return [
        {"field_name": r[0], "field_desc": r[1], "field_type": r[2], "field_length": r[3],
         "is_partition": r[4], "field_handle": r[5], "field_source_desc": r[6]}
        for r in rows
    ]


def get_tables_by_domains(
    domain1_list: list[str],
    domain2_list: list[str] | None = None,
    domain3_list: list[str] | None = None,
    db: Session = None,
) -> list[dict]:
    """根据多个主题域组合查询表列表"""
    asset = _find_asset(db, _TABLE_LIST_ASSET_NAME)
    if not asset:
        return []

    in_clause, params = _expand_in_params("d1", domain1_list)
    sql = f"SELECT table_name, table_desc, layering, cycle FROM dwd_table_list WHERE theme_domain_1 IN ({in_clause})"

    if domain2_list:
        in2, p2 = _expand_in_params("d2", domain2_list)
        sql += f" AND theme_domain_2 IN ({in2})"
        params.update(p2)
    if domain3_list:
        in3, p3 = _expand_in_params("d3", domain3_list)
        sql += f" AND theme_domain_3 IN ({in3})"
        params.update(p3)

    sql += " ORDER BY serial_number"
    rows = _execute(db, asset, sql, params)
    return [{"table_name": r[0], "table_desc": r[1], "layering": r[2], "cycle": r[3]} for r in rows]
