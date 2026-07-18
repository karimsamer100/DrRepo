from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Dict, List

from .grounding import normalize_evidence_path
from .profiles import get_profile, validate_profile_id
from .redaction import redact_audit_copy

LLM_ADVISOR_CONTRACT_VERSION = "v1"
ADVISOR_ACTION_REQUIRED_FIELDS = ("title", "why_it_matters", "evidence", "suggested_fix", "priority")
MAX_PAYLOAD_FINDINGS = 8
MAX_PAYLOAD_BLOCKERS = 6
MAX_PAYLOAD_RECOMMENDATIONS = 8
MAX_PAYLOAD_EXCERPT_CHARS = 240
MAX_SERIALIZED_PAYLOAD_CHARS = 100_000


def get_llm_advisor_action_schema() -> dict[str, object]:
    return {
        "type": "object",
        "required": list(ADVISOR_ACTION_REQUIRED_FIELDS),
        "properties": {
            "title": {"type": "string"},
            "why_it_matters": {"type": "string"},
            "evidence": {"type": "array", "items": {"type": "string"}},
            "suggested_fix": {"type": "string"},
            "priority": {"type": "string", "enum": ["high", "medium", "low"]},
        },
        "additionalProperties": False,
    }


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _safe_str(value: Any) -> str:
    return str(value) if value is not None else ""


def _text_or_missing(value: Any) -> str:
    return value if isinstance(value, str) and value else "missing"


def _number_or_missing(value: Any) -> Any:
    if isinstance(value, (int, float)):
        return value
    return "missing"


def _compact_categories(categories: Any) -> Dict[str, Any]:
    if not isinstance(categories, dict):
        return {}
    compact: Dict[str, Any] = {}
    for key in sorted(categories):
        compact[key] = _number_or_missing(categories.get(key))
    return compact


def _compact_analyzer_statuses(audit: Dict[str, Any]) -> List[Dict[str, Any]]:
    statuses: List[Dict[str, Any]] = []
    for section_name in ("static_analysis", "test_analysis", "repository_analysis"):
        entries = audit.get(section_name)
        if not isinstance(entries, list):
            statuses.append({"section": section_name, "status": "missing"})
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            statuses.append(
                {
                    "section": section_name,
                    "tool": _text_or_missing(entry.get("tool") or entry.get("name")),
                    "status": _text_or_missing(entry.get("status")),
                    "finding_count": len(entry.get("findings") or []) if isinstance(entry.get("findings"), list) else 0,
                }
            )
    return statuses


def _compact_profile(profile: Any) -> Dict[str, Any]:
    profile_dict = _as_dict(profile)
    return {
        "profile_id": _text_or_missing(profile_dict.get("profile_id")),
        "display_name": _text_or_missing(profile_dict.get("display_name")),
        "description": _text_or_missing(profile_dict.get("description")),
        "primary_user_goal": _text_or_missing(profile_dict.get("primary_user_goal")),
        "advisor_tone": _text_or_missing(profile_dict.get("advisor_tone")),
    }


def _compact_action(action: Any) -> Dict[str, Any]:
    action_dict = _as_dict(action)
    evidence = action_dict.get("evidence")
    if isinstance(evidence, list):
        evidence_list = [str(item) for item in evidence if str(item)]
    elif evidence in (None, ""):
        evidence_list = []
    else:
        evidence_list = [str(evidence)]
    return {
        "title": _text_or_missing(action_dict.get("title")),
        "priority": action_dict.get("priority") if action_dict.get("priority") in {"high", "medium", "low"} else "medium",
        "category": _text_or_missing(action_dict.get("category")),
        "reason": _text_or_missing(action_dict.get("reason") or action_dict.get("message") or action_dict.get("action")),
        "user_impact": _text_or_missing(action_dict.get("user_impact") or action_dict.get("why_it_matters")),
        "evidence": evidence_list,
        "source": _text_or_missing(action_dict.get("source")),
    }


def _dedupe_strings(items: List[str]) -> List[str]:
    seen = set()
    deduped: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _missing_evidence_notes(plan: Dict[str, Any]) -> List[str]:
    notes = []
    for note in _as_list(plan.get("evidence_notes")):
        if isinstance(note, str) and note.startswith("unavailable_evidence:"):
            section = note.split(":", 1)[1].strip()
            notes.append(f"Evidence was unavailable for {section}.")
    return notes


