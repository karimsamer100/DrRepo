"""Command-line interface for DrRepo.

Provides a minimal `audit` command as Phase 1 Batch 1.
"""
from __future__ import annotations

import json
from pathlib import Path

import typer

from drrepo.advisor.priorities import build_profiled_action_plan
from drrepo.advisor.reporting import build_deterministic_advisor_report
from drrepo.advisor.profiles import validate_profile_id
from drrepo.audit import build_audit
from drrepo.reports.markdown_report import render_markdown_report
from drrepo.reports.terminal_summary import render_terminal_summary
from drrepo.input.git import is_public_github_repo_url
from drrepo.input.workspace import (
    create_temp_workspace,
    cleanup_workspace,
    clone_public_github_repo,
)


app = typer.Typer(help="DrRepo - repository audit tool (minimal)")


@app.callback()
def main() -> None:
    """DrRepo command line interface."""


@app.command()
def audit(
    path: str = typer.Argument(..., help="Path to local repository or GitHub repo URL"),
    output_format: str = typer.Option("json", "--format", help="Output format: json or markdown"),
    output: Path | None = typer.Option(None, "--output", help="Optional output file path to write report to"),
    profile: str | None = typer.Option(None, "--profile", help="Optional advisor profile to include deterministic advisor guidance"),
) -> None:
    """Run a lightweight audit against a local path or a public GitHub repository URL."""
    workspace = None
    is_url = isinstance(path, str) and (
        path.startswith("https://github.com/") or path.startswith("http://github.com/") or path.startswith("git@github.com:")
    )

    # If it looks like a GitHub URL, validate it strictly
    if is_url and not is_public_github_repo_url(path):
        raise typer.BadParameter("Invalid GitHub repository URL.")

    try:
        if is_public_github_repo_url(path):
            # GitHub URL flow
            try:
                workspace = create_temp_workspace()
                repo_path = clone_public_github_repo(path, workspace)
            except (RuntimeError, FileExistsError, ValueError) as exc:
                # Ensure cleanup happens in finally
                raise typer.BadParameter(str(exc)) from exc

            audit_result = build_audit(repo_path)
            # annotate source for URL audits
            audit_result["source"] = {"type": "github_url", "value": path}
        else:
            # Local path flow
            try:
                audit_result = build_audit(Path(path))
            except FileNotFoundError as exc:
                raise typer.BadParameter(str(exc)) from exc
            except NotADirectoryError as exc:
                raise typer.BadParameter(str(exc)) from exc
    finally:
        if workspace is not None:
            try:
                cleanup_workspace(workspace)
            except Exception:
                # Do not mask original exceptions; typer will report failure
                pass

    fmt = (output_format or "json").lower()
    if fmt not in ("json", "markdown", "summary"):
        raise typer.BadParameter("Invalid format: must be 'json', 'markdown', or 'summary'")

    advisor_report = None
    if profile is not None:
        try:
            validate_profile_id(profile)
        except ValueError as exc:
            raise typer.BadParameter(f"Invalid profile: {profile}") from exc
        advisor_report = build_deterministic_advisor_report(audit_result, profile_id=profile)

    # Build the formatted string
    if fmt == "json":
        if advisor_report is not None:
            audit_result = dict(audit_result)
            audit_result["advisor_report"] = advisor_report
        formatted = json.dumps(audit_result, indent=2)
    elif fmt == "markdown":
        formatted = render_markdown_report(audit_result)
        if advisor_report is not None:
            formatted = f"{formatted}\n\n{advisor_report['markdown_section']}"
    else:
        formatted = render_terminal_summary(audit_result)
        if advisor_report is not None:
            formatted = f"{formatted}\n\nAdvisor summary:\n" + "\n".join(advisor_report["summary_lines"])

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
