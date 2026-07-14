import json

from drrepo.scoring.scorer import (
    cap_score_for_hard_flags,
    severity_penalty,
    score_tool_results,
    score_audit_sections,
)
from drrepo.analyzers.models import ToolResult, ToolFinding


def make_result(tool: str, status: str = "completed", findings=None, summary=None):
    return ToolResult(tool=tool, status=status, findings=(findings or []), summary=(summary or {}))


def test_severity_penalty():
    assert severity_penalty("high") == 15
    assert severity_penalty("medium") == 8
    assert severity_penalty("low") == 3
    assert severity_penalty("unknown") == 2
    assert severity_penalty(None) == 2
    assert severity_penalty("HIGH") == 15


def test_score_no_findings():
    res = score_tool_results([make_result("ruff", "completed")])
    assert res["score"] == 100
    assert res["finding_count"] == 0


def test_score_with_findings():
    findings = [ToolFinding(tool="x", message="m", severity="high"), ToolFinding(tool="x", message="m2", severity="low")]
    res = score_tool_results([make_result("bandit", "completed", findings=findings)])
    assert res["penalty"] == 18
    assert res["score"] == 82
    assert res["finding_count"] == 2


def test_score_status_penalties():
    r1 = make_result("readme", "failed_to_run")
    r2 = make_result("structure", "partial")
    res = score_tool_results([r1, r2])
    # 10 + 5 = 15
    assert res["penalty"] == 15
    assert res["score"] == 85


def test_optional_failed_analyzer_does_not_reduce_numeric_score_by_itself():
    res = score_tool_results([make_result("radon", "failed_to_run")])
    assert res["score"] == 100
    assert res["penalty"] == 0


def test_score_no_penalty_for_unavailable_or_not_applicable():
    r1 = make_result("a", "not_available")
    r2 = make_result("b", "not_applicable")
    res = score_tool_results([r1, r2])
    assert res["score"] == 100


def test_score_clamps_zero():
    findings = [ToolFinding(tool="x", message="m", severity="critical") for _ in range(10)]
    res = score_tool_results([make_result("x", "completed", findings=findings)])
    assert res["score"] == 0


def test_score_audit_sections():
    static = [make_result("ruff", "completed")]
    test = [make_result("pytest", "failed_to_run")]
    repo = [make_result("readme", "completed", findings=[ToolFinding(tool="r", message="m", severity="high")])]
    out = score_audit_sections(static, test, repo)
    assert "overall_score" in out
    assert "sections" in out
    # compute expected scores
    s_static = 100
    s_test = 90  # failed_to_run -> -10
    s_repo = 85  # high -> -15
    expected_overall = int(round((s_static + s_test + s_repo) / 3.0))
    assert out["overall_score"] == 79
    assert set(out["sections"].keys()) == {"static_analysis", "test_analysis", "repository_analysis"}
    assert expected_overall > out["overall_score"]


def test_cap_score_for_hard_flags_uses_stricter_caps():
    assert cap_score_for_hard_flags(96, ["README_INCOMPLETE"]) == 84
    assert cap_score_for_hard_flags(96, ["ANALYZER_ERRORS_PRESENT"]) == 79
    assert cap_score_for_hard_flags(96, ["TESTS_FAILING"]) == 79
    assert cap_score_for_hard_flags(96, ["README_INCOMPLETE", "TESTS_FAILING"]) == 79


def test_score_audit_sections_caps_high_scores_when_tests_fail():
    static = [make_result("ruff", "completed")]
    test = [
        make_result(
            "pytest",
            "completed",
            findings=[ToolFinding(tool="pytest", message="1 test failed", severity="high", code="PYTEST-FAILED")],
        )
    ]
    repo = [make_result("readme", "completed")]

    out = score_audit_sections(static, test, repo)

    assert out["sections"]["test_analysis"]["score"] == 85
    assert out["overall_score"] == 79
    assert out["repository_health_score"] == 79
    assert out["portfolio_readiness_score"] == 79


def test_readme_structure_flags_do_not_cap_repository_health_score():
    static = [make_result("ruff", "completed")]
    test = [make_result("pytest", "completed")]
    repo = [
        make_result("readme", "completed", findings=[ToolFinding(tool="readme", message="missing usage", severity="low", code="README-MISSING-USAGE")]),
        make_result("structure", "completed", findings=[ToolFinding(tool="structure", message="missing docs", severity="low", code="STRUCTURE-MISSING-DOCS")]),
    ]

    out = score_audit_sections(static, test, repo)

    assert out["repository_health_score"] > 84
    assert out["portfolio_readiness_score"] == 84


def test_no_tests_do_not_score_as_perfect_testing():
    static = [make_result("ruff", "completed")]
    test = [
        make_result("pytest", "not_applicable", summary={"outcome": "no_tests"}),
        make_result("coverage", "not_available"),
    ]
    repo = [make_result("readme", "completed")]

    out = score_audit_sections(static, test, repo)

    assert out["categories"]["testing"] == 70
    assert out["portfolio_readiness_score"] < 100


def test_passed_tests_can_score_testing_as_perfect():
    out = score_audit_sections(
        [make_result("ruff", "completed")],
        [make_result("pytest", "completed", summary={"outcome": "passed"}), make_result("coverage", "completed")],
        [make_result("readme", "completed")],
    )

    assert out["categories"]["testing"] == 100


def test_remote_skipped_tests_do_not_score_as_passed():
    out = score_audit_sections(
        [make_result("ruff", "completed")],
        [
            make_result("pytest", "skipped_by_config", summary={"outcome": "skipped_for_remote_safety"}),
            make_result("coverage", "skipped_by_config", summary={"outcome": "skipped_for_remote_safety"}),
        ],
        [make_result("readme", "completed")],
    )

    assert out["categories"]["testing"] == 70
