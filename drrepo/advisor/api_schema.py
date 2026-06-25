from __future__ import annotations

from copy import deepcopy
from typing import Any

from .profiles import get_profile, validate_profile_id
from .service import build_advisor_result

ADVISOR_API_RESPONSE_VERSION = "v1"


def _safe_text(value: Any, default: str = "") -> str:
    return value if isinstance(value, str) and value else default


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def build_advisor_api_response(
    audit: dict[str, object],
    profile_id: str = "student_portfolio",
    max_actions: int = 5,
    include_prompt_bundle: bool = False,
) -> dict[str, object]:
    validate_profile_id(profile_id)

    audit_copy = deepcopy(audit) if isinstance(audit, dict) else {}
    advisor_result = build_advisor_result(
        audit_copy,
        profile_id=profile_id,
        max_actions=max_actions,
        include_prompt_bundle=include_prompt_bundle,
    )

    scoring = _safe_dict(audit_copy.get("scoring"))
    diagnosis = _safe_dict(audit_copy.get("diagnosis"))
    repository_health = _safe_dict(diagnosis.get("repository_health"))
    metadata = _safe_dict(audit_copy.get("metadata"))

    audit_status = _safe_text(audit_copy.get("status"), "partial")
    if audit_status not in {"ok", "partial"}:
        audit_status = "partial"

    advisor_response = _safe_dict(advisor_result.get("advisor_report", {}).get("advisor_response"))
    advisor_report = _safe_dict(advisor_result.get("advisor_report"))

    response: dict[str, object] = {
        "response_version": ADVISOR_API_RESPONSE_VERSION,
        "status": "ok" if audit_status == "ok" else "partial",
        "profile_id": profile_id,
        "profile_display_name": get_profile(profile_id).get("display_name", profile_id),
        "repository": {
            "path": _safe_text(metadata.get("path"), ""),
            "status": audit_status,
        },
        "scores": {
            "overall_score": scoring.get("overall_score") if isinstance(scoring.get("overall_score"), (int, float)) else None,
            "repository_health_score": scoring.get("repository_health_score") if isinstance(scoring.get("repository_health_score"), (int, float)) else None,
            "portfolio_readiness_score": scoring.get("portfolio_readiness_score") if isinstance(scoring.get("portfolio_readiness_score"), (int, float)) else None,
            "category_scores": {key: value for key, value in _safe_dict(scoring.get("categories")).items() if isinstance(value, (int, float))},
        },
        "diagnosis": {
            "label": _safe_text(repository_health.get("label"), "unknown"),
            "summary": _safe_text(diagnosis.get("summary") or repository_health.get("summary"), "No diagnosis summary available."),
            "hard_flags": [str(flag) for flag in _safe_list(diagnosis.get("hard_flags")) if str(flag)],
            "limitations": [str(item) for item in _safe_list(diagnosis.get("limitations")) if str(item)],
        },
        "advisor": {
            "summary": _safe_text(advisor_response.get("summary")),
            "profile_context": _safe_text(advisor_response.get("profile_context")),
            "top_priorities": _safe_list(advisor_response.get("top_priorities")),
            "lower_priority_items": _safe_list(advisor_response.get("lower_priority_items")),
            "limitations": _safe_list(advisor_response.get("limitations")),
            "next_steps": _safe_list(advisor_response.get("next_steps")),
        },
        "reports": {
            "markdown_section": _safe_text(advisor_report.get("markdown_section")),
            "summary_lines": _safe_list(advisor_report.get("summary_lines")),
        },
        "debug": {
            "advisor_service_version": advisor_result.get("advisor_service_version", "unknown"),
            "advisor_report_version": advisor_report.get("advisor_report_version", "unknown"),
            "prompt_bundle_included": include_prompt_bundle,
        },
    }

    if include_prompt_bundle:
        response["prompt_bundle"] = advisor_result.get("prompt_bundle")

    return response


def validate_advisor_api_response(response: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if not isinstance(response, dict):
        return ["response must be a dict"]

    required_keys = [
        "response_version",
        "status",
        "profile_id",
        "repository",
        "scores",
        "diagnosis",
        "advisor",
        "reports",
        "debug",
    ]
    for key in required_keys:
        if key not in response:
            errors.append(f"missing required key: {key}")

    if response.get("response_version") != ADVISOR_API_RESPONSE_VERSION:
        errors.append("response_version must be v1")

    if response.get("status") not in {"ok", "partial"}:
        errors.append("status must be 'ok' or 'partial'")

    if isinstance(response.get("advisor"), dict):
        advisor = response["advisor"]
        if not isinstance(advisor.get("top_priorities"), list):
            errors.append("advisor.top_priorities must be a list")
        if not isinstance(advisor.get("lower_priority_items"), list):
            errors.append("advisor.lower_priority_items must be a list")
        if not isinstance(advisor.get("limitations"), list):
            errors.append("advisor.limitations must be a list")
        if not isinstance(advisor.get("next_steps"), list):
            errors.append("advisor.next_steps must be a list")

    if isinstance(response.get("reports"), dict):
        reports = response["reports"]
        if not isinstance(reports.get("summary_lines"), list):
            errors.append("reports.summary_lines must be a list")

    if isinstance(response.get("debug"), dict):
        debug = response["debug"]
        if not isinstance(debug.get("prompt_bundle_included"), bool):
            errors.append("debug.prompt_bundle_included must be a bool")
        else:
            has_prompt_bundle = "prompt_bundle" in response
            if debug["prompt_bundle_included"] and not has_prompt_bundle:
                errors.append("prompt_bundle_included is True but prompt_bundle is missing")
            if not debug["prompt_bundle_included"] and has_prompt_bundle:
                errors.append("prompt_bundle_included is False but prompt_bundle exists")

    return errors
