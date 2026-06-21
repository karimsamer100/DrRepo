from drrepo.remediation.suggestions import generate_suggestions, count_suggestions_by_severity


def test_not_available_creates_install_suggestion():
    audit = {
        "static_analysis": [
            {"tool": "ruff", "status": "not_available", "findings": [], "errors": []}
        ]
    }
    suggs = generate_suggestions(audit)
    assert any("Install optional tool" in s["title"] for s in suggs)
    assert any(s.get("code") == "TOOL-NOT-AVAILABLE" for s in suggs)


def test_pytest_failed_finding_creates_fix_tests():
    audit = {
        "test_analysis": [
            {
                "tool": "pytest",
                "status": "completed",
                "findings": [{"code": "PYTEST-FAILED", "severity": "high", "message": "1 failed"}],
                "errors": [],
            }
        ]
    }
    suggs = generate_suggestions(audit)
    s = [x for x in suggs if x.get("title") == "Fix failing tests"]
    assert len(s) == 1
    assert s[0]["severity"] == "high"


def test_readme_missing_creates_improve_readme():
    audit = {"repository_analysis": [{"tool": "readme", "status": "completed", "findings": [{"code": "README-MISSING-LICENSE", "message": "missing"}], "errors": []}]}
    suggs = generate_suggestions(audit)
    s = [x for x in suggs if x.get("title") == "Improve README documentation"]
    assert len(s) == 1


def test_structure_missing_tests_creates_add_tests():
    audit = {"repository_analysis": [{"tool": "structure", "status": "completed", "findings": [{"code": "STRUCTURE-MISSING-TESTS"}], "errors": []}]}
    suggs = generate_suggestions(audit)
    s = [x for x in suggs if x.get("title") == "Add tests"]
    assert len(s) == 1


def test_bandit_finding_creates_security_suggestion():
    audit = {"static_analysis": [{"tool": "bandit", "status": "completed", "findings": [{"code": "B101", "severity": "medium"}], "errors": []}]}
    suggs = generate_suggestions(audit)
    s = [x for x in suggs if x.get("title") == "Review security finding"]
    assert len(s) == 1


def test_analyzer_error_creates_investigate():
    audit = {"static_analysis": [{"tool": "ruff", "status": "failed_to_run", "findings": [], "errors": ["boom"]}]}
    suggs = generate_suggestions(audit)
    s = [x for x in suggs if x.get("title") == "Investigate analyzer error"]
    assert len(s) == 1


def test_deduplication_of_duplicate_findings():
    finding = {"code": "STRUCTURE-MISSING-TESTS"}
    audit = {"repository_analysis": [{"tool": "structure", "status": "completed", "findings": [finding, finding], "errors": []}]}
    suggs = generate_suggestions(audit)
    s = [x for x in suggs if x.get("title") == "Add tests"]
    assert len(s) == 1


def test_missing_keys_do_not_crash():
    assert generate_suggestions({}) == []


def test_count_suggestions_by_severity():
    suggs = [
        {"severity": "high"},
        {"severity": "low"},
        {},
    ]
    counts = count_suggestions_by_severity(suggs)
    assert counts.get("high") == 1
    assert counts.get("low") == 1
    assert counts.get("unknown") == 1
