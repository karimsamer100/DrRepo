from pathlib import Path

from drrepo.audit import build_audit
from drrepo.analyzers.models import ToolResult, ToolFinding


def make_finding(tool: str, code: str = "X", severity: str = "high", message: str = "m"):
    return ToolFinding(tool=tool, message=message, severity=severity, code=code)


def _scoring_for(monkeypatch, tmp_path: Path, static=None, tests=None, repo=None):
    monkeypatch.setattr(
        "drrepo.audit.run_static_analyzers", lambda p: static or []
    )
    monkeypatch.setattr(
        "drrepo.audit.run_test_analyzers", lambda p: tests or []
    )
    monkeypatch.setattr(
        "drrepo.audit.run_repository_analyzers", lambda p: repo or []
    )
    out = build_audit(tmp_path)
    return out.get("scoring", {})


def test_categories_and_top_level_scores_present(monkeypatch, tmp_path: Path):
    scoring = _scoring_for(
        monkeypatch,
        tmp_path,
        static=[ToolResult(tool="ruff", status="not_available")],
        tests=[ToolResult(tool="pytest", status="not_available")],
        repo=[ToolResult(tool="readme", status="not_available")],
    )
    cats = scoring.get("categories")
    assert isinstance(cats, dict)
    for cat in ("code_quality", "testing", "security", "maintainability", "documentation", "structure"):
        assert cat in cats

    assert isinstance(scoring.get("repository_health_score"), int)
    assert isinstance(scoring.get("portfolio_readiness_score"), int)


def test_scores_clamped_between_0_and_100(monkeypatch, tmp_path: Path):
    # create many critical findings for bandit to force negative before clamp
    findings = [make_finding("bandit", severity="critical") for _ in range(20)]
    bandit = ToolResult(tool="bandit", status="completed", findings=findings)
    scoring = _scoring_for(monkeypatch, tmp_path, static=[bandit])
    cats = scoring.get("categories", {})
    assert 0 <= cats.get("security", 0) <= 100


def test_ruff_finding_reduces_code_quality(monkeypatch, tmp_path: Path):
    ruff = ToolResult(tool="ruff", status="completed", findings=[make_finding("ruff", severity="low")])
    scoring = _scoring_for(monkeypatch, tmp_path, static=[ruff])
    cats = scoring.get("categories", {})
    assert cats["code_quality"] < 100


def test_bandit_severity_affects_security(monkeypatch, tmp_path: Path):
    low = ToolResult(tool="bandit", status="completed", findings=[make_finding("bandit", severity="low")])
    high = ToolResult(tool="bandit", status="completed", findings=[make_finding("bandit", severity="high")])
    critical = ToolResult(tool="bandit", status="completed", findings=[make_finding("bandit", severity="critical")])

    s_low = _scoring_for(monkeypatch, tmp_path, static=[low]).get("categories", {}).get("security")
    s_high = _scoring_for(monkeypatch, tmp_path, static=[high]).get("categories", {}).get("security")
    s_crit = _scoring_for(monkeypatch, tmp_path, static=[critical]).get("categories", {}).get("security")

    assert s_low > s_high
    assert s_high > s_crit


def test_radon_reduces_maintainability(monkeypatch, tmp_path: Path):
    radon = ToolResult(tool="radon", status="completed", findings=[make_finding("radon", severity="medium")])
    scoring = _scoring_for(monkeypatch, tmp_path, static=[radon])
    assert scoring.get("categories", {}).get("maintainability") < 100


def test_pytest_findings_reduce_testing(monkeypatch, tmp_path: Path):
    p = ToolResult(tool="pytest", status="completed", findings=[make_finding("pytest", severity="high")])
    scoring = _scoring_for(monkeypatch, tmp_path, tests=[p])
    assert scoring.get("categories", {}).get("testing") < 100


def test_coverage_partial_and_failed_reduce_testing(monkeypatch, tmp_path: Path):
    c_partial = ToolResult(tool="coverage", status="partial")
    scoring_partial = _scoring_for(monkeypatch, tmp_path, tests=[c_partial])
    assert scoring_partial.get("categories", {}).get("testing") < 100

    c_failed = ToolResult(tool="coverage", status="failed_to_run")
    scoring_failed = _scoring_for(monkeypatch, tmp_path, tests=[c_failed])
    # failed_to_run should reduce by 10 -> expect 90
    assert scoring_failed.get("categories", {}).get("testing") <= 90


def test_readme_finding_reduces_documentation(monkeypatch, tmp_path: Path):
    r = ToolResult(tool="readme", status="completed", findings=[make_finding("readme", severity="low")])
    scoring = _scoring_for(monkeypatch, tmp_path, repo=[r])
    assert scoring.get("categories", {}).get("documentation") < 100


def test_structure_finding_reduces_structure(monkeypatch, tmp_path: Path):
    s = ToolResult(tool="structure", status="completed", findings=[make_finding("structure", severity="medium")])
    scoring = _scoring_for(monkeypatch, tmp_path, repo=[s])
    assert scoring.get("categories", {}).get("structure") < 100


def test_category_reasons_include_expected_fields(monkeypatch, tmp_path: Path):
    f = make_finding("ruff", code="R001", severity="medium", message="m")
    ruff = ToolResult(tool="ruff", status="completed", findings=[f])
    scoring = _scoring_for(monkeypatch, tmp_path, static=[ruff])
    reasons = scoring.get("category_reasons", {}).get("code_quality", [])
    assert isinstance(reasons, list) and reasons
    r = reasons[0]
    for k in ("tool", "code", "severity", "message"):
        assert k in r


def test_not_available_does_not_reduce(monkeypatch, tmp_path: Path):
    ruff = ToolResult(tool="ruff", status="not_available")
    scoring = _scoring_for(monkeypatch, tmp_path, static=[ruff])
    assert scoring.get("categories", {}).get("code_quality") == 100


def test_failed_to_run_and_partial_status_penalties(monkeypatch, tmp_path: Path):
    r_failed = ToolResult(tool="ruff", status="failed_to_run")
    scoring_failed = _scoring_for(monkeypatch, tmp_path, static=[r_failed])
    assert scoring_failed.get("categories", {}).get("code_quality") == 90

    r_partial = ToolResult(tool="ruff", status="partial")
    scoring_partial = _scoring_for(monkeypatch, tmp_path, static=[r_partial])
    assert scoring_partial.get("categories", {}).get("code_quality") == 95
