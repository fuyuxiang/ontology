import pytest

from app.services.function_runtime.sandbox import UnifiedSandbox, ValidationResult


@pytest.fixture
def sandbox():
    return UnifiedSandbox()


class TestValidation:
    def test_clean_code_passes(self, sandbox):
        code = '''
def calc(params):
    return params["a"] + params["b"]
'''
        result = sandbox.validate(code)
        assert result.valid is True
        assert result.errors == []

    def test_import_os_rejected(self, sandbox):
        code = "import os\ndef f(params): return os.getcwd()"
        result = sandbox.validate(code)
        assert result.valid is False
        assert any("os" in e for e in result.errors)

    def test_import_from_subprocess_rejected(self, sandbox):
        code = "from subprocess import run\ndef f(params): return run(['ls'])"
        result = sandbox.validate(code)
        assert result.valid is False

    def test_dunder_import_rejected(self, sandbox):
        code = "def f(params): return __import__('os')"
        result = sandbox.validate(code)
        assert result.valid is False

    def test_open_call_rejected(self, sandbox):
        code = "def f(params): return open('/etc/passwd').read()"
        result = sandbox.validate(code)
        assert result.valid is False

    def test_eval_call_rejected(self, sandbox):
        code = "def f(params): return eval('1+1')"
        result = sandbox.validate(code)
        assert result.valid is False

    def test_allowed_import_json(self, sandbox):
        code = "import json\ndef f(params): return json.dumps(params)"
        result = sandbox.validate(code)
        assert result.valid is True

    def test_allowed_import_datetime(self, sandbox):
        code = "from datetime import datetime\ndef f(params): return str(datetime.now())"
        result = sandbox.validate(code)
        assert result.valid is True

    def test_syntax_error(self, sandbox):
        code = "def f(params)\n  return 1"
        result = sandbox.validate(code)
        assert result.valid is False

    def test_dunder_class_escape_rejected(self, sandbox):
        """Verify that __class__.__bases__.__subclasses__() sandbox escape is blocked."""
        code = '''
def exploit(params):
    return ().__class__.__bases__[0].__subclasses__()
'''
        result = sandbox.validate(code)
        assert result.valid is False
        assert any("__class__" in e or "__bases__" in e or "__subclasses__" in e for e in result.errors)

    def test_dunder_mro_rejected(self, sandbox):
        code = '''
def exploit(params):
    return "".__class__.__mro__[1]
'''
        result = sandbox.validate(code)
        assert result.valid is False

    def test_allowed_dunder_str_ok(self, sandbox):
        """Allowed dunders like __init__, __str__ should pass."""
        code = '''
def f(params):
    class Foo:
        def __init__(self):
            self.x = 1
        def __str__(self):
            return str(self.x)
    return str(Foo())
'''
        result = sandbox.validate(code)
        assert result.valid is True

    def test_dunder_globals_rejected(self, sandbox):
        code = '''
def exploit(params):
    return exploit.__globals__
'''
        result = sandbox.validate(code)
        assert result.valid is False
        assert any("__globals__" in e for e in result.errors)


class TestExecution:
    def test_simple_function(self, sandbox):
        code = '''
def add(params):
    return params["a"] + params["b"]
'''
        result = sandbox.execute(code, "add", {"params": {"a": 3, "b": 4}})
        assert result == 7

    def test_function_with_allowed_import(self, sandbox):
        code = '''
import json
def to_json(params):
    return json.dumps(params)
'''
        result = sandbox.execute(code, "to_json", {"params": {"x": 1}})
        assert result == '{"x": 1}'

    def test_namespace_injection(self, sandbox):
        code = '''
def my_func(params):
    return call_function("other", {"x": 1})
'''
        mock_call = lambda name, p: {"called": name, "params": p}
        ns = {"params": {}, "call_function": mock_call}
        result = sandbox.execute(code, "my_func", ns)
        assert result == {"called": "other", "params": {"x": 1}}

    def test_timeout(self, sandbox):
        code = '''
def slow(params):
    i = 0
    while True:
        i += 1
    return i
'''
        with pytest.raises(TimeoutError):
            sandbox.execute(code, "slow", {"params": {}}, timeout=1)

    def test_forbidden_builtin_at_runtime(self, sandbox):
        code = '''
def bad(params):
    return open("/etc/passwd")
'''
        with pytest.raises(Exception):
            sandbox.execute(code, "bad", {"params": {}})

    def test_function_not_found(self, sandbox):
        code = "def other(params): return 1"
        with pytest.raises(ValueError, match="not found"):
            sandbox.execute(code, "nonexistent", {"params": {}})
