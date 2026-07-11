from __future__ import annotations

from pathlib import Path
from typing import List

from ..input.resolver import resolve_local_path
from .models import ToolResult, tool_result_to_dict, make_tool_result
from .pytest_runner import run_pytest
from .coverage_runner import run_coverage


REMOTE_TEST_SKIP_REASON = "Skipped for remote GitHub audit safety."


def _skipped_remote_test_result(tool: str) -> ToolResult:
    return make_tool_result(
        tool,
        "skipped_by_config",
        summary={"reason": REMOTE_TEST_SKIP_REASON, "outcome": "skipped_for_remote_safety"},
        findings=[],
        errors=[],
        raw_output=None,
    )


def run_test_analyzers(path: str | Path, *, execute_tests: bool = True) -> List[ToolResult]:
    # Validate path; allow resolver errors to propagate so caller can handle them
    resolved = resolve_local_path(path)

    if not execute_tests:
        return [
            _skipped_remote_test_result("pytest"),
            _skipped_remote_test_result("coverage"),
        ]

    results: List[ToolResult] = []

    try:
        p = run_pytest(resolved)
    except Exception as exc:
        p = make_tool_result("pytest", "failed_to_run", summary={}, findings=[], errors=[str(exc)], raw_output=None)
    results.append(p)

    try:
        c = run_coverage(resolved)
    except Exception as exc:
        c = make_tool_result("coverage", "failed_to_run", summary={}, findings=[], errors=[str(exc)], raw_output=None)
    results.append(c)

    return results


def test_analyzers_to_dict(results: List[ToolResult]) -> List[dict]:
    return [tool_result_to_dict(r) for r in results]
