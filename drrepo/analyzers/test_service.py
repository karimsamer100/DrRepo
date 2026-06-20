from __future__ import annotations

from pathlib import Path
from typing import List

from ..input.resolver import resolve_local_path
from .models import ToolResult, tool_result_to_dict, make_tool_result
from .pytest_runner import run_pytest
from .coverage_runner import run_coverage


def run_test_analyzers(path: str | Path) -> List[ToolResult]:
    # Validate path; allow resolver errors to propagate so caller can handle them
    resolved = resolve_local_path(path)

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
