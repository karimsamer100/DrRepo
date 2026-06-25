from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from .profiles import get_profile, validate_profile_id

LLM_ADVISOR_CONTRACT_VERSION = "v1"


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


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
            notes.append(note.replace("unavailable_evidence:", "evidence missing: ", 1))
    return notes


def build_llm_advisor_payload(
    audit: dict[str, object],
    profiled_action_plan: dict[str, object],
) -> dict[str, object]:
    audit_copy = deepcopy(audit) if isinstance(audit, dict) else {}
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

    return {
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


def get_llm_advisor_output_schema() -> dict[str, object]:
    action_schema = {
        "type": "object",
        "required": ["title", "why_it_matters", "evidence", "suggested_fix", "priority"],
        "properties": {
            "title": {"type": "string"},
            "why_it_matters": {"type": "string"},
            "evidence": {"type": "array", "items": {"type": "string"}},
            "suggested_fix": {"type": "string"},
            "priority": {"type": "string", "enum": ["high", "medium", "low"]},
        },
        "additionalProperties": False,
    }

    return {
        "type": "object",
        "required": ["summary", "profile_context", "top_priorities", "lower_priority_items", "limitations", "next_steps"],
        "properties": {
            "summary": {"type": "string"},
            "profile_context": {"type": "string"},
            "top_priorities": {"type": "array", "items": action_schema},
            "lower_priority_items": {"type": "array", "items": action_schema},
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
            for required in ["title", "why_it_matters", "evidence", "suggested_fix", "priority"]:
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

    limitations = _dedupe_strings([str(item) for item in _as_list(plan_copy.get("limitations")) if str(item)] + _missing_evidence_notes(plan_copy))

    next_steps: List[str] = []
    if top_priorities:
        next_steps.append(f"Start with {top_priorities[0]['title']}.")
    else:
        next_steps.append("Start with the highest-priority profiled action.")
    if limitations:
        next_steps.append("Review the missing evidence before treating the plan as complete.")
    next_steps.append("Re-run the audit after the first fix lands.")

    return {
        "summary": f"{profile.get('display_name', 'Repository')} remediation advice grounded in the current audit evidence.",
        "profile_context": profile_context,
        "top_priorities": top_priorities,
        "lower_priority_items": lower_priority_items,
        "limitations": limitations,
        "next_steps": next_steps,
    }