def _bounded_text(value: Any, max_length: int = MAX_PAYLOAD_EXCERPT_CHARS) -> str:
    text = _safe_str(value)
    if len(text) > max_length:
        return text[: max_length - 3].rstrip() + "..."
    return text


def _compact_finding(finding: Dict[str, Any], audit_root: str | None = None, max_message_length: int = MAX_PAYLOAD_EXCERPT_CHARS) -> Dict[str, Any]:
    """Return a compact, grounded representation of a single finding."""
    message = _safe_str(finding.get("message"))
    if len(message) > max_message_length:
        message = message[: max_message_length - 3].rstrip() + "..."
    compact: Dict[str, Any] = {
        "tool": _safe_str(finding.get("tool")),
        "code": _safe_str(finding.get("code")),
        "severity": _safe_str(finding.get("severity")),
        "message": message,
    }
    file_path = normalize_evidence_path(_safe_str(finding.get("file_path")), audit_root)
    if file_path:
        compact["file_path"] = file_path
        line = finding.get("line")
        if isinstance(line, int):
            compact["line"] = line
    return compact


def _collect_top_findings(audit: Dict[str, Any], max_findings: int = MAX_PAYLOAD_FINDINGS) -> List[Dict[str, Any]]:
    """Collect the most severe findings from all analyzer sections."""
    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}
    all_findings: List[Dict[str, Any]] = []
    audit_root = _safe_str(audit.get("path"))
    for section in ("static_analysis", "test_analysis", "repository_analysis"):
        entries = audit.get(section)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            tool = _safe_str(entry.get("tool") or entry.get("name"))
            for finding in _as_list(entry.get("findings")):
                if not isinstance(finding, dict):
                    continue
                all_findings.append({**finding, "tool": tool, "section": section})
    all_findings.sort(key=lambda f: (severity_rank.get(_safe_str(f.get("severity")).lower(), 99), _safe_str(f.get("code"))))
    return [_compact_finding(f, audit_root=audit_root) for f in all_findings[:max_findings]]


