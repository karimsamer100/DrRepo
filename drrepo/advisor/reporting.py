from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from .llm_contract import build_fallback_advisor_response
from .priorities import build_profiled_action_plan

ADVISOR_REPORT_VERSION = "v1"


def _text(value: Any, default: str = "") -> str:
    return value if isinstance(value, str) and value else default


def _action_title(action: Any) -> str:
    return _text((action or {}).get("title")) if isinstance(action, dict) else ""


def _action_evidence(action: Any) -> List[str]:
    if not isinstance(action, dict):
        return []
    evidence = action.get("evidence")
    if isinstance(evidence, list):
        return [str(item) for item in evidence if str(item)]
    if evidence in (None, ""):
        return []
    return [str(evidence)]


def format_advisor_markdown_section(
    profiled_action_plan: dict[str, object],
    advisor_response: dict[str, object] | None = None,
) -> str:
    plan = deepcopy(profiled_action_plan) if isinstance(profiled_action_plan, dict) else {}
    response = deepcopy(advisor_response) if isinstance(advisor_response, dict) else {}

    profile = plan.get("profile") if isinstance(plan.get("profile"), dict) else {}
    profile_name = _text(profile.get("display_name"), "Selected profile")
    profile_context = _text(response.get("profile_context")) or _text(plan.get("profile_fit_summary"))
    summary = _text(response.get("summary")) or _text(plan.get("profile_fit_summary"))

    lines: List[str] = []
    lines.append("## Context-Aware Advisor")
    lines.append("")
    lines.append(f"- **Profile**: {profile_name}")
    lines.append(f"- **Profile context**: {profile_context or 'No profile context available.'}")
    lines.append(f"- **Summary**: {summary or 'No summary available.'}")
    lines.append("")

    top_priorities = response.get("top_priorities") if isinstance(response.get("top_priorities"), list) else []
    lower_priority_items = response.get("lower_priority_items") if isinstance(response.get("lower_priority_items"), list) else []
    limitations = response.get("limitations") if isinstance(response.get("limitations"), list) else []
    next_steps = response.get("next_steps") if isinstance(response.get("next_steps"), list) else []

    lines.append("### Top priorities")
    if top_priorities:
        for action in top_priorities:
            if not isinstance(action, dict):
                continue
            evidence = ", ".join(_action_evidence(action)) or "no explicit evidence"
            lines.append(f"- {action.get('title', 'Priority')} ({action.get('priority', 'medium')}): {action.get('why_it_matters', '')} Evidence: {evidence}")
    else:
        lines.append("- No urgent profile-specific actions were identified from the available evidence.")

    lines.append("")
    lines.append("### Lower priority items")
    if lower_priority_items:
        for action in lower_priority_items:
            if not isinstance(action, dict):
                continue
            lines.append(f"- {action.get('title', 'Lower priority')} ({action.get('priority', 'low')})")
    else:
        lines.append("- No lower-priority items were identified.")

    lines.append("")
    lines.append("### Limitations")
    if limitations:
        for item in limitations:
            lines.append(f"- {item}")
    else:
        lines.append("- No important evidence limitations were reported.")

    lines.append("")
    lines.append("### Next steps")
    if next_steps:
        for item in next_steps:
            lines.append(f"- {item}")
    else:
        if lower_priority_items:
            lines.append("- Review the lower-priority items if you want a more complete audit environment.")
        else:
            lines.append("- No profile-specific remediation actions were identified from the current evidence.")
        lines.append("- Re-run the audit after installing optional tools or making changes.")

    return "\n".join(lines)


def format_advisor_summary_lines(
    profiled_action_plan: dict[str, object],
    advisor_response: dict[str, object] | None = None,
    max_lines: int = 12,
) -> list[str]:
    if max_lines <= 0:
        return []

    plan = deepcopy(profiled_action_plan) if isinstance(profiled_action_plan, dict) else {}
    response = deepcopy(advisor_response) if isinstance(advisor_response, dict) else {}

    profile = plan.get("profile") if isinstance(plan.get("profile"), dict) else {}
    profile_name = _text(profile.get("display_name"), "Selected profile")
    summary = _text(response.get("summary")) or _text(plan.get("profile_fit_summary")) or "No summary available."
    lines: List[str] = [f"Profile: {profile_name}", f"Summary: {summary}"]

    top_priorities = response.get("top_priorities") if isinstance(response.get("top_priorities"), list) else []
    lower_priority_items = response.get("lower_priority_items") if isinstance(response.get("lower_priority_items"), list) else []
    limitations = response.get("limitations") if isinstance(response.get("limitations"), list) else []

    for action in top_priorities[: max_lines - 2]:
        if not isinstance(action, dict):
            continue
        title = _text(action.get("title"), "Priority")
        lines.append(f"Top advisor action: {title}")

    if not top_priorities and lower_priority_items and len(lines) < max_lines:
        count = len(lower_priority_items)
        label = "improvement" if count == 1 else "improvements"
        lines.append(f"Lower-priority items: {count} optional {label}")
    elif lower_priority_items and len(lines) < max_lines:
        count = len(lower_priority_items)
        label = "item" if count == 1 else "items"
        lines.append(f"Also lower-priority items: {count} optional {label}")
    if limitations and len(lines) < max_lines:
        lines.append(f"Evidence limitations: {len(limitations)}")

    return lines[:max_lines]


def build_deterministic_advisor_report(
    audit: dict[str, object],
    profile_id: str = "student_portfolio",
    max_actions: int = 5,
) -> dict[str, object]:
    audit_copy = deepcopy(audit) if isinstance(audit, dict) else {}
    profiled_action_plan = build_profiled_action_plan(audit_copy, profile_id=profile_id, max_actions=max_actions)
    advisor_response = build_fallback_advisor_response(profiled_action_plan)
    markdown_section = format_advisor_markdown_section(profiled_action_plan, advisor_response)
    summary_lines = format_advisor_summary_lines(profiled_action_plan, advisor_response, max_lines=12)
    return {
        "advisor_report_version": ADVISOR_REPORT_VERSION,
        "profiled_action_plan": profiled_action_plan,
        "advisor_response": advisor_response,
        "markdown_section": markdown_section,
        "summary_lines": summary_lines,
    }
