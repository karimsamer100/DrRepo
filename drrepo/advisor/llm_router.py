from __future__ import annotations

from copy import deepcopy
from typing import Any

from .llm_contract import build_fallback_advisor_response, validate_llm_advisor_response
from .llm_http import build_provider_callables_from_environment
from .llm_providers import LLMProviderResult, validate_provider_id

LLM_ROUTER_VERSION = "v1"


def route_llm_advisor_response(
    prompt_bundle: dict[str, object],
    fallback_response: dict[str, object],
    providers: list[callable] | None = None,
    provider_order: list[str] | None = None,
) -> dict[str, object]:
    prompt_copy = deepcopy(prompt_bundle) if isinstance(prompt_bundle, dict) else {}
    fallback_copy = deepcopy(fallback_response) if isinstance(fallback_response, dict) else {}

    if provider_order is not None:
        for provider_id in provider_order:
            validate_provider_id(provider_id)

    if providers is None:
        providers = build_default_router_providers_from_environment()
        providers = list(providers)
    else:
        providers = list(providers)

    if provider_order is not None:
        ordered_providers: list[callable] = []
        for provider_id in provider_order:
            if provider_id == "deterministic_fallback":
                ordered_providers.append(build_deterministic_provider(fallback_copy))
            elif provider_id in {"gemini", "groq", "cerebras", "openrouter"}:
                for candidate in providers:
                    if getattr(candidate, "__name__", "") == f"call_{provider_id}_advisor":
                        ordered_providers.append(candidate)
                        break
                else:
                    ordered_providers.append(build_deterministic_provider(fallback_copy))
        providers = ordered_providers

    providers.append(build_deterministic_provider(fallback_copy))

    attempts: list[dict[str, object]] = []
    for provider in providers:
        if provider is None:
            continue
        try:
            result = provider(prompt_copy, fallback_copy)
        except Exception as exc:  # pragma: no cover - defensive
            result = LLMProviderResult(provider_id="unknown", status="error", error=str(exc))

        provider_id = getattr(result, "provider_id", "unknown")
        attempts.append({"provider_id": provider_id, "status": result.status, "error": result.error})

        if result.status == "ok" and isinstance(result.response, dict):
            errors = validate_llm_advisor_response(result.response)
            if not errors:
                return {
                    "router_version": LLM_ROUTER_VERSION,
                    "selected_provider_id": provider_id,
                    "used_fallback": provider_id == "deterministic_fallback",
                    "provider_attempts": attempts,
                    "advisor_response": result.response,
                    "validation_errors": [],
                }

    fallback_result = build_deterministic_provider(fallback_copy)(prompt_copy, fallback_copy)
    return {
        "router_version": LLM_ROUTER_VERSION,
        "selected_provider_id": fallback_result.provider_id,
        "used_fallback": True,
        "provider_attempts": attempts + [{"provider_id": fallback_result.provider_id, "status": fallback_result.status}],
        "advisor_response": fallback_copy,
        "validation_errors": [],
    }


def build_deterministic_provider(fallback_response: dict[str, object]) -> callable:
    def provider(prompt_bundle: dict[str, object], fallback_response_arg: dict[str, object] | None = None) -> LLMProviderResult:
        response = fallback_response_arg if isinstance(fallback_response_arg, dict) else fallback_response
        if isinstance(response, dict):
            errors = validate_llm_advisor_response(response)
            if errors:
                response = build_fallback_advisor_response({})
        return LLMProviderResult(provider_id="deterministic_fallback", status="ok", response=response)

    provider.__name__ = "call_deterministic_fallback"
    return provider


def build_default_router_providers_from_environment() -> list[callable]:
    return build_provider_callables_from_environment()
