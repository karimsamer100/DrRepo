"""Command-line interface for DrRepo.

Provides a minimal `audit` command as Phase 1 Batch 1.
"""
from __future__ import annotations

import json
from pathlib import Path

import typer

from drrepo.advisor.service import build_advisor_for_audit
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
from drrepo.analyzers.registry import validate_analysis_mode
from drrepo.execution import check_docker_capability
from drrepo.execution.models import options_from_dict


app = typer.Typer(help="DrRepo - repository audit tool (minimal)")


@app.callback()
def main() -> None:
    """DrRepo command line interface."""


def _build_audit_cli(repo_path: str | Path, *, source_type: str, analysis_mode: str, profile_id: str, isolated_options: dict | None = None):
    execute_tests = source_type == "local_path" and analysis_mode == "deep_local"
    try:
        return build_audit(
            repo_path,
            source_type=source_type,
            analysis_mode=analysis_mode,
            execute_tests=execute_tests,
            profile_id=profile_id,
            isolated_options=isolated_options,
        )
    except TypeError as exc:
        if "unexpected keyword" not in str(exc):
            raise
        try:
            return build_audit(repo_path, execute_tests=execute_tests)
        except TypeError as exc2:
            if "unexpected keyword" not in str(exc2):
                raise
            return build_audit(repo_path)


def _validated_cli_isolated_options(
    mode: str,
    install_dependencies: bool,
    allow_install_network: bool,
    isolated_timeout: int,
    isolated_python: str,
) -> dict | None:
    if mode != "deep_isolated":
        if install_dependencies or allow_install_network:
            raise ValueError("isolated dependency flags require --analysis-mode deep_isolated.")
        return None
    raw = {
        "install_dependencies": install_dependencies,
        "allow_install_network": allow_install_network,
        "total_timeout_seconds": isolated_timeout,
        "per_command_timeout_seconds": min(120, isolated_timeout),
        "python_version": isolated_python,
    }
    options = options_from_dict(raw)
    capability = check_docker_capability()
    if not capability.deep_isolated_supported:
        raise ValueError(capability.unavailable_reason or "Docker isolated execution is unavailable.")
    typer.echo("Deep Isolated will execute supported checks inside a disposable Docker container.", err=True)
    if options.install_dependencies:
        typer.echo("Dependency installation may execute package build hooks inside the container.", err=True)
    if options.allow_install_network:
        typer.echo("Network is allowed only during the dependency installation phase.", err=True)
    return raw


def _format_ai_summary_block(ai_advisor: dict[str, object]) -> str:
    source = ai_advisor.get("source", "deterministic")
    status = ai_advisor.get("status", "unknown")
    provider = ai_advisor.get("provider") or "deterministic"
    model = ai_advisor.get("model") or "deterministic-advisor"
    fallback = ai_advisor.get("fallback_reason")
    grounding = ai_advisor.get("grounding_result") or {}
    used_fallback = source != "ai" or fallback is not None

    lines = ["## AI Advisor", "", f"Advisor mode: {source.upper()}", f"Status: {status}"]
    lines.append(f"Selected provider: {provider}")
    if source == "ai":
        lines.append(f"Model: {model}")
    lines.append(f"Fallback used: {'Yes' if used_fallback else 'No'}")
    if grounding:
        lines.append(f"Grounding: {'valid' if grounding.get('valid') else 'rejected'}")
        violations = grounding.get("violations") or []
        for violation in violations[:3]:
            lines.append(f"  - {violation}")
    if fallback:
        lines.append(f"Fallback reason: {fallback}")
    return "\n".join(lines)


