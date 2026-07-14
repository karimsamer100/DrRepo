from __future__ import annotations

from pathlib import Path
from typing import List

from ..input.resolver import resolve_local_path
from .models import ToolResult, tool_result_to_dict, make_tool_result
from .pytest_runner import run_pytest
from .coverage_runner import run_coverage
from .registry import (
    AnalysisMode,
    SourceType,
    definitions_for,
    should_run,
    skipped_result,
    timed_run,
)
from drrepo.execution import IsolatedExecutionRequest, isolated_result_to_tool_results, run_isolated_checks
from drrepo.execution.models import options_from_dict


REMOTE_TEST_SKIP_REASON = "Skipped for remote GitHub audit safety."


def run_test_analyzers(
    path: str | Path,
    *,
    execute_tests: bool | None = None,
    source_type: SourceType = "local_path",
    analysis_mode: AnalysisMode = "deep_local",
    isolated_options: dict | None = None,
) -> List[ToolResult]:
    # Validate path; allow resolver errors to propagate so caller can handle them
    resolved = resolve_local_path(path)

    if execute_tests is not None:
        analysis_mode = "deep_local" if execute_tests else "quick_safe"
        if not execute_tests:
            source_type = "github_url"

    if analysis_mode == "deep_isolated":
        options = options_from_dict(isolated_options)
        isolated = run_isolated_checks(IsolatedExecutionRequest(
            repository_path=resolved,
            source_type=source_type,
            python_version=options.python_version,
            install_dependencies=options.install_dependencies,
            allow_install_network=options.allow_install_network,
            requested_checks=("syntax", "pytest", "coverage"),
            total_timeout_seconds=options.total_timeout_seconds,
            per_command_timeout_seconds=options.per_command_timeout_seconds,
        ))
        return isolated_result_to_tool_results(isolated)

    results: List[ToolResult] = []

    for definition in definitions_for("test_analysis"):
        allowed, reason = should_run(definition, source_type, analysis_mode)
        if not allowed:
            results.append(skipped_result(definition, analysis_mode, reason or REMOTE_TEST_SKIP_REASON))
            continue
        runner = {
            "pytest": run_pytest,
            "coverage": run_coverage,
        }[definition.analyzer_id]
        try:
            result = timed_run(lambda runner=runner: runner(resolved), analysis_mode=analysis_mode)
        except Exception as exc:
            result = make_tool_result(
                definition.analyzer_id,
                "failed_to_run",
                summary={},
                findings=[],
                errors=[str(exc)],
                raw_output=None,
                execution_mode=analysis_mode,
            )
        results.append(result)

    return results


def test_analyzers_to_dict(results: List[ToolResult]) -> List[dict]:
    return [tool_result_to_dict(r) for r in results]
