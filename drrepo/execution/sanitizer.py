from __future__ import annotations

import re
from pathlib import Path

MAX_OUTPUT_CHARS = 4000


def sanitize_output(text: str | None, *, repository_path: Path | None = None) -> str:
    if not text:
        return ""
    sanitized = text.replace("\r\n", "\n").replace("\r", "\n")
    if repository_path is not None:
        try:
            sanitized = sanitized.replace(str(repository_path), "<repository>")
            sanitized = sanitized.replace(str(repository_path.resolve()), "<repository>")
        except Exception:
            pass
    sanitized = re.sub(r"[A-Za-z]:\\[^\s:]+(?:\\[^\s:]+)*", "<host-path>", sanitized)
    sanitized = re.sub(r"/(?:tmp|var/tmp|private/tmp)/[^\s:]+", "<temp-path>", sanitized)
    sanitized = re.sub(
        r"(?i)\bauthorization\s*[:=]\s*[^\n]+",
        "authorization=<redacted>",
        sanitized,
    )
    sanitized = re.sub(
        r"(?i)\b(authorization|api[_-]?key|token|password|secret)\s*[:=]\s*['\"]?[^'\n\"\s]+",
        r"\1=<redacted>",
        sanitized,
    )
    sanitized = re.sub(r"(?i)(bearer|basic)\s+[A-Za-z0-9._~+/=-]{12,}", r"\1 <redacted>", sanitized)
    if len(sanitized) > MAX_OUTPUT_CHARS:
        sanitized = sanitized[:MAX_OUTPUT_CHARS].rstrip() + "\n... <output truncated>"
    return sanitized
