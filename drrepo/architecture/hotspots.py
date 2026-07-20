from __future__ import annotations

from collections import defaultdict
from typing import Any

from drrepo.architecture.models import ArchitectureNode, RiskFactor, RiskHotspot


SEVERITY_POINTS = {
    "critical": 24,
    "high": 16,
    "medium": 8,
    "low": 3,
    "info": 1,
    "informational": 1,
    "unknown": 4,
    "A": 0,
    "B": 3,
    "C": 9,
    "D": 14,
    "E": 20,
    "F": 24,
}


def _is_test_path(path: str) -> bool:
    parts = path.replace("\\", "/").split("/")
    name = parts[-1] if parts else path
    return "tests" in parts or name.startswith("test_") or name.endswith("_test.py")


def _severity_points(finding: dict[str, Any]) -> int:
    sev = str(finding.get("severity") or "unknown")
    return SEVERITY_POINTS.get(sev, SEVERITY_POINTS.get(sev.lower(), 4))


def _risk_level(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 55:
        return "high"
    if score >= 30:
        return "medium"
    if score >= 12:
        return "low"
    return "informational"


def build_hotspots(
    nodes: list[ArchitectureNode],
    findings_by_path: dict[str, list[dict[str, Any]]],
    cycle_node_ids: set[str],
    test_status_by_path: dict[str, str],
    *,
    limit: int = 8,
) -> list[RiskHotspot]:
    hotspots: list[RiskHotspot] = []
    production_nodes = [node for node in nodes if node.kind != "test" and not _is_test_path(node.path)]
    for node in production_nodes:
        factors: list[RiskFactor] = []
        metrics = node.metrics
        findings = findings_by_path.get(node.path, [])
        production_findings: list[dict[str, Any]] = []
        informational_findings: list[dict[str, Any]] = []
        for finding in findings:
            code = str(finding.get("code") or "")
            if code == "B101" and _is_test_path(str(finding.get("file_path") or node.path)):
                item = dict(finding)
                item["architecture_context"] = "expected_test_assert"
                item["architecture_severity"] = "informational"
                informational_findings.append(item)
            else:
                production_findings.append(finding)
        finding_points = sum(_severity_points(item) for item in production_findings)
        if finding_points:
            factors.append(RiskFactor("findings", "Analyzer findings", min(40, finding_points), [str(item.get("code") or item.get("message")) for item in production_findings[:5]]))
        if informational_findings:
            factors.append(RiskFactor("test_context_findings", "Test-context findings", 1, ["Bandit B101 assert in pytest-style test file treated as informational."]))

        complexity = int(metrics.get("max_complexity") or 0)
        if complexity >= 10:
            factors.append(RiskFactor("complexity", "High cyclomatic complexity", min(25, complexity), [f"max_complexity={complexity}"]))

        inbound = int(metrics.get("incoming_internal_dependencies") or 0)
        outgoing = int(metrics.get("outgoing_internal_dependencies") or 0)
        centrality = inbound + outgoing
        if centrality >= 3:
            factors.append(RiskFactor("centrality", "Central dependency position", min(20, centrality * 4), [f"in={inbound}", f"out={outgoing}"]))
        elif inbound >= 1 and node.kind in {"entry_point", "api_route", "service", "repository/data-access"}:
            factors.append(RiskFactor("importance", "Important architecture role", 6, [node.kind]))

        if node.id in cycle_node_ids:
            factors.append(RiskFactor("cycle", "Participates in circular dependency", 14, ["cycle participation"]))

        test_status = test_status_by_path.get(node.path, "unavailable")
        if test_status == "no_associated_test_evidence" and node.kind in {"entry_point", "api_route", "service", "repository/data-access"}:
            factors.append(RiskFactor("test_gap", "Important module has limited associated test evidence", 12, [test_status]))
        elif test_status == "unavailable":
            factors.append(RiskFactor("test_evidence_unavailable", "Test relationship evidence unavailable", 3, [test_status]))

        line_count = int(metrics.get("line_count") or 0)
        if line_count >= 250:
            factors.append(RiskFactor("size", "Large file", min(10, line_count // 80), [f"{line_count} lines"]))

        score = min(100, sum(factor.contribution for factor in factors))
        if score <= 0:
            continue
        hotspots.append(RiskHotspot(
            id=f"hotspot:{node.id}",
            rank=0,
            node_id=node.id,
            path=node.path,
            title=f"Review {node.label}",
            risk_score=score,
            risk_level=_risk_level(score),
            confidence="high" if production_findings or complexity or centrality >= 3 else "medium",
            factors=factors,
            findings=[*production_findings[:6], *informational_findings[:3]],
            test_status=test_status,
            why_it_matters=_why_it_matters(node, factors),
            recommended_action=_recommended_action(node, factors),
            success_check="Relevant findings are addressed or justified, coupling is understood, and associated tests cover the changed behavior.",
        ))
    hotspots.sort(key=lambda item: (-item.risk_score, item.path, item.node_id))
    for index, item in enumerate(hotspots[:limit], start=1):
        item.rank = index
    return hotspots[:limit]


def _why_it_matters(node: ArchitectureNode, factors: list[RiskFactor]) -> str:
    names = ", ".join(factor.label.lower() for factor in factors[:3])
    return f"{node.path} appears important because of {names}." if names else f"{node.path} has limited but noteworthy architecture evidence."


def _recommended_action(node: ArchitectureNode, factors: list[RiskFactor]) -> str:
    factor_ids = {factor.id for factor in factors}
    if "cycle" in factor_ids:
        return "Inspect the dependency cycle and move shared behavior behind a lower-level module if the cycle is architectural rather than package initialization."
    if "complexity" in factor_ids:
        return "Start by splitting the highest-complexity function or class into smaller units with tests around the current behavior."
    if "findings" in factor_ids:
        return "Resolve or justify the associated analyzer findings in this module first."
    if "test_gap" in factor_ids:
        return "Add focused tests for the public behavior this module exposes."
    return "Review this module's role and keep its dependencies explicit."


def group_findings_by_path(audit: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for section in ("static_analysis", "test_analysis", "repository_analysis"):
        for entry in audit.get(section, []) or []:
            if not isinstance(entry, dict):
                continue
            tool = entry.get("tool")
            for finding in entry.get("findings", []) or []:
                if not isinstance(finding, dict):
                    continue
                path = str(finding.get("file_path") or "")
                if not path:
                    continue
                item = dict(finding)
                item.setdefault("tool", tool)
                grouped[path.replace("\\", "/")].append(item)
    return grouped
