"""Command-line interface for DrRepo.

Provides a minimal `audit` command as Phase 1 Batch 1.
"""
from __future__ import annotations

import json
from pathlib import Path

import typer

from drrepo.audit import build_audit
from drrepo.reports.markdown_report import render_markdown_report


app = typer.Typer(help="DrRepo - repository audit tool (minimal)")


@app.callback()
def main() -> None:
    """DrRepo command line interface."""


@app.command()
def audit(
    path: Path = typer.Argument(..., help="Path to local repository"),
    output_format: str = typer.Option("json", "--format", help="Output format: json or markdown"),
) -> None:
    """Run a lightweight audit placeholder against a local path."""
    try:
        audit_result = build_audit(path)
    except FileNotFoundError as exc:
        raise typer.BadParameter(str(exc)) from exc
    except NotADirectoryError as exc:
        raise typer.BadParameter(str(exc)) from exc

    fmt = (output_format or "json").lower()
    if fmt not in ("json", "markdown"):
        raise typer.BadParameter("Invalid format: must be 'json' or 'markdown'")

    if fmt == "json":
        typer.echo(json.dumps(audit_result, indent=2))
    else:
        md = render_markdown_report(audit_result)
        typer.echo(md)


if __name__ == "__main__":
    app()
