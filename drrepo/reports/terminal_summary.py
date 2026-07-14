from typing import Any, Dict, List


def _safe_get(d: Dict[str, Any], key: str, default: Any = None) -> Any:
    return d.get(key, default) if isinstance(d, dict) else default


def _limitation_reason(entry: Dict[str, Any]) -> str | None:
    tool = entry.get("tool") or entry.get("name") or "unknown"
    status = entry.get("status")
    summary = entry.get("summary") if isinstance(entry.get("summary"), dict) else {}
    if status == "skipped_by_config":
        reason = entry.get("skipped_reason") or summary.get("reason") or "Skipped by configuration."
        return f"{tool}: {reason}"
    if status == "not_available":
        reason = entry.get("unavailable_reason") or "tool unavailable in this environment."
        return f"{tool}: {reason}"
    if status == "failed_to_run":
        errors = entry.get("errors") or []
        reason = str(errors[0]).strip() if isinstance(errors, list) and errors else "Analyzer failed to run."
        return f"{tool}: analyzer failed to run ({reason})"
    if status == "partial":
        errors = entry.get("errors") or []
        reason = summary.get("partial_reason") or (str(errors[0]).strip() if isinstance(errors, list) and errors else "Analyzer produced partial evidence.")
        return f"{tool}: partial evidence ({reason})"
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

    executive = _safe_get(audit, "executive_report", {}) or {}
    understanding = _safe_get(audit, "project_understanding", {}) or {}
    identity = _safe_get(understanding, "project_identity", {}) or {}
    runnability = _safe_get(understanding, "runnability", {}) or {}
    devops = _safe_get(audit, "devops_readiness", {}) or {}

    if executive:
        lines.append(str(_safe_get(executive, "headline", "Executive summary")))
        summary_line = _safe_get(executive, "one_sentence_summary")
        if summary_line:
            lines.append(str(summary_line))
        next_step = _safe_get(executive, "next_best_step")
        if next_step:
            lines.append(f"Next best step: {next_step}")
        lines.append("")

    if identity:
        lines.append(f"Project type: {_safe_get(identity, 'project_type', 'unknown')}")
        frameworks = _safe_get(identity, "frameworks", []) or []
        if frameworks:
            lines.append("Frameworks: " + ", ".join(frameworks))
    if runnability:
        lines.append(f"Runnability: {_safe_get(runnability, 'status', 'unknown')}")
    if identity or runnability:
        lines.append("")

    if devops:
        score = _safe_get(devops, "observed_score")
        lines.append(
            "DevOps readiness: "
            f"{_safe_get(devops, 'verdict', 'unknown')} "
            f"({score if score is not None else 'not assessed'}, confidence {_safe_get(devops, 'evidence_confidence', 'unknown')})"
        )
        next_step = _safe_get(devops, "next_best_step")
        if next_step:
            lines.append(f"Release next step: {next_step}")
        blockers = _safe_get(devops, "blockers", []) or []
        if blockers:
            titles = [str(item.get("title", "blocker")) for item in blockers if isinstance(item, dict)]
            lines.append("Release blockers: " + ", ".join(titles[:3]))
        lines.append("")

    if source_value:
        lines.append(f"Source: {source_value}")
    else:
        lines.append(f"Path: {path}")
    analysis = _safe_get(audit, "analysis", {}) or {}
    if analysis:
        lines.append(f"Analysis mode: {_safe_get(analysis, 'mode', 'unknown')}")
        lines.append(f"Executes repository code: {_safe_get(analysis, 'executes_repository_code', False)}")
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
    recommendations_v2 = _safe_get(audit, "recommendations_v2", []) or []
    suggestions = recommendations_v2 or _safe_get(audit, "remediation_suggestions", []) or []
    lines.append("")
    # Suggestions summary and top actions
    total = None
    rem_summary = _safe_get(audit, "remediation_summary", {}) or {}
    if recommendations_v2:
        total = len(recommendations_v2)
    elif isinstance(rem_summary, dict):
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
            action = s.get("success_check") or s.get("action") or "unknown"
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
