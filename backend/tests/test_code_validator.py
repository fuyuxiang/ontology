import pytest

from app.services.code_validator import ValidationResult, validate_code


class TestCodeValidator:
    def test_safe_code_passes(self):
        code = "result = params['amount'] * 1.1"
        r = validate_code(code)
        assert r.safe is True
        assert r.violations == []

    def test_allowed_import_passes(self):
        code = "import math\nresult = math.sqrt(params['x'])"
        r = validate_code(code)
        assert r.safe is True

    def test_forbidden_import_os(self):
        code = "import os\nresult = os.listdir('/')"
        r = validate_code(code)
        assert r.safe is False
        assert any("os" in v.reason for v in r.violations)

    def test_forbidden_import_subprocess(self):
        code = "import subprocess\nresult = subprocess.run(['ls'])"
        r = validate_code(code)
        assert r.safe is False

    def test_forbidden_open(self):
        code = "f = open('/etc/passwd')\nresult = f.read()"
        r = validate_code(code)
        assert r.safe is False
        assert any("open" in v.reason for v in r.violations)

    def test_forbidden_eval(self):
        code = "result = eval('1+1')"
        r = validate_code(code)
        assert r.safe is False

    def test_forbidden_exec(self):
        code = "exec('print(1)')\nresult = None"
        r = validate_code(code)
        assert r.safe is False

    def test_forbidden_dunder_import(self):
        code = "os = __import__('os')\nresult = os.getcwd()"
        r = validate_code(code)
        assert r.safe is False

    def test_syntax_error(self):
        code = "def foo(\nresult = 1"
        r = validate_code(code)
        assert r.safe is False
        assert any("syntax" in v.reason.lower() for v in r.violations)

    def test_allowed_multiple_imports(self):
        code = "import math\nimport json\nimport re\nresult = math.pi"
        r = validate_code(code)
        assert r.safe is True

    def test_from_import_forbidden(self):
        code = "from os.path import join\nresult = join('a', 'b')"
        r = validate_code(code)
        assert r.safe is False
