from __future__ import annotations

import typer

from ..config.settings import load_settings
from ..ui.output import render_decision, render_execution_result, render_header
from ..ui.prompts import choose_candidate_action, confirm_execution, request_prompt_if_missing
from packages.core.mock_router import Candidate, build_decision

app = typer.Typer(help="Interactively choose and execute a routing decision.")


@app.callback(invoke_without_command=True)
def decide(
    prompt: str | None = typer.Argument(
        default=None,
        help="Prompt to evaluate for model routing.",
    )
) -> None:
    settings = load_settings()
    normalized_prompt = request_prompt_if_missing(prompt)
    decision = build_decision(normalized_prompt)

    render_header("Decision Preview")
    render_decision(decision=decision, max_alternatives=settings.max_alternatives)

    selected = choose_candidate_action(decision.recommended, decision.alternatives)
    if selected is None:
        render_execution_result(model_name=None, status="cancelled")
        raise typer.Exit(code=0)

    if not confirm_execution(selected.name, selected.provider):
        render_execution_result(model_name=selected.name, status="cancelled")
        raise typer.Exit(code=0)

    _simulate_execution(selected, normalized_prompt)


def _simulate_execution(candidate: Candidate, prompt: str) -> None:
    _ = prompt
    render_execution_result(model_name=candidate.name, status="running")
    render_execution_result(model_name=candidate.name, status="success")
