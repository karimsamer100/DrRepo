"""Path resolver helper utilities.

Keep this module free of CLI dependencies so it can be reused in other contexts.
"""
from __future__ import annotations

from pathlib import Path


def resolve_local_path(path: str | Path) -> Path:
    """Resolve a user-supplied path to an absolute local directory Path.

    - Expands user (~)
    - Resolves to an absolute path
    - Raises FileNotFoundError if missing
    - Raises NotADirectoryError if the path exists but is not a directory
    """
    p = Path(path).expanduser().resolve()

    if not p.exists():
        raise FileNotFoundError(f"Path does not exist: {p}")

    if not p.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {p}")

    return p
