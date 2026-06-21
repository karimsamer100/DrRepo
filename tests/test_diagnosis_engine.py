from drrepo.diagnosis.engine import build_diagnosis


def _make_audit_with_score(score):
    return {"scoring": {"overall_score": score}}


def test_label_healthy():
    d = build_diagnosis(_make_audit_with_score(90))
    assert d["repository_health"]["label"] == "healthy"


def test_label_needs_attention():
    d = build_diagnosis(_make_audit_with_score(75))
    assert d["repository_health"]["label"] == "needs_attention"


def test_label_needs_improvement():
    d = build_diagnosis(_make_audit_with_score(60))
    assert d["repository_health"]["label"] == "needs_improvement"


def test_label_needs_major_improvement():
    d = build_diagnosis(_make_audit_with_score(10))
    assert d["repository_health"]["label"] == "needs_major_improvement"


def test_missing_score_defaults_to_needs_attention():
    d = build_diagnosis({})
    assert d["repository_health"]["label"] == "needs_attention"


def test_tests_failing_flag():
    audit = {"test_analysis": [{"tool": "pytest", "status": "completed", "findings": [{"code": "PYTEST-FAILED"}]}]}
    d = build_diagnosis(audit)
    assert "TESTS_FAILING" in d["hard_flags"]


def test_security_flag_from_bandit():
    audit = {"static_analysis": [{"tool": "bandit", "status": "completed", "findings": [{"severity": "medium"}]}]}
    d = build_diagnosis(audit)
    assert "SECURITY_FINDINGS_PRESENT" in d["hard_flags"]


def test_readme_incomplete_flag():
    audit = {"repository_analysis": [{"tool": "readme", "status": "completed", "findings": [{"code": "README-MISSING"}]}]}
    d = build_diagnosis(audit)
    assert "README_INCOMPLETE" in d["hard_flags"]


def test_structure_incomplete_flag():
    audit = {"repository_analysis": [{"tool": "structure", "status": "completed", "findings": [{"code": "STRUCTURE-MISSING-TESTS"}]}]}
    d = build_diagnosis(audit)
    assert "STRUCTURE_INCOMPLETE" in d["hard_flags"]


def test_analyzer_errors_flag_and_not_available_limitation():
    audit = {"static_analysis": [{"tool": "ruff", "status": "failed_to_run", "errors": ["boom"]}, {"tool": "bandit", "status": "not_available"}]}
    d = build_diagnosis(audit)
    assert "ANALYZER_ERRORS_PRESENT" in d["hard_flags"]
    assert "Some optional analysis tools were not available." in d["limitations"]


def test_deduplication_order():
    audit = {"static_analysis": [{"tool": "bandit", "status": "completed", "findings": [{"severity": "medium"}]}, {"tool": "bandit", "status": "completed", "findings": [{"severity": "medium"}]}], "test_analysis": [{"tool": "pytest", "status": "completed", "findings": [{"code": "PYTEST-FAILED"}]}]}
    d = build_diagnosis(audit)
    # order should be first seen: SECURITY_FINDINGS_PRESENT then TESTS_FAILING
    assert d["hard_flags"][0] == "SECURITY_FINDINGS_PRESENT"
    assert "TESTS_FAILING" in d["hard_flags"]
    # limitations dedup
    audit2 = {"static_analysis": [{"tool": "ruff", "status": "not_available"}, {"tool": "bandit", "status": "not_available"}]}
    d2 = build_diagnosis(audit2)
    assert d2["limitations"][0] == "Some optional analysis tools were not available."
