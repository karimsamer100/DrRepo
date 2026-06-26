from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request

from drrepo.config import load_repo_dotenv

from .llm_contract import get_llm_advisor_action_schema, validate_llm_advisor_response
from .llm_providers import LLMProviderResult

load_repo_dotenv()

LLM_HTTP_ADAPTER_VERSION = "v1"
DEFAULT_HTTP_TIMEOUT_SECONDS = 30

_LLM_ADVISOR_REQUIRED_FIELDS = (
    "summary",
    "profile_context",
    "top_priorities",
    "lower_priority_items",
    "limitations",
    "next_steps",
)


class ProviderHTTPError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, safe_message: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.safe_message = safe_message or message


def _build_request_payload(
    prompt_bundle: dict[str, object],
    provider_id: str,
    *,
    endpoint_family: str | None = None,
    model_name: str | None = None,
) -> dict[str, object]:
    if endpoint_family == "gemini_interactions":
        system_prompt = str(prompt_bundle.get("system_prompt", ""))
        user_prompt = str(prompt_bundle.get("user_prompt", ""))
        combined_prompt = (
            f"System instructions:\n{system_prompt}\n\n"
            f"User request:\n{user_prompt}\n\n"
            "Return only valid JSON matching the advisor response contract."
        )
        return {
            "model": model_name or "gemini-2.5-flash",
            "input": combined_prompt,
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "profile_context": {"type": "string"},
                        "top_priorities": {"type": "array", "items": get_llm_advisor_action_schema()},
                        "lower_priority_items": {"type": "array", "items": get_llm_advisor_action_schema()},
                        "limitations": {"type": "array", "items": {"type": "string"}},
                        "next_steps": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": list(_LLM_ADVISOR_REQUIRED_FIELDS),
                },
            },
        }

    return {
        "provider_id": provider_id,
        "model": model_name or provider_id,
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
        with request.urlopen(req, timeout=DEFAULT_HTTP_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                parsed_body = _parse_json_text(body)
                if parsed_body is not None:
                    return parsed_body
                raise
    except error.HTTPError as exc:
        status_code = exc.code
        safe_message = _safe_http_error_message(str(exc.reason or exc), status_code)
        raise ProviderHTTPError(str(exc), status_code=status_code, safe_message=safe_message) from exc
    except error.URLError as exc:
        raise ProviderHTTPError(str(exc.reason or exc), safe_message="Network error while contacting provider") from exc
    except (TimeoutError, ValueError, json.JSONDecodeError) as exc:
        raise ProviderHTTPError(str(exc), safe_message="Request timed out or returned invalid JSON") from exc


def _sanitize_secret(message: str) -> str:
    message = str(message)
    for secret in (
        os.getenv("GEMINI_API_KEY", ""),
        os.getenv("GOOGLE_API_KEY", ""),
        os.getenv("GROQ_API_KEY", ""),
        os.getenv("CEREBRAS_API_KEY", ""),
        os.getenv("OPENROUTER_API_KEY", ""),
        "abc123",
    ):
        if secret:
            message = message.replace(secret, "<redacted>")
    return message


def _safe_http_error_message(message: str, status_code: int | None) -> str:
    lowered = (message or "").lower()
    if status_code in (401, 403):
        return "API key not valid or unauthorized"
    if status_code == 429:
        return "Rate limited by provider"
    if status_code is not None and 500 <= status_code < 600:
        return "Provider returned a server error"
    if "timeout" in lowered or "timed out" in lowered:
        return "Request timed out"
    if "network" in lowered or "connection" in lowered:
        return "Network error while contacting provider"
    return message or "Provider request failed"


def _classify_error(status_code: int | None, message: str | None) -> str:
    lowered = (message or "").lower()
    if status_code in (401, 403) or "unauthorized" in lowered or "forbidden" in lowered or "invalid key" in lowered or "invalid api key" in lowered or "invalid token" in lowered:
        return "auth_error"
    if status_code == 429 or "rate limit" in lowered or "too many requests" in lowered:
        return "rate_limit"
    if status_code is not None and 500 <= status_code < 600:
        return "provider_error"
    if "timeout" in lowered or "timed out" in lowered or "network" in lowered or "connection" in lowered:
        return "network_error"
    return "provider_error"


def _provider_error(
    provider_id: str,
    exc: Exception,
    *,
    endpoint_family: str | None = None,
    auth_method: str | None = None,
) -> LLMProviderResult:
    message = str(exc)
    http_status = None
    safe_message = message
    if isinstance(exc, ProviderHTTPError):
        http_status = exc.status_code
        safe_message = exc.safe_message
    elif hasattr(exc, "code") and getattr(exc, "code", None) is not None:
        http_status = getattr(exc, "code")
        safe_message = _safe_http_error_message(message, http_status)
    else:
        safe_message = _safe_http_error_message(message, None)

    safe_message = _sanitize_secret(safe_message)
    error_category = _classify_error(http_status, safe_message)
    return LLMProviderResult(
        provider_id=provider_id,
        status="error",
        error=safe_message,
        error_category=error_category,
        http_status=http_status,
        safe_message=safe_message,
        endpoint_family=endpoint_family,
        auth_method=auth_method,
    )


def _call_provider(
    provider_id: str,
    api_key: str | None,
    endpoint: str,
    transport: callable | None,
    prompt_bundle: dict[str, object],
    *,
    endpoint_family: str | None = None,
    auth_method: str | None = None,
    model_name: str | None = None,
) -> LLMProviderResult:
    if api_key is None:
        return LLMProviderResult(
            provider_id=provider_id,
            status="missing_api_key",
            endpoint_family=endpoint_family,
            auth_method=auth_method,
        )

    payload = _build_request_payload(prompt_bundle, provider_id, endpoint_family=endpoint_family, model_name=model_name)
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if auth_method == "x-goog-api-key":
        headers["x-goog-api-key"] = api_key
    else:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        if transport is None:
            raw_response = _default_transport(endpoint, headers, payload)
        else:
            try:
                raw_response = transport(endpoint, headers, payload)
            except TypeError:
                raw_response = transport(payload)
    except Exception as exc:  # pragma: no cover - exercised via tests
        return _provider_error(provider_id, exc, endpoint_family=endpoint_family, auth_method=auth_method)

    return parse_llm_json_response(provider_id, raw_response, endpoint_family=endpoint_family, auth_method=auth_method)


def call_gemini_advisor(
    prompt_bundle: dict[str, object],
    api_key: str | None = None,
    transport: callable | None = None,
) -> LLMProviderResult:
    resolved_key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    return _call_provider(
        "gemini",
        resolved_key,
        "https://generativelanguage.googleapis.com/v1beta/interactions",
        transport,
        prompt_bundle,
        endpoint_family="gemini_interactions",
        auth_method="x-goog-api-key",
        model_name="gemini-2.5-flash",
    )


def call_groq_advisor(
    prompt_bundle: dict[str, object],
    api_key: str | None = None,
    transport: callable | None = None,
) -> LLMProviderResult:
    resolved_key = api_key if api_key is not None else os.getenv("GROQ_API_KEY")
    return _call_provider(
        "groq",
        resolved_key,
        "https://api.groq.com/openai/v1/chat/completions",
        transport,
        prompt_bundle,
        endpoint_family="openai_compatible_chat",
        auth_method="bearer_token",
        model_name="openai/gpt-oss-120b",
    )


def call_cerebras_advisor(
    prompt_bundle: dict[str, object],
    api_key: str | None = None,
    transport: callable | None = None,
) -> LLMProviderResult:
    resolved_key = api_key if api_key is not None else os.getenv("CEREBRAS_API_KEY")
    return _call_provider(
        "cerebras",
        resolved_key,
        "https://api.cerebras.ai/v1/chat/completions",
        transport,
        prompt_bundle,
        endpoint_family="openai_compatible_chat",
        auth_method="bearer_token",
        model_name="gpt-oss-120b",
    )


def call_openrouter_advisor(
    prompt_bundle: dict[str, object],
    api_key: str | None = None,
    transport: callable | None = None,
) -> LLMProviderResult:
    resolved_key = api_key if api_key is not None else os.getenv("OPENROUTER_API_KEY")
    return _call_provider(
        "openrouter",
        resolved_key,
        "https://openrouter.ai/api/v1/chat/completions",
        transport,
        prompt_bundle,
        endpoint_family="openai_compatible_chat",
        auth_method="bearer_token",
        model_name="openai/gpt-oss-120b",
    )


def _has_advisor_response_fields(value: object) -> bool:
    return isinstance(value, dict) and all(field in value for field in _LLM_ADVISOR_REQUIRED_FIELDS)


def _extract_last_text_block(value: object) -> str | None:
    if isinstance(value, str):
        return value if value.strip() else None
    if isinstance(value, list):
        for item in reversed(value):
            candidate = _extract_last_text_block(item)
            if candidate is not None:
                return candidate
        return None
    if not isinstance(value, dict):
        return None

    for key in ("output_text", "final_output", "final_text", "response_text", "text", "output"):
        if key in value:
            candidate = _extract_last_text_block(value.get(key))
            if candidate is not None:
                return candidate

    for key in ("parts", "candidates", "steps", "model_output", "content"):
        if key in value:
            candidate = _extract_last_text_block(value.get(key))
            if candidate is not None:
                return candidate

    return None


def _parse_json_text(text: str) -> object | None:
    stripped = text.strip()
    candidates = [stripped]
    if "{" in stripped and "}" in stripped:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < end:
            candidates.append(stripped[start : end + 1])
    if "[" in stripped and "]" in stripped:
        start = stripped.find("[")
        end = stripped.rfind("]")
        if start < end:
            candidates.append(stripped[start : end + 1])

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _extract_gemini_candidate(raw_response: object) -> tuple[object | None, bool]:
    if _has_advisor_response_fields(raw_response):
        return raw_response, True
    if isinstance(raw_response, str):
        return raw_response, True
    if not isinstance(raw_response, dict):
        return None, False

    for key in ("output_text", "output", "text", "final_output", "final_text", "response_text"):
        if key not in raw_response:
            continue
        candidate_value = raw_response.get(key)
        if isinstance(candidate_value, dict) and _has_advisor_response_fields(candidate_value):
            return candidate_value, True
        candidate_text = _extract_last_text_block(candidate_value)
        if candidate_text is not None:
            return candidate_text, True

    for key in ("steps", "model_output", "content", "candidates"):
        if key not in raw_response:
            continue
        candidate_text = _extract_last_text_block(raw_response.get(key))
        if candidate_text is not None:
            return candidate_text, True

    return None, True


def _extract_candidate(raw_response: object, provider_id: str | None = None) -> object:
    if provider_id == "gemini":
        candidate, found_text = _extract_gemini_candidate(raw_response)
        if candidate is None and found_text:
            return None
        if candidate is not None:
            return candidate
        return None
    if isinstance(raw_response, dict):
        if isinstance(raw_response.get("response"), dict):
            return _extract_candidate(raw_response["response"])
        if isinstance(raw_response.get("output_text"), str):
            return raw_response["output_text"]
        if isinstance(raw_response.get("text"), str):
            return raw_response["text"]
        if isinstance(raw_response.get("candidates"), list):
            candidate = raw_response["candidates"][0] if raw_response["candidates"] else {}
            if isinstance(candidate, dict):
                content = candidate.get("content") or {}
                if isinstance(content, dict):
                    parts = content.get("parts") or []
                    if isinstance(parts, list) and parts:
                        text = parts[0].get("text") if isinstance(parts[0], dict) else None
                        if isinstance(text, str):
                            return text
                return None
        if isinstance(raw_response.get("choices"), list):
            choice = raw_response["choices"][0] if raw_response["choices"] else {}
            if isinstance(choice, dict):
                message = choice.get("message") or {}
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str):
                        return content
        return raw_response
    if isinstance(raw_response, str):
        return raw_response
    return None


def parse_llm_json_response(
    provider_id: str,
    raw_response: object,
    *,
    endpoint_family: str | None = None,
    auth_method: str | None = None,
) -> LLMProviderResult:
    candidate = _extract_candidate(raw_response, provider_id)

    if candidate is None:
        safe_message = "no final Gemini output text found" if provider_id == "gemini" and isinstance(raw_response, dict) else "No JSON payload found"
        return LLMProviderResult(
            provider_id=provider_id,
            status="invalid_response",
            error=safe_message,
            error_category="invalid_response",
            safe_message=safe_message,
            endpoint_family=endpoint_family,
            auth_method=auth_method,
        )

    if isinstance(candidate, str):
        if provider_id == "gemini":
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError as exc:
                return LLMProviderResult(
                    provider_id=provider_id,
                    status="invalid_response",
                    error=str(exc),
                    error_category="invalid_response",
                    safe_message=str(exc),
                    endpoint_family=endpoint_family,
                    auth_method=auth_method,
                )
        elif candidate.startswith("{") or candidate.startswith("["):
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError as exc:
                return LLMProviderResult(
                    provider_id=provider_id,
                    status="invalid_response",
                    error=str(exc),
                    error_category="invalid_response",
                    safe_message=str(exc),
                    endpoint_family=endpoint_family,
                    auth_method=auth_method,
                )
        else:
            return LLMProviderResult(
                provider_id=provider_id,
                status="invalid_response",
                error="Unsupported response payload",
                error_category="invalid_response",
                safe_message="Unsupported response payload",
                endpoint_family=endpoint_family,
                auth_method=auth_method,
            )
    else:
        parsed = candidate

    if isinstance(parsed, dict):
        errors = validate_llm_advisor_response(parsed)
        if errors:
            return LLMProviderResult(
                provider_id=provider_id,
                status="invalid_response",
                error="; ".join(errors),
                raw_response=raw_response,
                error_category="invalid_response",
                safe_message="; ".join(errors),
                endpoint_family=endpoint_family,
                auth_method=auth_method,
            )
        return LLMProviderResult(
            provider_id=provider_id,
            status="ok",
            response=parsed,
            raw_response=raw_response,
            endpoint_family=endpoint_family,
            auth_method=auth_method,
        )

    return LLMProviderResult(
        provider_id=provider_id,
        status="invalid_response",
        error="Parsed payload is not a JSON object",
        raw_response=raw_response,
        error_category="invalid_response",
        safe_message="Parsed payload is not a JSON object",
        endpoint_family=endpoint_family,
        auth_method=auth_method,
    )


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
