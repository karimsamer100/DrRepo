from typing import Any, Dict, List, Optional
from pathlib import Path

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
    if tool_entry.get("status") in {"not_available", "skipped_by_config"}:
        return 0
    errors = tool_entry.get("errors")
    if errors is None:
        return 0
    if isinstance(errors, list):
        return len(errors)
    return 0


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


def _genuine_errors(entry: Dict[str, Any]) -> List[str]:
    if entry.get("status") not in {"failed_to_run", "partial"}:
        return []
    errors = entry.get("errors") or []
    return [str(error) for error in errors if str(error).strip()] if isinstance(errors, list) else []


def _display_location(file_path: Any, audit_root: Any, source_value: Any) -> str:
    if not isinstance(file_path, str) or not file_path:
        return ""
    if source_value and isinstance(audit_root, str):
        try:
            return str(Path(file_path).resolve().relative_to(Path(audit_root).resolve()))
        except Exception:
            pass
    return file_path


def _format_ai_advisor_section(ai_advisor: Dict[str, Any] | None) -> str:
    """Render the AI advisor guidance section for Markdown output."""
    if not isinstance(ai_advisor, dict) or not ai_advisor.get("requested"):
        return ""

    status = ai_advisor.get("status", "unknown")
    source = ai_advisor.get("source", "deterministic")
    provider = ai_advisor.get("provider") or "deterministic"
    model = ai_advisor.get("model") or "deterministic-advisor"
    fallback_reason = ai_advisor.get("fallback_reason")
    grounding = ai_advisor.get("grounding_result") or {}

    lines: List[str] = []
    lines.append("")
    lines.append("## AI Advisor Guidance")
    lines.append("")
    lines.append(f"- **Source**: {source}")
    lines.append(f"- **Status**: {status}")
    if source in {"ai", "llm"}:
        lines.append(f"- **Provider**: {provider}")
        lines.append(f"- **Model**: {model}")
    if grounding:
        lines.append(f"- **Grounding**: {'valid' if grounding.get('valid') else 'rejected'}")
        codes = grounding.get("violation_codes") or []
        if codes:
            lines.append(f"- **Grounding violation codes**: {', '.join(str(code) for code in codes[:6])}")
        violations = grounding.get("violations") or []
        if violations:
            lines.append("- **Grounding violations**:")
            for violation in violations[:6]:
                lines.append(f"  - {violation}")
    if fallback_reason:
        lines.append(f"- **Fallback reason**: {fallback_reason}")

    response = ai_advisor.get("advisor_response") or {}
    summary = response.get("summary")
    profile_context = response.get("profile_context")
    if profile_context:
        lines.append(f"- **Profile context**: {profile_context}")
    if summary:
        lines.append("")
        lines.append(f"**Headline**: {summary}")

    top_priorities = response.get("top_priorities") or []
    lower_priority_items = response.get("lower_priority_items") or []
    limitations = response.get("limitations") or []
    next_steps = response.get("next_steps") or []

    lines.append("")
    lines.append("### Fix-first action")
    if top_priorities:
        first = top_priorities[0]
        lines.append(f"- **{first.get('title', 'Priority')}** ({first.get('priority', 'medium')})")
        why = first.get('why_it_matters')
        if why:
            lines.append(f"  - Why it matters: {why}")
        fix = first.get('suggested_fix')
        if fix:
            lines.append(f"  - Suggested fix: {fix}")
        evidence = first.get('evidence') or []
        if evidence:
            lines.append(f"  - Evidence: {', '.join(str(e) for e in evidence[:4])}")
    else:
        lines.append("- No immediate fix-first action was identified.")

    if top_priorities[1:] or lower_priority_items:
        lines.append("")
        lines.append("### Ordered plan")
        for idx, action in enumerate(top_priorities[1:], start=2):
            lines.append(f"{idx}. **{action.get('title', 'Priority')}** ({action.get('priority', 'medium')})")
        for action in lower_priority_items:
            lines.append(f"- **{action.get('title', 'Lower priority')}** ({action.get('priority', 'low')})")

    if next_steps:
        lines.append("")
        lines.append("### Success checks / next steps")
        for step in next_steps:
            lines.append(f"- {step}")

    if limitations:
        lines.append("")
        lines.append("### Limitations")
        for limitation in limitations:
            lines.append(f"- {limitation}")

    return "\n".join(lines)


