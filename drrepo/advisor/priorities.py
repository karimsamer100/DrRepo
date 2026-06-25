from __future__ import annotations

from typing import Any, Dict, List

from .profiles import get_profile, validate_profile_id

PROFILED_PLAN_VERSION = "v1"


def _safe_get(d: Dict[str, Any] | None, key: str, default: Any = None) -> Any:
    if not isinstance(d, dict):
        return default
    return d.get(key, default)


def _normalize_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return ""


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _infer_category(suggestion: Dict[str, Any]) -> str:
    title = _normalize_text(suggestion.get("title")).lower()
    message = _normalize_text(suggestion.get("message")).lower()
    code = _normalize_text(suggestion.get("code")).lower()
    if "readme" in title or "documentation" in title or "readme" in message or "license" in code:
        return "documentation"
    if "test" in title or "pytest" in title or "pytest" in code:
        return "tests"
    if "security" in title or "bandit" in title or "security" in message or code.startswith("b"):
        return "security"
    if "lint" in title or "ruff" in title or "complexity" in title or "radon" in title:
        return "maintainability"
    if "tool" in title and "install" in title:
        return "optional_tooling"
    if "deploy" in title or "deployment" in title or "ci" in title or "workflow" in title:
        return "deployment_readiness"
    if "dependency" in title or "packag" in title:
        return "packaging"
    return "general"


def _profile_priority(profile: Dict[str, Any], category: str, severity: str | None, suggestion: Dict[str, Any]) -> tuple[int, str]:
    sev = (severity or "").lower()
    title = _normalize_text(suggestion.get("title")).lower()
    profile_id = profile.get("profile_id", "")

    if sev in {"high", "critical"}:
        return 0, "high"
    if "failing tests" in title or "test collection" in title or "fix test" in title:
        return 0, "high"

    if "optional" in title and "tool" in title and "install" in title:
        return 5, "low"

    high_categories = set(profile.get("high_priority_categories", []) or [])
    medium_categories = set(profile.get("medium_priority_categories", []) or [])
    lower_categories = set(profile.get("lower_priority_categories", []) or [])

    if category in high_categories:
        return 1, "high"
    if category in medium_categories:
        return 3, "medium"
    if category in lower_categories:
        return 4, "low"

    if profile_id == "student_portfolio" and category == "security" and sev in {"low", "medium"}:
        return 4, "low"
    if profile_id == "production_service" and category == "documentation":
        return 3, "medium"
    return 4, "medium"


def rank_remediation_suggestions(suggestions: List[Dict[str, Any]], profile_id: str) -> List[Dict[str, object]]:
    validate_profile_id(profile_id)
    profile = get_profile(profile_id)
    ranked: List[Dict[str, Any]] = []
    for suggestion in suggestions:
        if not isinstance(suggestion, dict):
            continue
        copy = dict(suggestion)
        category = _infer_category(copy)
        priority_rank, priority = _profile_priority(profile, category, _normalize_text(copy.get("severity")).lower(), copy)
        copy["profile_category"] = category
        copy["profile_priority_rank"] = priority_rank
        copy["profile_priority"] = priority
        ranked.append(copy)
    ranked.sort(key=lambda s: (int(s.get("profile_priority_rank", 99)), _normalize_text(s.get("title")).lower()))
    return ranked


def explain_profile_impact(suggestion: Dict[str, Any], profile_id: str) -> str:
    validate_profile_id(profile_id)
    title = _normalize_text(suggestion.get("title")).lower()
    category = _infer_category(suggestion)
    if profile_id == "student_portfolio":
        if category == "documentation" or "readme" in title or "documentation" in title:
            return "This directly affects how recruiters or reviewers understand and run the project."
        if category == "tests" or "test" in title:
            return "This improves confidence that the project behaves as expected."
        if category == "security" and "high" in _normalize_text(suggestion.get("severity")).lower():
            return "This reduces real risk that would matter for a public-facing or shared project."
        return "This supports a more credible and understandable presentation of the project."
    if profile_id == "production_service":
        if category == "security":
            return "This affects whether the project is safe enough to run with real users or real data."
        if category == "tests" or "test" in title:
            return "This improves confidence that changes will not break critical behavior."
        return "This helps keep the service reliable and easier to operate safely."
    if profile_id == "open_source_library":
        if category == "documentation" or category == "packaging":
            return "This makes the project easier for others to discover, install, and contribute to."
        return "This increases trust and usability for a wider community."
    if profile_id == "learning_or_research_project":
        if category == "documentation" or category == "reproducibility":
            return "This makes the work easier to explain, rerun, and understand."
        return "This improves the clarity and repeatability of the project."
    return "This helps the project better match the selected goal."


