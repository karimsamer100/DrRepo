"""Command-line interface for DrRepo.

Provides a minimal `audit` command as Phase 1 Batch 1.
"""
from __future__ import annotations

import json
from pathlib import Path

import typer

from drrepo.input.resolver import resolve_local_path
from drrepo.scanner.repository_scanner import scan_repository
from drrepo.analyzers.service import run_static_analyzers, static_analyzers_to_dict
from drrepo.analyzers.test_service import run_test_analyzers, test_analyzers_to_dict
from drrepo.analyzers.repository_service import run_repository_analyzers, repository_analyzers_to_dict
from drrepo.scoring import score_audit_sections
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
        resolved_path = resolve_local_path(path)
    except FileNotFoundError as exc:
        raise typer.BadParameter(str(exc)) from exc
    except NotADirectoryError as exc:
        raise typer.BadParameter(str(exc)) from exc
    # Delegate to the scanner which performs the repository walk and
    # returns the JSON-serializable metadata structure.
    scanned = scan_repository(resolved_path)
    # Run static analyzers against the detected repository root. Let unexpected
    # errors propagate — the analyzer service already converts per-analyzer
    # failures into ToolResult objects.
    analyzer_results = run_static_analyzers(scanned["path"])
    scanned["static_analysis"] = static_analyzers_to_dict(analyzer_results)
    # Run test analyzers (pytest)
    test_results = run_test_analyzers(scanned["path"])
    # Run repository analyzers (readme, structure)
    repo_results = run_repository_analyzers(scanned["path"])

    # Score the raw ToolResult objects before converting to dicts
    scoring = score_audit_sections(analyzer_results, test_results, repo_results)

    scanned["static_analysis"] = static_analyzers_to_dict(analyzer_results)
    scanned["test_analysis"] = test_analyzers_to_dict(test_results)
    scanned["repository_analysis"] = repository_analyzers_to_dict(repo_results)
    scanned["scoring"] = scoring

    fmt = (output_format or "json").lower()
    if fmt not in ("json", "markdown"):
        raise typer.BadParameter("Invalid format: must be 'json' or 'markdown'")

    if fmt == "json":
        typer.echo(json.dumps(scanned, indent=2))
    else:
        md = render_markdown_report(scanned)
        typer.echo(md)


if __name__ == "__main__":
    app()
