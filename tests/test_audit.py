from __future__ import annotations

from pathlib import Path

from drrepo.audit import build_audit
from drrepo.analyzers.models import ToolResult, ToolFinding


def test_build_audit_top_level_keys(monkeypatch, tmp_path: Path):
    # Monkeypatch analyzer services used inside drrepo.audit
    monkeypatch.setattr("drrepo.audit.run_static_analyzers", lambda p: [ToolResult(tool="ruff", status="completed")])
    monkeypatch.setattr("drrepo.audit.run_test_analyzers", lambda p: [ToolResult(tool="pytest", status="completed")])
    monkeypatch.setattr("drrepo.audit.run_repository_analyzers", lambda p: [ToolResult(tool="readme", status="completed")])

    result = build_audit(tmp_path)
    assert "status" in result
    assert "path" in result
    assert "metadata" in result
    assert "static_analysis" in result
    assert "test_analysis" in result
    assert "repository_analysis" in result
    assert "scoring" in result


def test_build_audit_passes_detected_root(monkeypatch, tmp_path: Path):
    project_root = tmp_path / "proj"
    project_root.mkdir()
    (project_root / "pyproject.toml").write_text("[tool.poetry]\nname = \"proj\"\n")
    nested = project_root / "tests"
    nested.mkdir()

    captured = {}

    def fake_static(p):
        captured["static_path"] = p
        return [ToolResult(tool="ruff", status="completed")]

    def fake_test(p):
        captured["test_path"] = p
        return [ToolResult(tool="pytest", status="completed")]

    def fake_repo(p):
        captured["repo_path"] = p
        return [ToolResult(tool="readme", status="completed")]

    monkeypatch.setattr("drrepo.audit.run_static_analyzers", fake_static)
    monkeypatch.setattr("drrepo.audit.run_test_analyzers", fake_test)
    monkeypatch.setattr("drrepo.audit.run_repository_analyzers", fake_repo)

    result = build_audit(nested)
    # services should receive the detected project_root
    assert str(captured.get("static_path")) == str(project_root)
    assert str(captured.get("test_path")) == str(project_root)
    assert str(captured.get("repo_path")) == str(project_root)


def test_build_audit_scoring(monkeypatch, tmp_path: Path):
    # static: no findings
    monkeypatch.setattr("drrepo.audit.run_static_analyzers", lambda p: [ToolResult(tool="ruff", status="completed")])
    # tests: one high severity finding
    test_tool = ToolResult(
        tool="pytest",
        status="completed",
        findings=[ToolFinding(tool="pytest", message="fail", severity="high", code="PYTEST-FAILED")],
    )
    monkeypatch.setattr("drrepo.audit.run_test_analyzers", lambda p: [test_tool])
    # repo: one low severity finding
    repo_tool = ToolResult(
        tool="readme",
        status="completed",
        findings=[ToolFinding(tool="readme", message="missing", severity="low", code="README-MISSING")],
    )
    monkeypatch.setattr("drrepo.audit.run_repository_analyzers", lambda p: [repo_tool])

    out = build_audit(tmp_path)
    sections = out["scoring"]["sections"]
    assert sections["static_analysis"]["score"] == 100
    assert sections["test_analysis"]["score"] == 85
    assert sections["repository_analysis"]["score"] == 97
    assert out["scoring"]["overall_score"] == 94


def test_build_audit_invalid_path_raises():
    import pytest

    with pytest.raises(FileNotFoundError):
        build_audit("no/such/path")