def summarize_profile_fit(audit: Dict[str, Any], profile_id: str) -> str:
    validate_profile_id(profile_id)
    profile = get_profile(profile_id)
    if not isinstance(audit, dict):
        return f"For a {profile['display_name'].lower()}, the plan is intentionally conservative because no audit evidence was supplied."
    if _safe_get(audit, "diagnosis") and _safe_get(_safe_get(audit, "diagnosis"), "hard_flags"):
        hard_flags_note = "Hard flags are present."
    else:
        hard_flags_note = "No hard flags were recorded."
    if _safe_get(audit, "remediation_suggestions"):
        suggestion_note = "Remediation suggestions are available."
    else:
        suggestion_note = "No remediation suggestions were provided."
    if profile_id == "student_portfolio":
        return f"For a student portfolio, the main focus is presentation, reproducibility, and basic trust signals. {hard_flags_note} {suggestion_note}"
    if profile_id == "production_service":
        return "For a production service, the plan emphasizes security, test confidence, deployment readiness, and operational safety."
    if profile_id == "open_source_library":
        return "For an open source library, the plan emphasizes documentation, packaging, and contribution readiness."
    return "For a learning or research project, the plan emphasizes clarity, reproducibility, and explanation."


def build_profiled_action_plan(audit: Dict[str, Any], profile_id: str = "student_portfolio", max_actions: int = 8) -> Dict[str, Any]:
    validate_profile_id(profile_id)
    profile = get_profile(profile_id)
    audit_copy = dict(audit or {})
    suggestions = _safe_get(audit_copy, "remediation_suggestions")
    suggestion_list: List[Dict[str, Any]] = []
    if isinstance(suggestions, list):
        suggestion_list = [dict(s) for s in suggestions if isinstance(s, dict)]
    ranked_suggestions = rank_remediation_suggestions(suggestion_list, profile_id)

    top_actions: List[Dict[str, Any]] = []
    deprioritized_actions: List[Dict[str, Any]] = []
    evidence_notes: List[str] = []

    for section in ("static_analysis", "test_analysis", "repository_analysis", "diagnosis", "scoring"):
        if section not in audit_copy or audit_copy.get(section) in (None, []):
            evidence_notes.append(f"unavailable_evidence:{section}")

    for suggestion in ranked_suggestions:
        category = _infer_category(suggestion)
        severity = _normalize_text(suggestion.get("severity")).lower()
        priority = suggestion.get("profile_priority", "medium")
        if priority in {"high"}:
            top_actions.append({
                "title": _normalize_text(suggestion.get("title")) or "Review recommendation",
                "priority": "high",
                "category": category,
                "reason": _normalize_text(suggestion.get("message")) or _normalize_text(suggestion.get("action")),
                "user_impact": explain_profile_impact(suggestion, profile_id),
                "evidence": [
                    _normalize_text(suggestion.get("code")) or _normalize_text(suggestion.get("title")),
                    _normalize_text(suggestion.get("tool")),
                ],
                "source": "remediation_suggestion",
                "original_severity": severity or None,
            })
        else:
            deprioritized_actions.append({
                "title": _normalize_text(suggestion.get("title")) or "Review recommendation",
                "priority": priority,
                "category": category,
                "reason": _normalize_text(suggestion.get("message")) or _normalize_text(suggestion.get("action")),
                "user_impact": explain_profile_impact(suggestion, profile_id),
                "evidence": [
                    _normalize_text(suggestion.get("code")) or _normalize_text(suggestion.get("title")),
                    _normalize_text(suggestion.get("tool")),
                ],
                "source": "remediation_suggestion",
                "original_severity": severity or None,
            })

    diagnosis = _safe_get(audit_copy, "diagnosis") or {}
    diagnosis_limitations = [str(item) for item in _as_list(diagnosis.get("limitations")) if str(item)]
    hard_flags = diagnosis.get("hard_flags") if isinstance(diagnosis, dict) else None
    hard_flags = hard_flags or []
    if isinstance(hard_flags, list):
        for flag in hard_flags:
            flag_str = str(flag).lower()
            if "security" in flag_str or "secret" in flag_str:
                top_actions.append({
                    "title": "Address security hard flag",
                    "priority": "high",
                    "category": "security",
                    "reason": "The audit recorded a security-related hard flag.",
                    "user_impact": explain_profile_impact({"title": "Security hard flag", "message": "Security hard flag"}, profile_id),
                    "evidence": [flag_str],
                    "source": "hard_flag",
                })
                break

    if not top_actions:
        scoring = _safe_get(audit_copy, "scoring") or {}
        repo_score = int(scoring.get("repository_health_score") or 0)
        if repo_score < 60:
            top_actions.append({
                "title": "Improve project stability",
                "priority": "medium",
                "category": "maintainability",
                "reason": "Repository health score is below a strong baseline.",
                "user_impact": explain_profile_impact({"title": "Improve project stability"}, profile_id),
                "evidence": [f"repository_health_score:{repo_score}"],
                "source": "derived_from_audit",
            })

    top_actions = top_actions[:max_actions]
    deprioritized_actions = deprioritized_actions[:max(0, max_actions)]
    if not evidence_notes:
        evidence_notes.append("evidence:complete")

    limitations = [note for note in evidence_notes if note.startswith("unavailable_evidence")]
    limitations.extend(diagnosis_limitations)

    return {
        "plan_version": PROFILED_PLAN_VERSION,
        "profile": profile,
        "profile_fit_summary": summarize_profile_fit(audit_copy, profile_id),
        "top_actions": top_actions,
        "deprioritized_actions": deprioritized_actions,
        "evidence_notes": evidence_notes,
        "limitations": limitations,
        "max_actions": max_actions,
    }
