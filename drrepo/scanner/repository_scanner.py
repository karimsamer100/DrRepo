"""Repository scanner placeholder functions.

Phase 1: simple placeholder returning a not_implemented status.
"""
from __future__ import annotations

from pathlib import Path


def scan_repository(path: str | Path) -> dict[str, str]:
    """Placeholder scanner that returns a not_implemented response.

    The function intentionally does not perform any scanning yet.
    """
    p = Path(path).expanduser().resolve()
    return {"status": "not_implemented", "path": str(p)}
