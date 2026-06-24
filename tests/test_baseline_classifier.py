from drrepo.ml.baseline import (
    predict_repository_readiness_baseline,
    predict_portfolio_readiness_baseline,
    predict_record_baseline,
)


def test_repository_baseline_ready():
    features = {"repository_health_score": 90, "pytest_failed_count": 0, "pytest_error_count": 0, "bandit_high_or_critical_count": 0}
    assert predict_repository_readiness_baseline(features) == "repository_ready"


def test_repository_baseline_needs_improvement():
    features = {"repository_health_score": 65, "pytest_failed_count": 0, "pytest_error_count": 0, "bandit_high_or_critical_count": 0}
    assert predict_repository_readiness_baseline(features) == "needs_improvement"


def test_repository_baseline_major_improvement():
    features = {"repository_health_score": 50}
    assert predict_repository_readiness_baseline(features) == "needs_major_improvement"


def test_repository_not_ready_if_tests_fail_or_bandit_blockers():
    features = {"repository_health_score": 90, "pytest_failed_count": 1, "pytest_error_count": 0, "bandit_high_or_critical_count": 0}
    assert predict_repository_readiness_baseline(features) != "repository_ready"
    features2 = {"repository_health_score": 90, "pytest_failed_count": 0, "pytest_error_count": 0, "bandit_high_or_critical_count": 1}
    assert predict_repository_readiness_baseline(features2) != "repository_ready"


def test_portfolio_baseline():
    f = {"portfolio_readiness_score": 90, "has_readme": True}
    assert predict_portfolio_readiness_baseline(f) == "portfolio_ready"
    f2 = {"portfolio_readiness_score": 65}
    assert predict_portfolio_readiness_baseline(f2) == "almost_ready"
    f3 = {"portfolio_readiness_score": 50}
    assert predict_portfolio_readiness_baseline(f3) == "not_portfolio_ready"


def test_predict_record_baseline_includes_version():
    rec = {"features": {"repository_health_score": 90, "pytest_failed_count": 0, "pytest_error_count": 0, "bandit_high_or_critical_count": 0, "portfolio_readiness_score": 90, "has_readme": True}}
    out = predict_record_baseline(rec)
    assert "baseline_version" in out
    assert "repository_readiness_baseline" in out and "portfolio_readiness_baseline" in out
