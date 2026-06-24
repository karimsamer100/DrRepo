from __future__ import annotations

from typing import Dict, Any, List

RUBRIC_VERSION = "v1-draft"

_REPOSITORY_LABELS = (
    "needs_major_improvement",
    "needs_improvement",
    "repository_ready",
)

_PORTFOLIO_LABELS = (
    "not_portfolio_ready",
    "almost_ready",
    "portfolio_ready",
)

_ALLOWED_EVIDENCE = {
    "tests",
    "coverage",
    "static_analysis",
    "readme",
    "structure",
    "security",
    "maintainability",
    "manual_review",
}

_WEAK_METHODS = {"rule_score", "baseline_prediction", "copied_from_score"}


def _label_entry(label: str, meaning: str, pos: list, neg: list, notes: str) -> Dict[str, Any]:
    return {
        "label": label,
        "meaning": meaning,
        "positive_signals": pos,
        "negative_signals": neg,
        "reviewer_notes": notes,
    }


def get_repository_readiness_rubric() -> Dict[str, Any]:
    return {
        "rubric_version": RUBRIC_VERSION,
        "labels": [
            _label_entry(
                "needs_major_improvement",
                "Repository lacks basic CI/tests/docs and has significant issues.",
                ["no_tests", "low_coverage", "many_high_severity_security_findings"],
                ["passing_tests", "high_health_score"],
                "Requires substantial developer effort.",
            ),
            _label_entry(
                "needs_improvement",
                "Repository has some tests/docs but requires attention before production use.",
                ["some_failing_tests", "moderate_security_findings"],
                ["most_tests_passing", "reasonable_coverage"],
                "Consider incremental improvements.",
            ),
            _label_entry(
                "repository_ready",
                "Repository is in good health: CI, tests, and low severity findings.",
                ["passing_tests", "good_coverage", "low_security_findings"],
                ["failing_tests", "critical_security_findings"],
                "Suitable for production with normal review.",
            ),
        ],
    }


def get_portfolio_readiness_rubric() -> Dict[str, Any]:
    return {
        "rubric_version": RUBRIC_VERSION,
        "labels": [
            _label_entry(
                "not_portfolio_ready",
                "Repository is unlikely to be suitable as a standard portfolio component.",
                ["missing_docs", "low_structure_score"],
                ["consistent_docs", "high_structure_score"],
                "May be acceptable for exploration but not integration.",
            ),
            _label_entry(
                "almost_ready",
                "Repository is close to portfolio readiness but needs minor improvements.",
                ["minor_docs_gaps", "some_structure_issues"],
                ["good_docs", "consistent_structure"],
                "Fix minor issues and re-evaluate.",
            ),
            _label_entry(
                "portfolio_ready",
                "Repository meets portfolio standards for reuse and integration.",
                ["clear_docs", "consistent_structure", "good_testing"],
                ["missing_docs", "unstable_tests"],
                "Candidate for inclusion in portfolio.",
            ),
        ],
    }


def get_full_labeling_rubric() -> Dict[str, Any]:
    return {
        "rubric_version": RUBRIC_VERSION,
        "repository_readiness": get_repository_readiness_rubric(),
        "portfolio_readiness": get_portfolio_readiness_rubric(),
        "leakage_warning": "Do not assign labels solely by copying DrRepo rule scores or baseline predictions. Human review required.",
        "recommended_label_provenance_fields": ["rubric_version", "method", "labeler", "reviewed_evidence"],
    }


def validate_label_provenance_for_training(labels: object, label_provenance: object) -> List[str]:
    errs: List[str] = []
    if not labels:
        return errs
    if not isinstance(labels, dict):
        errs.append("labels must be a dict")
        return errs
    if not isinstance(label_provenance, dict):
        errs.append("label_provenance must be a dict when labels are provided")
        return errs

    # required fields
    for k in ("rubric_version", "method", "labeler", "reviewed_evidence"):
        if k not in label_provenance:
            errs.append(f"label_provenance missing required key: {k}")

    if label_provenance.get("rubric_version") != RUBRIC_VERSION:
        errs.append(f"label_provenance.rubric_version must be {RUBRIC_VERSION}")

    method = label_provenance.get("method")
    if isinstance(method, str) and method in _WEAK_METHODS:
        errs.append(f"label_provenance.method '{method}' is a weak method and poses leakage risk")

    reviewed = label_provenance.get("reviewed_evidence")
    if not isinstance(reviewed, list) or len(reviewed) == 0:
        errs.append("label_provenance.reviewed_evidence must be a non-empty list")
    else:
        for ev in reviewed:
            if ev not in _ALLOWED_EVIDENCE:
                errs.append(f"label_provenance.reviewed_evidence contains unknown evidence: {ev}")

    return errs
