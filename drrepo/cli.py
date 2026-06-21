"""Command-line interface for DrRepo.

Provides a minimal `audit` command as Phase 1 Batch 1.
"""
from __future__ import annotations

import json
from pathlib import Path

import typer

from drrepo.audit import build_audit
from drrepo.reports.markdown_report import render_markdown_report
from drrepo.reports.terminal_summary import render_terminal_summary


app = typer.Typer(help="DrRepo - repository audit tool (minimal)")


@app.callback()
def main() -> None:
    """DrRepo command line interface."""


@app.command()
def audit(
    path: Path = typer.Argument(..., help="Path to local repository"),
    output_format: str = typer.Option("json", "--format", help="Output format: json or markdown"),
    output: Path | None = typer.Option(None, "--output", help="Optional output file path to write report to"),
) -> None:
    """Run a lightweight audit placeholder against a local path."""
    try:
        audit_result = build_audit(path)
    except FileNotFoundError as exc:
        raise typer.BadParameter(str(exc)) from exc
    except NotADirectoryError as exc:
        raise typer.BadParameter(str(exc)) from exc

    fmt = (output_format or "json").lower()
    if fmt not in ("json", "markdown", "summary"):
        raise typer.BadParameter("Invalid format: must be 'json', 'markdown', or 'summary'")

    # Build the formatted string
    if fmt == "json":
        formatted = json.dumps(audit_result, indent=2)
    elif fmt == "markdown":
        formatted = render_markdown_report(audit_result)
    else:
        formatted = render_terminal_summary(audit_result)

    if output:
        out_path = Path(output)
        # create parent directories if necessary (and not current dir)
        parent = out_path.parent
        if str(parent) != "":
            parent.mkdir(parents=True, exist_ok=True)
        try:
            out_path.write_text(formatted, encoding="utf-8")
        except OSError as exc:
            raise typer.BadParameter(f"Failed to write report: {exc}") from exc
        typer.echo(f"Wrote audit report to {out_path}")
    else:
        typer.echo(formatted)


if __name__ == "__main__":
    app()
