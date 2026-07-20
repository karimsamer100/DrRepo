"""Evidence grounding for AI advisor output.

Builds an explicit evidence index from a deterministic audit and validates
that provider-generated advisor references only point to real audit findings,
files, analyzers, scores, and project facts.
"""
from __future__ import annotations

import re
from typing import Any


_GROUNDING_VERSION = "v1"


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_str(value: Any) -> str:
    return str(value) if value is not None else ""


_WINDOWS_ABS_RE = re.compile(r"^[A-Za-z]:")
_LINE_REF_RE = re.compile(r"^(.+):(\d+)$")

_KNOWN_ANALYZERS = {
    "bandit",
    "coverage",
    "mypy",
    "pytest",
    "radon",
    "readme",
    "ruff",
    "structure",
    "repository_intelligence",
    "architecture_graph",
    "ci_config",
    "container_config",
}
_KNOWN_FRAMEWORKS = {
    "django",
    "fastapi",
    "flask",
    "react",
    "vue",
    "angular",
    "svelte",
    "next.js",
    "nextjs",
    "express",
    "spring",
}
_KNOWN_INTERFACES = {"cli", "rest_api", "graphql", "web_ui", "api", "library"}


def normalize_evidence_path(path: str, audit_root: str | None = None) -> str | None:
    """Normalize a repository-relative path for grounding.

    - Converts backslashes to forward slashes.
    - Removes leading `./`.
    - Rejects absolute paths (including Windows drive letters), parent traversal,
      and empty paths.
    - Optionally strips the audit root prefix while indexing deterministic audit
      evidence; provider references should call this without an audit root.
    """
    if not isinstance(path, str) or not path:
        return None

    # Convert backslashes and strip whitespace
    normalized = path.replace("\\", "/").strip()
    if not normalized:
        return None

    # Optional: strip audit root prefix while building the evidence index from
    # analyzer output. Provider-sourced references pass no audit_root and remain
    # repository-relative only.
    if audit_root and (path.startswith(audit_root) or path.startswith(str(audit_root).replace("/", "\\"))):
        suffix = path[len(str(audit_root)):]
        normalized = suffix.replace("\\", "/").strip("/")

    # Reject absolute paths and traversal.
    if (
        normalized.startswith("/")
        or normalized.startswith("//")
        or "://" in normalized
        or _WINDOWS_ABS_RE.match(normalized)
        or ".." in normalized.split("/")
    ):
        return None

    # Remove leading ./
    while normalized.startswith("./"):
        normalized = normalized[2:]

    if not normalized or normalized == ".":
        return None

    return normalized


def _add_violation(violations: list[dict[str, str]], code: str, description: str) -> None:
    violations.append({"code": code, "description": description})


def _allowed_lower(index: dict[str, Any], key: str) -> set[str]:
    values = index.get(key, set())
    if not isinstance(values, set):
        return set()
    return {_safe_str(value).lower() for value in values if _safe_str(value)}


