from __future__ import annotations

from typing import List, Dict, Any

from drrepo.analyzers.models import ToolResult, ToolFinding
from drrepo.assessment import cap_score_for_hard_flags, derive_hard_flags
from drrepo.analyzers.registry import is_core_analyzer


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


def status_penalty(result: ToolResult) -> int:
    """Status penalties are about observed quality, not tool availability.

    Missing optional tools do not reduce score. Test absence and intentional
    remote safety skips are different: they mean DrRepo did not observe a
    passing test signal, so the testing category must not look perfect.
    """
    if result.status == "failed_to_run" and (is_core_analyzer(result.tool) or result.tool == "pytest"):
        return 10
    if result.status == "partial" and (is_core_analyzer(result.tool) or result.tool == "pytest"):
        return 5
    if result.tool == "pytest" and result.status == "not_applicable":
        outcome = (result.summary or {}).get("outcome") if isinstance(result.summary, dict) else None
        if outcome == "no_tests":
            return 30
    if result.tool in {"pytest", "coverage"} and result.status == "skipped_by_config":
        return 15
    return 0


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
        penalty_total += status_penalty(r)
        # do not penalize not_available; it is confidence-limiting evidence

    final = max(0, min(100, score - penalty_total))
    return {
        "score": int(final),
        "finding_count": finding_count,
        "penalty": int(penalty_total),
        "status_counts": status_counts,
        "assessment_state": _assessment_state(results),
        "assessed": _is_assessed(results),
    }


def _is_assessed(results: List[ToolResult]) -> bool:
    return any(result.status in {"completed", "partial", "failed_to_run"} for result in results)


def _assessment_state(results: List[ToolResult]) -> str:
    if not results:
        return "not_assessed"
    statuses = {result.status for result in results}
    if any(status == "completed" for status in statuses):
        if any(result.findings for result in results):
            return "verified_with_findings"
        if statuses & {"partial", "failed_to_run"}:
            return "partial_evidence"
        return "verified_clean"
    if statuses & {"partial"}:
        return "partial_evidence"
    if statuses & {"failed_to_run"}:
        return "failed"
    if statuses <= {"skipped_by_config", "not_applicable"}:
        return "skipped"
    return "not_assessed"


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

    # category mapping to tool names
    category_tool_map = {
        "code_quality": ["ruff"],
        "security": ["bandit"],
        "maintainability": ["radon"],
        "testing": ["pytest", "coverage"],
        "documentation": ["readme"],
        "structure": ["structure"],
    }

    # helper to collect tool results for given tool names from all sections
    def _collect_tools(names: List[str]):
        out: List[ToolResult] = []
        all_results = list(static_analysis) + list(test_analysis) + list(repository_analysis)
        for r in all_results:
            if r.tool in names:
                out.append(r)
        return out

    categories: Dict[str, Any] = {}
    category_details: Dict[str, Any] = {}
    category_reasons: Dict[str, List[Dict[str, Any]]] = {}
    for cat, tools in category_tool_map.items():
        results = _collect_tools(tools)
        if results:
            scored = score_tool_results(results)
            assessed = bool(scored["assessed"])
            categories[cat] = scored["score"] if assessed else None
            reasons: List[Dict[str, Any]] = []
            for r in results:
                for f in (r.findings or []):
                    reasons.append(
                        {
                            "tool": r.tool,
                            "code": f.code,
                            "severity": f.severity,
                            "message": f.message,
                        }
                    )
            category_reasons[cat] = reasons
            category_details[cat] = {
                "score": scored["score"] if assessed else None,
                "legacy_score": scored["score"],
                "assessment_state": scored["assessment_state"],
                "assessed": assessed,
                "tools": tools,
                "status_counts": scored["status_counts"],
                "finding_count": scored["finding_count"],
                "reasons": reasons,
            }
        else:
            # Missing evidence is not clean evidence.
            categories[cat] = None
            category_reasons[cat] = []
            category_details[cat] = {
                "score": None,
                "legacy_score": 100,
                "assessment_state": "not_assessed",
                "assessed": False,
                "tools": tools,
                "status_counts": {},
                "finding_count": 0,
                "reasons": [],
            }

    # compute repository health and portfolio readiness using weighted averages
    def _weighted_score(weights: Dict[str, float]) -> int | None:
        total = 0.0
        assessed_weight = 0.0
        for k, w in weights.items():
            value = categories.get(k)
            if value is None:
                continue
            total += float(value) * w
            assessed_weight += w
        if assessed_weight <= 0:
            return None
        return int(round(total / assessed_weight))

    def _assessed_weight_ratio(weights: Dict[str, float]) -> float:
        assessed_weight = sum(w for k, w in weights.items() if categories.get(k) is not None)
        return round(min(1.0, max(0.0, assessed_weight)), 2)

    repo_weights = {
        "code_quality": 0.20,
        "testing": 0.20,
        "security": 0.20,
        "documentation": 0.15,
        "structure": 0.15,
        "maintainability": 0.10,
    }

    portfolio_weights = {
        "documentation": 0.30,
        "structure": 0.20,
        "testing": 0.15,
        "code_quality": 0.15,
        "security": 0.10,
        "maintainability": 0.10,
    }

    repository_health_score = _weighted_score(repo_weights)
    portfolio_readiness_score = _weighted_score(portfolio_weights)
    assessed_weight_ratio = _assessed_weight_ratio(repo_weights)

    avg = repository_health_score if repository_health_score is not None else round((static_score["score"] + test_score["score"] + repo_score["score"]) / 3.0)
    hard_flags = derive_hard_flags(list(static_analysis) + list(test_analysis) + list(repository_analysis))
    repo_blocking_flags = list(hard_flags)
    observed_score = cap_score_for_hard_flags(avg, hard_flags)

    return {
        "overall_score": int(observed_score) if observed_score is not None else None,
        "observed_score": int(observed_score) if observed_score is not None else None,
        "assessed_weight_ratio": assessed_weight_ratio,
        "score_basis": "assessed_categories_only",
        "unassessed_categories": [cat for cat, detail in category_details.items() if not detail["assessed"]],
        "hard_flags": hard_flags,
        "sections": sec_scores,
        "categories": categories,
        "category_details": category_details,
        "category_reasons": category_reasons,
        "repository_health_score": int(cap_score_for_hard_flags(repository_health_score, repo_blocking_flags)) if repository_health_score is not None else None,
        "portfolio_readiness_score": int(cap_score_for_hard_flags(portfolio_readiness_score, hard_flags)) if portfolio_readiness_score is not None else None,
    }
