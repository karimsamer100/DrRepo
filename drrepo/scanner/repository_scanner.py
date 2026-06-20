"""Repository scanner with minimal metadata extraction.

This scanner is intentionally simple: it walks the repository tree,
ignoring common cache/build directories and computes a few lightweight
metrics about files and project layout. The output is JSON-serializable
and suitable for printing by the CLI.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from drrepo.input.resolver import resolve_local_path, find_repository_root


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
    # Determine the repository root (may be the same as the input path)
    root = find_repository_root(path)

    total_files = 0
    python_files = 0
    test_files = 0
    total_directories = 0
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
    entries = {p.name for p in root.iterdir() if p.exists()}

    # README detection (case-insensitive)
    for name in entries:
        if name.lower().startswith("readme"):
            has_readme = True
            break

    if "pyproject.toml" in entries:
        has_pyproject = True

    if "requirements.txt" in entries:
        has_requirements = True

    if ".gitignore" in entries:
        has_gitignore = True

    if ".env.example" in entries:
        has_env_example = True

    # dockerfile may be upper or lower case
    if any(n.lower() == "dockerfile" for n in entries):
        has_dockerfile = True

    if (root / ".github" / "workflows").is_dir():
        has_ci = True

    if (root / "docs").is_dir():
        has_docs = True

    if (root / "tests").is_dir():
        has_tests_folder = True

    # Collect root markers present at detected root
    possible_markers = [
        ".git",
        "pyproject.toml",
        "setup.py",
        "requirements.txt",
        "README.md",
        "README.rst",
    ]

    root_markers: list[str] = []
    for m in possible_markers:
        if (root / m).exists():
            root_markers.append(m)

    # Top-level files and directories (exclude ignored)
    top_level_files: list[str] = []
    top_level_directories: list[str] = []
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        if _is_ignored(child, root, _IGNORED_DIRS):
            continue
        if child.is_dir():
            top_level_directories.append(child.name)
        elif child.is_file():
            top_level_files.append(child.name)

    # Single pass: collect scanned files and directories excluding ignored
    scanned_files: list[Path] = []
    scanned_directories: list[Path] = []
    for p in root.rglob("*"):
        if p.is_dir():
            if not _is_ignored(p, root, _IGNORED_DIRS):
                scanned_directories.append(p)
            continue

        if _is_ignored(p, root, _IGNORED_DIRS):
            continue

        scanned_files.append(p)

    # Use collected lists to compute metrics
    total_files = len(scanned_files)
    total_directories = len(scanned_directories)

    file_extensions: dict[str, int] = {}
    for p in scanned_files:
        ext = p.suffix.lower() if p.suffix else "<no_ext>"
        file_extensions[ext] = file_extensions.get(ext, 0) + 1

        if p.suffix == ".py":
            python_files += 1
            name = p.name
            if name.startswith("test_") or name.endswith("_test.py") or "tests" in p.parts:
                test_files += 1

    has_tests = has_tests_folder or test_files > 0

    # dependency and config files at root
    dependency_names = [
        "requirements.txt",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "Pipfile",
        "Pipfile.lock",
        "poetry.lock",
        "uv.lock",
        "environment.yml",
        "environment.yaml",
    ]

    config_names = [
        "pyproject.toml",
        "setup.cfg",
        "tox.ini",
        "pytest.ini",
        "mypy.ini",
        ".ruff.toml",
        ".pre-commit-config.yaml",
    ]

    dependency_files = sorted([n for n in dependency_names if (root / n).exists()])
    config_files = sorted([n for n in config_names if (root / n).exists()])

    # source roots: top-level locations that contain python files
    source_roots_set: set[str] = set()
    # root level python files
    if any((root / f).is_file() and (root / f).suffix.lower() == ".py" for f in top_level_files):
        source_roots_set.add(".")

    excluded_source_dirs = {"tests", "test", "docs", "examples", ".github"}
    for dname in top_level_directories:
        if dname in excluded_source_dirs:
            continue
        dpath = root / dname
        # find any .py file in this top-level directory (recursively)
        found = False
        for p in dpath.rglob("*.py"):
            if _is_ignored(p, root, _IGNORED_DIRS):
                continue
            found = True
            break
        if found:
            source_roots_set.add(dname)

    source_roots = sorted(source_roots_set)

    metadata = {
        "total_files": total_files,
        "total_directories": total_directories,
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
        "root_markers": root_markers,
        "top_level_files": top_level_files,
        "top_level_directories": top_level_directories,
        "file_extensions": file_extensions,
        "dependency_files": dependency_files,
        "config_files": config_files,
        "source_roots": source_roots,
    }

    return {"status": "ok", "path": str(root), "metadata": metadata}