def _collect_tool_findings(audit: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for section in ("static_analysis", "test_analysis", "repository_analysis"):
        entries = _as_list(audit.get(section))
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            tool = _safe_str(entry.get("tool") or entry.get("name"))
            for finding in _as_list(entry.get("findings")):
                if not isinstance(finding, dict):
                    continue
                findings.append({
                    "tool": tool,
                    "code": _safe_str(finding.get("code")),
                    "message": _safe_str(finding.get("message")),
                    "file_path": normalize_evidence_path(_safe_str(finding.get("file_path")), audit.get("path")),
                    "line": finding.get("line") if isinstance(finding.get("line"), int) else None,
                    "severity": _safe_str(finding.get("severity")),
                })
    return findings


def _collect_devops_blockers(audit: dict[str, Any]) -> list[dict[str, Any]]:
    devops = _as_dict(audit.get("devops_readiness"))
    blockers: list[dict[str, Any]] = []
    for blocker in _as_list(devops.get("blockers")):
        if not isinstance(blocker, dict):
            continue
        blockers.append({
            "id": _safe_str(blocker.get("id")),
            "title": _safe_str(blocker.get("title")),
            "category": _safe_str(blocker.get("category")),
        })
    return blockers


def _collect_recommendation_ids(audit: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for rec in _as_list(audit.get("recommendations_v2")):
        if isinstance(rec, dict):
            rid = _safe_str(rec.get("id"))
            if rid:
                ids.add(rid)
    for suggestion in _as_list(audit.get("remediation_suggestions")):
        if isinstance(suggestion, dict):
            code = _safe_str(suggestion.get("code"))
            if code:
                ids.add(code)
    return ids


def _collect_pytest_outcome(audit: dict[str, Any]) -> dict[str, Any]:
    outcome: dict[str, Any] = {"outcome": "unknown", "summary": None}
    for entry in _as_list(audit.get("test_analysis")):
        if not isinstance(entry, dict):
            continue
        if _safe_str(entry.get("tool")).lower() == "pytest":
            summary = _as_dict(entry.get("summary"))
            outcome["summary"] = summary
            if entry.get("status") == "completed":
                if isinstance(entry.get("findings"), list) and entry["findings"]:
                    outcome["outcome"] = "failed"
                else:
                    outcome["outcome"] = "passed"
            else:
                outcome["outcome"] = _safe_str(entry.get("status"))
            break
    return outcome


def _collect_coverage_value(audit: dict[str, Any]) -> dict[str, Any]:
    value: dict[str, Any] = {"percent": None, "status": "unknown"}
    for entry in _as_list(audit.get("test_analysis")):
        if not isinstance(entry, dict):
            continue
        if _safe_str(entry.get("tool")).lower() == "coverage":
            summary = _as_dict(entry.get("summary"))
            percent = summary.get("coverage_percent")
            if isinstance(percent, (int, float)):
                value["percent"] = percent
            value["status"] = _safe_str(entry.get("status"))
            break
    return value


def _collect_project_facts(audit: dict[str, Any]) -> dict[str, set[str]]:
    facts: dict[str, set[str]] = {
        "project_types": set(),
        "frameworks": set(),
        "interfaces": set(),
        "entry_points": set(),
    }
    understanding = _as_dict(audit.get("project_understanding"))
    identity = _as_dict(understanding.get("project_identity"))
    facts["project_types"].add(_safe_str(identity.get("project_type")).lower())
    facts["project_types"].update(_safe_str(t).lower() for t in _as_list(identity.get("secondary_project_types")))
    facts["frameworks"].update(_safe_str(t).lower() for t in _as_list(identity.get("frameworks")))
    facts["interfaces"].update(_safe_str(t).lower() for t in _as_list(identity.get("interfaces")))
    for entry in _as_list(understanding.get("entry_points")):
        if isinstance(entry, dict):
            path = normalize_evidence_path(_safe_str(entry.get("path")), audit.get("path"))
            if path:
                facts["entry_points"].add(path)
            symbol = _safe_str(entry.get("symbol"))
            if symbol:
                facts["entry_points"].add(symbol)
    return facts


def _collect_architecture_facts(audit: dict[str, Any]) -> dict[str, set[str]]:
    architecture = _as_dict(audit.get("architecture_assessment"))
    facts: dict[str, set[str]] = {
        "architecture_node_ids": set(),
        "architecture_hotspot_ids": set(),
        "architecture_cycle_ids": set(),
        "architecture_paths": set(),
    }
    for node in _as_list(architecture.get("nodes")):
        if not isinstance(node, dict):
            continue
        node_id = _safe_str(node.get("id"))
        if node_id:
            facts["architecture_node_ids"].add(node_id)
        path = normalize_evidence_path(_safe_str(node.get("path")), audit.get("path"))
        if path:
            facts["architecture_paths"].add(path)
    for hotspot in _as_list(architecture.get("hotspots")):
        if not isinstance(hotspot, dict):
            continue
        hotspot_id = _safe_str(hotspot.get("id"))
        if hotspot_id:
            facts["architecture_hotspot_ids"].add(hotspot_id)
        node_id = _safe_str(hotspot.get("node_id"))
        if node_id:
            facts["architecture_node_ids"].add(node_id)
        path = normalize_evidence_path(_safe_str(hotspot.get("path")), audit.get("path"))
        if path:
            facts["architecture_paths"].add(path)
    for cycle in _as_list(architecture.get("cycles")):
        if not isinstance(cycle, dict):
            continue
        cycle_id = _safe_str(cycle.get("id"))
        if cycle_id:
            facts["architecture_cycle_ids"].add(cycle_id)
        for path_value in _as_list(cycle.get("paths")):
            path = normalize_evidence_path(_safe_str(path_value), audit.get("path"))
            if path:
                facts["architecture_paths"].add(path)
    return facts


def build_evidence_index(audit: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic index of allowed audit references.

    The index is used to validate provider-generated advisor output.
    """
    audit = _as_dict(audit)
    findings = _collect_tool_findings(audit)

    analyzer_ids: set[str] = set()
    for section in ("static_analysis", "test_analysis", "repository_analysis"):
        for entry in _as_list(audit.get(section)):
            if isinstance(entry, dict):
                tool = _safe_str(entry.get("tool") or entry.get("name"))
                if tool:
                    analyzer_ids.add(tool)

    finding_codes: set[str] = set()
    file_paths: set[str] = set()
    line_references: set[str] = set()
    for finding in findings:
        code = finding["code"]
        if code:
            finding_codes.add(code)
        if finding["tool"]:
            finding_codes.add(finding["tool"])
        if finding["file_path"]:
            file_paths.add(finding["file_path"])
            if finding["line"] is not None:
                line_references.add(f"{finding['file_path']}:{finding['line']}")

    scoring = _as_dict(audit.get("scoring"))
    diagnosis = _as_dict(audit.get("diagnosis"))
    repo_health = _as_dict(diagnosis.get("repository_health"))

    devops = _as_dict(audit.get("devops_readiness"))
    devops_blocker_ids = {b["id"] for b in _collect_devops_blockers(audit) if b["id"]}
    devops_blocker_titles = {b["title"] for b in _collect_devops_blockers(audit) if b["title"]}

    facts = _collect_project_facts(audit)
    architecture_facts = _collect_architecture_facts(audit)
    file_paths.update(architecture_facts["architecture_paths"])

    return {
        "version": _GROUNDING_VERSION,
        "overall_score": scoring.get("overall_score") if isinstance(scoring.get("overall_score"), (int, float)) else None,
        "repository_health_score": scoring.get("repository_health_score") if isinstance(scoring.get("repository_health_score"), (int, float)) else None,
        "verdict": _safe_str(repo_health.get("label")).lower() if isinstance(repo_health.get("label"), str) else None,
        "pytest_outcome": _collect_pytest_outcome(audit),
        "coverage": _collect_coverage_value(audit),
        "analyzer_ids": analyzer_ids,
        "finding_codes": finding_codes,
        "file_paths": file_paths,
        "line_references": line_references,
        "recommendation_ids": _collect_recommendation_ids(audit),
        "devops_blocker_ids": devops_blocker_ids,
        "devops_blocker_titles": devops_blocker_titles,
        "project_types": facts["project_types"],
        "frameworks": facts["frameworks"],
        "interfaces": facts["interfaces"],
        "entry_points": facts["entry_points"],
        "architecture_node_ids": architecture_facts["architecture_node_ids"],
        "architecture_hotspot_ids": architecture_facts["architecture_hotspot_ids"],
        "architecture_cycle_ids": architecture_facts["architecture_cycle_ids"],
    }


def _check_text_claims(text: str, index: dict[str, Any], violations: list[dict[str, str]]) -> None:
    """Check free-text fields for contradictions with known audit facts.

    This is intentionally bounded and deterministic: it looks for exact
    or near-exact mentions of scores, verdicts, pytest outcomes, coverage
    values, and project facts that do not appear in the evidence index.
    """
    lowered = text.lower()

    # Score contradictions
    overall_score = index.get("overall_score")
    if overall_score is not None:
        # Look for phrases like "overall score is 88" or "score of 88"
        for match in re.finditer(r"(?:overall score|score)\s+(?:is|of)\s+(\d+)", lowered):
            claimed = int(match.group(1))
            if abs(claimed - overall_score) > 2:
                _add_violation(violations, "score_contradiction", f"Claimed overall score {claimed} does not match audit score {overall_score}.")

    # Verdict contradictions
    verdict = index.get("verdict")
    if verdict and verdict != "unknown":
        # Look for explicit verdict claims
        if re.search(rf"verdict\s+(?:is|of)\s+\b({re.escape(verdict)})\b", lowered):
            # Allowed; do nothing
            pass
        # Look for contradictory verdicts
        contradictory = {"healthy": "needs", "needs major improvement": "healthy", "needs improvement": "healthy"}
        for known, opposite in contradictory.items():
            if known != verdict and re.search(rf"\b{re.escape(known)}\b", lowered):
                _add_violation(violations, "verdict_contradiction", f"Claimed verdict {known} does not match audit verdict {verdict}.")

    # Pytest outcome contradictions
    pytest_outcome = index.get("pytest_outcome", {}).get("outcome")
    if pytest_outcome == "passed":
        if "tests failed" in lowered or "pytest failed" in lowered:
            _add_violation(violations, "pytest_contradiction", "Claimed pytest failed, but audit evidence says pytest passed.")
    elif pytest_outcome == "failed":
        if "tests passed" in lowered or "pytest passed" in lowered:
            _add_violation(violations, "pytest_contradiction", "Claimed pytest passed, but audit evidence says pytest failed.")

    # Coverage contradictions
    coverage_percent = index.get("coverage", {}).get("percent")
    if coverage_percent is not None:
        for match in re.finditer(r"coverage\s+(?:is|of)\s+(\d+)\s*%", lowered):
            claimed = int(match.group(1))
            if abs(claimed - coverage_percent) > 5:
                _add_violation(violations, "coverage_contradiction", f"Claimed coverage {claimed}% does not match audit coverage {coverage_percent}%.")

    analyzer_allowed = _allowed_lower(index, "analyzer_ids")
    for analyzer in _KNOWN_ANALYZERS - analyzer_allowed:
        if re.search(rf"\b{re.escape(analyzer)}\b", lowered):
            _add_violation(violations, "unknown_analyzer_id", f"Referenced analyzer '{analyzer}' is not present in audit evidence.")

    framework_allowed = _allowed_lower(index, "frameworks")
    for framework in _KNOWN_FRAMEWORKS - framework_allowed:
        if re.search(rf"\b{re.escape(framework)}\b", lowered):
            _add_violation(violations, "invented_framework", f"Referenced framework '{framework}' is not present in audit evidence.")

    interface_allowed = _allowed_lower(index, "interfaces")
    for interface in _KNOWN_INTERFACES - interface_allowed:
        if re.search(rf"\b{re.escape(interface)}\b", lowered):
            _add_violation(violations, "invented_interface", f"Referenced interface '{interface}' is not present in audit evidence.")

    entry_points = _allowed_lower(index, "entry_points")
    for match in re.finditer(r"(?:entry point|entrypoint)\s+(?:is|at|`)?\s*([a-z0-9_./\\-]+)", lowered):
        entry = normalize_evidence_path(match.group(1))
        if entry and entry.lower() not in entry_points:
            _add_violation(violations, "invented_entry_point", f"Referenced entry point '{entry}' is not present in audit evidence.")


def _check_action_grounding(action: dict[str, Any], index: dict[str, Any], violations: list[dict[str, str]]) -> int:
    """Check a single advisor action against the evidence index."""
    if not isinstance(action, dict):
        return 0

    title = _safe_str(action.get("title"))
    evidence = _as_list(action.get("evidence"))
    validated_refs = 0

    # Check evidence references
    for ref in evidence:
        ref_str = _safe_str(ref)
        if not ref_str:
            continue
        normalized_ref = normalize_evidence_path(ref_str, None)
        line_ref = _LINE_REF_RE.match(ref_str.replace("\\", "/").strip())
        normalized_line_ref = None
        if line_ref:
            ref_path = normalize_evidence_path(line_ref.group(1), None)
            if ref_path:
                normalized_line_ref = f"{ref_path}:{line_ref.group(2)}"
        allowed_sets = [
            index.get("finding_codes", set()),
            index.get("recommendation_ids", set()),
            index.get("devops_blocker_ids", set()),
            index.get("devops_blocker_titles", set()),
            index.get("analyzer_ids", set()),
            index.get("architecture_node_ids", set()),
            index.get("architecture_hotspot_ids", set()),
            index.get("architecture_cycle_ids", set()),
            index.get("file_paths", set()),
            index.get("line_references", set()),
        ]
        # Also allow the title itself as a reference if it matches a known code
        if any(
            ref_str in allowed_set
            or (normalized_ref and normalized_ref in allowed_set)
            or (normalized_line_ref and normalized_line_ref in allowed_set)
            for allowed_set in allowed_sets
        ):
            validated_refs += 1
            continue
        if normalized_ref is None:
            _add_violation(violations, "invalid_path_reference", "Evidence reference must be repository-relative and cannot be absolute or contain traversal.")
            continue
        # If the ref looks like a path or line reference but isn't in the index, flag it
        if ref_str.startswith("node:"):
            _add_violation(violations, "unknown_architecture_node_id", f"Architecture node '{ref_str}' is not present in audit evidence.")
        elif ref_str.startswith("hotspot:"):
            _add_violation(violations, "unknown_hotspot_id", f"Architecture hotspot '{ref_str}' is not present in audit evidence.")
        elif ref_str.startswith("cycle:"):
            _add_violation(violations, "unknown_cycle_id", f"Architecture cycle '{ref_str}' is not present in audit evidence.")
        elif line_ref and normalized_line_ref not in index.get("line_references", set()):
            _add_violation(violations, "unsupported_line_reference", f"Line reference '{normalized_line_ref}' is not present in audit evidence.")
        elif "/" in ref_str or ":" in ref_str or "\\" in ref_str:
            _add_violation(violations, "unknown_file_path", f"File path '{normalized_ref}' is not present in audit evidence.")
        elif len(ref_str) > 3:
            # Likely a code or title; flag if it doesn't match anything known
            code = "unknown_evidence_reference"
            if ref_str.isupper() and "NO-" in ref_str:
                code = "unknown_blocker_id"
            elif ref_str.isupper() and "-" in ref_str:
                code = "unknown_finding_or_recommendation_id"
            _add_violation(violations, code, f"Evidence reference '{ref_str}' is not present in audit evidence.")

    # Check text claims in title and why_it_matters
    why = _safe_str(action.get("why_it_matters"))
    fix = _safe_str(action.get("suggested_fix"))
    combined = f"{title} {why} {fix}"
    _check_text_claims(combined, index, violations)
    return validated_refs


def validate_grounding(
    advisor_response: dict[str, Any],
    evidence_index: dict[str, Any],
) -> dict[str, Any]:
    """Validate provider-generated advisor output against the evidence index.

    Returns a structured grounding result. The deterministic fallback is not
    passed through this validator; it is treated as trusted by construction.
    """
    violations: list[dict[str, str]] = []
    checked = 0
    validated = 0
    validated_refs = 0

    advisor_response = _as_dict(advisor_response)

    # Check summary/profile_context for contradictions
    for field in ("summary", "profile_context"):
        text = _safe_str(advisor_response.get(field))
        if text:
            checked += 1
            before = len(violations)
            _check_text_claims(text, evidence_index, violations)
            if len(violations) == before:
                validated += 1

    # Check each action's evidence references
    for field in ("top_priorities", "lower_priority_items"):
        for action in _as_list(advisor_response.get(field)):
            checked += 1
            before = len(violations)
            validated_refs += _check_action_grounding(action, evidence_index, violations)
            if len(violations) == before:
                validated += 1

    violation_codes = [item["code"] for item in violations]
    violation_descriptions = [item["description"] for item in violations]
    return {
        "valid": len(violations) == 0,
        "status": "valid" if len(violations) == 0 else "rejected",
        "checked_claims": checked,
        "validated_references": validated_refs if validated_refs else validated,
        "violation_codes": violation_codes,
        "violation_details": violations,
        "violations": violation_descriptions,
    }
