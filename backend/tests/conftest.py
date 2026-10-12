"""Keep the entire suite off user databases, workspaces and external monitors."""
import os
import tempfile
from pathlib import Path

import pytest

TEST_ROOT = Path(tempfile.mkdtemp(prefix="ontology-pytest-"))
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_ROOT / 'metadata.db'}"
os.environ.setdefault("SECRET_KEY", "isolated-pytest-signing-key")
os.environ["WORKSPACE_ROOT"] = str(TEST_ROOT / "workspace")
os.environ["LOCAL_DATA_ROOT"] = str(TEST_ROOT / "sources")
os.environ["MONITOR_ENABLED"] = "false"
os.environ["DATA_PLANE_REFRESH_ENABLED"] = "false"
os.environ["LLM_API_KEY"] = "isolated-test-key"
os.environ["LLM_BASE_URL"] = "http://127.0.0.1:9/v1"
os.environ["LLM_MODEL"] = "isolated-model"


@pytest.fixture(scope="session", autouse=True)
def initialize_test_schema():
    import app.models  # noqa: F401
    from app.database import Base, engine
    from app.migrations import run_startup_migrations
    Base.metadata.create_all(engine)
    run_startup_migrations(engine)
    yield
    engine.dispose()
