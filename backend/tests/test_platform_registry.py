"""平台场景包注册测试。"""

from pathlib import Path

import pytest

from app.config.settings import get_settings
from app.platform import PlatformContext, PlatformRuntime
from app.scenario import discover_scenario_packages


def test_platform_discovers_scenario_packages():
    """平台应能从 scenarios 目录发现可加载场景包。"""
    settings = get_settings()
    packages = discover_scenario_packages(settings.project_dir, settings.scenarios_dir)

    assert settings.scenario_key in packages
    package = packages[settings.scenario_key]
    assert package.scenario_path.name == "telecom-porting.yaml"
    assert package.rules_path.name == "porting-risk.yaml"


def test_summary_uses_registry_scenario_key():
    """设置对象应暴露当前激活场景 Key。"""
    settings = get_settings()

    assert settings.scenario_key == "telecom_porting"
    assert settings.scenario_path == Path(settings.scenarios_dir / "telecom-porting.yaml").resolve()


def test_activate_scenario_does_not_persist_state_when_runtime_build_fails(monkeypatch: pytest.MonkeyPatch):
    """场景切换若在运行时构建阶段失败，不应提前写坏平台状态。"""
    context = PlatformContext()
    runtime = context.runtime
    assert runtime is not None

    save_calls: list[str] = []

    def fake_save_platform_state(*args, **kwargs):
        save_calls.append("called")
        raise AssertionError("save_platform_state should not be called before runtime build succeeds")

    def fake_build_runtime(self: PlatformContext, scenario_key: str | None = None) -> PlatformRuntime:
        if scenario_key is not None:
            raise RuntimeError("boom")
        assert runtime is not None
        return runtime

    monkeypatch.setattr("app.platform.save_platform_state", fake_save_platform_state)
    monkeypatch.setattr(PlatformContext, "_build_runtime", fake_build_runtime)

    with pytest.raises(RuntimeError, match="boom"):
        context.activate_scenario(runtime.settings.scenario_key)

    assert save_calls == []
    assert context.runtime is runtime