def _format_architecture_sections(architecture: Dict[str, Any] | None) -> List[str]:
    if not isinstance(architecture, dict):
        return []
    lines: List[str] = []
    lines.append("")
    lines.append("## Architecture Overview")
    lines.append("")
    lines.append(f"- **Status**: {_safe_get(architecture, 'status', 'unknown')}")
    lines.append(f"- **Confidence**: {_safe_get(architecture, 'confidence', 'unknown')}")
    summary = _safe_get(architecture, "summary")
    if summary:
        lines.append(f"- **Summary**: {summary}")
    entry_points = _safe_get(architecture, "entry_points", []) or []
    if entry_points:
        lines.append("- **Entry points**:")
        for entry in entry_points[:6]:
            if isinstance(entry, dict):
                lines.append(f"  - {entry.get('kind', 'entry')}: `{entry.get('path', 'unknown')}` ({entry.get('confidence', 'unknown')})")
    layers = _safe_get(architecture, "layers", []) or []
    if layers:
        lines.append("- **Layers**:")
        for layer in layers[:8]:
            if isinstance(layer, dict):
                node_count = len(layer.get("node_ids") or []) if isinstance(layer.get("node_ids"), list) else 0
                lines.append(f"  - {layer.get('label', layer.get('id', 'layer'))}: {node_count} node(s)")
    externals = _safe_get(architecture, "external_integrations", []) or []
    if externals:
        lines.append("- **External integrations**: " + ", ".join(str(item.get("name")) for item in externals[:8] if isinstance(item, dict) and item.get("name")))
    cycles = _safe_get(architecture, "cycles", []) or []
    if cycles:
        lines.append("- **Detected cycles**:")
        for cycle in cycles[:4]:
            if isinstance(cycle, dict):
                lines.append(f"  - {cycle.get('id', 'cycle')}: {cycle.get('classification', 'requires review')} ({', '.join(str(p) for p in (cycle.get('paths') or [])[:4])})")
    gaps = _safe_get(architecture, "evidence_gaps", []) or []
    if gaps:
        lines.append("- **Evidence gaps**:")
        for gap in gaps[:4]:
            lines.append(f"  - {gap}")

    hotspots = _safe_get(architecture, "hotspots", []) or []
    lines.append("")
    lines.append("## Top Risk Hotspots")
    if not hotspots:
        lines.append("")
        lines.append("No production hotspot exceeded the v1 threshold.")
        return lines
    for hotspot in hotspots[:8]:
        if not isinstance(hotspot, dict):
            continue
        lines.append("")
        lines.append(f"### {hotspot.get('rank', '-')}. {hotspot.get('path', 'unknown')}")
        lines.append(f"- **Risk**: {hotspot.get('risk_level', 'unknown')} ({hotspot.get('risk_score', 'unknown')})")
        lines.append(f"- **Confidence**: {hotspot.get('confidence', 'unknown')}")
        lines.append(f"- **Test status**: {hotspot.get('test_status', 'unknown')}")
        why = hotspot.get("why_it_matters")
        if why:
            lines.append(f"- **Why it matters**: {why}")
        action = hotspot.get("recommended_action")
        if action:
            lines.append(f"- **Recommended action**: {action}")
        factors = hotspot.get("factors") or []
        if factors:
            lines.append("- **Factors**:")
            for factor in factors[:5]:
                if isinstance(factor, dict):
                    lines.append(f"  - {factor.get('label', factor.get('id', 'factor'))}: +{factor.get('contribution', 0)}")
    return lines


