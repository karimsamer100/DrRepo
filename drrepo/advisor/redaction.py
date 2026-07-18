"""Redaction helpers for advisor LLM payloads and error messages.

Prevents secret-like values from being serialized into prompts, logs, or
error responses even when they appear inside analyzer findings.
"""
from __future__ import annotations

import os
import re
from copy import deepcopy
from typing import Any


# Patterns that commonly indicate secret-like values in analyzer output.
_SENSITIVE_PATTERNS: list[tuple[str, str]] = [
    (r"[a-zA-Z0-9_-]*api[_-]?key[\s]*[=:][\s]*['\"]?([A-Za-z0-9_\-./+=]+)['\"]?", "<redacted_api_key>"),
    (r"[a-zA-Z0-9_-]*token[\s]*[=:][\s]*['\"]?([A-Za-z0-9_\-./+=]+)['\"]?", "<redacted_token>"),
    (r"[a-zA-Z0-9_-]*secret[\s]*[=:][\s]*['\"]?([A-Za-z0-9_\-./+=]+)['\"]?", "<redacted_secret>"),
    (r"[a-zA-Z0-9_-]*password[\s]*[=:][\s]*['\"]?([^'\"\s]+)['\"]?", "<redacted_password>"),
    (r"BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY", "<redacted_private_key>"),
    (r"AKIA[0-9A-Z]{16}", "<redacted_aws_key>"),
    (r"ghp_[A-Za-z0-9_]{36}", "<redacted_github_token>"),
    (r"glpat-[A-Za-z0-9_\-]{20}", "<redacted_gitlab_token>"),
    (r"sk-[a-zA-Z0-9]{48}", "<redacted_openai_key>"),
]


def _known_secrets() -> set[str]:
    """Collect known provider/API secrets from environment variables."""
    env_vars = (
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GROQ_API_KEY",
        "CEREBRAS_API_KEY",
        "OPENROUTER_API_KEY",
    )
    secrets: set[str] = set()
    for name in env_vars:
        value = os.getenv(name)
        if value:
            secrets.add(value)
    return secrets


def redact_text(text: str) -> str:
    """Redact secret-like values from a text string."""
    if not isinstance(text, str):
        return text

    redacted = text
    for pattern, replacement in _SENSITIVE_PATTERNS:
        redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)

    for secret in _known_secrets():
        if secret and secret in redacted:
            redacted = redacted.replace(secret, "<redacted>")

    return redacted


def _redact_value(value: Any) -> Any:
    """Recursively redact strings inside a JSON-like structure."""
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {k: _redact_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    return value


def redact_audit_copy(audit: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy of the audit with secret-like strings redacted.

    The original audit is never mutated.
    """
    if not isinstance(audit, dict):
        return {}
    return _redact_value(deepcopy(audit))


def redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Redact a prompt payload before serialization or logging."""
    return _redact_value(deepcopy(payload))


def redact_exception_message(message: str) -> str:
    """Redact secrets from an exception or safe error message."""
    return redact_text(message)
