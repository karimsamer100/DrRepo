from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from drrepo.cli import app
from drrepo.analyzers.models import ToolResult, ToolFinding
import drrepo.cli as cli_module


runner = CliRunner()


def test_help_shows_audit():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "audit" in result.output


def test_audit_help_shows_format_option():
    result = runner.invoke(app, ["audit", "--help"])
    assert result.exit_code == 0
    assert "--format" in result.output


def test_audit_placeholder_ok(tmp_path: Path):
    result = runner.invoke(app, ["audit", str(tmp_path)])
    assert result.exit_code == 0
    # parse-ish check for presence of metadata
    assert '"status": "ok"' in result.output
    assert '"metadata"' in result.output
    assert '"total_files"' in result.output
    assert '"python_files"' in result.output


def test_explicit_json_format(tmp_path: Path):
    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "json"])
    assert result.exit_code == 0
    import json as _json

    out = _json.loads(result.output)
    assert out.get("status") == "ok"


def test_markdown_format_outputs_markdown(tmp_path: Path):
    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "markdown"])
    assert result.exit_code == 0
    out = result.output
    assert "# DrRepo Audit Report" in out
    assert "## Repository" in out
    assert "## Score Summary" in out
    assert "## Analyzer Summary" in out
    # Ensure output is not JSON
    assert "{\n  \"status\"" not in out


def test_invalid_format_fails(tmp_path: Path):
    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "xml"])
    assert result.exit_code != 0
    assert "Invalid format" in result.output or "must be 'json' or 'markdown'" in result.output


def test_output_file_json(tmp_path: Path):
    out_dir = tmp_path / "reports"
    out_file = out_dir / "audit.json"
    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "json", "--output", str(out_file)])
    assert result.exit_code == 0
    assert "Wrote audit report to" in result.output
    assert out_file.exists()
    import json as _json

    content = _json.loads(out_file.read_text(encoding="utf-8"))
    assert content.get("status") == "ok"
    # stdout should not contain the full JSON
    assert "{\n  \"status\"" not in result.output


def test_output_file_markdown_and_parent_created(tmp_path: Path):
    nested = tmp_path / "a" / "b"
    out_file = nested / "audit.md"
    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "markdown", "--output", str(out_file)])
    assert result.exit_code == 0
    assert "Wrote audit report to" in result.output
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "# DrRepo Audit Report" in content
    # stdout should not contain the report itself
    assert "# DrRepo Audit Report" not in result.output


def test_audit_missing_path():
    result = runner.invoke(app, ["audit", "no/such/path"]) 
    assert result.exit_code != 0


def test_audit_includes_static_analysis(monkeypatch, tmp_path: Path):
    # Prepare fake analyzer results (all completed)
    fake = [ToolResult(tool="ruff", status="completed"), ToolResult(tool="bandit", status="completed"), ToolResult(tool="radon", status="completed")]
    monkeypatch.setattr("drrepo.audit.run_static_analyzers", lambda p: fake)

    # Prepare fake test analyzer results: pytest has a high-severity finding
    fake_tests = [
        ToolResult(
            tool="pytest",
            status="completed",
            findings=[ToolFinding(tool="pytest", message="1 test failed", severity="high", code="PYTEST-FAILED")],
        ),
        ToolResult(tool="coverage", status="not_available", errors=["missing"]),
    ]
    monkeypatch.setattr("drrepo.audit.run_test_analyzers", lambda p: fake_tests)

    # Prepare fake repository analyzer results: readme has a low-severity finding
    fake_repo = [
        ToolResult(
            tool="readme",
            status="completed",
            findings=[ToolFinding(tool="readme", message="README is missing license information", severity="low", code="README-MISSING-LICENSE")],
        ),
        ToolResult(tool="structure", status="completed"),
    ]
    monkeypatch.setattr("drrepo.audit.run_repository_analyzers", lambda p: fake_repo)

    result = runner.invoke(app, ["audit", str(tmp_path)])
    assert result.exit_code == 0
    import json as _json

    out = _json.loads(result.output)
    assert out["status"] == "ok"
    assert "metadata" in out
    assert "static_analysis" in out
    assert [t["tool"] for t in out["static_analysis"]] == ["ruff", "bandit", "radon"]
    assert "test_analysis" in out
    assert [t["tool"] for t in out["test_analysis"]] == ["pytest", "coverage"]
    assert "repository_analysis" in out
    assert [t["tool"] for t in out["repository_analysis"]] == ["readme", "structure"]
    assert "scoring" in out
    # Expected scores: static 100, test 85 (high finding -> -15), repo 97 (low finding -> -3)
    assert out["scoring"]["overall_score"] == 94
    assert out["scoring"]["sections"]["static_analysis"]["score"] == 100
    assert out["scoring"]["sections"]["test_analysis"]["score"] == 85
    assert out["scoring"]["sections"]["repository_analysis"]["score"] == 97


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

    monkeypatch.setattr("drrepo.audit.run_static_analyzers", recorder)
    monkeypatch.setattr("drrepo.audit.run_test_analyzers", recorder_tests)
    def recorder_repo(path):
        captured["repo_path"] = path
        return [ToolResult(tool="readme", status="completed"), ToolResult(tool="structure", status="completed")]
    monkeypatch.setattr("drrepo.audit.run_repository_analyzers", recorder_repo)

    result = runner.invoke(app, ["audit", str(nested)])
    assert result.exit_code == 0
    # The service should be called with the detected repository root
    assert str(captured.get("path")) == str(project_root)
    assert str(captured.get("test_path")) == str(project_root)
    assert str(captured.get("repo_path")) == str(project_root)
