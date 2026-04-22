from __future__ import annotations

import typer

from ..config.settings import load_settings
from ..ui.output import render_decision, render_header
from ..ui.prompts import request_prompt_if_missing
from packages.core.mock_router import build_decision

app = typer.Typer(help="Build and display a routing decision.")


@app.callback(invoke_without_command=True)
def route(
    prompt: str | None = typer.Argument(
        default=None,
        help="Prompt to evaluate for model routing.",
    )
) -> None:
    settings = load_settings()
    normalized_prompt = request_prompt_if_missing(prompt)
    decision = build_decision(normalized_prompt)

    render_header("Route Decision")
    render_decision(decision=decision, max_alternatives=settings.max_alternatives)
