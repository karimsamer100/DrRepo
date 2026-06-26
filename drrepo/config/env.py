from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - defensive fallback
    load_dotenv = None


DEFAULT_ENV_FILENAME = ".env"


def locate_env_file(start: Optional[Path] = None) -> Optional[Path]:
    """Locate the repository-level .env file by walking upward from the start path."""
    base = start or Path(__file__).resolve().parent.parent.parent
    current = base if base.is_dir() else base.parent

    for candidate in [current, *current.parents]:
        env_path = candidate / DEFAULT_ENV_FILENAME
        if env_path.is_file():
            return env_path

    return None


def load_repo_dotenv(start: Optional[Path] = None, override: bool = False) -> Optional[Path]:
    """Load the repository-level .env file into os.environ if present."""
    if load_dotenv is None:
        return None

    env_path = locate_env_file(start)
    if env_path is None:
        return None

    loaded = load_dotenv(dotenv_path=env_path, override=override)
    return env_path if loaded else env_path


def get_environment_diagnostics(start: Optional[Path] = None) -> dict[str, object]:
    """Return lightweight diagnostics about the .env resolution state."""
    env_path = locate_env_file(start)
    return {
        "env_path": str(env_path) if env_path else None,
        "dotenv_available": load_dotenv is not None,
        "env_exists": env_path is not None,
    }