@app.command()
def audit(
    path: str = typer.Argument(..., help="Path to local repository or GitHub repo URL"),
    output_format: str = typer.Option("json", "--format", help="Output format: json or markdown"),
    output: Path | None = typer.Option(None, "--output", help="Optional output file path to write report to"),
    profile: str | None = typer.Option(None, "--profile", help="Optional advisor profile to include deterministic advisor guidance"),
    ai: bool = typer.Option(False, "--ai", help="Use the AI advisor router when a profile is selected"),
    analysis_mode: str | None = typer.Option(None, "--analysis-mode", help="Analysis mode: quick_safe, deep_local, or deep_isolated"),
    install_dependencies: bool = typer.Option(False, "--install-dependencies", help="For deep_isolated only: install dependencies inside the container before checks."),
    allow_install_network: bool = typer.Option(False, "--allow-install-network", help="For deep_isolated only: temporarily allow network during dependency installation."),
    isolated_timeout: int = typer.Option(300, "--isolated-timeout", help="For deep_isolated only: total timeout in seconds."),
    isolated_python: str = typer.Option("3.12", "--isolated-python", help="For deep_isolated only: Python version allowlist value."),
) -> None:
    """Run a lightweight audit against a local path or a public GitHub repository URL."""
    workspace = None
    is_url = isinstance(path, str) and (
        path.startswith("https://github.com/") or path.startswith("http://github.com/") or path.startswith("git@github.com:")
    )

    if ai and profile is None:
        profile = "student_portfolio"

    if profile is not None:
        try:
            validate_profile_id(profile)
        except ValueError as exc:
            raise typer.BadParameter(f"Invalid profile: {profile}") from exc

    # If it looks like a GitHub URL, validate it strictly
    if is_url and not is_public_github_repo_url(path):
        raise typer.BadParameter("Invalid GitHub repository URL.")

    try:
        if is_public_github_repo_url(path):
            try:
                mode = validate_analysis_mode("github_url", analysis_mode)
                isolated_options = _validated_cli_isolated_options(mode, install_dependencies, allow_install_network, isolated_timeout, isolated_python)
            except ValueError as exc:
                raise typer.BadParameter(str(exc)) from exc
            # GitHub URL flow
            try:
                workspace = create_temp_workspace()
                repo_path = clone_public_github_repo(path, workspace)
            except (RuntimeError, FileExistsError, ValueError) as exc:
                # Ensure cleanup happens in finally
                raise typer.BadParameter(str(exc)) from exc

            audit_result = _build_audit_cli(repo_path, source_type="github_url", analysis_mode=mode, profile_id=profile or "student_portfolio", isolated_options=isolated_options)
            # annotate source for URL audits
            audit_result["source"] = {"type": "github_url", "value": path}
        else:
            try:
                mode = validate_analysis_mode("local_path", analysis_mode)
                isolated_options = _validated_cli_isolated_options(mode, install_dependencies, allow_install_network, isolated_timeout, isolated_python)
            except ValueError as exc:
                raise typer.BadParameter(str(exc)) from exc
            # Local path flow
            try:
                audit_result = _build_audit_cli(Path(path), source_type="local_path", analysis_mode=mode, profile_id=profile or "student_portfolio", isolated_options=isolated_options)
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
    ai_advisor = None
    if profile is not None:
        try:
            validate_profile_id(profile)
        except ValueError as exc:
            raise typer.BadParameter(f"Invalid profile: {profile}") from exc
        advisor_package = build_advisor_for_audit(
            audit_result, profile_id=profile, ai=ai
        )
        advisor_report = advisor_package.get("advisor_report")
        ai_advisor = advisor_package.get("ai")

    # Build the formatted string
    if fmt == "json":
        output_result = dict(audit_result)
        if advisor_report is not None:
            output_result["advisor_report"] = advisor_report
        if ai_advisor is not None:
            output_result["ai_advisor"] = ai_advisor
            # Preserve backward-compatible llm_router summary for CLI consumers
            router_result = ai_advisor.get("router_result")
            if router_result:
                output_result["llm_router"] = {
                    "router_version": "v1",
                    "selected_provider_id": router_result.get("selected_provider_id"),
                    "used_fallback": router_result.get("used_fallback"),
                    "provider_attempts": router_result.get("provider_attempts", []),
                }
        formatted = json.dumps(output_result, indent=2)
    elif fmt == "markdown":
        formatted = render_markdown_report(audit_result, ai_advisor=ai_advisor)
        if advisor_report is not None and not (ai_advisor and ai_advisor.get("requested")):
            markdown_section = advisor_report.get("markdown_section")
            if markdown_section:
                formatted = f"{formatted}\n\n{markdown_section}"
    else:
        formatted = render_terminal_summary(audit_result)
        if advisor_report is not None:
            formatted = f"{formatted}\n\nAdvisor summary:\n" + "\n".join(advisor_report.get("summary_lines", []))
        if ai_advisor is not None and ai_advisor.get("requested"):
            formatted = f"{formatted}\n\n{_format_ai_summary_block(ai_advisor)}"

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
