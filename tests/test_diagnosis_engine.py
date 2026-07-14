from drrepo.diagnosis.engine import build_diagnosis


def _make_audit_with_score(score):
    return {
        "scoring": {"overall_score": score},
        "static_analysis": [
            {"tool": "ruff", "status": "completed"},
            {"tool": "bandit", "status": "completed"},
            {"tool": "radon", "status": "completed"},
        ],
        "test_analysis": [
            {"tool": "pytest", "status": "completed"},
            {"tool": "coverage", "status": "completed"},
        ],
    }


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
    assert d["evidence_confidence"]["label"] == "limited"


def test_tests_failing_flag():
    audit = {"test_analysis": [{"tool": "pytest", "status": "completed", "findings": [{"code": "PYTEST-FAILED"}]}]}
    d = build_diagnosis(audit)
    assert "TESTS_FAILING" in d["hard_flags"]


def test_pytest_error_sets_distinct_flag():
    audit = {
        "test_analysis": [
            {"tool": "pytest", "status": "completed", "findings": [{"code": "PYTEST-ERROR"}]}
        ]
    }
    d = build_diagnosis(audit)
    assert "TESTS_COULD_NOT_RUN" in d["hard_flags"]


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


def test_optional_analyzer_errors_are_limitations_not_hard_flags():
    audit = {"static_analysis": [{"tool": "radon", "status": "failed_to_run", "errors": ["boom"]}, {"tool": "bandit", "status": "not_available"}]}
    d = build_diagnosis(audit)
    assert "ANALYZER_ERRORS_PRESENT" not in d["hard_flags"]
    assert "Optional analyzer radon could not complete; evidence confidence is reduced." in d["limitations"]
    assert "Some optional analysis tools were not available." in d["limitations"]


def test_core_analyzer_error_can_be_hard_flag():
    audit = {"repository_analysis": [{"tool": "readme", "status": "failed_to_run", "errors": ["boom"]}]}
    d = build_diagnosis(audit)
    assert "ANALYZER_ERRORS_PRESENT" in d["hard_flags"]


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


def test_hard_flags_reduce_healthy_label_even_when_score_is_high():
    audit = {
        "scoring": {"overall_score": 96},
        "test_analysis": [
            {"tool": "pytest", "status": "completed", "findings": [{"code": "PYTEST-FAILED"}]}
        ],
    }
    d = build_diagnosis(audit)
    assert d["repository_health"]["score"] == 79
    assert d["repository_health"]["label"] == "needs_attention"


def test_readme_and_structure_flags_cap_high_scores_to_needs_attention():
    audit = {
        "scoring": {"overall_score": 97},
        "repository_analysis": [
            {"tool": "readme", "status": "completed", "findings": [{"code": "README-MISSING-USAGE"}]},
            {"tool": "structure", "status": "completed", "findings": [{"code": "STRUCTURE-MISSING-TESTS"}]},
        ],
    }
    d = build_diagnosis(audit)
    assert d["repository_health"]["score"] == 84
    assert d["repository_health"]["label"] == "needs_attention"


def test_evidence_confidence_is_partial_when_optional_tools_are_missing():
    audit = {
        "static_analysis": [
            {"tool": "ruff", "status": "completed"},
            {"tool": "bandit", "status": "not_available"},
            {"tool": "radon", "status": "not_available"},
        ],
        "test_analysis": [
            {"tool": "pytest", "status": "completed"},
            {"tool": "coverage", "status": "not_available"},
        ],
    }
    d = build_diagnosis(audit)
    confidence = d["evidence_confidence"]
    assert confidence["label"] == "limited"
    assert confidence["missing_optional_tools"] == ["bandit", "radon", "coverage"]
    assert "Limited evidence" in confidence["summary"]


def test_evidence_confidence_is_limited_when_all_optional_tools_are_unavailable():
    audit = {
        "scoring": {"overall_score": 96},
        "static_analysis": [
            {"tool": "ruff", "status": "not_available"},
            {"tool": "bandit", "status": "not_available"},
            {"tool": "radon", "status": "not_available"},
        ],
        "test_analysis": [
            {"tool": "pytest", "status": "not_available"},
            {"tool": "coverage", "status": "not_available"},
        ],
    }
    d = build_diagnosis(audit)
    confidence = d["evidence_confidence"]
    assert confidence["label"] == "limited"
    assert d["repository_health"]["score"] == 96
    assert d["repository_health"]["label"] == "healthy"
    assert confidence["available_optional_tools"] == []
    assert confidence["missing_optional_tools"] == ["ruff", "bandit", "radon", "coverage", "pytest"]


def test_optional_failed_tool_reduces_confidence():
    audit = {
        "static_analysis": [
            {"tool": "ruff", "status": "completed"},
            {"tool": "bandit", "status": "completed"},
            {"tool": "radon", "status": "failed_to_run"},
        ],
        "test_analysis": [
            {"tool": "pytest", "status": "completed"},
            {"tool": "coverage", "status": "completed"},
        ],
    }
    d = build_diagnosis(audit)
    assert d["evidence_confidence"]["label"] == "partial"
    assert d["evidence_confidence"]["failed_optional_tools"] == ["radon"]
    assert "ANALYZER_ERRORS_PRESENT" not in d["hard_flags"]


def test_limited_evidence_does_not_downgrade_clean_healthy_verdict():
    audit = {
        "scoring": {"overall_score": 100},
        "static_analysis": [
            {"tool": "ruff", "status": "not_available"},
            {"tool": "bandit", "status": "not_available"},
            {"tool": "radon", "status": "not_available"},
        ],
        "test_analysis": [
            {"tool": "pytest", "status": "not_available"},
            {"tool": "coverage", "status": "not_available"},
        ],
    }
    d = build_diagnosis(audit)
    assert d["repository_health"]["score"] == 100
    assert d["repository_health"]["label"] == "healthy"
    assert d["evidence_confidence"]["label"] == "limited"


def test_skipped_remote_tests_reduce_confidence_without_hard_failure():
    audit = {
        "scoring": {"overall_score": 94},
        "static_analysis": [
            {"tool": "ruff", "status": "completed"},
            {"tool": "bandit", "status": "completed"},
            {"tool": "radon", "status": "completed"},
        ],
        "test_analysis": [
            {
                "tool": "pytest",
                "status": "skipped_by_config",
                "summary": {"reason": "Skipped for remote GitHub audit safety."},
            },
            {
                "tool": "coverage",
                "status": "skipped_by_config",
                "summary": {"reason": "Skipped for remote GitHub audit safety."},
            },
        ],
    }
    d = build_diagnosis(audit)
    assert "TESTS_FAILING" not in d["hard_flags"]
    assert "TESTS_COULD_NOT_RUN" not in d["hard_flags"]
    assert d["evidence_confidence"]["label"] == "partial"
    assert d["evidence_confidence"]["skipped_optional_tools"] == ["coverage", "pytest"]
    assert "Skipped for remote GitHub audit safety." in d["limitations"]


def test_pytest_failure_limitations_are_concise():
    audit = {
        "test_analysis": [
            {
                "tool": "pytest",
                "status": "failed_to_run",
                "errors": ["Pytest could not run: ModuleNotFoundError: No module named 'app'"],
            }
        ]
    }
    d = build_diagnosis(audit)
    assert "Pytest could not run: ModuleNotFoundError: No module named 'app'" in d["limitations"]
