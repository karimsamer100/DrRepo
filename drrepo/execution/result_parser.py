from __future__ import annotations

from drrepo.analyzers.coverage_runner import parse_coverage_json
from drrepo.analyzers.models import ToolFinding, ToolResult
from drrepo.analyzers.pytest_runner import parse_pytest_output
from drrepo.analyzers.registry import apply_outcome_metadata

from .models import CommandExecutionResult, IsolatedExecutionResult


def _combined(command: CommandExecutionResult | None) -> tuple[str, str, int]:
    if command is None:
        return "", "", 1
    return command.stdout or "", command.stderr or "", command.exit_code if command.exit_code is not None else 1


def _with_isolated_metadata(result: ToolResult, isolated: IsolatedExecutionResult, command: CommandExecutionResult | None) -> ToolResult:
    result.execution_mode = "deep_isolated"
    result.duration_ms = command.duration_ms if command else None
    result.summary = dict(result.summary or {})
    result.summary.update({
        "execution_mode": "deep_isolated",
        "isolated_status": isolated.status,
        "runner_image": isolated.image,
        "docker_version": isolated.docker_version,
        "cleanup_status": isolated.cleanup_status,
    })
    if command and command.reason:
        result.summary["reason"] = command.reason
    return apply_outcome_metadata(result)


def _setup_limitation(tool: str, isolated: IsolatedExecutionResult) -> ToolResult:
    setup = isolated.setup
    reason = setup.reason if setup and setup.reason else "Dependency setup failed inside the isolated runner."
    result = ToolResult(
        tool=tool,
        status="skipped_by_config",
        summary={"outcome": "setup_failed", "reason": reason, "execution_mode": "deep_isolated"},
        findings=[],
        errors=[],
        execution_mode="deep_isolated",
        skipped_reason=reason,
    )
    return apply_outcome_metadata(result)


def _docker_unavailable(tool: str, isolated: IsolatedExecutionResult) -> ToolResult:
    reason = isolated.limitations[0] if isolated.limitations else "Docker isolated execution is unavailable."
    result = ToolResult(
        tool=tool,
        status="not_available",
        summary={"outcome": "docker_unavailable", "reason": reason, "execution_mode": "deep_isolated"},
        findings=[],
        errors=[],
        execution_mode="deep_isolated",
        unavailable_reason=reason,
    )
    return apply_outcome_metadata(result)


def _timeout_result(tool: str, command: CommandExecutionResult | None, isolated: IsolatedExecutionResult) -> ToolResult:
    reason = "Isolated execution timed out."
    if command and command.reason:
        reason = command.reason
    result = ToolResult(
        tool=tool,
        status="failed_to_run",
        summary={"outcome": "timeout", "reason": reason, "execution_mode": "deep_isolated", "isolated_status": isolated.status},
        findings=[],
        errors=[reason],
        execution_mode="deep_isolated",
    )
    return apply_outcome_metadata(result)


def isolated_result_to_tool_results(isolated: IsolatedExecutionResult) -> list[ToolResult]:
    if isolated.status == "docker_unavailable":
        return [_docker_unavailable("pytest", isolated), _docker_unavailable("coverage", isolated)]
    if isolated.status == "setup_failed":
        return [_setup_limitation("pytest", isolated), _setup_limitation("coverage", isolated)]

    pytest_command = isolated.command("pytest")
    coverage_command = isolated.command("coverage")
    coverage_json_command = isolated.command("coverage_json")

    if isolated.status == "timeout":
        return [_timeout_result("pytest", pytest_command, isolated), _timeout_result("coverage", coverage_command, isolated)]

    stdout, stderr, returncode = _combined(pytest_command)
    pytest_result = parse_pytest_output(stdout, stderr, returncode)
    pytest_result = _with_isolated_metadata(pytest_result, isolated, pytest_command)

    coverage_result: ToolResult
    if coverage_command and coverage_command.timeout:
        coverage_result = _timeout_result("coverage", coverage_command, isolated)
    elif coverage_command and coverage_command.exit_code not in (0, None):
        coverage_result = ToolResult(
            tool="coverage",
            status="failed_to_run",
            summary={"outcome": "tests_failed", "execution_mode": "deep_isolated"},
            findings=[ToolFinding(tool="coverage", message="Coverage could not complete because tests failed in isolation.", severity="medium", code="COVERAGE-TESTS-FAILED")],
            errors=["Coverage run did not complete successfully inside the isolated runner."],
            raw_output=coverage_command.stdout,
            execution_mode="deep_isolated",
        )
        coverage_result = _with_isolated_metadata(coverage_result, isolated, coverage_command)
    elif isolated.metadata.get("coverage_json"):
        parsed = parse_coverage_json(str(isolated.metadata.get("coverage_json")))
        coverage_result = _with_isolated_metadata(parsed, isolated, coverage_json_command or coverage_command)
    else:
        coverage_result = ToolResult(
            tool="coverage",
            status="failed_to_run",
            summary={"outcome": "no_data", "execution_mode": "deep_isolated"},
            findings=[],
            errors=["Coverage did not produce JSON output inside the isolated runner."],
            execution_mode="deep_isolated",
        )
        coverage_result = _with_isolated_metadata(coverage_result, isolated, coverage_json_command or coverage_command)

    return [pytest_result, coverage_result]
