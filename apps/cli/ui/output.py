from __future__ import annotations

from typing import Literal

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from packages.core.mock_router import Candidate, Decision

console = Console()


def render_header(title: str) -> None:
    console.print()
    console.print(
        Panel.fit(
            Text(f"llm-router | {title}", style="bold cyan"),
            border_style="cyan",
        )
    )


def render_decision(decision: Decision, max_alternatives: int) -> None:
    recommended = decision.recommended
    console.print(
        Panel(
            f"[bold]Prompt[/bold]\n{decision.prompt}\n\n"
            f"[bold]Recommended model:[/bold] {recommended.name}\n"
            f"[bold]Provider:[/bold] {recommended.provider}\n"
            f"[bold]Score:[/bold] {recommended.score:.3f}",
            title="Decision Summary",
            border_style="green",
        )
    )

    reasons_table = Table(title="Why this model", header_style="bold magenta")
    reasons_table.add_column("#", justify="right", style="dim")
    reasons_table.add_column("Reason", style="white")
    for idx, reason in enumerate(recommended.reasons, start=1):
        reasons_table.add_row(str(idx), reason)
    console.print(reasons_table)

    alternatives = decision.alternatives[:max_alternatives]
    if alternatives:
        alt_table = Table(title="Alternatives", header_style="bold yellow")
        alt_table.add_column("Model", style="cyan")
        alt_table.add_column("Provider", style="green")
        alt_table.add_column("Capability", style="white")
        alt_table.add_column("Score", justify="right", style="yellow")
        for alt in alternatives:
            alt_table.add_row(alt.name, alt.provider, alt.capability, f"{alt.score:.3f}")
        console.print(alt_table)


def render_models(models: list[Candidate]) -> None:
    table = Table(title="Available Models", header_style="bold blue")
    table.add_column("Name", style="cyan")
    table.add_column("Provider", style="green")
    table.add_column("Capability", style="white")
    table.add_column("Estimated Cost", style="yellow")
    for model in models:
        table.add_row(model.name, model.provider, model.capability, model.estimated_cost)
    console.print(table)


def render_execution_result(model_name: str | None, status: Literal["running", "success", "cancelled"]) -> None:
    if status == "running":
        console.print(Panel(f"[bold yellow]Executing with {model_name}...[/bold yellow]", border_style="yellow"))
        return
    if status == "success":
        console.print(Panel(f"[bold green]Execution finished with {model_name}[/bold green]", border_style="green"))
        return
    console.print(Panel("[bold red]Operation cancelled by user[/bold red]", border_style="red"))
