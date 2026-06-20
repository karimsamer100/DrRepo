from __future__ import annotations

from pathlib import Path
from typing import List

from ..input.resolver import resolve_local_path
from .models import ToolResult, tool_result_to_dict, make_tool_result
from .readme_auditor import audit_readme
from .structure_auditor import audit_structure


def run_repository_analyzers(path: str | Path) -> List[ToolResult]:
    resolved = resolve_local_path(path)
    results: List[ToolResult] = []

    try:
        r = audit_readme(resolved)
    except Exception as exc:
        r = make_tool_result("readme", "failed_to_run", summary={}, findings=[], errors=[str(exc)], raw_output=None)
    results.append(r)

    try:
        s = audit_structure(resolved)
    except Exception as exc:
        s = make_tool_result("structure", "failed_to_run", summary={}, findings=[], errors=[str(exc)], raw_output=None)
    results.append(s)

    return results


def repository_analyzers_to_dict(results: List[ToolResult]) -> List[dict]:
    return [tool_result_to_dict(r) for r in results]
