from __future__ import annotations

from dataclasses import dataclass
from typing import Any

LLM_PROVIDER_INTERFACE_VERSION = "v1"

DEFAULT_PROVIDER_ORDER = [
    "gemini",
    "groq",
    "cerebras",
    "openrouter",
    "deterministic_fallback",
]

SUPPORTED_PROVIDER_IDS = set(DEFAULT_PROVIDER_ORDER)


@dataclass
class LLMProviderResult:
    provider_id: str
    status: str
    response: dict[str, object] | None = None
    error: str | None = None
    raw_response: object | None = None


def get_default_provider_order() -> list[str]:
    return list(DEFAULT_PROVIDER_ORDER)


def get_supported_provider_ids() -> list[str]:
    return sorted(SUPPORTED_PROVIDER_IDS)


def validate_provider_id(provider_id: str) -> None:
    if provider_id not in SUPPORTED_PROVIDER_IDS:
        raise ValueError(f"unsupported provider id: {provider_id}")


def build_provider_metadata(provider_id: str) -> dict[str, object]:
    validate_provider_id(provider_id)

    if provider_id == "gemini":
        return {
            "provider_id": provider_id,
            "display_name": "Google Gemini",
            "model": "gemini-2.5-flash",
            "role": "primary",
            "api_key_env": "GEMINI_API_KEY",
            "supports_structured_output": True,
            "notes": ["Free-tier/API-key-based usage may have rate limits and model availability limits."],
        }
    if provider_id == "groq":
        return {
            "provider_id": provider_id,
            "display_name": "Groq",
            "model": "gpt-oss-120b",
            "role": "primary",
            "api_key_env": "GROQ_API_KEY",
            "supports_structured_output": True,
            "notes": ["Free-tier/API-key-based usage may have rate limits and model availability limits."],
        }
    if provider_id == "cerebras":
        return {
            "provider_id": provider_id,
            "display_name": "Cerebras",
            "model": "gpt-oss-120b",
            "role": "fallback",
            "api_key_env": "CEREBRAS_API_KEY",
            "supports_structured_output": True,
            "notes": ["Free-tier/API-key-based usage may have rate limits and model availability limits."],
        }
    if provider_id == "openrouter":
        return {
            "provider_id": provider_id,
            "display_name": "OpenRouter",
            "model": "openai/gpt-oss-120b:free",
            "role": "fallback",
            "api_key_env": "OPENROUTER_API_KEY",
            "supports_structured_output": True,
            "notes": ["Model availability and free-tier eligibility can vary by account and region."],
        }
    return {
        "provider_id": provider_id,
        "display_name": "Deterministic Fallback",
        "model": "deterministic-advisor",
        "role": "deterministic_fallback",
        "api_key_env": None,
        "supports_structured_output": True,
        "notes": ["Uses the local deterministic advisor response when providers are unavailable or invalid."],
    }