def render_markdown_report(audit: Dict[str, Any], ai_advisor: Dict[str, Any] | None = None) -> str:
    """Render an audit dictionary into a Markdown string.

    The function is defensive: missing keys are handled gracefully.
    """
    if not isinstance(audit, dict):
        audit = {}

    lines: List[str] = []

    # Title
    lines.append("# DrRepo Audit Report")

    executive = _safe_get(audit, "executive_report", {}) or {}
    understanding = _safe_get(audit, "project_understanding", {}) or {}
    identity = _safe_get(understanding, "project_identity", {}) or {}
    runnability = _safe_get(understanding, "runnability", {}) or {}
    entry_points = _safe_get(understanding, "entry_points", []) or []
    recs_v2 = _safe_get(audit, "recommendations_v2", []) or []
    devops = _safe_get(audit, "devops_readiness", {}) or {}
    architecture = _safe_get(audit, "architecture_assessment", {}) or {}

    if executive:
        lines.append("")
        lines.append("## Executive Summary")
        headline = _safe_get(executive, "headline")
        summary = _safe_get(executive, "one_sentence_summary")
        description = _safe_get(executive, "project_description")
        if headline:
            lines.append(f"**{headline}**")
        if summary:
            lines.append("")
            lines.append(str(summary))
        if description:
            lines.append("")
            lines.append(str(description))
        biggest_gap = _safe_get(executive, "biggest_gap")
        next_step = _safe_get(executive, "next_best_step")
        if biggest_gap:
            lines.append(f"- **Biggest gap**: {biggest_gap}")
        if next_step:
            lines.append(f"- **Next best step**: {next_step}")

    if identity:
        lines.append("")
        lines.append("## Project Identity")
        lines.append(f"- **Type**: {_safe_get(identity, 'project_type', 'unknown')}")
        lines.append(f"- **Primary language**: {_safe_get(identity, 'primary_language', 'unknown')}")
        frameworks = _safe_get(identity, "frameworks", []) or []
        interfaces = _safe_get(identity, "interfaces", []) or []
        secondary = _safe_get(identity, "secondary_project_types", []) or []
        lines.append(f"- **Frameworks**: {', '.join(frameworks) if frameworks else 'None detected'}")
        lines.append(f"- **Interfaces**: {', '.join(interfaces) if interfaces else 'None detected'}")
        lines.append(f"- **Secondary types**: {', '.join(secondary) if secondary else 'None'}")
        lines.append(f"- **Package layout**: {_safe_get(identity, 'package_layout', 'unknown')}")
        lines.append(f"- **Confidence**: {_safe_get(identity, 'confidence', 'unknown')}")

    lines.extend(_format_architecture_sections(architecture))

    if devops:
        lines.append("")
        lines.append("## DevOps & Release Readiness")
        lines.append(f"- **Verdict**: {_safe_get(devops, 'verdict', 'unknown')}")
        score = _safe_get(devops, "observed_score")
        lines.append(f"- **Observed readiness score**: {score if score is not None else 'Not assessed'}")
        lines.append(f"- **Evidence confidence**: {_safe_get(devops, 'evidence_confidence', 'unknown')}")
        next_step = _safe_get(devops, "next_best_step")
        if next_step:
            lines.append(f"- **Next best step**: {next_step}")
        strengths = _safe_get(devops, "strengths", []) or []
        if strengths:
            lines.append("- **Strengths**:")
            for strength in strengths[:6]:
                lines.append(f"  - {strength}")
        blockers = _safe_get(devops, "blockers", []) or []
        if blockers:
            lines.append("")
            lines.append("### Release Blockers")
            for blocker in blockers[:8]:
                if not isinstance(blocker, dict):
                    continue
                lines.append(f"- **{blocker.get('severity', 'unknown')}**: {blocker.get('title', 'Blocker')}")
                fix = blocker.get("suggested_fix")
                if fix:
                    lines.append(f"  - Fix: {fix}")
        dimensions = _safe_get(devops, "dimensions", []) or []
        if isinstance(dimensions, list) and dimensions:
            lines.append("")
            lines.append("### Readiness dimensions")
            lines.append("")
            lines.append("| Dimension | Applicability | Status | Score | Confidence |")
            lines.append("|---|---|---|---:|---|")
            for dim in dimensions:
                if not isinstance(dim, dict):
                    continue
                dim_score = dim.get("score")
                lines.append(
                    f"| {dim.get('title', dim.get('id', 'unknown'))} | {dim.get('applicability', 'unknown')} | "
                    f"{dim.get('status', 'unknown')} | {dim_score if dim_score is not None else 'N/A'} | {dim.get('confidence', 'unknown')} |"
                )

    if runnability:
        lines.append("")
        lines.append("## How to Run / Runnability")
        lines.append(f"- **Status**: {_safe_get(runnability, 'status', 'unknown')}")
        lines.append(f"- **Confidence**: {_safe_get(runnability, 'confidence', 'unknown')}")
        for label, key in (
            ("Install commands", "install_commands"),
            ("Run commands", "run_commands"),
            ("Test commands", "test_commands"),
            ("Build commands", "build_commands"),
        ):
            commands = _safe_get(runnability, key, []) or []
            lines.append(f"- **{label}**: {', '.join(commands) if commands else 'None inferred'}")
        missing = _safe_get(runnability, "missing_requirements", []) or []
        if missing:
            lines.append(f"- **Missing requirements**: {', '.join(missing)}")
        if isinstance(entry_points, list) and entry_points:
            lines.append("")
            lines.append("### Likely entry points")
            for entry in entry_points[:8]:
                if not isinstance(entry, dict):
                    continue
                detail = entry.get("command") or entry.get("symbol") or ""
                suffix = f" `{detail}`" if detail else ""
                lines.append(f"- **{entry.get('kind', 'entry')}**: {entry.get('path', 'unknown')}{suffix}")

    if isinstance(recs_v2, list) and recs_v2:
        lines.append("")
        lines.append("## Top Actions")
        for rec in recs_v2[:5]:
            if not isinstance(rec, dict):
                continue
            lines.append(f"### {rec.get('priority', '-')}. {rec.get('title', 'Recommendation')}")
            lines.append(f"- **Type**: {rec.get('recommendation_type', 'unknown')}")
            lines.append(f"- **Impact / effort**: {rec.get('impact', 'unknown')} / {rec.get('effort', 'unknown')}")
            why = rec.get("why_it_matters")
            if why:
                lines.append(f"- **Why it matters**: {why}")
            steps = rec.get("recommended_steps") or []
            if isinstance(steps, list) and steps:
                lines.append("- **Steps**:")
                for step in steps[:4]:
                    lines.append(f"  - {step}")
            success = rec.get("success_check")
            if success:
                lines.append(f"- **Success check**: {success}")

    # Repository
    lines.append("## Repository")
    path = _safe_get(audit, "path", "N/A")
    source = _safe_get(audit, "source", {}) or {}
    source_value = _safe_get(source, "value")
    status = _safe_get(audit, "status", "N/A")
    analysis = _safe_get(audit, "analysis", {}) or {}
    if source_value:
        lines.append(f"- **Source**: {source_value}")
    else:
        lines.append(f"- **Path**: {path}")
    lines.append(f"- **Status**: {status}")
    if analysis:
        lines.append(f"- **Analysis mode**: {_safe_get(analysis, 'mode', 'N/A')}")
        lines.append(f"- **Executes repository code**: {_format_bool(_safe_get(analysis, 'executes_repository_code'))}")

    # Score Summary
    lines.append("")
    lines.append("## Score Summary")
    scoring = _safe_get(audit, "scoring", {}) or {}
    overall = _safe_get(scoring, "overall_score", "N/A")
    lines.append(f"- **Overall score**: {overall}")
    # Repository and portfolio scores (Phase 4 category scores)
    repo_health = _safe_get(scoring, "repository_health_score")
    port_ready = _safe_get(scoring, "portfolio_readiness_score")
    if repo_health is not None:
        lines.append(f"- **Repository health score**: {repo_health}")
    if port_ready is not None:
        lines.append(f"- **Portfolio readiness score**: {port_ready}")
    sections = _safe_get(scoring, "sections", {}) or {}
    for sec in ("static_analysis", "test_analysis", "repository_analysis"):
        secscore = _safe_get(sections, sec, {})
        s = _safe_get(secscore, "score", "N/A")
        lines.append(f"- **{sec}**: {s}")

    # Category scores
    cats = _safe_get(scoring, "categories", {}) or {}
    if cats:
        lines.append("")
        lines.append("### Category scores")
        lines.append("")
        lines.append("| Category | Score |")
        lines.append("|---|---:|")
        for cat in ("code_quality", "testing", "security", "maintainability", "documentation", "structure"):
            val = cats.get(cat, "N/A")
            lines.append(f"| {cat} | {val} |")

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
    evidence_confidence = _safe_get(diagnosis, "evidence_confidence", {}) or {}

    lines.append(f"- Label: {label}")
    lines.append(f"- Summary: {summary_text}")
    lines.append(f"- Hard flags: {', '.join(hard_flags) if hard_flags else 'None'}")
    lines.append(f"- Limitations: {', '.join(limitations) if limitations else 'None'}")
    if evidence_confidence:
        evidence_label = _safe_get(evidence_confidence, "label", "unknown")
        evidence_summary = _safe_get(evidence_confidence, "summary", "")
        if evidence_summary:
            lines.append(f"- Evidence confidence: {evidence_label}; {evidence_summary}")
        else:
            lines.append(f"- Evidence confidence: {evidence_label}")

    lines.append("")
    lines.append("## Evidence Limitations / Unavailable Tools")
    evidence_limitations: List[str] = []
    for sec in ("static_analysis", "test_analysis", "repository_analysis"):
        entries = _safe_get(audit, sec, []) or []
        if not isinstance(entries, list):
            continue
        for entry in entries:
            reason = _limitation_reason(entry)
            if reason:
                evidence_limitations.append(reason)
    if evidence_limitations:
        for reason in evidence_limitations:
            lines.append(f"- {reason}")
    else:
        lines.append("None")

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
                        loc = _display_location(file_path, path, source_value)
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
            errors = _genuine_errors(entry)
            if errors:
                any_errors = True
                lines.append(f"### {sec} / {tool}")
                for e in errors:
                    lines.append(f"- {e}")

    if not any_errors:
        lines.append("No analyzer errors reported.")

    lines.append(_format_ai_advisor_section(ai_advisor))

    return "\n".join(lines)