def _collect_test_outcome(audit: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize pytest and coverage outcomes from the audit."""
    result: Dict[str, Any] = {"pytest": "unknown", "coverage": None}
    for section in ("test_analysis",):
        entries = _as_list(audit.get(section))
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            tool = _safe_str(entry.get("tool")).lower()
            status = _safe_str(entry.get("status"))
            if tool == "pytest":
                result["pytest"] = status
                summary = _as_dict(entry.get("summary"))
                if summary.get("failed"):
                    result["pytest_failed"] = summary.get("failed")
                if summary.get("passed"):
                    result["pytest_passed"] = summary.get("passed")
            elif tool == "coverage":
                summary = _as_dict(entry.get("summary"))
                percent = summary.get("coverage_percent")
                if isinstance(percent, (int, float)):
                    result["coverage"] = percent
                result["coverage_status"] = status
    return result


def _collect_devops_blockers(audit: Dict[str, Any], max_blockers: int = MAX_PAYLOAD_BLOCKERS) -> List[Dict[str, Any]]:
    devops = _as_dict(audit.get("devops_readiness"))
    blockers: List[Dict[str, Any]] = []
    for blocker in _as_list(devops.get("blockers")):
        if not isinstance(blocker, dict):
            continue
        blockers.append({
            "id": _safe_str(blocker.get("id")),
            "title": _safe_str(blocker.get("title")),
            "severity": _safe_str(blocker.get("severity")),
            "category": _safe_str(blocker.get("category")),
        })
    return blockers[:max_blockers]


def _collect_project_identity(audit: Dict[str, Any]) -> Dict[str, Any]:
    understanding = _as_dict(audit.get("project_understanding"))
    identity = _as_dict(understanding.get("project_identity"))
    audit_root = _safe_str(audit.get("path"))
    entry_points = [
        normalize_evidence_path(_safe_str(entry.get("path")), audit_root)
        for entry in _as_list(understanding.get("entry_points"))
        if isinstance(entry, dict)
    ]
    entry_points = [p for p in entry_points if p]
    return {
        "project_type": _safe_str(identity.get("project_type")),
        "secondary_project_types": [str(t) for t in _as_list(identity.get("secondary_project_types"))],
        "frameworks": [str(t) for t in _as_list(identity.get("frameworks"))],
        "interfaces": [str(t) for t in _as_list(identity.get("interfaces"))],
        "package_layout": _safe_str(identity.get("package_layout")),
        "confidence": _safe_str(identity.get("confidence")),
        "entry_points": entry_points,
    }


def _collect_recommendations(audit: Dict[str, Any], max_recs: int = MAX_PAYLOAD_RECOMMENDATIONS) -> List[Dict[str, Any]]:
    recs: List[Dict[str, Any]] = []
    for rec in _as_list(audit.get("recommendations_v2")):
        if not isinstance(rec, dict):
            continue
        recs.append({
            "id": _safe_str(rec.get("id")),
            "title": _bounded_text(rec.get("title")),
            "priority": rec.get("priority") if isinstance(rec.get("priority"), int) else None,
            "severity": _safe_str(rec.get("severity")),
            "category": _safe_str(rec.get("category")),
            "recommendation_type": _safe_str(rec.get("recommendation_type")),
            "why_it_matters": _bounded_text(rec.get("why_it_matters")),
            "success_check": _bounded_text(rec.get("success_check")),
        })
    return recs[:max_recs]


def _enforce_payload_size(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Keep the serialized advisor payload within the v1 hard cap."""
    compact = deepcopy(payload)
    while len(json.dumps(compact, sort_keys=True)) > MAX_SERIALIZED_PAYLOAD_CHARS:
        evidence = _as_dict(compact.get("bounded_evidence"))
        if _as_list(evidence.get("top_findings")):
            evidence["top_findings"] = _as_list(evidence.get("top_findings"))[:-1]
            continue
        if _as_list(evidence.get("deterministic_recommendations")):
            evidence["deterministic_recommendations"] = _as_list(evidence.get("deterministic_recommendations"))[:-1]
            continue
        if _as_list(evidence.get("devops_blockers")):
            evidence["devops_blockers"] = _as_list(evidence.get("devops_blockers"))[:-1]
            continue
        compact["payload_truncated"] = True
        compact["bounded_evidence"] = {
            "top_findings": [],
            "test_outcome": evidence.get("test_outcome", {}),
            "devops_blockers": [],
            "project_identity": evidence.get("project_identity", {}),
            "deterministic_recommendations": [],
        }
        break
    return compact


def _friendly_limitation_note(item: str) -> str:
    note = str(item).strip()
    lowered = note.lower()
    if "coverage evidence" in lowered:
        return "Coverage evidence was unavailable, so testing confidence is based on pytest status and repository structure rather than coverage percentage."
    if "optional tools" in lowered or "tooling" in lowered:
        return "Some optional tools were unavailable, so lint/security/complexity confidence may be limited."
    if lowered.startswith("evidence was unavailable for"):
        return note
    return note


def _build_fallback_summary(profile: Dict[str, Any], top_priorities: List[Dict[str, Any]], lower_priority_items: List[Dict[str, Any]], limitations: List[str]) -> str:
    profile_id = profile.get("profile_id", "")
    if profile_id == "student_portfolio":
        if top_priorities:
            return "For a student portfolio, the main improvements should focus on presentation, reproducibility, and trust signals."
        if lower_priority_items:
            return "For a student portfolio, this repository looks strong from the available evidence. The remaining items are mostly optional audit-completeness improvements."
        return "For a student portfolio, no urgent profile-specific blockers were identified from the available evidence."
    if profile_id == "production_service":
        if top_priorities:
            return "For a production service, the main findings emphasize security, test confidence, and deployment readiness."
        if limitations:
            return "For a production service, the evidence shows no urgent production blockers, but some evidence limitations remain for security and testing confidence."
        return "For a production service, the current evidence does not show urgent production readiness issues."
    return "This advisor guidance is grounded in the current audit evidence for the selected profile."


def build_llm_advisor_payload(
    audit: dict[str, object],
    profiled_action_plan: dict[str, object],
) -> dict[str, object]:
    audit_copy = redact_audit_copy(audit) if isinstance(audit, dict) else {}
    plan_copy = deepcopy(profiled_action_plan) if isinstance(profiled_action_plan, dict) else {}

    profile = _as_dict(plan_copy.get("profile"))
    profile_id = profile.get("profile_id") if isinstance(profile.get("profile_id"), str) else "student_portfolio"
    if isinstance(profile_id, str):
        validate_profile_id(profile_id)
    else:
        profile_id = "student_portfolio"
    profile = get_profile(profile_id)

    scoring = _as_dict(audit_copy.get("scoring"))
    diagnosis = _as_dict(audit_copy.get("diagnosis"))
    repository_health = _as_dict(diagnosis.get("repository_health"))

    audit_summary = {
        "overall_score": _number_or_missing(scoring.get("overall_score") if scoring.get("overall_score") is not None else scoring.get("overall")),
        "repository_health_score": _number_or_missing(scoring.get("repository_health_score")),
        "portfolio_readiness_score": _number_or_missing(scoring.get("portfolio_readiness_score")),
        "diagnosis": _text_or_missing(repository_health.get("summary") or diagnosis.get("summary")),
        "hard_flags": [str(flag) for flag in _as_list(diagnosis.get("hard_flags")) if str(flag)],
        "limitations": [str(item) for item in _as_list(diagnosis.get("limitations")) if str(item)],
        "category_scores": _compact_categories(scoring.get("categories")),
        "analyzer_statuses": _compact_analyzer_statuses(audit_copy),
    }

    profile_fit_summary = _text_or_missing(plan_copy.get("profile_fit_summary"))
    profiled_plan = {
        "plan_version": _text_or_missing(plan_copy.get("plan_version")),
        "profile": _compact_profile(profile),
        "profile_fit_summary": profile_fit_summary,
        "top_actions": [_compact_action(action) for action in _as_list(plan_copy.get("top_actions")) if isinstance(action, dict)],
        "deprioritized_actions": [_compact_action(action) for action in _as_list(plan_copy.get("deprioritized_actions")) if isinstance(action, dict)],
        "limitations": [str(item) for item in _as_list(plan_copy.get("limitations")) if str(item)],
        "evidence_notes": [str(item) for item in _as_list(plan_copy.get("evidence_notes")) if str(item)],
    }

    bounded_evidence = {
        "top_findings": _collect_top_findings(audit_copy),
        "test_outcome": _collect_test_outcome(audit_copy),
        "devops_blockers": _collect_devops_blockers(audit_copy),
        "project_identity": _collect_project_identity(audit_copy),
        "deterministic_recommendations": _collect_recommendations(audit_copy),
    }

    payload: Dict[str, Any] = {
        "contract_version": LLM_ADVISOR_CONTRACT_VERSION,
        "role": "grounded_repository_advisor",
        "grounding_rules": [
            "Use only supplied audit evidence.",
            "Do not invent missing tools, files, tests, vulnerabilities, dependencies, or project features.",
            "Do not claim the project is production-ready unless the evidence supports it.",
            "Adapt advice to the selected profile.",
            "Explain what to fix first and why.",
            "Mention limitations when important evidence is unavailable.",
            "Keep advice practical and actionable.",
            "Do not over-prioritize production security for student portfolios unless high-risk evidence exists.",
        ],
        "user_goal_profile": {
            "profile_id": profile["profile_id"],
            "display_name": profile["display_name"],
            "description": profile["description"],
            "primary_user_goal": profile["primary_user_goal"],
            "advisor_tone": profile["advisor_tone"],
            "profile_fit_summary": profile_fit_summary,
        },
        "audit_summary": audit_summary,
        "bounded_evidence": bounded_evidence,
        "profiled_action_plan": profiled_plan,
        "response_requirements": {
            "must_return_json_only": True,
            "must_follow_schema": True,
            "must_ground_in_audit": True,
            "must_prioritize_by_profile": True,
            "must_explain_first_fix": True,
            "must_call_out_missing_evidence": True,
        },
    }
    return _enforce_payload_size(payload)


def get_llm_advisor_output_schema() -> dict[str, object]:
    return {
        "type": "object",
        "required": ["summary", "profile_context", "top_priorities", "lower_priority_items", "limitations", "next_steps"],
        "properties": {
            "summary": {"type": "string"},
            "profile_context": {"type": "string"},
            "top_priorities": {"type": "array", "items": get_llm_advisor_action_schema()},
            "lower_priority_items": {"type": "array", "items": get_llm_advisor_action_schema()},
            "limitations": {"type": "array", "items": {"type": "string"}},
            "next_steps": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": False,
    }


def validate_llm_advisor_response(response: dict[str, object]) -> list[str]:
    errors: List[str] = []
    if not isinstance(response, dict):
        return ["response must be a dict"]

    required_fields = ["summary", "profile_context", "top_priorities", "lower_priority_items", "limitations", "next_steps"]
    for field_name in required_fields:
        if field_name not in response:
            errors.append(f"missing required field: {field_name}")

    if "top_priorities" in response and not isinstance(response.get("top_priorities"), list):
        errors.append("top_priorities must be a list")
    if "lower_priority_items" in response and not isinstance(response.get("lower_priority_items"), list):
        errors.append("lower_priority_items must be a list")
    if "limitations" in response and not isinstance(response.get("limitations"), list):
        errors.append("limitations must be a list")
    if "next_steps" in response and not isinstance(response.get("next_steps"), list):
        errors.append("next_steps must be a list")

    for field_name in ("top_priorities", "lower_priority_items"):
        items = response.get(field_name)
        if not isinstance(items, list):
            continue
        for index, action in enumerate(items):
            if not isinstance(action, dict):
                errors.append(f"{field_name}[{index}] must be a dict")
                continue
            for required in ADVISOR_ACTION_REQUIRED_FIELDS:
                if required not in action:
                    errors.append(f"{field_name}[{index}] missing required field: {required}")
            if action.get("priority") not in {"high", "medium", "low"}:
                errors.append(f"{field_name}[{index}].priority must be one of high, medium, low")
            if "evidence" in action and not isinstance(action.get("evidence"), list):
                errors.append(f"{field_name}[{index}].evidence must be a list")

    return errors


def build_fallback_advisor_response(
    profiled_action_plan: dict[str, object],
) -> dict[str, object]:
    plan_copy = deepcopy(profiled_action_plan) if isinstance(profiled_action_plan, dict) else {}
    profile = _as_dict(plan_copy.get("profile"))
    profile_context = _text_or_missing(plan_copy.get("profile_fit_summary"))

    def build_action(action: Any) -> Dict[str, Any]:
        compact = _compact_action(action)
        return {
            "title": compact["title"],
            "why_it_matters": compact["user_impact"],
            "evidence": compact["evidence"],
            "suggested_fix": compact["reason"],
            "priority": compact["priority"],
        }

    top_priorities = [build_action(action) for action in _as_list(plan_copy.get("top_actions")) if isinstance(action, dict)]
    lower_priority_items = [build_action(action) for action in _as_list(plan_copy.get("deprioritized_actions")) if isinstance(action, dict)]

    limitations = _dedupe_strings(
        [_friendly_limitation_note(item) for item in _as_list(plan_copy.get("limitations")) if str(item)]
        + [_friendly_limitation_note(item) for item in _missing_evidence_notes(plan_copy)]
    )

    next_steps: List[str] = []
    if top_priorities:
        next_steps.append(f"Start with {top_priorities[0]['title']}.")
    elif lower_priority_items:
        next_steps.append("Review the lower-priority items if you want a more complete audit environment.")
    else:
        next_steps.append("No urgent profile-specific remediation actions were identified from the current evidence.")
    if limitations:
        next_steps.append("Consider the evidence limitations before treating the plan as complete.")
    next_steps.append("Re-run the audit after installing optional tools or making changes.")

    return {
        "summary": _build_fallback_summary(profile, top_priorities, lower_priority_items, limitations),
        "profile_context": profile_context,
        "top_priorities": top_priorities,
        "lower_priority_items": lower_priority_items,
        "limitations": limitations,
        "next_steps": next_steps,
    }
