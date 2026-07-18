from __future__ import annotations

import time
from copy import deepcopy
from typing import Any, Callable

from .grounding import build_evidence_index, validate_grounding
from .llm_providers import build_provider_metadata
from .llm_router import route_llm_advisor_response
from .priorities import build_profiled_action_plan
from .profiles import validate_profile_id
from .prompting import build_llm_prompt_bundle
from .reporting import build_deterministic_advisor_report

ADVISOR_SERVICE_VERSION = "v1"


def build_advisor_result(
    audit: dict[str, object],
    profile_id: str = "student_portfolio",
    max_actions: int = 5,
    include_prompt_bundle: bool = False,
) -> dict[str, object]:
    """Return a deterministic advisor report with an optional prompt bundle."""
    validate_profile_id(profile_id)

    audit_copy = deepcopy(audit) if isinstance(audit, dict) else {}
    profiled_action_plan = build_profiled_action_plan(audit_copy, profile_id=profile_id, max_actions=max_actions)
    advisor_report = build_deterministic_advisor_report(audit_copy, profile_id=profile_id, max_actions=max_actions)

    result: dict[str, object] = {
        "advisor_service_version": ADVISOR_SERVICE_VERSION,
        "profile_id": profile_id,
        "advisor_report": advisor_report,
    }

    if include_prompt_bundle:
        result["prompt_bundle"] = build_llm_prompt_bundle(audit_copy, profiled_action_plan)

    return result


def _classify_ai_fallback_status(attempts: list[dict[str, Any]]) -> tuple[str, str]:
    """Map provider attempt statuses to a safe API status and reason."""
    for attempt in attempts:
        provider_id = attempt.get("provider_id", "unknown")
        if provider_id == "deterministic_fallback":
            continue
        status = attempt.get("status", "error")
        error = attempt.get("error") or ""
        diagnostics = attempt.get("diagnostics") if isinstance(attempt.get("diagnostics"), dict) else {}
        if status == "missing_api_key":
            return "provider_not_configured", f"Provider {provider_id} is not configured."
        if diagnostics.get("classification") == "invalid_json" or status == "invalid_json" or "invalid json" in error.lower() or "malformed" in error.lower():
            return "invalid_json", f"Provider {provider_id} returned malformed JSON."
        if status == "invalid_response":
            return "schema_invalid", f"Provider {provider_id} response was not accepted because it did not match the advisor schema."
        if "timeout" in error.lower() or status == "timeout":
            return "timeout", f"Provider {provider_id} timed out."
        if "network" in error.lower():
            return "timeout", f"Provider {provider_id} could not be reached."
        if status == "error":
            return "provider_unavailable", f"Provider {provider_id} was unavailable."
    return "internal_advisor_error", "AI advisor could not produce a valid response."


def build_advisor_for_audit(
    audit: dict[str, object],
    profile_id: str = "student_portfolio",
    ai: bool = False,
    max_actions: int = 5,
    providers: list[Callable[..., Any]] | None = None,
    provider_order: list[str] | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, object]:
    """Shared advisor orchestration used by API and CLI.

    Builds the deterministic audit report exactly once. If ``ai`` is True, it
    routes the prompt to configured providers, validates the schema, grounds the
    response against the audit evidence, and falls back safely to the
    deterministic report on any failure.
    """
    validate_profile_id(profile_id)

    audit_copy = deepcopy(audit) if isinstance(audit, dict) else {}
    advisor_report = build_deterministic_advisor_report(audit_copy, profile_id=profile_id, max_actions=max_actions)
    profiled_action_plan = advisor_report.get("profiled_action_plan", {})
    deterministic_response = advisor_report.get("advisor_response", {})

    ai_result: dict[str, Any] = {
        "requested": False,
        "status": "not_requested",
        "source": "deterministic",
        "provider": None,
        "model": "deterministic-advisor",
        "advisor_response": deterministic_response,
        "grounding_result": None,
        "fallback_reason": None,
        "limitations": list(advisor_report.get("advisor_response", {}).get("limitations", [])),
        "duration_ms": 0,
        "router_result": None,
    }

    if not ai:
        return {
            "advisor_service_version": ADVISOR_SERVICE_VERSION,
            "profile_id": profile_id,
            "advisor_report": advisor_report,
            "ai": ai_result,
        }

    ai_result["requested"] = True
    start = time.perf_counter()

    try:
        prompt_bundle = build_llm_prompt_bundle(audit_copy, profiled_action_plan)
        router_result = route_llm_advisor_response(
            prompt_bundle,
            deterministic_response,
            providers=providers,
            provider_order=provider_order,
        )
    except Exception as exc:  # pragma: no cover - defensive
        ai_result.update(
            {
                "status": "internal_advisor_error",
                "source": "deterministic",
                "fallback_reason": f"Advisor router failed: {type(exc).__name__}",
                "duration_ms": int((time.perf_counter() - start) * 1000),
            }
        )
        return {
            "advisor_service_version": ADVISOR_SERVICE_VERSION,
            "profile_id": profile_id,
            "advisor_report": advisor_report,
            "ai": ai_result,
        }

    duration_ms = int((time.perf_counter() - start) * 1000)
    provider_id = router_result.get("selected_provider_id", "deterministic_fallback")
    used_fallback = router_result.get("used_fallback", True)
    attempts = router_result.get("provider_attempts", [])
    selected_response = router_result.get("advisor_response", deterministic_response)

    ai_result["router_result"] = {
        "selected_provider_id": provider_id,
        "used_fallback": used_fallback,
        "provider_attempts": attempts,
    }

    if timeout_seconds is not None:
        ai_result["timeout_seconds"] = timeout_seconds

    if provider_id == "deterministic_fallback" or used_fallback:
        fallback_status, fallback_reason = _classify_ai_fallback_status(attempts)
        ai_result.update(
            {
                "status": fallback_status,
                "source": "deterministic",
                "provider": provider_id,
                "model": "deterministic-advisor",
                "advisor_response": selected_response,
                "grounding_result": None,
                "fallback_reason": fallback_reason,
                "duration_ms": duration_ms,
            }
        )
        return {
            "advisor_service_version": ADVISOR_SERVICE_VERSION,
            "profile_id": profile_id,
            "advisor_report": advisor_report,
            "ai": ai_result,
        }

    # Provider returned a candidate response. Ground it before trusting it.
    evidence_index = build_evidence_index(audit_copy)
    grounding_result = validate_grounding(selected_response, evidence_index)
    ai_result["grounding_result"] = grounding_result

    if grounding_result.get("valid"):
        try:
            model = build_provider_metadata(provider_id).get("model", "unknown")
        except Exception:  # pragma: no cover - defensive
            model = "unknown"
        ai_result.update(
            {
                "status": "completed",
                "source": "llm",
                "provider": provider_id,
                "model": model,
                "advisor_response": selected_response,
                "fallback_reason": None,
                "duration_ms": duration_ms,
            }
        )
    else:
        ai_result.update(
            {
                "status": "grounding_rejected",
                "source": "deterministic",
                "provider": provider_id,
                "model": "deterministic-advisor",
                "advisor_response": deterministic_response,
                "fallback_reason": "AI response contradicted the audit evidence; using deterministic guidance.",
                "duration_ms": duration_ms,
            }
        )

    return {
        "advisor_service_version": ADVISOR_SERVICE_VERSION,
        "profile_id": profile_id,
        "advisor_report": advisor_report,
        "ai": ai_result,
    }
