"""Repository scanner with minimal metadata extraction.

This scanner is intentionally simple: it walks the repository tree,
ignoring common cache/build directories and computes a few lightweight
metrics about files and project layout. The output is JSON-serializable
and suitable for printing by the CLI.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from drrepo.input.resolver import resolve_local_path


_IGNORED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "drrepo.egg-info",
}


def _is_ignored(path: Path, root: Path, ignored: set[str]) -> bool:
    """Return True if `path` is inside any ignored directory relative to root."""
    try:
        rel = path.relative_to(root)
    except Exception:
        return False

    for part in rel.parts:
        if part in ignored:
            return True
    return False


def scan_repository(path: str | Path) -> dict[str, object]:
    """Scan a local repository path and return lightweight metadata.

    The function resolves and validates the path using
    `drrepo.input.resolver.resolve_local_path` and then walks the tree
    counting files while skipping common generated/cache directories.
    """
    root = resolve_local_path(path)

    total_files = 0
    python_files = 0
    test_files = 0
    has_readme = False
    has_tests_folder = False
    has_docs = False
    has_requirements = False
    has_pyproject = False
    has_gitignore = False
    has_env_example = False
    has_dockerfile = False
    has_ci = False

    # Check for some root-level markers first
    root_files = {p.name.lower(): p for p in root.iterdir() if p.exists()}
    # README detection (case-insensitive)
    for name in root_files:
        if name.startswith("readme"):
            has_readme = True
            break

    if "pyproject.toml" in root_files:
        has_pyproject = True

    if "requirements.txt" in root_files:
        has_requirements = True

    if ".gitignore" in root_files:
        has_gitignore = True

    if ".env.example" in root_files:
        has_env_example = True

    if "dockerfile" in root_files or "dockerfile" in (n.lower() for n in root_files):
        # dockerfile may be upper or lower case
        has_dockerfile = True

    if (root / ".github" / "workflows").is_dir():
        has_ci = True

    if (root / "docs").is_dir():
        has_docs = True

    if (root / "tests").is_dir():
        has_tests_folder = True

    # Walk the tree and collect file counts, skipping ignored directories
    for p in root.rglob("*"):
        if p.is_dir():
            continue

        if _is_ignored(p, root, _IGNORED_DIRS):
            continue

        total_files += 1

        if p.suffix == ".py":
            python_files += 1

            name = p.name
            # test file naming conventions
            if name.startswith("test_") or name.endswith("_test.py"):
                test_files += 1
            else:
                # file inside a tests/ folder also counts as test file
                if "tests" in p.parts:
                    test_files += 1

    has_tests = has_tests_folder or test_files > 0

    metadata = {
        "total_files": total_files,
        "python_files": python_files,
        "test_files": test_files,
        "has_readme": has_readme,
        "has_tests": has_tests,
        "has_docs": has_docs,
        "has_requirements": has_requirements,
        "has_pyproject": has_pyproject,
        "has_gitignore": has_gitignore,
        "has_env_example": has_env_example,
        "has_dockerfile": has_dockerfile,
        "has_ci": has_ci,
    }

    return {"status": "ok", "path": str(root), "metadata": metadata}
