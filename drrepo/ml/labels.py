from __future__ import annotations

from typing import Dict, Any, List
from drrepo.features.schema import FEATURE_FIELDS

LABEL_RUBRIC_VERSION = "v1-draft"

REPOSITORY_READINESS_LABELS = (
    "needs_major_improvement",
    "needs_improvement",
    "repository_ready",
)

PORTFOLIO_READINESS_LABELS = (
    "not_portfolio_ready",
    "almost_ready",
    "portfolio_ready",
)

LABEL_FIELDS = ("repository_readiness_label", "portfolio_readiness_label")


def get_label_rubric() -> Dict[str, Any]:
    return {
        "rubric_version": LABEL_RUBRIC_VERSION,
        "label_fields": list(LABEL_FIELDS),
        "repository_readiness_labels": list(REPOSITORY_READINESS_LABELS),
        "portfolio_readiness_labels": list(PORTFOLIO_READINESS_LABELS),
        "notes": "These are draft Phase 6 label spaces and rubrics. Review before training.",
    }


def validate_labels(labels: object) -> List[str]:
    errors: List[str] = []
    if labels is None:
        return errors
    if not isinstance(labels, dict):
        errors.append("labels must be a dict")
        return errors

    # unknown keys
    for k in labels.keys():
        if k not in LABEL_FIELDS:
            errors.append(f"unknown label key: {k}")

    # validate values
    repo_label = labels.get("repository_readiness_label")
    if repo_label is not None and repo_label not in REPOSITORY_READINESS_LABELS:
        errors.append(f"invalid repository_readiness_label: {repo_label}")

    port_label = labels.get("portfolio_readiness_label")
    if port_label is not None and port_label not in PORTFOLIO_READINESS_LABELS:
        errors.append(f"invalid portfolio_readiness_label: {port_label}")

    # reject keys that look like feature fields
    for k in labels.keys():
        if k in FEATURE_FIELDS:
            errors.append(f"label key conflicts with feature field: {k}")

    return errors
