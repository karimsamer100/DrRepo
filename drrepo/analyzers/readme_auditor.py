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

HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(?P<text>.+?)\s*$")
SETEXT_UNDERLINE_RE = re.compile(r"^[=-]{3,}\s*$")

DESCRIPTION_PATTERNS = (
    r"\bdescription\b",
    r"\boverview\b",
    r"\babout\b",
    r"\bwhat it does\b",
)

INSTALLATION_PATTERNS = (
    r"\binstall(?:ation|ing|ed)?\b",
    r"\bsetup\b",
    r"\bset up\b",
    r"\bgetting started\b",
    r"\bquick ?start\b",
)

INSTALLATION_EVIDENCE_PATTERNS = (
    r"\bpip install\b",
    r"\bpoetry install\b",
    r"\buv sync\b",
    r"\bnpm (?:install|ci)\b",
    r"\bpnpm install\b",
    r"\byarn install\b",
    r"\bmake install\b",
)

USAGE_HEADING_PATTERNS = (
    r"\busage\b",
    r"\brun\b",
    r"\bdemo\b",
    r"\bexample(?:s)?\b",
)

USAGE_TEXT_PATTERNS = (
    r"\bhow to run\b",
    r"\brun locally\b",
    r"\bto run\b",
    r"\brun the (?:app|application|project|service|server|cli)\b",
    r"\bstart the (?:app|application|project|service|server|cli)\b",
    r"\blaunch\b",
    r"\bdemo\b",
    r"\bexample usage\b",
)

USAGE_COMMAND_PATTERNS = (
    r"\bpython\s+-m\s+(?!pytest\b)\S+\b",
    r"\bpython\s+\S+\.py\b",
    r"\bdrrepo\s+\w+\b",
    r"\buvicorn\b",
    r"\bnpm\s+(?:run\s+\w+|start)\b",
    r"\bpnpm\s+(?:run\s+\w+|start)\b",
    r"\byarn\s+(?:start|\w+)\b",
    r"\bdocker compose up\b",
)

REQUIREMENTS_PATTERNS = (
    r"\brequirements?\b",
    r"\bdependencies?\b",
    r"\bprerequisites?\b",
)

REQUIREMENTS_EVIDENCE_PATTERNS = (
    r"\brequires?\b.*\bpython\b",
    r"\bpython\s+\d+(?:\.\d+)?\+?\b",
    r"\brequirements\.txt\b",
    r"\bpyproject\.toml\b",
    r"\bpip install\b",
)

ENVIRONMENT_PATTERNS = (
    r"\benvironment\b",
    r"\benvironment variables?\b",
    r"\benv vars?\b",
    r"\benv variables?\b",
    r"\bconfiguration\b",
    r"\bconfig\b",
    r"\bconfigure\b",
    r"\bsettings\b",
)

ENVIRONMENT_EVIDENCE_PATTERNS = (
    r"\.env(?:\.[a-z0-9_-]+)?\b",
    r"(?m)^\s*(?:export\s+)?[A-Z][A-Z0-9_]{2,}\s*=",
    r"(?m)^\s*set(?:x)?\s+[A-Z][A-Z0-9_]{2,}\s*=",
)

TEST_PATTERNS = (
    r"\btests?\b",
    r"\btesting\b",
)

TEST_EVIDENCE_PATTERNS = (
    r"\bpytest\b",
    r"\bpython\s+-m\s+pytest\b",
    r"\brun (?:the )?tests?\b",
    r"\bmake test\b",
    r"\btox\b",
    r"\bnox\b",
)

LICENSE_HEADING_PATTERNS = (
    r"\blicen[cs]e\b",
)

LICENSE_TEXT_PATTERNS = (
    r"\blicen[cs]e\b",
    r"\b(?:licensed|released) under (?:the )?(?:mit|apache(?:[-\s]2(?:\.0)?)?|bsd(?:[-\s]\d)?(?:-clause)?|gpl(?:[-\s]v?\d(?:\.\d)?)?|mpl(?:[-\s]2(?:\.0)?)?|unlicense)\b",
)


def _locate_readme(root: Path) -> Path | None:
    for name in COMMON_README_NAMES:
        p = root / name
        if p.exists() and p.is_file():
            return p
    return None


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _extract_sections(raw: str) -> list[tuple[str | None, str]]:
    sections: list[tuple[str | None, str]] = []
    current_heading: str | None = None
    current_body: list[str] = []

    for line in raw.splitlines():
        heading = HEADING_RE.match(line)
        if heading:
            sections.append((current_heading, "\n".join(current_body).casefold()))
            current_heading = heading.group("text").strip().casefold()
            current_body = []
            continue
        current_body.append(line)

    sections.append((current_heading, "\n".join(current_body).casefold()))
    return sections


