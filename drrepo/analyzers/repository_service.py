from __future__ import annotations

from pathlib import Path
from typing import List

from ..input.resolver import resolve_local_path
from .models import ToolResult, tool_result_to_dict, make_tool_result
from .readme_auditor import audit_readme
from .structure_auditor import audit_structure
from .registry import (
    AnalysisMode,
    SourceType,
    definitions_for,
    should_run,
    skipped_result,
    timed_run,
)


def run_repository_analyzers(
    path: str | Path,
    *,
    source_type: SourceType = "local_path",
    analysis_mode: AnalysisMode = "deep_local",
) -> List[ToolResult]:
    resolved = resolve_local_path(path)
    results: List[ToolResult] = []

    for definition in definitions_for("repository_analysis"):
        allowed, reason = should_run(definition, source_type, analysis_mode)
        if not allowed:
            results.append(skipped_result(definition, analysis_mode, reason or "Skipped by analysis policy."))
            continue
        runner = {
            "readme": audit_readme,
            "structure": audit_structure,
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


def repository_analyzers_to_dict(results: List[ToolResult]) -> List[dict]:
    return [tool_result_to_dict(r) for r in results]
