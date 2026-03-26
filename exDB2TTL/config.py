"""exDB2TTL 配置模型与项目配置加载逻辑。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """配置解析或校验失败时抛出的异常。"""

    pass


@dataclass(frozen=True)
class DatabaseConfig:
    """数据库或样例 CSV 的连接/抽取配置。"""

    dialect: str
    database_name: str
    tables: list[str]
    sqlite_path: str | None = None
    sample_csv_dir: str | None = None
    sample_csv_encoding: str = "utf-8"
    connection_url: str | None = None
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password_env: str | None = None
    schema: str | None = None
    mysql_charset: str = "utf8mb4"
    sample_rows: int = 5


@dataclass(frozen=True)
class LLMConfig:
    """模型调用配置。"""

    base_url: str
    model: str
    api_key_env: str
    temperature: float = 0.1
    timeout_seconds: int = 120
    use_json_mode: bool = True
    extra_headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class OntologyConfig:
    """目标本体命名空间配置。"""

    ontology_namespace: str
    data_namespace: str


@dataclass(frozen=True)
class BackendSyncConfig:
    """生成结果同步到后端工程的配置。"""

    enabled: bool = True
    backend_project_dir: str = "backend"
    activate_profile: bool = True


@dataclass(frozen=True)
class OutputConfig:
    """输出目录配置。"""

    directory: str


@dataclass(frozen=True)
class ProjectConfig:
    """exDB2TTL 项目的完整配置集合。"""

    database: DatabaseConfig
    llm: LLMConfig
    ontology: OntologyConfig
    backend_sync: BackendSyncConfig
    output: OutputConfig
    business_context: dict[str, Any] = field(default_factory=dict)

    @property
    def output_dir(self) -> Path:
        """把输出目录字符串转换为 `Path` 对象。"""
        return Path(self.output.directory)


def _expect_string_list(payload: Any, key: str) -> list[str]:
    """校验非空字符串列表配置。"""
    if not isinstance(payload, list) or not all(isinstance(item, str) and item.strip() for item in payload):
        raise ConfigError(f"{key} must be a non-empty list of strings")
    return [item.strip() for item in payload]


def load_project_config(path: str | Path) -> ProjectConfig:
    """从 JSON 文件加载并校验项目配置。"""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    database_raw = raw.get("database") or {}
    llm_raw = raw.get("llm") or {}
    ontology_raw = raw.get("ontology") or {}
    backend_sync_raw = raw.get("backend_sync") or {}
    output_raw = raw.get("output") or {}

    database = DatabaseConfig(
        dialect=str(database_raw.get("dialect", "")).strip().lower(),
        database_name=str(database_raw.get("database_name", "")).strip(),
        tables=_expect_string_list(database_raw.get("tables"), "database.tables"),
        sqlite_path=_nullable_string(database_raw.get("sqlite_path")),
        sample_csv_dir=_nullable_string(database_raw.get("sample_csv_dir")),
        sample_csv_encoding=str(database_raw.get("sample_csv_encoding", "utf-8")).strip() or "utf-8",
        connection_url=_nullable_string(database_raw.get("connection_url")),
        host=_nullable_string(database_raw.get("host")),
        port=_nullable_int(database_raw.get("port")),
        username=_nullable_string(database_raw.get("username")),
        password_env=_nullable_string(database_raw.get("password_env")),
        schema=_nullable_string(database_raw.get("schema")),
        mysql_charset=str(database_raw.get("mysql_charset", "utf8mb4")).strip() or "utf8mb4",
        sample_rows=int(database_raw.get("sample_rows", 5)),
    )
    if not database.dialect:
        raise ConfigError("database.dialect is required")
    if not database.database_name:
        raise ConfigError("database.database_name is required")

    llm = LLMConfig(
        base_url=str(llm_raw.get("base_url", "")).rstrip("/"),
        model=str(llm_raw.get("model", "")).strip(),
        api_key_env=str(llm_raw.get("api_key_env", "")).strip(),
        temperature=float(llm_raw.get("temperature", 0.1)),
        timeout_seconds=int(llm_raw.get("timeout_seconds", 120)),
        use_json_mode=bool(llm_raw.get("use_json_mode", True)),
        extra_headers={str(k): str(v) for k, v in (llm_raw.get("extra_headers") or {}).items()},
    )
    if not llm.base_url:
        raise ConfigError("llm.base_url is required")
    if not llm.model:
        raise ConfigError("llm.model is required")
    if not llm.api_key_env:
        raise ConfigError("llm.api_key_env is required")

    ontology = OntologyConfig(
        ontology_namespace=str(ontology_raw.get("ontology_namespace", "")).strip(),
        data_namespace=str(ontology_raw.get("data_namespace", "")).strip(),
    )
    if not ontology.ontology_namespace or not ontology.data_namespace:
        raise ConfigError("ontology.ontology_namespace and ontology.data_namespace are required")

    output = OutputConfig(directory=str(output_raw.get("directory", "exDB2TTL/out")).strip())
    if not output.directory:
        raise ConfigError("output.directory is required")

    backend_sync = BackendSyncConfig(
        enabled=bool(backend_sync_raw.get("enabled", True)),
        backend_project_dir=str(backend_sync_raw.get("backend_project_dir", "backend")).strip() or "backend",
        activate_profile=bool(backend_sync_raw.get("activate_profile", True)),
    )

    return ProjectConfig(
        database=database,
        llm=llm,
        ontology=ontology,
        backend_sync=backend_sync,
        output=output,
        business_context=raw.get("business_context") or {},
    )


def create_bootstrap_config(database_name: str, tables: list[str], dialect: str, output_dir: str) -> dict[str, Any]:
    """生成一个可直接手工补全的初始化配置模板。"""
    return {
        "database": {
            "dialect": dialect,
            "database_name": database_name,
            "tables": tables,
            "sqlite_path": "CHANGE_ME_IF_SQLITE.db",
            "sample_csv_dir": "exDB2TTL/sample-csv",
            "sample_csv_encoding": "utf-8",
            "connection_url": "",
            "host": "",
            "port": None,
            "username": "",
            "password_env": "DB_PASSWORD",
            "schema": "public" if dialect == "postgresql" else None,
            "mysql_charset": "utf8mb4",
            "sample_rows": 5,
        },
        "llm": {
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4.1-mini",
            "api_key_env": "OPENAI_API_KEY",
            "temperature": 0.1,
            "timeout_seconds": 120,
            "use_json_mode": True,
            "extra_headers": {},
        },
        "ontology": {
            "ontology_namespace": "http://example.com/telecom#",
            "data_namespace": "http://example.com/telecom/data/",
        },
        "backend_sync": {
            "enabled": True,
            "backend_project_dir": "backend",
            "activate_profile": True,
        },
        "business_context": {
            "scenario": "从关系数据库自动生成可接入当前 telecom backend 的本体、SHACL 和规则 YAML",
            "goal": "识别核心实体、关系、字段约束和候选业务规则，并产出 backend 可直接加载的文件集",
            "notes": [
                "如果当前只有数据库名和表名，请先补充连接信息，再运行 extract/run。",
                "如果暂时无法直连数据库，可让 DBA 导出字段元数据和样例数据，再替换 metadata.json。",
                "当前 backend 仍然是电信场景实现，优先复用现有 telecom 词表和规则格式。",
            ],
        },
        "output": {
            "directory": output_dir,
        },
    }


def _nullable_string(value: Any) -> str | None:
    """把空字符串归一为 `None`。"""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _nullable_int(value: Any) -> int | None:
    """把可空整数字段转换为 `int | None`。"""
    if value in (None, "", "null"):
        return None
    return int(value)
