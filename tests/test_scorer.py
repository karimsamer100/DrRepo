import json

from drrepo.scoring.scorer import severity_penalty, score_tool_results, score_audit_sections
from drrepo.analyzers.models import ToolResult, ToolFinding


def make_result(tool: str, status: str = "completed", findings=None):
    return ToolResult(tool=tool, status=status, findings=(findings or []))


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
    r1 = make_result("a", "failed_to_run")
    r2 = make_result("b", "partial")
    res = score_tool_results([r1, r2])
    # 10 + 5 = 15
    assert res["penalty"] == 15
    assert res["score"] == 85


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
    assert out["overall_score"] == expected_overall
    assert set(out["sections"].keys()) == {"static_analysis", "test_analysis", "repository_analysis"}
