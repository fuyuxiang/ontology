"""
模块功能：
- 项目运行时配置加载器，统一解析环境变量、默认值和生成配置。
- 该文件位于 `backend/app/config/settings.py`，集中解析环境变量、场景包和路径配置，生成后端运行时依赖的统一设置对象。
- 文件中定义的核心类包括：`Settings`。
- 文件中对外暴露或复用的主要函数包括：`get_settings`, `_resolve_scenario_paths`, `_load_active_profile`, `_resolve_path`, `_build_default_query`, `_env_flag`, `_env_text`。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.scenario import discover_scenario_packages, resolve_active_scenario_key

ACTIVE_PROFILE_PATH = Path("runtime/generated-profile/active-profile.json")
DEFAULT_DOIM_NS = "http://purl.org/doim/1.0#"
DEFAULT_TELECOM_NS = "http://example.com/telecom#"
DEFAULT_DATA_NS = "http://example.com/telecom/data/"
SCENARIO_PATH_OVERRIDES: dict[str, tuple[str, str, str]] = {
    "data_dir": ("ONTOLOGY_DATA_DIR", "data_dir", "data_dir"),
    "mapping_path": ("ONTOLOGY_MAPPING_PATH", "mapping_path", "mapping_path"),
    "ontology_core_path": ("ONTOLOGY_CORE_PATH", "ontology_core_path", "ontology_core_path"),
    "ontology_domain_path": ("ONTOLOGY_DOMAIN_PATH", "ontology_domain_path", "ontology_domain_path"),
    "ontology_shapes_path": ("ONTOLOGY_SHAPES_PATH", "ontology_shapes_path", "ontology_shapes_path"),
    "rules_path": ("ONTOLOGY_RULES_PATH", "rules_path", "rules_path"),
    "scenario_path": ("ONTOLOGY_SCENARIO_PATH", "scenario_path", "scenario_path"),
}


@dataclass(frozen=True)
class Settings:
    """
    功能：
    - 集中保存后端运行所需的路径、命名空间和服务参数。
    - 该类定义在 `backend/app/config/settings.py` 中，用于组织与 `Settings` 相关的数据或行为。
    - 类中声明的主要字段包括：`project_dir`, `scenario_key`, `data_dir`, `mappings_dir`, `mapping_path`, `ontology_dir`, `rules_dir`, `scenarios_dir`, `runtime_dir`, `runtime_state_path`, `platform_state_path`, `ontology_governance_state_path`, `store_dir`, `reports_dir`, `ontology_core_path`, `ontology_domain_path`, `ontology_shapes_path`, `rules_path`, `scenario_path`, `host`, `port`, `doim_ns`, `telecom_ns`, `data_ns`, `base_graph_uri`, `deductions_graph_uri`, `default_query`, `runtime_persistence_enabled`, `llm_base_url`, `llm_api_key`, `llm_model`, `llm_timeout_seconds`。
    """

    project_dir: Path
    scenario_key: str
    data_dir: Path
    mappings_dir: Path
    mapping_path: Path
    ontology_dir: Path
    rules_dir: Path
    scenarios_dir: Path
    runtime_dir: Path
    runtime_state_path: Path
    platform_state_path: Path
    ontology_governance_state_path: Path
    store_dir: Path
    reports_dir: Path
    ontology_core_path: Path
    ontology_domain_path: Path
    ontology_shapes_path: Path
    rules_path: Path
    scenario_path: Path
    host: str
    port: int
    doim_ns: str
    telecom_ns: str
    data_ns: str
    base_graph_uri: str
    deductions_graph_uri: str
    default_query: str
    runtime_persistence_enabled: bool
    llm_base_url: str | None
    llm_api_key: str | None
    llm_model: str | None
    llm_timeout_seconds: float


def get_settings(active_scenario_key_override: str | None = None) -> Settings:
    """
    功能：
    - 构建当前后端使用的完整配置对象。

    输入：
    - `active_scenario_key_override`: 函数执行所需的 `active_scenario_key_override` 参数。

    输出：
    - 返回值: 返回 `Settings` 类型结果，供后续流程继续消费。
    """
    project_dir = Path(__file__).resolve().parents[2]
    ontology_dir = project_dir / "ontology"
    rules_dir = project_dir / "rules"
    scenarios_dir = project_dir / "scenarios"
    scenario_packages = discover_scenario_packages(project_dir, scenarios_dir)
    active_scenario_key = active_scenario_key_override or resolve_active_scenario_key(project_dir, scenario_packages)
    if active_scenario_key not in scenario_packages:
        raise ValueError(f"Unknown active scenario: {active_scenario_key}")
    active_package = scenario_packages[active_scenario_key]
    profile = _load_active_profile(project_dir)
    resolved_paths = _resolve_scenario_paths(project_dir, profile, active_package)

    doim_ns = os.getenv("ONTOLOGY_DOIM_NS", str(profile.get("doim_ns") or DEFAULT_DOIM_NS))
    telecom_ns = os.getenv("ONTOLOGY_TELECOM_NS", str(profile.get("telecom_ns") or DEFAULT_TELECOM_NS))
    data_ns = os.getenv("ONTOLOGY_DATA_NS", str(profile.get("data_ns") or DEFAULT_DATA_NS))

    return Settings(
        project_dir=project_dir,
        scenario_key=active_scenario_key,
        data_dir=resolved_paths["data_dir"],
        mappings_dir=project_dir / "mappings",
        mapping_path=resolved_paths["mapping_path"],
        ontology_dir=ontology_dir,
        rules_dir=rules_dir,
        scenarios_dir=scenarios_dir,
        runtime_dir=project_dir / "runtime",
        runtime_state_path=project_dir / "runtime" / "operations-state.json",
        platform_state_path=project_dir / "runtime" / "platform-state.json",
        ontology_governance_state_path=project_dir / "runtime" / "ontology-governance-state.json",
        store_dir=project_dir / "runtime" / "store",
        reports_dir=project_dir / "runtime" / "reports",
        ontology_core_path=resolved_paths["ontology_core_path"],
        ontology_domain_path=resolved_paths["ontology_domain_path"],
        ontology_shapes_path=resolved_paths["ontology_shapes_path"],
        rules_path=resolved_paths["rules_path"],
        scenario_path=resolved_paths["scenario_path"],
        host=os.getenv("ONTOLOGY_HOST", "127.0.0.1"),
        port=int(os.getenv("ONTOLOGY_PORT", "8088")),
        doim_ns=doim_ns,
        telecom_ns=telecom_ns,
        data_ns=data_ns,
        base_graph_uri="urn:doim:poc:base",
        deductions_graph_uri="urn:doim:poc:deductions",
        default_query=_build_default_query(doim_ns, telecom_ns),
        runtime_persistence_enabled=_env_flag(
            "ONTOLOGY_RUNTIME_PERSIST",
            "PYTEST_CURRENT_TEST" not in os.environ,
        ),
        llm_base_url=_env_text("LLM_BASE_URL"),
        llm_api_key=_env_text("LLM_API_KEY"),
        llm_model=_env_text("LLM_MODEL"),
        llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
    )


def _resolve_scenario_paths(project_dir: Path, profile: dict[str, Any], active_package: Any) -> dict[str, Path]:
    """
    功能：
    - 批量解析当前场景涉及的路径，避免在设置构造时重复写同一套优先级规则。

    输入：
    - `project_dir`: 项目根目录路径，用于解析配置、场景包和运行时文件。
    - `profile`: 字典参数 `profile`，承载键值形式的输入数据。
    - `active_package`: 函数执行所需的 `active_package` 参数。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
    return {
        field_name: _resolve_path(
            project_dir,
            os.getenv(env_name),
            profile.get(profile_key),
            getattr(active_package, package_attr),
        )
        for field_name, (env_name, profile_key, package_attr) in SCENARIO_PATH_OVERRIDES.items()
    }


