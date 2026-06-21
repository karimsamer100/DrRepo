from typing import Any, Dict, List


def _first_seen_dedup(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for i in items:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _label_for_score(score: float | int | None) -> str:
    try:
        s = float(score)
    except Exception:
        return "needs_attention"
    if s >= 85:
        return "healthy"
    if s >= 70:
        return "needs_attention"
    if s >= 50:
        return "needs_improvement"
    return "needs_major_improvement"


def build_diagnosis(audit: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(audit, dict):
        audit = {}

    scoring = audit.get("scoring") or {}
    # support both overall_score and overall
    score = None
    if isinstance(scoring, dict):
        score = scoring.get("overall_score") if scoring.get("overall_score") is not None else scoring.get("overall")

    label = _label_for_score(score)

    hard_flags: List[str] = []
    limitations: List[str] = []

    # Helper to inspect analyzer entries
    def _inspect_entries(section_name: str):
        entries = audit.get(section_name) or []
        if not isinstance(entries, list):
            return
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            tool = entry.get("tool") or entry.get("name") or ""
            status = entry.get("status")
            findings = entry.get("findings") or []

            # Analyzer errors present
            if status in ("failed_to_run", "partial"):
                hard_flags.append("ANALYZER_ERRORS_PRESENT")

            # Missing optional evidence
            if status == "not_available":
                limitations.append("Some optional analysis tools were not available.")

            # Coverage specific
            if tool == "coverage" and status in ("not_available", "not_applicable"):
                limitations.append("Coverage evidence was unavailable.")

            # Pytest not applicable
            if tool == "pytest" and status == "not_applicable":
                limitations.append("Test evidence was unavailable.")

            # Findings-based flags
            if isinstance(findings, list) and findings:
                # README findings
                if tool == "readme":
                    hard_flags.append("README_INCOMPLETE")
                # structure findings
                if tool == "structure":
                    hard_flags.append("STRUCTURE_INCOMPLETE")
                # bandit security
                if tool == "bandit":
                    for f in findings:
                        sev = f.get("severity")
                        if sev in ("medium", "high", "critical"):
                            hard_flags.append("SECURITY_FINDINGS_PRESENT")
                            break
                # pytest findings
                if tool == "pytest":
                    for f in findings:
                        code = f.get("code")
                        if code in ("PYTEST-FAILED", "PYTEST-ERROR"):
                            hard_flags.append("TESTS_FAILING")
                            break

    # Inspect all analyzer sections
    for sec in ("static_analysis", "test_analysis", "repository_analysis"):
        _inspect_entries(sec)

    # Deduplicate preserving first seen order
    hard_flags = _first_seen_dedup(hard_flags)
    limitations = _first_seen_dedup(limitations)

    # Build summary text
    summaries = {
        "healthy": "Repository looks healthy based on available evidence.",
        "needs_attention": "Repository is mostly usable but has issues worth addressing.",
        "needs_improvement": "Repository needs improvement before it should be considered ready.",
        "needs_major_improvement": "Repository has major readiness issues that should be fixed first.",
    }
    summary = summaries.get(label, "Repository status uncertain.")
    if hard_flags:
        summary = summary + " Hard flags: " + ", ".join(hard_flags) + "."

    diagnosis = {
        "repository_health": {"label": label, "score": score, "summary": summary},
        "hard_flags": hard_flags,
        "limitations": limitations,
    }

    return diagnosis
