from typing import Dict, List, Any, Tuple


def _mk_suggestion(section: str, tool: str, code: str | None, severity: str | None, title: str, message: str, action: str) -> Dict[str, Any]:
    return {
        "section": section,
        "tool": tool,
        "code": code,
        "severity": severity,
        "title": title,
        "message": message,
        "action": action,
    }


def generate_suggestions(audit: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not audit or not isinstance(audit, dict):
        return []

    suggestions: List[Dict[str, Any]] = []
    seen: set[Tuple[Any, ...]] = set()

    sections = ["static_analysis", "test_analysis", "repository_analysis"]

    for section in sections:
        analyzers = audit.get(section) or []
        if not isinstance(analyzers, list):
            continue

        for analyzer in analyzers:
            tool = analyzer.get("tool") if isinstance(analyzer, dict) else None
            status = analyzer.get("status") if isinstance(analyzer, dict) else None
            findings = analyzer.get("findings") if isinstance(analyzer, dict) else None
            errors = analyzer.get("errors") if isinstance(analyzer, dict) else None

            # Findings first
            if isinstance(findings, list):
                for finding in findings:
                    if not isinstance(finding, dict):
                        continue
                    code = finding.get("code")
                    sev = finding.get("severity")
                    message = finding.get("message") or ""

                    title = None
                    action = None

                    # Test findings
                    if code == "PYTEST-FAILED":
                        title = "Fix failing tests"
                        action = "Run pytest locally, inspect failing tests, and fix the failing behavior."
                    elif code == "PYTEST-ERROR":
                        title = "Fix test collection/runtime errors"
                        action = "Run pytest locally and fix import, fixture, or runtime errors."

                    # README findings
                    elif isinstance(code, str) and code.startswith("README-MISSING-"):
                        title = "Improve README documentation"
                        action = "Add the missing README section or information mentioned by the finding."
                    elif code == "README-TOO-SHORT":
                        title = "Expand README"
                        action = "Add project overview, setup, usage, tests, configuration, and license information."

                    # Structure findings
                    elif code == "STRUCTURE-MISSING-TESTS":
                        title = "Add tests"
                        action = "Create a tests/ directory and add pytest tests for core behavior."
                    elif code == "STRUCTURE-MISSING-DEPENDENCY-FILE":
                        title = "Add dependency configuration"
                        action = "Add pyproject.toml or requirements.txt to document project dependencies."
                    elif code == "STRUCTURE-MISSING-GITIGNORE":
                        title = "Add .gitignore"
                        action = "Add a .gitignore file to exclude virtual environments, caches, and build artifacts."
                    elif code == "STRUCTURE-MISSING-ENV-EXAMPLE":
                        title = "Add .env.example"
                        action = "Add .env.example to document required environment variables without secrets."
                    elif code == "STRUCTURE-MISSING-DOCS":
                        title = "Add documentation folder"
                        action = "Create docs/ for additional project documentation when needed."
                    elif code == "STRUCTURE-MISSING-SOURCE-ROOT":
                        title = "Clarify source layout"
                        action = "Move Python source into a clear package directory or src/ layout."

                    # Static/security findings by tool
                    elif tool == "bandit":
                        title = "Review security finding"
                        action = "Inspect the Bandit finding and replace unsafe code with a safer alternative."
                    elif tool == "ruff":
                        title = "Fix lint finding"
                        action = "Run Ruff locally and apply the suggested lint fix."
                    elif tool == "radon":
                        title = "Reduce code complexity"
                        action = "Refactor complex functions into smaller, simpler units."

                    # Generic fallback
                    else:
                        title = "Review analyzer finding"
                        action = "Inspect the finding and decide whether code, tests, or documentation should be updated."

                    msg = message or ""
                    # Build suggestion
                    sugg = _mk_suggestion(section=section, tool=tool or "", code=code, severity=sev, title=title, message=msg, action=action)

                    key = (section, tool, code, title, action)
                    if key not in seen:
                        suggestions.append(sugg)
                        seen.add(key)

            # Status-based suggestions (not_available)
            if status == "not_available":
                title = f"Install optional tool: {tool or ''}"
                msg = f"{tool or 'Tool'} is not available in this environment."
                action = "Install the optional tool or ignore this result if it is not needed."
                code = "TOOL-NOT-AVAILABLE"
                severity = "low"
                key = (section, tool, code, title, action)
                if key not in seen:
                    suggestions.append(_mk_suggestion(section, tool or "", code, severity, title, msg, action))
                    seen.add(key)

            # Error fallback (if there are errors and status is not 'not_available')
            if status is not None and status != "not_available":
                if isinstance(errors, list) and errors:
                    title = "Investigate analyzer error"
                    action = "Review analyzer stderr/output and fix configuration or execution issues."
                    msg = "; ".join(str(e) for e in errors)
                    code = "ANALYZER-ERROR"
                    key = (section, tool, code, title, action)
                    if key not in seen:
                        suggestions.append(_mk_suggestion(section, tool or "", code, None, title, msg, action))
                        seen.add(key)

    return suggestions


def count_suggestions_by_severity(suggestions: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for s in suggestions:
        sev = s.get("severity") if isinstance(s, dict) else None
        key = sev if isinstance(sev, str) and sev else "unknown"
        counts[key] = counts.get(key, 0) + 1

    # Return dict sorted by key for deterministic output
    return dict(sorted(counts.items()))
