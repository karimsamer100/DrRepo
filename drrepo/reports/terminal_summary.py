from typing import Any, Dict, List


def _safe_get(d: Dict[str, Any], key: str, default: Any = None) -> Any:
    return d.get(key, default) if isinstance(d, dict) else default


def _limitation_reason(entry: Dict[str, Any]) -> str | None:
    tool = entry.get("tool") or entry.get("name") or "unknown"
    status = entry.get("status")
    summary = entry.get("summary") if isinstance(entry.get("summary"), dict) else {}
    if status == "skipped_by_config":
        reason = summary.get("reason") or "Skipped by configuration."
        return f"{tool}: {reason}"
    if status == "not_available":
        return f"{tool}: tool unavailable in this environment."
    return None


def render_terminal_summary(audit: Dict[str, Any]) -> str:
    if not isinstance(audit, dict):
        audit = {}

    lines: List[str] = []
    lines.append("# DrRepo Audit Summary")
    path = _safe_get(audit, "path", "unknown")
    source = _safe_get(audit, "source", {}) or {}
    source_value = _safe_get(source, "value")
    scoring = _safe_get(audit, "scoring", {}) or {}
    overall = _safe_get(scoring, "overall_score", _safe_get(scoring, "overall", "unknown"))

    diagnosis = _safe_get(audit, "diagnosis", {}) or {}
    repo_health = _safe_get(diagnosis, "repository_health", {}) or {}
    label = _safe_get(repo_health, "label", "unknown")
    summary = _safe_get(repo_health, "summary", "unknown")

    if source_value:
        lines.append(f"Source: {source_value}")
    else:
        lines.append(f"Path: {path}")
    lines.append(f"Overall score: {overall}")
    # Repository & portfolio scores
    repo_health_score = _safe_get(scoring, "repository_health_score")
    port_ready_score = _safe_get(scoring, "portfolio_readiness_score")
    if repo_health_score is not None:
        lines.append(f"Repository health score: {repo_health_score}")
    if port_ready_score is not None:
        lines.append(f"Portfolio readiness score: {port_ready_score}")
    lines.append(f"Diagnosis: {label}")
    lines.append(f"Summary: {summary}")
    lines.append("")

    hard_flags = _safe_get(diagnosis, "hard_flags", []) or []
    limitations = _safe_get(diagnosis, "limitations", []) or []
    evidence_confidence = _safe_get(diagnosis, "evidence_confidence", {}) or {}
    lines.append("Hard flags:")
    lines.append(", ".join(hard_flags) if hard_flags else "None")
    lines.append("")
    lines.append("Limitations:")
    lines.append(", ".join(limitations) if limitations else "None")
    if evidence_confidence:
        lines.append("")
        lines.append(
            "Evidence confidence: "
            + str(_safe_get(evidence_confidence, "summary", _safe_get(evidence_confidence, "label", "unknown")))
        )
    lines.append("")

    evidence_limitations: List[str] = []
    for sec in ("static_analysis", "test_analysis", "repository_analysis"):
        entries = _safe_get(audit, sec, []) or []
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            reason = _limitation_reason(entry)
            if reason:
                evidence_limitations.append(reason)
    lines.append("Evidence limitations / unavailable tools:")
    lines.append(", ".join(evidence_limitations) if evidence_limitations else "None")
    lines.append("")

    # Suggestions: top 3 actions
    suggestions = _safe_get(audit, "remediation_suggestions", []) or []
    lines.append("")
    # Suggestions summary and top actions
    total = None
    rem_summary = _safe_get(audit, "remediation_summary", {}) or {}
    if isinstance(rem_summary, dict):
        total = rem_summary.get("total")
    if total is None:
        try:
            total = len(suggestions) if isinstance(suggestions, list) else 0
        except Exception:
            total = 0

    lines.append("")
    lines.append(f"Suggestions: {total}")
    lines.append("Top actions:")
    if suggestions and isinstance(suggestions, list):
        top = suggestions[:3]
        for idx, s in enumerate(top, start=1):
            sev = s.get("severity") or "unknown"
            title = s.get("title") or "unknown"
            action = s.get("action") or "unknown"
            lines.append(f"{idx}. [{sev}] {title} — {action}")
    else:
        lines.append("None")

    # Category scores compact block
    cats = _safe_get(scoring, "categories", {}) or {}
    if cats:
        lines.append("")
        lines.append("Category scores:")
        for cat in ("code_quality", "testing", "security", "maintainability", "documentation", "structure"):
            lines.append(f"- {cat}: {cats.get(cat, 'N/A')}")

    # Analyzer statuses
    def _format_section(sec_name: str) -> str:
        entries = _safe_get(audit, sec_name, []) or []
        if not isinstance(entries, list):
            return ""
        parts = []
        for e in entries:
            if not isinstance(e, dict):
                continue
            tool = e.get("tool") or e.get("name") or "unknown"
            status = e.get("status") or "unknown"
            parts.append(f"{tool}={status}")
        return ", ".join(parts)

    lines.append("")
    lines.append("Analyzer status:")
    lines.append(f"- static_analysis: {_format_section('static_analysis')}")
    lines.append(f"- test_analysis: {_format_section('test_analysis')}")
    lines.append(f"- repository_analysis: {_format_section('repository_analysis')}")

    return "\n".join(lines)
