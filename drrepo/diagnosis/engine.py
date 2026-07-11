from typing import Any, Dict, List

from drrepo.assessment import (
    build_evidence_confidence,
    cap_score_for_hard_flags,
    derive_hard_flags,
    first_seen_dedup,
)


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


def _first_error(errors: Any) -> str | None:
    if not isinstance(errors, list):
        return None
    for error in errors:
        if isinstance(error, str) and error.strip():
            return error.strip()
    return None


def build_diagnosis(audit: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(audit, dict):
        audit = {}

    scoring = audit.get("scoring") or {}
    # support both overall_score and overall
    score = None
    if isinstance(scoring, dict):
        score = scoring.get("overall_score") if scoring.get("overall_score") is not None else scoring.get("overall")

    limitations: List[str] = []
    analyzer_entries: List[Dict[str, Any]] = []

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
            errors = entry.get("errors") or []
            summary = entry.get("summary") or {}

            analyzer_entries.append(entry)

            # Missing optional evidence
            if status == "not_available":
                limitations.append("Some optional analysis tools were not available.")
            if status == "skipped_by_config" and isinstance(summary, dict):
                reason = summary.get("reason")
                if isinstance(reason, str) and reason:
                    limitations.append(reason)

            # Coverage specific
            if tool == "coverage" and status in ("not_available", "not_applicable"):
                limitations.append("Coverage evidence was unavailable.")

            # Pytest not applicable
            if tool == "pytest" and status == "not_applicable":
                limitations.append("Test evidence was unavailable.")
            if tool == "pytest" and status == "not_available":
                limitations.append("Pytest was not available in this environment.")
            if tool == "pytest" and status == "failed_to_run":
                reason = _first_error(errors)
                if reason:
                    limitations.append(reason)
                else:
                    limitations.append("Pytest could not run in this environment.")
            if tool == "pytest" and isinstance(entry.get("summary"), dict):
                outcome = entry["summary"].get("outcome")
                if outcome == "failed_tests":
                    limitations.append("Tests ran but failed.")
                elif outcome == "collection_error":
                    limitations.append("Tests could not run because pytest collection failed.")
                elif outcome == "env_error":
                    limitations.append("Tests could not run because of an import or environment issue.")
                elif outcome == "timeout":
                    limitations.append("Pytest timed out before completing.")
                elif outcome == "pytest_unavailable":
                    limitations.append("Pytest was not available in this environment.")

    # Inspect all analyzer sections
    for sec in ("static_analysis", "test_analysis", "repository_analysis"):
        _inspect_entries(sec)

    # Deduplicate preserving first seen order
    hard_flags = derive_hard_flags(analyzer_entries)
    limitations = first_seen_dedup(limitations)
    evidence_confidence = build_evidence_confidence(analyzer_entries)
    calibrated_score = cap_score_for_hard_flags(score, hard_flags)
    label = _label_for_score(calibrated_score)

    # Build summary text
    summaries = {
        "healthy": "Repository looks healthy based on available evidence.",
        "needs_attention": "Repository is mostly usable but has issues worth addressing.",
        "needs_improvement": "Repository needs improvement before it should be considered ready.",
        "needs_major_improvement": "Repository has major readiness issues that should be fixed first.",
    }
    summary = summaries.get(label, "Repository status uncertain.")
    if evidence_confidence and evidence_confidence.get("label") != "full":
        summary = f"{summary} {evidence_confidence.get('summary')}"
    if hard_flags:
        summary = summary + " Hard flags: " + ", ".join(hard_flags) + "."

    diagnosis = {
        "repository_health": {"label": label, "score": calibrated_score, "summary": summary},
        "hard_flags": hard_flags,
        "limitations": limitations,
    }
    if evidence_confidence:
        diagnosis["evidence_confidence"] = evidence_confidence

    return diagnosis
