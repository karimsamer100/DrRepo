from __future__ import annotations

import os
from pathlib import Path
from typing import Any


FALSE_VALUES = {"0", "false", "no", "off", "disabled"}


def local_path_policy() -> dict[str, Any]:
    enabled = os.getenv("DRREPO_LOCAL_PATH_AUDITS", "true").strip().lower() not in FALSE_VALUES
    roots = _allowed_roots()
    return {
        "enabled": enabled,
        "restricted_to_allowed_roots": bool(roots),
        "public_mode": not enabled,
        "limitation": (
            "Local repository audits are disabled on this API instance; public GitHub repository audits remain available."
            if not enabled
            else "Local repository paths are resolved on the API server filesystem."
        ),
    }


def validate_local_source_path(source_value: str) -> str:
    policy = local_path_policy()
    if not policy["enabled"]:
        raise ValueError("Local repository audits are disabled on this API instance. Use a public GitHub repository URL.")

    roots = _allowed_roots()
    if not roots:
        return source_value

    candidate = Path(source_value).expanduser().resolve(strict=True)
    if any(_is_relative_to(candidate, root) for root in roots):
        return str(candidate)
    raise ValueError("Local repository path is outside the allowed audit roots.")


def _allowed_roots() -> list[Path]:
    raw = os.getenv("DRREPO_ALLOWED_ROOTS", "")
    if not raw.strip():
        return []
    parts: list[str] = []
    for chunk in raw.split(os.pathsep):
        parts.extend(item.strip() for item in chunk.split(","))
    roots: list[Path] = []
    for item in parts:
        if not item:
            continue
        roots.append(Path(item).expanduser().resolve(strict=True))
    return roots


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
