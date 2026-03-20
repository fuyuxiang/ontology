from __future__ import annotations

import json

import typer
import uvicorn

from app.config.settings import get_settings
from app.services.semantic_service import SemanticService

cli = typer.Typer(help="Ontology semantic layer CLI.")


@cli.command("rebuild-all")
def rebuild_all() -> None:
    service = SemanticService(get_settings())
    typer.echo(json.dumps(service.get_summary(), ensure_ascii=False, indent=2))


@cli.command("run-inference")
def run_inference() -> None:
    service = SemanticService(get_settings())
    typer.echo(json.dumps(service.run_inference(), ensure_ascii=False, indent=2))


@cli.command("serve")
def serve(port: int | None = None) -> None:
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.host, port=port or settings.port, reload=False)

