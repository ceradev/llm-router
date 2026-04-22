from __future__ import annotations

import typer

from .commands.decide import app as decide_app
from .commands.models import app as models_app
from .commands.route import app as route_app

app = typer.Typer(
    help="LLM Router CLI: local routing decisions without HTTP.",
    no_args_is_help=True,
    add_completion=False,
)

app.add_typer(route_app, name="route")
app.add_typer(decide_app, name="decide")
app.add_typer(models_app, name="models")


if __name__ == "__main__":
    app()
