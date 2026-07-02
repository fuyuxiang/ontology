"""占位符改写回归测试。

重点覆盖：SQL 正文里字面量的 `%`（如 LIKE '%关键词%'）必须转义成 `%%`，
否则 pymysql 在 `query % escape_args(args)` 阶段会抛
`ValueError: unsupported format character`，导致 Agent 工具反复失败、
最终耗尽推理轮次。
"""
from app.connectors._param_style import to_named, to_pyformat


def _simulate_pymysql(rendered: str, escaped_args) -> str:
    """模拟 pymysql cursor.execute 的 `query % args` 格式化步骤。"""
    return rendered % escaped_args


def test_literal_percent_escaped_without_params():
    # 无参数但含字面量 % —— pymysql 传空 dict 时仍会做 % 格式化
    sql = "SELECT * FROM policy WHERE name LIKE '%流量王%'"
    rendered, args = to_pyformat(sql, {})
    assert rendered == "SELECT * FROM policy WHERE name LIKE '%%流量王%%'"
    # 还原后与原始 SQL 一致，不再抛 ValueError
    assert _simulate_pymysql(rendered, {}) == sql


def test_literal_percent_with_named_params():
    sql = (
        "SELECT * FROM policy WHERE name LIKE :kw "
        "AND type = :t AND note LIKE '%已停用%'"
    )
    rendered, args = to_pyformat(sql, {"kw": "%流量王%", "t": "A"})
    assert "%(kw)s" in rendered
    assert "%(t)s" in rendered
    assert "'%%已停用%%'" in rendered
    # 参数值本身不参与格式化，% 应原样保留在 args 中
    assert args == {"kw": "%流量王%", "t": "A"}
    escaped = {"kw": "'%流量王%'", "t": "'A'"}
    out = _simulate_pymysql(rendered, escaped)
    assert "LIKE '%流量王%'" in out
    assert "LIKE '%已停用%'" in out


def test_named_placeholder_not_escaped():
    # 生成的 %(name)s 不能被当作字面量 % 再次转义
    rendered, _ = to_pyformat("WHERE a = :x", {"x": 1})
    assert rendered == "WHERE a = %(x)s"


def test_pg_cast_not_treated_as_placeholder():
    # PG 的 ::int 类型转换不应被误改为占位符
    rendered, _ = to_pyformat("SELECT a::int FROM t WHERE b = :b", {"b": 1})
    assert "::int" in rendered
    assert "%(b)s" in rendered


def test_to_named_keeps_percent_untouched():
    # named 风格（oracledb）不做 % 转义，SQL 原样返回
    sql = "SELECT * FROM t WHERE name LIKE '%x%' AND id = :id"
    rendered, args = to_named(sql, {"id": 1})
    assert rendered == sql
    assert args == {"id": 1}
