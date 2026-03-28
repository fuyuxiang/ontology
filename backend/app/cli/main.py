"""
模块功能：
- 后端命令行入口，便于本地重建语义层和启动服务。
- 该文件位于 `backend/app/cli/main.py`，组装应用入口、生命周期和根路由，是后端服务启动时的首个加载点。
- 文件中对外暴露或复用的主要函数包括：`rebuild_all`, `run_inference`, `list_scenarios`, `activate_scenario`, `serve`。
"""

from __future__ import annotations

import json

import typer
import uvicorn

from app.config.settings import get_settings
from app.platform import PlatformContext
from app.services.semantic_service import SemanticService

cli = typer.Typer(help="Ontology semantic layer CLI.")


@cli.command("rebuild-all")
def rebuild_all() -> None:
    """
    功能：
    - 重建语义层并输出最新概览数据。

    输入：
    - 无。

    输出：
    - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
    """
    service = SemanticService(get_settings())
    typer.echo(json.dumps(service.get_summary(), ensure_ascii=False, indent=2))


@cli.command("run-inference")
def run_inference() -> None:
    """
    功能：
    - 只执行推理流程并输出结果统计。

    输入：
    - 无。

    输出：
    - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
    """
    service = SemanticService(get_settings())
    typer.echo(json.dumps(service.run_inference(), ensure_ascii=False, indent=2))


@cli.command("list-scenarios")
def list_scenarios() -> None:
    """
    功能：
    - 列出当前平台可加载的场景包。

    输入：
    - 无。

    输出：
    - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
    """
    context = PlatformContext()
    typer.echo(json.dumps(context.platform_summary(), ensure_ascii=False, indent=2))


@cli.command("activate-scenario")
def activate_scenario(scenario_key: str) -> None:
    """
    功能：
    - 激活指定场景包。

    输入：
    - `scenario_key`: 当前激活的场景配置对象。

    输出：
    - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
    """
    context = PlatformContext()
    typer.echo(json.dumps(context.activate_scenario(scenario_key), ensure_ascii=False, indent=2))


@cli.command("serve")
def serve(port: int | None = None) -> None:
    """
    功能：
    - 启动 FastAPI 服务。

    输入：
    - `port`: 函数执行所需的 `port` 参数。

    输出：
    - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
    """
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.host, port=port or settings.port, reload=False)
