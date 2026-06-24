from __future__ import annotations

from typing import Dict, Any


BASELINE_VERSION = "v1"


def predict_repository_readiness_baseline(features: Dict[str, Any]) -> str:
    rh = int(features.get("repository_health_score") or 0)
    pytest_failed = int(features.get("pytest_failed_count") or 0)
    pytest_errors = int(features.get("pytest_error_count") or 0)
    bandit_blockers = int(features.get("bandit_high_or_critical_count") or 0)

    if rh >= 85 and pytest_failed == 0 and pytest_errors == 0 and bandit_blockers == 0:
        return "repository_ready"
    if rh >= 60:
        return "needs_improvement"
    return "needs_major_improvement"


def predict_portfolio_readiness_baseline(features: Dict[str, Any]) -> str:
    pr = int(features.get("portfolio_readiness_score") or 0)
    has_readme = bool(features.get("has_readme"))

    if pr >= 85 and has_readme:
        return "portfolio_ready"
    if pr >= 60:
        return "almost_ready"
    return "not_portfolio_ready"


def predict_record_baseline(record: Dict[str, Any]) -> Dict[str, Any]:
    features = record.get("features") or {}
    return {
        "baseline_version": BASELINE_VERSION,
        "repository_readiness_baseline": predict_repository_readiness_baseline(features),
        "portfolio_readiness_baseline": predict_portfolio_readiness_baseline(features),
    }
