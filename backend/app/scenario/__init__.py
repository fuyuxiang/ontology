"""
模块功能：
- 场景配置对外导出模块。
- 该文件位于 `backend/app/scenario/__init__.py`，对外导出当前包的公共能力，便于上层模块以稳定接口进行导入。
"""

from .config import (
    AlertDisplayField,
    DatasetConfig,
    FactConfig,
    OntologyFileConfig,
    RelationConfig,
    RuleCardConfig,
    ScenarioConfig,
    SortConfig,
    SourceCardConfig,
    load_scenario_config,
)
from .registry import (
    PLATFORM_STATE_PATH,
    ScenarioPackage,
    discover_scenario_packages,
    load_platform_state,
    resolve_active_scenario_key,
    save_platform_state,
)

__all__ = [
    "AlertDisplayField",
    "DatasetConfig",
    "FactConfig",
    "OntologyFileConfig",
    "RelationConfig",
    "RuleCardConfig",
    "ScenarioConfig",
    "ScenarioPackage",
    "SortConfig",
    "SourceCardConfig",
    "PLATFORM_STATE_PATH",
    "discover_scenario_packages",
    "load_scenario_config",
    "load_platform_state",
    "resolve_active_scenario_key",
    "save_platform_state",
]
