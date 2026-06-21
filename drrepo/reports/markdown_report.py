from typing import Any, Dict, List, Optional

def _safe_get(d: Dict[str, Any], key: str, default: Any = None) -> Any:
    return d.get(key, default) if isinstance(d, dict) else default


def _format_bool(v: Optional[bool]) -> str:
    if v is True:
        return "Yes"
    if v is False:
        return "No"
    return "N/A"


def _count_findings(tool_entry: Dict[str, Any]) -> int:
    findings = tool_entry.get("findings")
    if findings is None:
        return 0
    if isinstance(findings, list):
        return len(findings)
    return 0


def _count_errors(tool_entry: Dict[str, Any]) -> int:
    errors = tool_entry.get("errors")
    if errors is None:
        return 0
    if isinstance(errors, list):
        return len(errors)
    return 0


def render_markdown_report(audit: Dict[str, Any]) -> str:
    """Render an audit dictionary into a Markdown string.

    The function is defensive: missing keys are handled gracefully.
    """
    if not isinstance(audit, dict):
        audit = {}

    lines: List[str] = []

    # Title
    lines.append("# DrRepo Audit Report")

    # Repository
    lines.append("## Repository")
    path = _safe_get(audit, "path", "N/A")
    status = _safe_get(audit, "status", "N/A")
    lines.append(f"- **Path**: {path}")
    lines.append(f"- **Status**: {status}")

    # Score Summary
    lines.append("")
    lines.append("## Score Summary")
    scoring = _safe_get(audit, "scoring", {}) or {}
    overall = _safe_get(scoring, "overall_score", "N/A")
    lines.append(f"- **Overall score**: {overall}")
    sections = _safe_get(scoring, "sections", {}) or {}
    for sec in ("static_analysis", "test_analysis", "repository_analysis"):
        secscore = _safe_get(sections, sec, {})
        s = _safe_get(secscore, "score", "N/A")
        lines.append(f"- **{sec}**: {s}")

    # Diagnosis
    lines.append("")
    lines.append("## Diagnosis")
    diagnosis = _safe_get(audit, "diagnosis", {}) or {}
    repo_health = _safe_get(diagnosis, "repository_health", {}) or {}
    label = _safe_get(repo_health, "label", "N/A")
    score_val = _safe_get(repo_health, "score", "N/A")
    summary_text = _safe_get(repo_health, "summary", "N/A")
    hard_flags = _safe_get(diagnosis, "hard_flags", []) or []
    limitations = _safe_get(diagnosis, "limitations", []) or []

    lines.append(f"- Label: {label}")
    lines.append(f"- Summary: {summary_text}")
    lines.append(f"- Hard flags: {', '.join(hard_flags) if hard_flags else 'None'}")
    lines.append(f"- Limitations: {', '.join(limitations) if limitations else 'None'}")

    # Metadata Summary
    lines.append("")
    lines.append("## Metadata Summary")
    metadata = _safe_get(audit, "metadata", {}) or {}
    # List common metadata keys
    meta_keys = [
        ("total_files", "Total files"),
        ("total_directories", "Total directories"),
        ("python_files", "Python files"),
        ("test_files", "Test files"),
        ("has_readme", "Has README"),
        ("has_tests", "Has tests"),
        ("has_docs", "Has docs"),
        ("has_pyproject", "Has pyproject"),
        ("has_gitignore", "Has .gitignore"),
    ]
    for key, label in meta_keys:
        val = metadata.get(key)
        if isinstance(val, bool):
            val_str = _format_bool(val)
        else:
            val_str = str(val) if val is not None else "N/A"
        lines.append(f"- **{label}**: {val_str}")

    # Analyzer Summary (table)
    lines.append("")
    lines.append("## Analyzer Summary")
    lines.append("")
    lines.append("| Section | Tool | Status | Findings | Errors |")
    lines.append("|---|---|---:|---:|---:|")

    def _render_section_table(section_name: str) -> None:
        entries = _safe_get(audit, section_name, []) or []
        if not isinstance(entries, list):
            return
        for entry in entries:
            tool = entry.get("tool") or entry.get("name") or "-"
            status = entry.get("status", "N/A")
            findings = _count_findings(entry)
            errors = _count_errors(entry)
            lines.append(f"| {section_name} | {tool} | {status} | {findings} | {errors} |")

    _render_section_table("static_analysis")
    _render_section_table("test_analysis")
    _render_section_table("repository_analysis")

    # Prioritized Action Plan (Remediation Suggestions)
    lines.append("")
    lines.append("## Prioritized Action Plan")
    suggestions = _safe_get(audit, "remediation_suggestions", []) or []
    summary = _safe_get(audit, "remediation_summary", {}) or {}

    def _escape_cell(text: str) -> str:
        return text.replace("|", "\\|") if isinstance(text, str) else str(text)

    if suggestions and isinstance(suggestions, list):
        # Optional summary lines
        total = summary.get("total") if isinstance(summary, dict) else None
        if isinstance(total, int):
            lines.append(f"Total suggestions: {total}")
        by_sev = summary.get("by_severity") if isinstance(summary, dict) else None
        if isinstance(by_sev, dict) and by_sev:
            # deterministic order by key
            parts = [f"{k}={by_sev[k]}" for k in sorted(by_sev.keys())]
            lines.append(f"By severity: {', '.join(parts)}")

        lines.append("")
        lines.append("| Severity | Section | Tool | Title | Action |")
        lines.append("|---|---|---|---|---|")
        for s in suggestions:
            if not isinstance(s, dict):
                continue
            sev = s.get("severity") or "unknown"
            sec = s.get("section") or "unknown"
            tool = s.get("tool") or "unknown"
            title = _escape_cell(s.get("title") or "")
            action = _escape_cell(s.get("action") or "")
            lines.append(f"| {sev} | {sec} | {tool} | {title} | {action} |")
    else:
        lines.append("No remediation suggestions generated.")

    # Findings
    lines.append("")
    lines.append("## Findings")
    any_findings = False
    for sec in ("static_analysis", "test_analysis", "repository_analysis"):
        entries = _safe_get(audit, sec, []) or []
        if not isinstance(entries, list):
            continue
        for entry in entries:
            tool = entry.get("tool") or entry.get("name") or sec
            findings = entry.get("findings") or []
            if findings:
                any_findings = True
                lines.append(f"### {sec} / {tool}")
                for f in findings:
                    severity = f.get("severity", "unknown")
                    code = f.get("code", "")
                    message = f.get("message", "")
                    file_path = f.get("file_path")
                    line = f.get("line")
                    loc = ""
                    if file_path:
                        loc = file_path
                        if line:
                            loc = f"{loc}:{line}"
                    loc_part = f" ({loc})" if loc else ""
                    lines.append(f"- **{severity}** `{code}`: {message}{loc_part}")

    if not any_findings:
        lines.append("No findings reported.")

    # Errors
    lines.append("")
    lines.append("## Errors")
    any_errors = False
    for sec in ("static_analysis", "test_analysis", "repository_analysis"):
        entries = _safe_get(audit, sec, []) or []
        if not isinstance(entries, list):
            continue
        for entry in entries:
            tool = entry.get("tool") or entry.get("name") or sec
            errors = entry.get("errors") or []
            if errors:
                any_errors = True
                lines.append(f"### {sec} / {tool}")
                for e in errors:
                    lines.append(f"- {e}")

    if not any_errors:
        lines.append("No analyzer errors reported.")

    return "\n".join(lines)
