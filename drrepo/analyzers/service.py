from __future__ import annotations

import json
from pathlib import Path
from typing import List

from ..input.resolver import resolve_local_path
from .models import ToolResult, tool_result_to_dict, make_tool_result
from .ruff_runner import run_ruff
from .bandit_runner import run_bandit
from .radon_runner import run_radon
from .registry import (
    AnalysisMode,
    SourceType,
    definitions_for,
    should_run,
    skipped_result,
    timed_run,
)


def run_static_analyzers(
    path: str | Path,
    *,
    source_type: SourceType = "local_path",
    analysis_mode: AnalysisMode = "deep_local",
) -> List[ToolResult]:
    # Validate path using resolver; allow resolver exceptions to propagate
    resolved = resolve_local_path(path)

    results: List[ToolResult] = []

    for definition in definitions_for("static_analysis"):
        allowed, reason = should_run(definition, source_type, analysis_mode)
        if not allowed:
            results.append(skipped_result(definition, analysis_mode, reason or "Skipped by analysis policy."))
            continue
        runner = {
            "ruff": run_ruff,
            "bandit": run_bandit,
            "radon": run_radon,
        }[definition.analyzer_id]
        try:
            result = timed_run(lambda runner=runner: runner(resolved), analysis_mode=analysis_mode)
        except Exception as exc:  # unexpected
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


def static_analyzers_to_dict(results: List[ToolResult]) -> List[dict]:
    return [tool_result_to_dict(r) for r in results]
