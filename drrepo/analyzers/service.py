from __future__ import annotations

import json
from pathlib import Path
from typing import List

from ..input.resolver import resolve_local_path
from .models import ToolResult, tool_result_to_dict, make_tool_result
from .ruff_runner import run_ruff
from .bandit_runner import run_bandit
from .radon_runner import run_radon


def run_static_analyzers(path: str | Path) -> List[ToolResult]:
    # Validate path using resolver; allow resolver exceptions to propagate
    resolved = resolve_local_path(path)

    results: List[ToolResult] = []

    # Run in specified order, catching unexpected exceptions and converting to ToolResult
    try:
        r = run_ruff(resolved)
    except Exception as exc:  # unexpected
        r = make_tool_result("ruff", "failed_to_run", summary={}, findings=[], errors=[str(exc)], raw_output=None)
    results.append(r)

    try:
        b = run_bandit(resolved)
    except Exception as exc:
        b = make_tool_result("bandit", "failed_to_run", summary={}, findings=[], errors=[str(exc)], raw_output=None)
    results.append(b)

    try:
        ra = run_radon(resolved)
    except Exception as exc:
        ra = make_tool_result("radon", "failed_to_run", summary={}, findings=[], errors=[str(exc)], raw_output=None)
    results.append(ra)

    return results


def static_analyzers_to_dict(results: List[ToolResult]) -> List[dict]:
    return [tool_result_to_dict(r) for r in results]
