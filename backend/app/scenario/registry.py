"""
模块功能：
- 场景包注册、发现与激活。
- 该文件位于 `backend/app/scenario/registry.py`，负责发现、解析和持久化场景包注册信息，支撑平台多场景切换。
- 文件中定义的核心类包括：`ScenarioPackage`。
- 文件中对外暴露或复用的主要函数包括：`discover_scenario_packages`, `resolve_active_scenario_key`, `load_platform_state`, `save_platform_state`, `_resolve_package_path`。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import yaml


PLATFORM_STATE_PATH = Path("runtime/platform-state.json")


@dataclass(frozen=True)
class ScenarioPackage:
    """
    功能：
    - 描述一个可被平台加载的场景包。
    - 该类定义在 `backend/app/scenario/registry.py` 中，用于组织与 `ScenarioPackage` 相关的数据或行为。
    - 类中声明的主要字段包括：`key`, `name`, `scenario_path`, `version`, `description`, `data_dir`, `mapping_path`, `ontology_core_path`, `ontology_domain_path`, `ontology_shapes_path`, `rules_path`。
    """

    key: str
    name: str
    scenario_path: Path
    version: str
    description: str
    data_dir: Path
    mapping_path: Path
    ontology_core_path: Path
    ontology_domain_path: Path
    ontology_shapes_path: Path
    rules_path: Path

    def to_summary(self, active_key: str) -> dict[str, object]:
        """
        功能：
        - 处理与 `to_summary` 相关的逻辑。

        输入：
        - `active_key`: 函数执行所需的 `active_key` 参数。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        return {
            "key": self.key,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "scenarioPath": str(self.scenario_path),
            "dataDir": str(self.data_dir),
            "mappingPath": str(self.mapping_path),
            "ontologyCorePath": str(self.ontology_core_path),
            "ontologyDomainPath": str(self.ontology_domain_path),
            "ontologyShapesPath": str(self.ontology_shapes_path),
            "rulesPath": str(self.rules_path),
            "active": self.key == active_key,
        }


def discover_scenario_packages(project_dir: Path, scenarios_dir: Path) -> dict[str, ScenarioPackage]:
    """
    功能：
    - 扫描场景目录并构建可加载的场景包清单。

    输入：
    - `project_dir`: 项目根目录路径，用于解析配置、场景包和运行时文件。
    - `scenarios_dir`: 场景包所在目录路径。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
    packages: dict[str, ScenarioPackage] = {}
    if not scenarios_dir.exists():
        return packages

    for path in sorted(scenarios_dir.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            continue
        scenario_raw = raw.get("scenario") or {}
        if not isinstance(scenario_raw, dict) or not scenario_raw.get("key"):
            continue
        platform_raw = raw.get("platform") or {}
        if not isinstance(platform_raw, dict):
            platform_raw = {}

        key = str(scenario_raw["key"])
        packages[key] = ScenarioPackage(
            key=key,
            name=str(scenario_raw.get("name") or key),
            scenario_path=path.resolve(),
            version=str(platform_raw.get("version") or "1.0.0"),
            description=str(platform_raw.get("description") or scenario_raw.get("dashboard_subtitle") or ""),
            data_dir=_resolve_package_path(project_dir, platform_raw.get("data_dir"), Path("data/raw")),
            mapping_path=_resolve_package_path(project_dir, platform_raw.get("mapping_path"), Path("mappings/doim_mapping.csv")),
            ontology_core_path=_resolve_package_path(project_dir, platform_raw.get("ontology_core_path"), Path("ontology/doim-core.ttl")),
            ontology_domain_path=_resolve_package_path(project_dir, platform_raw.get("ontology_domain_path"), Path("ontology/telecom-porting.ttl")),
            ontology_shapes_path=_resolve_package_path(project_dir, platform_raw.get("ontology_shapes_path"), Path("ontology/telecom-shapes.ttl")),
            rules_path=_resolve_package_path(project_dir, platform_raw.get("rules_path"), Path("rules/porting-risk.yaml")),
        )
    return packages


def resolve_active_scenario_key(project_dir: Path, packages: dict[str, ScenarioPackage]) -> str:
    """
    功能：
    - 按环境变量、平台状态、默认值解析当前激活场景。

    输入：
    - `project_dir`: 项目根目录路径，用于解析配置、场景包和运行时文件。
    - `packages`: 字典参数 `packages`，承载键值形式的输入数据。

    输出：
    - 返回值: 返回字符串结果，供调用方继续展示、拼接或查询。
    """
    preferred = os.getenv("ONTOLOGY_ACTIVE_SCENARIO", "").strip()
    if preferred:
        if preferred not in packages:
            raise ValueError(f"Unknown active scenario: {preferred}")
        return preferred

    state = load_platform_state(project_dir)
    active_key = str(state.get("activeScenarioKey") or "").strip()
    if active_key and active_key in packages:
        return active_key

    if packages:
        return next(iter(packages))
    raise RuntimeError("No scenario packages found under scenarios directory")


def load_platform_state(project_dir: Path) -> dict[str, object]:
    """
    功能：
    - 读取平台运行时状态。

    输入：
    - `project_dir`: 项目根目录路径，用于解析配置、场景包和运行时文件。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
    path = project_dir / PLATFORM_STATE_PATH
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def save_platform_state(project_dir: Path, active_scenario_key: str) -> Path:
    """
    功能：
    - 持久化当前激活场景。

    输入：
    - `project_dir`: 项目根目录路径，用于解析配置、场景包和运行时文件。
    - `active_scenario_key`: 函数执行所需的 `active_scenario_key` 参数。

    输出：
    - 返回值: 返回解析后的路径对象。
    """
    path = project_dir / PLATFORM_STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"activeScenarioKey": active_scenario_key}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def _resolve_package_path(project_dir: Path, raw_path: object, default: Path) -> Path:
    """
    功能：
    - 解析并返回package路径。

    输入：
    - `project_dir`: 项目根目录路径，用于解析配置、场景包和运行时文件。
    - `raw_path`: 尚未校验或转换的原始配置值。
    - `default`: 无法解析时使用的默认值。

    输出：
    - 返回值: 返回解析后的路径对象。
    """
    value = str(raw_path).strip() if raw_path else ""
    target = Path(value) if value else default
    if target.is_absolute():
        return target
    return (project_dir / target).resolve()
