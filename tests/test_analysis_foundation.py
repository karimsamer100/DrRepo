from pathlib import Path

import pytest

from drrepo.analyzers.models import ToolResult
from drrepo.analyzers.registry import (
    capability_payload,
    default_analysis_mode,
    validate_analysis_mode,
)
from drrepo.analyzers.test_service import run_test_analyzers
from drrepo.environment import detect_dependency_environment


def test_analysis_mode_defaults_are_source_specific():
    assert default_analysis_mode("local_path") == "deep_local"
    assert default_analysis_mode("github_url") == "quick_safe"


def test_deep_local_is_rejected_for_github_url():
    with pytest.raises(ValueError, match="deep_local"):
        validate_analysis_mode("github_url", "deep_local")


def test_capability_payload_includes_registry_and_safety_policy():
    payload = capability_payload()
    analyzers = {entry["analyzer_id"]: entry for entry in payload["analyzers"]}

    assert {"readme", "structure", "ruff", "bandit", "radon", "pytest", "coverage"} <= set(analyzers)
    assert analyzers["pytest"]["executes_repository_code"] is True
    assert analyzers["ruff"]["executes_repository_code"] is False
    assert payload["docker_isolated_execution"]["supported"] is False
    assert "Remote GitHub audits never execute" in payload["remote_execution_safety_policy"]
    assert ".[analysis]" in payload["setup"]["install_command"]


def test_quick_safe_never_runs_pytest_or_coverage(monkeypatch, tmp_path: Path):
    called = {"pytest": False, "coverage": False}

    def fake_pytest(path):
        called["pytest"] = True
        return ToolResult(tool="pytest", status="completed")

    def fake_coverage(path):
        called["coverage"] = True
        return ToolResult(tool="coverage", status="completed")

    monkeypatch.setattr("drrepo.analyzers.test_service.run_pytest", fake_pytest)
    monkeypatch.setattr("drrepo.analyzers.test_service.run_coverage", fake_coverage)

    results = run_test_analyzers(tmp_path, source_type="local_path", analysis_mode="quick_safe")

    assert called == {"pytest": False, "coverage": False}
    assert {result.tool: result.status for result in results} == {
        "pytest": "skipped_by_config",
        "coverage": "skipped_by_config",
    }
    assert all(result.execution_mode == "quick_safe" for result in results)


def test_deep_local_runs_pytest_and_coverage(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        "drrepo.analyzers.test_service.run_pytest",
        lambda path: ToolResult(tool="pytest", status="completed", summary={"outcome": "passed"}),
    )
    monkeypatch.setattr(
        "drrepo.analyzers.test_service.run_coverage",
        lambda path: ToolResult(tool="coverage", status="completed", summary={"coverage_percent": 91}),
    )

    results = run_test_analyzers(tmp_path, source_type="local_path", analysis_mode="deep_local")

    assert {result.tool: result.status for result in results} == {
        "pytest": "completed",
        "coverage": "completed",
    }
    assert all(result.duration_ms is not None for result in results)
    assert all(result.execution_mode == "deep_local" for result in results)


def test_github_url_tests_are_skipped_for_remote_safety(tmp_path: Path):
    results = run_test_analyzers(tmp_path, source_type="github_url", analysis_mode="quick_safe")

    assert {result.tool: result.status for result in results} == {
        "pytest": "skipped_by_config",
        "coverage": "skipped_by_config",
    }
    assert all("remote GitHub audit safety" in (result.skipped_reason or "") for result in results)


def test_dependency_environment_detection_prefers_locked_strategy(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")

    detected = detect_dependency_environment(tmp_path)

    assert detected["detected_dependency_strategy"] == "uv"
    assert detected["dependency_metadata_exists"] is True
    assert detected["lock_file_exists"] is True
    assert detected["likely_install_command"] == "uv sync"
