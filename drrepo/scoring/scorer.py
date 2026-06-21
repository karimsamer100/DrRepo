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
    category_reasons: Dict[str, List[Dict[str, Any]]] = {}
    for cat, tools in category_tool_map.items():
        results = _collect_tools(tools)
        if results:
            scored = score_tool_results(results)
            categories[cat] = scored["score"]
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
        else:
            # missing evidence -> perfect score but empty reasons
            categories[cat] = 100
            category_reasons[cat] = []

    # compute repository health and portfolio readiness using weighted averages
    def _weighted_score(weights: Dict[str, float]) -> int:
        total = 0.0
        for k, w in weights.items():
            total += categories.get(k, 100) * w
        return int(round(total))

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

    # average of the three section scores (preserve existing overall behavior)
    avg = round((static_score["score"] + test_score["score"] + repo_score["score"]) / 3.0)

    return {
        "overall_score": int(avg),
        "sections": sec_scores,
        "categories": categories,
        "category_reasons": category_reasons,
        "repository_health_score": repository_health_score,
        "portfolio_readiness_score": portfolio_readiness_score,
    }
