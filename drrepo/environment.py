from __future__ import annotations

from pathlib import Path
from typing import Any


DEPENDENCY_FILES = (
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "poetry.lock",
    "uv.lock",
    "Pipfile",
    "Pipfile.lock",
    "environment.yml",
    "setup.py",
    "setup.cfg",
)

LOCK_FILES = {"poetry.lock", "uv.lock", "Pipfile.lock"}


def detect_dependency_environment(path: str | Path) -> dict[str, Any]:
    root = Path(path)
    present = [name for name in DEPENDENCY_FILES if (root / name).exists()]
    lock_files = [name for name in present if name in LOCK_FILES]

    strategy = "unknown"
    install_command = None
    if "pyproject.toml" in present and "uv.lock" in present:
        strategy = "uv"
        install_command = "uv sync"
    elif "pyproject.toml" in present and "poetry.lock" in present:
        strategy = "poetry"
        install_command = "poetry install"
    elif "Pipfile" in present:
        strategy = "pipenv"
        install_command = "pipenv install --dev"
    elif "environment.yml" in present:
        strategy = "conda"
        install_command = "conda env create -f environment.yml"
    elif "requirements-dev.txt" in present:
        strategy = "pip_requirements"
        install_command = "python -m pip install -r requirements-dev.txt"
    elif "requirements.txt" in present:
        strategy = "pip_requirements"
        install_command = "python -m pip install -r requirements.txt"
    elif "pyproject.toml" in present:
        strategy = "pyproject"
        install_command = "python -m pip install -e ."
    elif "setup.py" in present or "setup.cfg" in present:
        strategy = "setuptools"
        install_command = "python -m pip install -e ."

    return {
        "dependency_files": present,
        "dependency_metadata_exists": bool(present),
        "lock_files": lock_files,
        "lock_file_exists": bool(lock_files),
        "detected_dependency_strategy": strategy,
        "likely_install_command": install_command,
        "note": "Informational only. DrRepo does not install target repository dependencies during audits.",
    }
