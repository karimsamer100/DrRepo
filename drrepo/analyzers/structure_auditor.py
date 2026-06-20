from __future__ import annotations

from pathlib import Path
from typing import List

from ..input.resolver import resolve_local_path
from .models import ToolResult, ToolFinding


IGNORED_DIRS = {"tests", "docs", ".git", ".venv", "venv", "__pycache__"}


def audit_structure(path: str | Path) -> ToolResult:
    tool = "structure"
    resolved = resolve_local_path(path)

    # Gather top-level files and directories
    top_level_files: List[str] = []
    top_level_dirs: List[str] = []
    for child in sorted(resolved.iterdir(), key=lambda p: p.name):
        if child.is_dir():
            top_level_dirs.append(child.name)
        elif child.is_file():
            top_level_files.append(child.name)

    findings: List[ToolFinding] = []

    # Tests check
    has_tests = False
    if (resolved / "tests").is_dir():
        has_tests = True
    else:
        # search for test_*.py or *_test.py anywhere
        for p in resolved.rglob("test_*.py"):
            if p.is_file():
                has_tests = True
                break
        if not has_tests:
            for p in resolved.rglob("*_test.py"):
                if p.is_file():
                    has_tests = True
                    break

    if not has_tests:
        findings.append(
            ToolFinding(
                tool=tool,
                message="Repository has no obvious tests",
                severity="medium",
                code="STRUCTURE-MISSING-TESTS",
            )
        )

    # Dependency file
    dep_files = [
        "pyproject.toml",
        "requirements.txt",
        "setup.py",
        "setup.cfg",
        "Pipfile",
        "poetry.lock",
    ]
    has_dependency_file = any((resolved / f).exists() for f in dep_files)
    if not has_dependency_file:
        findings.append(
            ToolFinding(
                tool=tool,
                message="Repository has no dependency/configuration file",
                severity="medium",
                code="STRUCTURE-MISSING-DEPENDENCY-FILE",
            )
        )

    # .gitignore
    has_gitignore = (resolved / ".gitignore").exists()
    if not has_gitignore:
        findings.append(
            ToolFinding(
                tool=tool,
                message="Repository is missing .gitignore",
                severity="low",
                code="STRUCTURE-MISSING-GITIGNORE",
            )
        )

    # .env.example
    has_env_example = (resolved / ".env.example").exists()
    if not has_env_example:
        findings.append(
            ToolFinding(
                tool=tool,
                message="Repository is missing .env.example",
                severity="low",
                code="STRUCTURE-MISSING-ENV-EXAMPLE",
            )
        )

    # docs
    has_docs = (resolved / "docs").is_dir()
    if not has_docs:
        findings.append(
            ToolFinding(
                tool=tool,
                message="Repository is missing docs directory",
                severity="low",
                code="STRUCTURE-MISSING-DOCS",
            )
        )

    # Source roots
    source_roots: List[str] = []
    # src/ preferred
    if (resolved / "src").is_dir():
        source_roots.append("src")

    # top-level dirs with .py files
    for dname in top_level_dirs:
        if dname in IGNORED_DIRS:
            continue
        dpath = resolved / dname
        has_py = any(p.is_file() for p in dpath.rglob("*.py"))
        if has_py:
            source_roots.append(dname)

    # root-level .py files
    has_root_py = any(p.is_file() for p in resolved.glob("*.py"))
    if has_root_py:
        source_roots.append(".")

    if not source_roots:
        findings.append(
            ToolFinding(
                tool=tool,
                message="Repository has no obvious Python source root",
                severity="medium",
                code="STRUCTURE-MISSING-SOURCE-ROOT",
            )
        )

    summary = {
        "has_tests": has_tests,
        "has_dependency_file": has_dependency_file,
        "has_config_file": has_dependency_file,
        "has_gitignore": has_gitignore,
        "has_env_example": has_env_example,
        "has_docs": has_docs,
        "source_roots": source_roots,
        "top_level_directories": top_level_dirs,
        "top_level_files": top_level_files,
    }

    return ToolResult(tool=tool, status="completed", summary=summary, findings=findings)
