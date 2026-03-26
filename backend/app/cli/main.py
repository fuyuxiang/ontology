"""后端命令行入口，便于本地重建语义层和启动服务。"""

from __future__ import annotations

import json

import typer
import uvicorn

from app.config.settings import get_settings
from app.services.semantic_service import SemanticService

cli = typer.Typer(help="Ontology semantic layer CLI.")


@cli.command("rebuild-all")
def rebuild_all() -> None:
    """重建语义层并输出最新概览数据。"""
    service = SemanticService(get_settings())
    typer.echo(json.dumps(service.get_summary(), ensure_ascii=False, indent=2))


@cli.command("run-inference")
def run_inference() -> None:
    """只执行推理流程并输出结果统计。"""
    service = SemanticService(get_settings())
    typer.echo(json.dumps(service.run_inference(), ensure_ascii=False, indent=2))


@cli.command("serve")
def serve(port: int | None = None) -> None:
    """启动 FastAPI 服务。"""
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.host, port=port or settings.port, reload=False)
