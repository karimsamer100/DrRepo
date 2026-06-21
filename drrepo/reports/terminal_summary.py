from typing import Any, Dict, List


def _safe_get(d: Dict[str, Any], key: str, default: Any = None) -> Any:
    return d.get(key, default) if isinstance(d, dict) else default


def render_terminal_summary(audit: Dict[str, Any]) -> str:
    if not isinstance(audit, dict):
        audit = {}

    lines: List[str] = []
    lines.append("# DrRepo Audit Summary")
    path = _safe_get(audit, "path", "unknown")
    scoring = _safe_get(audit, "scoring", {}) or {}
    overall = _safe_get(scoring, "overall_score", _safe_get(scoring, "overall", "unknown"))

    diagnosis = _safe_get(audit, "diagnosis", {}) or {}
    repo_health = _safe_get(diagnosis, "repository_health", {}) or {}
    label = _safe_get(repo_health, "label", "unknown")
    summary = _safe_get(repo_health, "summary", "unknown")

    lines.append(f"Path: {path}")
    lines.append(f"Overall score: {overall}")
    lines.append(f"Diagnosis: {label}")
    lines.append(f"Summary: {summary}")
    lines.append("")

    hard_flags = _safe_get(diagnosis, "hard_flags", []) or []
    limitations = _safe_get(diagnosis, "limitations", []) or []
    lines.append("Hard flags:")
    lines.append(", ".join(hard_flags) if hard_flags else "None")
    lines.append("")
    lines.append("Limitations:")
    lines.append(", ".join(limitations) if limitations else "None")
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
