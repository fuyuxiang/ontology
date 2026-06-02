"""DWD 数据目录查询服务 — 查询 dwd_table_list / dwd_table_details"""
from __future__ import annotations

from sqlalchemy import create_engine, text, bindparam
from app.config import settings

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(settings.DWD_DATABASE_URL, pool_pre_ping=True, pool_size=5)
    return _engine


def get_domains() -> list[str]:
    with _get_engine().connect() as conn:
        rows = conn.execute(text("SELECT DISTINCT theme_domain_1 FROM dwd_table_list WHERE theme_domain_1 IS NOT NULL AND theme_domain_1 != '' ORDER BY theme_domain_1"))
        return [r[0] for r in rows]


def get_sub_domains(domain1: str) -> list[str]:
    with _get_engine().connect() as conn:
        rows = conn.execute(text("SELECT DISTINCT theme_domain_2 FROM dwd_table_list WHERE theme_domain_1 = :d1 AND theme_domain_2 IS NOT NULL AND theme_domain_2 != '' ORDER BY theme_domain_2"), {"d1": domain1})
        return [r[0] for r in rows]


def get_themes(domain1: str, domain2: str) -> list[str]:
    with _get_engine().connect() as conn:
        rows = conn.execute(text("SELECT DISTINCT theme_domain_3 FROM dwd_table_list WHERE theme_domain_1 = :d1 AND theme_domain_2 = :d2 AND theme_domain_3 IS NOT NULL AND theme_domain_3 != '' ORDER BY theme_domain_3"), {"d1": domain1, "d2": domain2})
        return [r[0] for r in rows]


def get_tables(domain1: str, domain2: str, domain3: str | None = None) -> list[dict]:
    with _get_engine().connect() as conn:
        sql = "SELECT table_name, table_desc, layering, cycle FROM dwd_table_list WHERE theme_domain_1 = :d1 AND theme_domain_2 = :d2"
        params: dict = {"d1": domain1, "d2": domain2}
        if domain3:
            sql += " AND theme_domain_3 = :d3"
            params["d3"] = domain3
        sql += " ORDER BY serial_number"
        rows = conn.execute(text(sql), params)
        return [{"table_name": r[0], "table_desc": r[1], "layering": r[2], "cycle": r[3]} for r in rows]


def get_table_schema(table_name: str) -> list[dict]:
    with _get_engine().connect() as conn:
        rows = conn.execute(text(
            "SELECT field_name, field_desc, field_type, field_length, is_partition, field_handle, field_source_desc "
            "FROM dwd_table_details WHERE table_name = :tn ORDER BY field_serial_number"
        ), {"tn": table_name})
        return [
            {"field_name": r[0], "field_desc": r[1], "field_type": r[2], "field_length": r[3],
             "is_partition": r[4], "field_handle": r[5], "field_source_desc": r[6]}
            for r in rows
        ]


def get_tables_by_domains(domain1_list: list[str], domain2_list: list[str] | None = None, domain3_list: list[str] | None = None) -> list[dict]:
    """根据多个主题域组合查询表列表"""
    with _get_engine().connect() as conn:
        sql = "SELECT table_name, table_desc, layering, cycle FROM dwd_table_list WHERE theme_domain_1 IN :d1s"
        params: dict = {"d1s": domain1_list}
        expanding = [bindparam("d1s", expanding=True)]
        if domain2_list:
            sql += " AND theme_domain_2 IN :d2s"
            params["d2s"] = domain2_list
            expanding.append(bindparam("d2s", expanding=True))
        if domain3_list:
            sql += " AND theme_domain_3 IN :d3s"
            params["d3s"] = domain3_list
            expanding.append(bindparam("d3s", expanding=True))
        sql += " ORDER BY serial_number"
        stmt = text(sql).bindparams(*expanding)
        rows = conn.execute(stmt, params)
        return [{"table_name": r[0], "table_desc": r[1], "layering": r[2], "cycle": r[3]} for r in rows]
