from __future__ import annotations

from pathlib import Path
from typing import Any

from drrepo.environment import detect_dependency_environment

WORKDIR = "/workspace"


def allowed_install_command(repository_path: Path) -> list[str] | None:
    """Return a conservative dependency-install command.

    The plan intentionally ignores README/prose commands and supports only
    common Python strategies that do not require host-side package managers.
    Dependency installation still may execute package build hooks, so callers
    must require an explicit opt-in before using this command.
    """
    detected = detect_dependency_environment(repository_path)
    files = set(detected.get("dependency_files", []) or [])
    if "requirements-dev.txt" in files:
        return ["-m", "pip", "install", "-r", "requirements-dev.txt"]
    if "requirements.txt" in files:
        return ["-m", "pip", "install", "-r", "requirements.txt"]
    if "pyproject.toml" in files:
        return ["-m", "pip", "install", "-e", "."]
    if "setup.py" in files or "setup.cfg" in files:
        return ["-m", "pip", "install", "-e", "."]
    return None


def build_runner_plan(
    *,
    repository_path: Path,
    requested_checks: tuple[str, ...],
    install_dependencies: bool,
    allow_install_network: bool,
    per_command_timeout_seconds: int,
    include_setup: bool = True,
    include_checks: bool = True,
    python_bin: str = "python",
) -> dict[str, Any]:
    commands: list[dict[str, Any]] = []
    setup_command = allowed_install_command(repository_path) if install_dependencies else None
    if include_setup and install_dependencies and setup_command is None:
        commands.append({
            "id": "setup",
            "args": [],
            "skip": True,
            "reason": "No supported dependency installation strategy was detected.",
            "network": False,
            "timeout_seconds": per_command_timeout_seconds,
        })
    elif include_setup and setup_command:
        commands.append({
            "id": "setup_venv",
            "args": ["python", "-m", "venv", f"{WORKDIR}/.drrepo_venv"],
            "network": False,
            "timeout_seconds": per_command_timeout_seconds,
        })
        commands.append({
            "id": "setup",
            "args": [f"{WORKDIR}/.drrepo_venv/bin/python", *setup_command],
            "network": allow_install_network,
            "timeout_seconds": per_command_timeout_seconds,
        })
    if not include_checks:
        return {"workdir": WORKDIR, "commands": commands}
    if "syntax" in requested_checks:
        commands.append({
            "id": "syntax",
            "args": [python_bin, "-m", "compileall", "-q", WORKDIR],
            "network": False,
            "timeout_seconds": per_command_timeout_seconds,
        })
    if "pytest" in requested_checks:
        commands.append({
            "id": "pytest",
            "args": [python_bin, "-m", "pytest", WORKDIR, "-q", "-p", "no:cacheprovider", "--ignore-glob=*pytest-cache-files-*"],
            "network": False,
            "timeout_seconds": per_command_timeout_seconds,
        })
    if "coverage" in requested_checks:
        commands.append({
            "id": "coverage",
            "args": [python_bin, "-m", "coverage", "run", "-m", "pytest", WORKDIR, "-q"],
            "network": False,
            "timeout_seconds": per_command_timeout_seconds,
        })
        commands.append({
            "id": "coverage_json",
            "args": [python_bin, "-m", "coverage", "json", "-o", "/results/coverage.json"],
            "network": False,
            "timeout_seconds": per_command_timeout_seconds,
        })
    return {"workdir": WORKDIR, "commands": commands}
