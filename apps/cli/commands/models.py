from __future__ import annotations

import typer

from ..ui.output import render_header, render_models
from packages.core.mock_router import list_available_models

app = typer.Typer(help="List mock models available for routing.")


@app.callback(invoke_without_command=True)
def models() -> None:
    render_header("Model Catalog")
    render_models(list_available_models())