def _extract_prose_lines(raw: str) -> list[str]:
    prose_lines: list[str] = []
    in_fenced_block = False

    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fenced_block = not in_fenced_block
            continue
        if in_fenced_block or not stripped or HEADING_RE.match(stripped):
            continue
        prose_lines.append(stripped.casefold())

    return prose_lines


def _has_project_title(lines: list[str]) -> bool:
    if not lines:
        return False
    if lines[0].strip().startswith("#"):
        return True
    return len(lines) >= 2 and bool(SETEXT_UNDERLINE_RE.fullmatch(lines[1].strip()))


def _has_description(lower: str, prose_lines: list[str], word_count: int) -> bool:
    if _matches_any(lower, DESCRIPTION_PATTERNS):
        return True
    if any(len(re.findall(r"\w+", line)) >= 5 for line in prose_lines[:3]):
        return True
    return word_count >= 50 and bool(prose_lines)


def _has_heading(headings: list[str], patterns: tuple[str, ...]) -> bool:
    return any(_matches_any(heading, patterns) for heading in headings)


def _has_section_body_match(
    sections: list[tuple[str | None, str]],
    heading_patterns: tuple[str, ...],
    body_patterns: tuple[str, ...],
) -> bool:
    for heading, body in sections:
        if heading and _matches_any(heading, heading_patterns) and _matches_any(body, body_patterns):
            return True
    return False


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
    section_count = sum(1 for line in raw.splitlines() if HEADING_RE.match(line))

    # detect signals/sections
    lower = raw.casefold()
    sections = _extract_sections(raw)
    headings = [heading for heading, _ in sections if heading]
    prose_lines = _extract_prose_lines(raw)

    missing: List[str] = []

    # project title: first non-empty line starts with '#' or uses setext-style markup
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    has_title = _has_project_title(lines)
    if not has_title:
        missing.append("project_title")

    # description: explicit description keywords or early prose introducing the project
    has_description = _has_description(lower, prose_lines, word_count)
    if not has_description:
        missing.append("description")

    # installation
    has_installation = (
        _has_heading(headings, INSTALLATION_PATTERNS)
        or _matches_any(lower, INSTALLATION_EVIDENCE_PATTERNS)
    )
    if not has_installation:
        missing.append("installation")

    # usage
    has_usage = (
        _has_heading(headings, USAGE_HEADING_PATTERNS)
        or _matches_any(lower, USAGE_TEXT_PATTERNS)
        or _has_section_body_match(sections, INSTALLATION_PATTERNS + USAGE_HEADING_PATTERNS, USAGE_COMMAND_PATTERNS)
        or _matches_any(lower, USAGE_COMMAND_PATTERNS)
    )
    if not has_usage:
        missing.append("usage")

    # tests
    has_tests = _has_heading(headings, TEST_PATTERNS) or _matches_any(lower, TEST_EVIDENCE_PATTERNS)
    if not has_tests:
        missing.append("tests")

    # requirements / dependencies
    has_requirements = (
        _has_heading(headings, REQUIREMENTS_PATTERNS)
        or _matches_any(lower, REQUIREMENTS_EVIDENCE_PATTERNS)
        or _has_section_body_match(sections, INSTALLATION_PATTERNS, REQUIREMENTS_EVIDENCE_PATTERNS)
    )
    if not has_requirements:
        missing.append("requirements")

    # environment / configuration
    has_environment = _has_heading(headings, ENVIRONMENT_PATTERNS) or _matches_any(lower, ENVIRONMENT_EVIDENCE_PATTERNS)
    if not has_environment:
        missing.append("environment")

    # license
    has_license = _has_heading(headings, LICENSE_HEADING_PATTERNS) or _matches_any(lower, LICENSE_TEXT_PATTERNS)
    if not has_license:
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

    # Keep a short README finding for genuinely thin READMEs, but do not penalize
    # compact READMEs that still cover all required documentation areas.
    if word_count < 20 or (word_count < 50 and missing):
        findings.append(
            ToolFinding(
                tool=tool,
                message="README is very short",
                severity="low",
                code="README-TOO-SHORT",
            )
        )

    return ToolResult(tool=tool, status="completed", summary=summary, findings=findings)
