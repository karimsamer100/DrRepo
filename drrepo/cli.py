"""Command-line interface for DrRepo.

Provides a minimal `audit` command as Phase 1 Batch 1.
"""
from __future__ import annotations

import json
from pathlib import Path

import typer

from drrepo.input.resolver import resolve_local_path


app = typer.Typer(help="DrRepo - repository audit tool (minimal)")


@app.callback()
def main() -> None:
    """DrRepo command line interface."""


@app.command()
def audit(path: Path = typer.Argument(..., help="Path to local repository")) -> None:
    """Run a lightweight audit placeholder against a local path."""
    try:
        resolved_path = resolve_local_path(path)
    except FileNotFoundError as exc:
        raise typer.BadParameter(str(exc)) from exc
    except NotADirectoryError as exc:
        raise typer.BadParameter(str(exc)) from exc

    result = {
        "status": "ok",
        "path": str(resolved_path),
    }
    typer.echo(json.dumps(result, indent=2))


if __name__ == "__main__":
    app()
