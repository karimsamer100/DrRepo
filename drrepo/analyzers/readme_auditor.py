from __future__ import annotations

from pathlib import Path
from typing import List
import re

from ..input.resolver import resolve_local_path
from .models import ToolResult, ToolFinding


COMMON_README_NAMES = [
    "README.md",
    "README.rst",
    "README.txt",
    "readme.md",
    "readme.rst",
    "readme.txt",
]


def _locate_readme(root: Path) -> Path | None:
    for name in COMMON_README_NAMES:
        p = root / name
        if p.exists() and p.is_file():
            return p
    return None


def audit_readme(path: str | Path) -> ToolResult:
    tool = "readme"
    resolved = resolve_local_path(path)

    readme_path = _locate_readme(resolved)
    if not readme_path:
        summary = {
            "has_readme": False,
            "readme_path": None,
            "word_count": 0,
            "section_count": 0,
            "missing_sections": [
                "project_title",
                "description",
                "installation",
                "usage",
                "tests",
                "requirements",
                "environment",
                "license",
            ],
        }
        finding = ToolFinding(
            tool=tool,
            message="README file is missing",
            severity="medium",
            code="README-MISSING",
        )
        return ToolResult(tool=tool, status="not_applicable", summary=summary, findings=[finding])

    # Read content
    raw = readme_path.read_text(encoding="utf-8", errors="replace")
    words = re.findall(r"\w+", raw)
    word_count = len(words)
    # count markdown headings (# at line start)
    section_count = sum(1 for line in raw.splitlines() if line.strip().startswith("#"))

    # detect signals/sections
    lower = raw.lower()

    missing: List[str] = []

    # project title: first non-empty line starts with '#'
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    has_title = False
    if lines:
        has_title = lines[0].strip().startswith("#")
    if not has_title:
        missing.append("project_title")

    # description: either explicit keywords, a long README, or a short paragraph under title
    has_description = False
    if "description" in lower or "overview" in lower or "about" in lower or word_count >= 50:
        has_description = True
    else:
        # check second non-empty line for a short description
        if len(lines) >= 2:
            second = lines[1].strip()
            if not second.startswith("#") and len(re.findall(r"\w+", second)) >= 5:
                has_description = True

    if not has_description:
        missing.append("description")

    # installation
    if not ("install" in lower or "installation" in lower or "setup" in lower):
        missing.append("installation")

    # usage
    if not ("usage" in lower or "how to run" in lower or "howto" in lower or "run" in lower):
        missing.append("usage")

    # tests
    if not ("test" in lower or "pytest" in lower):
        missing.append("tests")

    # requirements / dependencies
    if not ("requirements" in lower or "dependencies" in lower or "pip install" in lower):
        missing.append("requirements")

    # environment / configuration
    if not (".env" in lower or "environment" in lower or "configuration" in lower or "config" in lower):
        missing.append("environment")

    # license
    if not ("license" in lower):
        missing.append("license")

    summary = {
        "has_readme": True,
        "readme_path": str(readme_path),
        "word_count": word_count,
        "section_count": section_count,
        "missing_sections": missing,
    }

    findings: List[ToolFinding] = []
    # Findings for missing sections
    for sec in missing:
        findings.append(
            ToolFinding(
                tool=tool,
                message="README is missing information",
                severity="low",
                code=f"README-MISSING-{sec.upper()}",
            )
        )

    # Too short
    if word_count < 50:
        findings.append(
            ToolFinding(
                tool=tool,
                message="README is very short",
                severity="low",
                code="README-TOO-SHORT",
            )
        )

    return ToolResult(tool=tool, status="completed", summary=summary, findings=findings)
