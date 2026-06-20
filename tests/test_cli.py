from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from drrepo.cli import app
from drrepo.analyzers.models import ToolResult
import drrepo.cli as cli_module


runner = CliRunner()


def test_help_shows_audit():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "audit" in result.output


def test_audit_placeholder_ok(tmp_path: Path):
    result = runner.invoke(app, ["audit", str(tmp_path)])
    assert result.exit_code == 0
    # parse-ish check for presence of metadata
    assert '"status": "ok"' in result.output
    assert '"metadata"' in result.output
    assert '"total_files"' in result.output
    assert '"python_files"' in result.output


def test_audit_missing_path():
    result = runner.invoke(app, ["audit", "no/such/path"]) 
    assert result.exit_code != 0


def test_audit_includes_static_analysis(monkeypatch, tmp_path: Path):
    # Prepare fake analyzer results
    fake = [ToolResult(tool="ruff", status="completed"), ToolResult(tool="bandit", status="not_available", errors=["missing"]), ToolResult(tool="radon", status="completed")]

    def fake_run(path):
        return fake

    monkeypatch.setattr(cli_module, "run_static_analyzers", lambda p: fake)
    # Prepare fake test analyzer results
    fake_tests = [ToolResult(tool="pytest", status="completed", summary={"passed": 3}), ToolResult(tool="coverage", status="completed", summary={"coverage_percent": 80.0})]
    monkeypatch.setattr(cli_module, "run_test_analyzers", lambda p: fake_tests)

    result = runner.invoke(app, ["audit", str(tmp_path)])
    assert result.exit_code == 0
    out = result.output
    assert '"status": "ok"' in out
    assert '"metadata"' in out
    assert '"static_analysis"' in out
    # Ensure ordering of tools
    assert "ruff" in out
    assert "bandit" in out
    assert "radon" in out
    assert '"test_analysis"' in out
    assert "pytest" in out


def test_cli_passes_detected_root_to_analyzers(monkeypatch, tmp_path: Path):
    # Create project root with marker
    project_root = tmp_path / "proj"
    project_root.mkdir()
    (project_root / "pyproject.toml").write_text("[tool.poetry]\nname = \"proj\"\n")
    nested = project_root / "tests"
    nested.mkdir()

    captured = {}

    def recorder(path):
        captured["path"] = path
        return [ToolResult(tool="ruff", status="completed"), ToolResult(tool="bandit", status="completed"), ToolResult(tool="radon", status="completed")]

    def recorder_tests(path):
        captured["test_path"] = path
        return [ToolResult(tool="pytest", status="completed"), ToolResult(tool="coverage", status="completed", summary={"coverage_percent": 80.0})]

    monkeypatch.setattr(cli_module, "run_static_analyzers", recorder)
    monkeypatch.setattr(cli_module, "run_test_analyzers", recorder_tests)

    result = runner.invoke(app, ["audit", str(nested)])
    assert result.exit_code == 0
    # The service should be called with the detected repository root
    assert str(captured.get("path")) == str(project_root)
    assert str(captured.get("test_path")) == str(project_root)
