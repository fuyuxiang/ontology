"""GraphEngine 回归测试 — 覆盖拓扑排序/模板解析/上下文查找/条件路由/handler 分发等纯逻辑。

这些测试作为 graph_engine 模块拆分(上帝类 → mixin)前的行为锚点：
拆分是纯结构调整,这些断言在拆分前后必须保持一致。

用 __new__ 绕过 __init__(避免 get_llm_client/ToolRouter 的外部依赖),
手动注入测试所需的最小属性。
"""
from app.services.agent.graph_engine import GraphEngine


def _make_engine(nodes=None, edges=None):
    """构造一个不触发外部依赖的最小 GraphEngine 实例。"""
    eng = GraphEngine.__new__(GraphEngine)
    eng.nodes = {n["id"]: n for n in (nodes or [])}
    eng.edges = edges or []
    eng.node_io = {}
    return eng


# ── 拓扑排序 ──────────────────────────────────────────────

def test_topological_sort_linear():
    eng = _make_engine(
        nodes=[{"id": "a"}, {"id": "b"}, {"id": "c"}],
        edges=[{"source": "a", "target": "b"}, {"source": "b", "target": "c"}],
    )
    assert eng._topological_sort() == ["a", "b", "c"]


def test_topological_sort_diamond():
    # a → b,c → d
    eng = _make_engine(
        nodes=[{"id": "a"}, {"id": "b"}, {"id": "c"}, {"id": "d"}],
        edges=[
            {"source": "a", "target": "b"},
            {"source": "a", "target": "c"},
            {"source": "b", "target": "d"},
            {"source": "c", "target": "d"},
        ],
    )
    order = eng._topological_sort()
    # a 必须最先, d 必须最后, b/c 在中间
    assert order[0] == "a"
    assert order[-1] == "d"
    assert set(order) == {"a", "b", "c", "d"}


def test_topological_sort_ignores_unknown_edge_targets():
    eng = _make_engine(
        nodes=[{"id": "a"}, {"id": "b"}],
        edges=[{"source": "a", "target": "b"}, {"source": "a", "target": "ghost"}],
    )
    order = eng._topological_sort()
    assert order == ["a", "b"]


# ── 上下文查找 ────────────────────────────────────────────

def test_lookup_in_context_direct_key():
    eng = _make_engine()
    assert eng._lookup_in_context("score", {"score": 42}) == 42


def test_lookup_in_context_dotted_path():
    eng = _make_engine()
    ctx = {"node1": {"result": {"risk": "high"}}}
    assert eng._lookup_in_context("node1.result.risk", ctx) == "high"


def test_lookup_in_context_search_in_node_outputs():
    eng = _make_engine()
    ctx = {"node1": {"churn_rate": 0.3}}
    assert eng._lookup_in_context("churn_rate", ctx) == 0.3


def test_lookup_in_context_missing_returns_none():
    eng = _make_engine()
    assert eng._lookup_in_context("nope", {"a": 1}) is None
    assert eng._lookup_in_context("", {"a": 1}) is None


# ── 模板解析 ──────────────────────────────────────────────

def test_resolve_template_question_placeholder():
    eng = _make_engine()
    out = eng._resolve_template("问题是: {question}", {"question": "为什么退单"})
    assert out == "问题是: 为什么退单"


def test_resolve_template_node_value():
    eng = _make_engine()
    out = eng._resolve_template("结果: {n1}", {"n1": "已完成"})
    assert out == "结果: 已完成"


# ── handler 分发 ──────────────────────────────────────────

def test_execute_node_unknown_type_uses_default():
    eng = _make_engine()
    # 未知类型应路由到 _exec_default,不抛异常
    result, summary = eng._execute_node("totally-unknown-type", {}, {}, "q")
    assert isinstance(summary, str)


def test_execute_node_output_type():
    eng = _make_engine()
    # output 节点是纯逻辑,不依赖外部服务
    result, summary = eng._execute_node("output", {"text": "done"}, {}, "q")
    assert isinstance(summary, str)


# ── 条件分支跳过 ──────────────────────────────────────────

def test_skip_subtree_marks_descendants():
    eng = _make_engine(
        nodes=[{"id": "a"}, {"id": "b"}, {"id": "c"}],
        edges=[{"source": "b", "target": "c"}],
    )
    children = {"a": [], "b": ["c"], "c": []}
    skipped = set()
    eng._skip_subtree("b", children, skipped)
    assert "b" in skipped
    assert "c" in skipped

