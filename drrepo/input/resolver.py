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


def find_repository_root(path: str | Path) -> Path:
    """Find the repository root by walking parents for common root markers.

    The function resolves the supplied path first, then walks upward
    until it finds a directory that contains one of the root marker
    files or folders. If none is found, the resolved path is returned.

    This is intentionally simple: it looks only for files/folders and
    does not invoke any VCS commands.
    """
    p = resolve_local_path(path)

    markers = [
        ".git",
        "pyproject.toml",
        "setup.py",
        "requirements.txt",
        "README.md",
        "README.rst",
    ]

    current: Path = p
    for candidate in [current] + list(current.parents):
        try:
            entries = {child.name for child in candidate.iterdir()}
        except Exception:
            entries = set()

        for m in markers:
            if m in entries:
                return candidate

    return p
