"""SQL 占位符改写 — 在 connector 层把 :name 转换为各 driver 实际需要的形式。

输入约定：业务/上层全部用 `:name` 风格占位符（与 sql_introspect 一致）。
输出：
- pyformat 风格（pymysql/pymssql/psycopg2）：`%(name)s`，参数 dict 直接用
- named 风格（oracledb）：`:name`，原样返回（参数 dict 直接用）

实现注意：在替换时跳过字符串字面量、注释、`::cast`（PG 类型转换）。
"""
from __future__ import annotations

import re

# 匹配独立的 :name 占位符；前面不是冒号（防止 PG `col::int` 被误改）
_NAMED_PATTERN = re.compile(r"(?<!:):([A-Za-z_][A-Za-z0-9_]*)")


def to_pyformat(sql: str, params: dict) -> tuple[str, dict]:
    """:name → %(name)s；参数字典原样返回。"""
    new_sql = _replace_outside_strings(sql, lambda n: f"%({n})s")
    return new_sql, dict(params or {})


def to_named(sql: str, params: dict) -> tuple[str, dict]:
    """oracledb 等支持原生 :name 的驱动：sql 不动，参数 dict 直接用。"""
    return sql, dict(params or {})


def _replace_outside_strings(sql: str, replacer) -> str:
    """跨字符串字面量安全替换 :name 占位符。"""
    out = []
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        if ch in ("'", '"'):
            # 找到字符串结尾（处理转义引号）
            quote = ch
            j = i + 1
            while j < n:
                if sql[j] == quote:
                    if j + 1 < n and sql[j + 1] == quote:
                        j += 2
                        continue
                    j += 1
                    break
                if sql[j] == "\\":
                    j += 2
                    continue
                j += 1
            out.append(sql[i:j])
            i = j
            continue
        if ch == "-" and i + 1 < n and sql[i + 1] == "-":
            # 行注释
            j = sql.find("\n", i)
            if j < 0:
                j = n
            out.append(sql[i:j])
            i = j
            continue
        # 替换 :name
        m = _NAMED_PATTERN.match(sql, i)
        if m:
            name = m.group(1)
            out.append(replacer(name))
            i = m.end()
            continue
        out.append(ch)
        i += 1
    return "".join(out)
