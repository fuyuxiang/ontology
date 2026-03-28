"""
模块功能：
- 平台上下文，管理场景包注册、激活与共享服务实例。
- 该文件位于 `backend/app/platform.py`，负责平台级运行时装配、场景切换以及服务与 agent 的统一上下文管理。
- 文件中定义的核心类包括：`PlatformRuntime`, `PlatformContext`。
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any

from app.agent import SupervisorAgentService
from app.config.settings import Settings, get_settings
from app.scenario import (
    ScenarioPackage,
    discover_scenario_packages,
    resolve_active_scenario_key,
    save_platform_state,
)
from app.services.semantic_service import SemanticService


@dataclass(frozen=True)
class PlatformRuntime:
    """
    功能：
    - 当前激活场景对应的一组后端运行时对象。
    - 该类定义在 `backend/app/platform.py` 中，用于组织与 `PlatformRuntime` 相关的数据或行为。
    - 类中声明的主要字段包括：`settings`, `scenarios`, `service`, `agent`。
    """

    settings: Settings
    scenarios: dict[str, ScenarioPackage]
    service: SemanticService
    agent: SupervisorAgentService


class PlatformContext:
    """
    功能：
    - 维护当前激活场景及其对应的服务实例。
    - 该类定义在 `backend/app/platform.py` 中，用于组织与 `PlatformContext` 相关的数据或行为。
    """

    def __init__(self) -> None:
        """
        功能：
        - 初始化当前对象并准备后续调用所需的依赖、状态和缓存。

        输入：
        - 无。

        输出：
        - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
        """
        self.lock = RLock()
        self.runtime: PlatformRuntime | None = None
        self.reload()

    def reload(self) -> None:
        """
        功能：
        - 重新装载平台当前上下文。

        输入：
        - 无。

        输出：
        - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
        """
        with self.lock:
            self.runtime = self._build_runtime()

    def activate_scenario(self, scenario_key: str) -> dict[str, Any]:
        """
        功能：
        - 激活指定场景并热切换平台上下文。

        输入：
        - `scenario_key`: 当前激活的场景配置对象。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        with self.lock:
            runtime = self._require_runtime()
            project_dir = runtime.settings.project_dir
            packages = discover_scenario_packages(project_dir, runtime.settings.scenarios_dir)
            if scenario_key not in packages:
                raise ValueError(f"unknown_scenario:{scenario_key}")
            next_runtime = self._build_runtime(scenario_key)
            save_platform_state(project_dir, scenario_key)
            self.runtime = next_runtime
            return self.platform_summary()

    def platform_summary(self) -> dict[str, Any]:
        """
        功能：
        - 返回平台层概览。

        输入：
        - 无。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        with self.lock:
            runtime = self._require_runtime()
            active_key = runtime.settings.scenario_key
            active_package = runtime.scenarios[active_key]
            return {
                "activeScenarioKey": active_key,
                "activeScenarioName": active_package.name,
                "scenarioCount": len(runtime.scenarios),
                "statePath": str(runtime.settings.platform_state_path),
                "scenarios": [
                    package.to_summary(active_key)
                    for package in runtime.scenarios.values()
                ],
                "capabilities": [
                    "scenario-packages",
                    "ontology-runtime",
                    "rule-engine",
                    "runtime-workbench",
                    "tool-catalog",
                    "supervised-agent",
                ],
            }

    def service(self) -> SemanticService:
        """
        功能：
        - 处理与 `service` 相关的逻辑。

        输入：
        - 无。

        输出：
        - 返回值: 返回 `SemanticService` 类型结果，供后续流程继续消费。
        """
        with self.lock:
            return self._require_runtime().service

    def agent(self) -> SupervisorAgentService:
        """
        功能：
        - 处理与 `agent` 相关的逻辑。

        输入：
        - 无。

        输出：
        - 返回值: 返回 `SupervisorAgentService` 类型结果，供后续流程继续消费。
        """
        with self.lock:
            return self._require_runtime().agent

    def list_scenarios(self) -> list[dict[str, object]]:
        """
        功能：
        - 列出可用场景包。

        输入：
        - 无。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        with self.lock:
            runtime = self._require_runtime()
            active_key = resolve_active_scenario_key(runtime.settings.project_dir, runtime.scenarios)
            return [package.to_summary(active_key) for package in runtime.scenarios.values()]

    def _build_runtime(self, scenario_key: str | None = None) -> PlatformRuntime:
        """
        功能：
        - 构建runtime。

        输入：
        - `scenario_key`: 当前激活的场景配置对象。

        输出：
        - 返回值: 返回 `PlatformRuntime` 类型结果，供后续流程继续消费。
        """
        settings = get_settings(active_scenario_key_override=scenario_key)
        service = SemanticService(settings)
        return PlatformRuntime(
            settings=settings,
            scenarios=discover_scenario_packages(settings.project_dir, settings.scenarios_dir),
            service=service,
            agent=SupervisorAgentService(service),
        )

    def _require_runtime(self) -> PlatformRuntime:
        """
        功能：
        - 处理与 `_require_runtime` 相关的逻辑。

        输入：
        - 无。

        输出：
        - 返回值: 返回 `PlatformRuntime` 类型结果，供后续流程继续消费。
        """
        if self.runtime is None:
            raise RuntimeError("platform_runtime_not_initialized")
        return self.runtime
