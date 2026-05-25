"""SQL 内省 / 安全审查 — sqlglot 封装。

为 ExecuteService 提供 4 道闸门的核心能力：
1. AST 解析（拒绝非 SELECT、多语句、解析失败）
2. 表引用提取（用于白名单校验：必须解析到已登记 Asset）
3. 危险函数检测（SLEEP/BENCHMARK/INTO OUTFILE 等黑名单）
4. 占位符规范化（:name → 各 dialect 风格 → 由 driver 参数化绑定）

也供 AssetService.register sql_view 时提取 dependencies 使用。
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Iterable

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

logger = logging.getLogger(__name__)


# ── 危险函数黑名单（不区分大小写）────────────────────────────────
_DANGEROUS_FUNCTIONS = {
    "sleep", "benchmark", "load_file", "pg_read_file", "pg_sleep",
    "xp_cmdshell", "extractvalue", "updatexml",
    "dbms_lock", "dbms_pipe",
}

# ── 危险关键字（非函数）──────────────────────────────────────────
_DANGEROUS_TOKENS = re.compile(
    r"\b(into\s+outfile|into\s+dumpfile|load\s+data\s+infile)\b",
    re.IGNORECASE,
)


# ── 占位符识别 ──────────────────────────────────────────────────
# 支持 :name 风格（推荐）；客户端绝不允许直接拼字符串
_PLACEHOLDER_PATTERN = re.compile(r":([A-Za-z_][A-Za-z0-9_]*)")


@dataclass
class IntrospectResult:
    ok: bool
    reason: str | None = None
    tables: list[str] = None
    placeholders: list[str] = None
    statement_type: str | None = None
    is_select: bool = False
    is_dml: bool = False
    is_ddl: bool = False


# ── 主入口 ──────────────────────────────────────────────────────

def introspect(sql: str, *, dialect: str | None = None) -> IntrospectResult:
    """全面解析 SQL 并返回审查结果。失败时 ok=False + reason。"""
    sql = (sql or "").strip().rstrip(";")
    if not sql:
        return IntrospectResult(ok=False, reason="empty_sql")

    # 多语句拒绝（朴素分号检测；sqlglot 也会失败但先快速否掉）
    if _looks_like_multi_statement(sql):
        return IntrospectResult(ok=False, reason="multi_statement")

    # 危险关键字
    if _DANGEROUS_TOKENS.search(sql):
        return IntrospectResult(ok=False, reason="dangerous_function")

    # AST
    try:
        ast = sqlglot.parse_one(sql, read=_dialect_name(dialect))
    except ParseError as e:
        logger.debug("parse failed: %s", e)
        return IntrospectResult(ok=False, reason="ast_failed")
    if ast is None:
        return IntrospectResult(ok=False, reason="ast_failed")

    # 危险函数
    for f in ast.find_all(exp.Anonymous):
        if (f.name or "").lower() in _DANGEROUS_FUNCTIONS:
            return IntrospectResult(ok=False, reason="dangerous_function")
    for f in ast.find_all(exp.Func):
        if (f.sql_name() or "").lower() in _DANGEROUS_FUNCTIONS:
            return IntrospectResult(ok=False, reason="dangerous_function")

    # 类型判定
    is_select = isinstance(ast, exp.Select) or ast.find(exp.Select) is not None and not _is_modifying(ast)
    is_dml = _is_modifying(ast)
    is_ddl = isinstance(ast, (exp.Create, exp.Drop, exp.Alter, exp.TruncateTable))

    return IntrospectResult(
        ok=True,
        tables=_extract_tables(ast),
        placeholders=_extract_placeholders(sql),
        statement_type=type(ast).__name__,
        is_select=is_select,
        is_dml=is_dml,
        is_ddl=is_ddl,
    )


def extract_table_refs(sql: str, *, dialect: str | None = None) -> list[str]:
    """仅提取表引用，用于 sql_view 注册时存 dependencies。"""
    r = introspect(sql, dialect=dialect)
    return r.tables or []


def extract_placeholders(sql: str) -> list[str]:
    """:name 形式占位符列表，用于校验调用方是否提供齐参数。"""
    return _extract_placeholders(sql)


def render_placeholders_for_driver(sql: str, dialect: str | None) -> tuple[str, list[str]]:
    """把 :name 改写为驱动需要的占位符形式，返回 (改写后 sql, 参数顺序列表)。

    pymysql/psycopg2 通常用 %(name)s；Oracle cx_Oracle 用 :name（保持原样）；
    本平台连接器统一吃 paramstyle=named（pymysql 不支持，但 connector 内部再转）；
    为减少各 driver 差异，这里**保持 :name 原样**返回，由各 connector 在 execute_sql 时自适配。
    """
    placeholders = _extract_placeholders(sql)
    return sql, placeholders


# ── 内部 ─────────────────────────────────────────────────────────

def _dialect_name(dialect: str | None) -> str | None:
    if not dialect:
        return None
    aliases = {
        "mysql": "mysql",
        "postgresql": "postgres",
        "postgres": "postgres",
        "oracle": "oracle",
        "sqlserver": "tsql",
        "mssql": "tsql",
        "hive": "hive",
        "clickhouse": "clickhouse",
    }
    return aliases.get(dialect.lower())


def _looks_like_multi_statement(sql: str) -> bool:
    # 移除字符串字面量内的分号干扰，然后检查剩余分号
    stripped = re.sub(r"'[^']*'", "''", sql)
    stripped = re.sub(r'"[^"]*"', '""', stripped)
    semicolons = [pos for pos, ch in enumerate(stripped) if ch == ";"]
    # 末尾的分号已经被 rstrip 掉；中间还有就是多语句
    return any(p < len(stripped) - 1 for p in semicolons)


def _extract_tables(ast: exp.Expression) -> list[str]:
    tables: list[str] = []
    for t in ast.find_all(exp.Table):
        # t.name 是表名；t.db 是 schema/database 前缀
        full = ".".join(filter(None, [t.catalog, t.db, t.name]))
        if full:
            tables.append(full)
    return tables


def _extract_placeholders(sql: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for m in _PLACEHOLDER_PATTERN.finditer(sql):
        n = m.group(1)
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _is_modifying(ast: exp.Expression) -> bool:
    return isinstance(ast, (exp.Insert, exp.Update, exp.Delete, exp.Merge))
