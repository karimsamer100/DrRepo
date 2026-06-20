from __future__ import annotations

from typing import List, Dict, Any

from drrepo.analyzers.models import ToolResult, ToolFinding


def severity_penalty(severity: str | None) -> int:
    if not severity:
        return 2
    s = severity.lower()
    if s == "critical":
        return 25
    if s == "high":
        return 15
    if s == "medium":
        return 8
    if s == "low":
        return 3
    return 2


def score_tool_results(results: List[ToolResult]) -> Dict[str, Any]:
    score = 100
    penalty_total = 0
    finding_count = 0
    status_counts: Dict[str, int] = {}

    for r in results:
        status_counts[r.status] = status_counts.get(r.status, 0) + 1
        # findings penalties
        for f in (r.findings or []):
            pen = severity_penalty(f.severity)
            penalty_total += pen
            finding_count += 1
        # status penalties
        if r.status == "failed_to_run":
            penalty_total += 10
        elif r.status == "partial":
            penalty_total += 5
        # do not penalize not_available or not_applicable

    final = max(0, min(100, score - penalty_total))
    return {
        "score": int(final),
        "finding_count": finding_count,
        "penalty": int(penalty_total),
        "status_counts": status_counts,
    }


def score_audit_sections(
    static_analysis: List[ToolResult],
    test_analysis: List[ToolResult],
    repository_analysis: List[ToolResult],
) -> Dict[str, Any]:
    static_score = score_tool_results(static_analysis)
    test_score = score_tool_results(test_analysis)
    repo_score = score_tool_results(repository_analysis)

    sec_scores = {
        "static_analysis": static_score,
        "test_analysis": test_score,
        "repository_analysis": repo_score,
    }

    # average of the three section scores
    avg = round((static_score["score"] + test_score["score"] + repo_score["score"]) / 3.0)
    return {"overall_score": int(avg), "sections": sec_scores}