def _load_active_profile(project_dir: Path) -> dict[str, Any]:
    """
    功能：
    - 读取当前激活的生成档案，用于覆盖默认本体与规则路径。

    输入：
    - `project_dir`: 项目根目录路径，用于解析配置、场景包和运行时文件。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
    if os.getenv("ONTOLOGY_IGNORE_ACTIVE_PROFILE", "").strip().lower() in {"1", "true", "yes"}:
        return {}
    path = project_dir / ACTIVE_PROFILE_PATH
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _resolve_path(project_dir: Path, env_value: str | None, profile_value: Any, default: Path) -> Path:
    """
    功能：
    - 按 环境变量 > 激活档案 > 默认值 的优先级解析路径。

    输入：
    - `project_dir`: 项目根目录路径，用于解析配置、场景包和运行时文件。
    - `env_value`: 函数执行所需的 `env_value` 参数。
    - `profile_value`: 函数执行所需的 `profile_value` 参数。
    - `default`: 无法解析时使用的默认值。

    输出：
    - 返回值: 返回解析后的路径对象。
    """
    raw = env_value or (str(profile_value).strip() if profile_value else "")
    if not raw:
        return default
    path = Path(raw)
    if path.is_absolute():
        return path
    return (project_dir / path).resolve()


def _build_default_query(doim_ns: str, telecom_ns: str) -> str:
    """
    功能：
    - 生成前端默认展示的 SPARQL 示例查询。

    输入：
    - `doim_ns`: DOIM 命名空间字符串。
    - `telecom_ns`: 领域本体命名空间字符串。

    输出：
    - 返回值: 返回字符串结果，供调用方继续展示、拼接或查询。
    """
    return f"""PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX doim: <{doim_ns}>
PREFIX telecom: <{telecom_ns}>
SELECT ?userId ?deviceNumber ?riskLevel ?areaId
WHERE {{
  ?s a telecom:User ;
     telecom:userId ?userId ;
     telecom:deviceNumber ?deviceNumber ;
     telecom:inferredRiskLevel ?riskLevel .
  OPTIONAL {{ ?s telecom:areaId ?areaId }}
}}
ORDER BY DESC(?riskLevel) ?userId
"""


def _env_flag(name: str, default: bool) -> bool:
    """
    功能：
    - 解析布尔环境变量，兼容常见真值和假值文本。

    输入：
    - `name`: 名称、字段名或标识名。
    - `default`: 无法解析时使用的默认值。

    输出：
    - 返回值: 返回布尔值，表示条件是否成立或当前操作是否允许。
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _env_text(name: str) -> str | None:
    """
    功能：
    - 读取字符串环境变量，空串按未配置处理。

    输入：
    - `name`: 名称、字段名或标识名。

    输出：
    - 返回值: 返回处理结果；当目标不存在、未命中或无法解析时返回 `None`。
    """
    raw = os.getenv(name)
    if raw is None:
        return None
    value = raw.strip()
    return value or None
