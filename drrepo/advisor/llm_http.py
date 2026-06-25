from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request

from .llm_contract import validate_llm_advisor_response
from .llm_providers import LLMProviderResult

LLM_HTTP_ADAPTER_VERSION = "v1"


def _build_request_payload(prompt_bundle: dict[str, object], provider_id: str) -> dict[str, object]:
    return {
        "provider_id": provider_id,
        "model": provider_id,
        "messages": [
            {"role": "system", "content": prompt_bundle.get("system_prompt", "")},
            {"role": "user", "content": prompt_bundle.get("user_prompt", "")},
        ],
        "response_format": {"type": "json_object"},
        "metadata": {
            "contract_version": prompt_bundle.get("contract_version", "v1"),
            "expected_output_schema": prompt_bundle.get("expected_output_schema", {}),
        },
    }


def _default_transport(url: str, headers: dict[str, str], payload: dict[str, object]) -> Any:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except (error.URLError, error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(str(exc)) from exc


def _provider_error(provider_id: str, exc: Exception) -> LLMProviderResult:
    message = str(exc)
    for secret in (
        os.getenv("GEMINI_API_KEY", ""),
        os.getenv("GROQ_API_KEY", ""),
        os.getenv("CEREBRAS_API_KEY", ""),
        os.getenv("OPENROUTER_API_KEY", ""),
        "abc123",
    ):
        if secret:
            message = message.replace(secret, "<redacted>")
    return LLMProviderResult(provider_id=provider_id, status="error", error=message)


def _call_provider(
    provider_id: str,
    api_key: str | None,
    endpoint: str,
    transport: callable | None,
    prompt_bundle: dict[str, object],
) -> LLMProviderResult:
    if api_key is None:
        return LLMProviderResult(provider_id=provider_id, status="missing_api_key")

    payload = _build_request_payload(prompt_bundle, provider_id)
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    try:
        if transport is None:
            raw_response = _default_transport(endpoint, headers, payload)
        else:
            try:
                raw_response = transport(payload)
            except TypeError:
                raw_response = transport(endpoint, headers, payload)
    except Exception as exc:  # pragma: no cover - exercised via tests
        return _provider_error(provider_id, exc)

    return parse_llm_json_response(provider_id, raw_response)


def call_gemini_advisor(
    prompt_bundle: dict[str, object],
    api_key: str | None = None,
    transport: callable | None = None,
) -> LLMProviderResult:
    resolved_key = api_key or os.getenv("GEMINI_API_KEY")
    return _call_provider("gemini", resolved_key, "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent", transport, prompt_bundle)


def call_groq_advisor(
    prompt_bundle: dict[str, object],
    api_key: str | None = None,
    transport: callable | None = None,
) -> LLMProviderResult:
    resolved_key = api_key or os.getenv("GROQ_API_KEY")
    return _call_provider("groq", resolved_key, "https://api.groq.com/openai/v1/chat/completions", transport, prompt_bundle)


def call_cerebras_advisor(
    prompt_bundle: dict[str, object],
    api_key: str | None = None,
    transport: callable | None = None,
) -> LLMProviderResult:
    resolved_key = api_key or os.getenv("CEREBRAS_API_KEY")
    return _call_provider("cerebras", resolved_key, "https://api.cerebras.ai/v1/chat/completions", transport, prompt_bundle)


def call_openrouter_advisor(
    prompt_bundle: dict[str, object],
    api_key: str | None = None,
    transport: callable | None = None,
) -> LLMProviderResult:
    resolved_key = api_key or os.getenv("OPENROUTER_API_KEY")
    return _call_provider("openrouter", resolved_key, "https://openrouter.ai/api/v1/chat/completions", transport, prompt_bundle)


def parse_llm_json_response(provider_id: str, raw_response: object) -> LLMProviderResult:
    if isinstance(raw_response, dict):
        if isinstance(raw_response.get("response"), dict):
            candidate = raw_response["response"]
        elif isinstance(raw_response.get("candidates"), list):
            candidate = raw_response["candidates"][0] if raw_response["candidates"] else {}
            if isinstance(candidate, dict):
                content = candidate.get("content") or {}
                if isinstance(content, dict):
                    parts = content.get("parts") or []
                    if isinstance(parts, list) and parts:
                        text = parts[0].get("text") if isinstance(parts[0], dict) else None
                        if isinstance(text, str):
                            candidate = text
                        else:
                            candidate = None
                    else:
                        candidate = None
                else:
                    candidate = None
            else:
                candidate = None
        elif isinstance(raw_response.get("choices"), list):
            choice = raw_response["choices"][0] if raw_response["choices"] else {}
            if isinstance(choice, dict):
                message = choice.get("message") or {}
                if isinstance(message, dict):
                    content = message.get("content")
                    candidate = content if isinstance(content, str) else None
                else:
                    candidate = None
            else:
                candidate = None
        else:
            candidate = raw_response
    elif isinstance(raw_response, str):
        candidate = raw_response
    else:
        candidate = None

    if candidate is None:
        return LLMProviderResult(provider_id=provider_id, status="invalid_response", error="No JSON payload found")

    if isinstance(candidate, str):
        if candidate.startswith("{") or candidate.startswith("["):
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError as exc:
                return LLMProviderResult(provider_id=provider_id, status="invalid_response", error=str(exc))
        else:
            return LLMProviderResult(provider_id=provider_id, status="invalid_response", error="Unsupported response payload")
    else:
        parsed = candidate

    if isinstance(parsed, dict):
        errors = validate_llm_advisor_response(parsed)
        if errors:
            return LLMProviderResult(provider_id=provider_id, status="invalid_response", error="; ".join(errors), raw_response=raw_response)
        return LLMProviderResult(provider_id=provider_id, status="ok", response=parsed, raw_response=raw_response)

    return LLMProviderResult(provider_id=provider_id, status="invalid_response", error="Parsed payload is not a JSON object", raw_response=raw_response)


def build_provider_callables_from_environment(
    include_providers: list[str] | None = None,
) -> list[callable]:
    providers = include_providers or ["gemini", "groq", "cerebras", "openrouter"]
    callables: list[callable] = []
    for provider_id in providers:
        if provider_id == "gemini":
            callables.append(_wrap_provider_callable(call_gemini_advisor))
        elif provider_id == "groq":
            callables.append(_wrap_provider_callable(call_groq_advisor))
        elif provider_id == "cerebras":
            callables.append(_wrap_provider_callable(call_cerebras_advisor))
        elif provider_id == "openrouter":
            callables.append(_wrap_provider_callable(call_openrouter_advisor))
    return callables


def _wrap_provider_callable(adapter: callable) -> callable:
    def wrapped(prompt_bundle: dict[str, object], fallback_response: dict[str, object] | None = None) -> LLMProviderResult:
        return adapter(prompt_bundle, api_key=None, transport=None)

    wrapped.__name__ = getattr(adapter, "__name__", "provider")
    return wrapped
