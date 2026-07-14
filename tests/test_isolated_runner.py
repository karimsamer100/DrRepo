from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from drrepo.analyzers.models import ToolResult
from drrepo.analyzers.test_service import run_test_analyzers
from drrepo.execution.command_plan import allowed_install_command, build_runner_plan
from drrepo.execution.docker_runner import (
    DEFAULT_RUNNER_IMAGE,
    DockerCapability,
    _docker_run_command,
    check_docker_capability,
    run_isolated_checks,
)
from drrepo.execution.models import (
    CommandExecutionResult,
    IsolatedExecutionOptions,
    IsolatedExecutionRequest,
    IsolatedExecutionResult,
    options_from_dict,
)
from drrepo.execution.result_parser import isolated_result_to_tool_results
from drrepo.execution.sanitizer import sanitize_output


def test_docker_capability_available(monkeypatch):
    def fake_run(cmd, **kwargs):
        if cmd[:2] == ["docker", "version"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="27.0.1\n", stderr="")
        if cmd[:3] == ["docker", "image", "inspect"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="sha256:abc\n", stderr="")
        raise AssertionError(cmd)

    monkeypatch.setattr("drrepo.execution.docker_runner.subprocess.run", fake_run)

    capability = check_docker_capability()

    assert capability.deep_isolated_supported is True
    assert capability.docker_version == "27.0.1"
    assert capability.runner_image_available is True


def test_docker_capability_engine_unreachable(monkeypatch):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="Cannot connect to Docker daemon")

    monkeypatch.setattr("drrepo.execution.docker_runner.subprocess.run", fake_run)

    capability = check_docker_capability()

    assert capability.docker_cli_available is True
    assert capability.engine_reachable is False
    assert capability.deep_isolated_supported is False
    assert "Docker daemon" in (capability.unavailable_reason or "")


def test_docker_run_command_uses_security_flags_and_no_socket(tmp_path: Path):
    cmd = _docker_run_command(
        image=DEFAULT_RUNNER_IMAGE,
        container_name="drrepo-test",
        repo_path=tmp_path / "repo",
        results_path=tmp_path / "results",
        plan_path=tmp_path / "plan.json",
        network=False,
        timeout_seconds=120,
    )
    joined = " ".join(cmd)

    assert "--cap-drop" in cmd
    assert "ALL" in cmd
    assert "no-new-privileges" in joined
    assert "--network" in cmd
    assert "none" in cmd
    assert "--pids-limit" in cmd
    assert "--memory" in cmd
    assert "--cpus" in cmd
    assert "/var/run/docker.sock" not in joined
    assert "--privileged" not in cmd


def test_isolated_options_validate_network_and_bounds():
    with pytest.raises(ValueError, match="allow_install_network"):
        options_from_dict({"allow_install_network": True})
    with pytest.raises(ValueError, match="Unsupported isolated Python"):
        options_from_dict({"python_version": "3.10"})
    with pytest.raises(ValueError, match="between"):
        options_from_dict({"total_timeout_seconds": 5})

    options = options_from_dict({"install_dependencies": True, "allow_install_network": True, "python_version": "3.11"})
    assert options == IsolatedExecutionOptions(install_dependencies=True, allow_install_network=True, python_version="3.11")


def test_command_plan_allows_only_supported_install_strategies(tmp_path: Path):
    assert allowed_install_command(tmp_path) is None
    (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")
    assert allowed_install_command(tmp_path) == ["-m", "pip", "install", "-r", "requirements.txt"]

    plan = build_runner_plan(
        repository_path=tmp_path,
        requested_checks=("syntax", "pytest", "coverage"),
        install_dependencies=True,
        allow_install_network=False,
        per_command_timeout_seconds=60,
    )

    assert [item["id"] for item in plan["commands"][:2]] == ["setup_venv", "setup"]
    assert plan["commands"][0]["network"] is False
    assert plan["commands"][1]["network"] is False
    assert [item["id"] for item in plan["commands"]][-2:] == ["coverage", "coverage_json"]


def test_result_parser_maps_pytest_passed_and_coverage_completed():
    isolated = IsolatedExecutionResult(
        status="completed",
        image=DEFAULT_RUNNER_IMAGE,
        docker_version="27",
        commands=[
            CommandExecutionResult("pytest", 0, "completed", 10, stdout="2 passed in 0.01s"),
            CommandExecutionResult("coverage", 0, "completed", 10),
            CommandExecutionResult("coverage_json", 0, "completed", 10),
        ],
        cleanup_status="cleaned",
        metadata={"coverage_json": '{"totals": {"percent_covered": 87.5, "covered_lines": 7, "num_statements": 8, "missing_lines": 1}}'},
    )

    pytest_result, coverage_result = isolated_result_to_tool_results(isolated)

    assert pytest_result.tool == "pytest"
    assert pytest_result.status == "completed"
    assert pytest_result.summary["outcome"] == "passed"
    assert pytest_result.execution_mode == "deep_isolated"
    assert coverage_result.status == "completed"
    assert coverage_result.summary["coverage_percent"] == 87.5


def test_result_parser_setup_failure_is_limitation_not_failed_tests():
    isolated = IsolatedExecutionResult(
        status="setup_failed",
        image=DEFAULT_RUNNER_IMAGE,
        setup=CommandExecutionResult("setup", 1, "failed", 10, stderr="No matching distribution", reason="Dependency setup failed."),
        cleanup_status="cleaned",
    )

    results = isolated_result_to_tool_results(isolated)

    assert {result.tool: result.status for result in results} == {"pytest": "skipped_by_config", "coverage": "skipped_by_config"}
    assert all(result.summary["outcome"] == "setup_failed" for result in results)


def test_sanitizer_redacts_paths_and_tokens(tmp_path: Path):
    text = f"{tmp_path}\\file.py\nTOKEN=abc123456789abcdef\nAuthorization: Bearer abc123456789abcdef"
    sanitized = sanitize_output(text, repository_path=tmp_path)

    assert str(tmp_path) not in sanitized
    assert "abc123456789abcdef" not in sanitized
    assert "<redacted>" in sanitized


def test_deep_isolated_does_not_call_host_pytest_or_coverage(monkeypatch, tmp_path: Path):
    called = {"pytest": False, "coverage": False}

    def fail_pytest(path):
        called["pytest"] = True
        return ToolResult(tool="pytest", status="completed")

    def fail_coverage(path):
        called["coverage"] = True
        return ToolResult(tool="coverage", status="completed")

    isolated = IsolatedExecutionResult(
        status="docker_unavailable",
        image=DEFAULT_RUNNER_IMAGE,
        limitations=["Docker unavailable"],
        cleanup_status="not_needed",
    )
    monkeypatch.setattr("drrepo.analyzers.test_service.run_pytest", fail_pytest)
    monkeypatch.setattr("drrepo.analyzers.test_service.run_coverage", fail_coverage)
    monkeypatch.setattr("drrepo.analyzers.test_service.run_isolated_checks", lambda request: isolated)

    results = run_test_analyzers(tmp_path, source_type="github_url", analysis_mode="deep_isolated")

    assert called == {"pytest": False, "coverage": False}
    assert {result.tool: result.status for result in results} == {"pytest": "not_available", "coverage": "not_available"}
    assert all(result.execution_mode == "deep_isolated" for result in results)


def test_isolated_runner_splits_network_setup_from_test_phase(monkeypatch, tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")
    networks: list[bool] = []

    monkeypatch.setattr(
        "drrepo.execution.docker_runner.check_docker_capability",
        lambda image=DEFAULT_RUNNER_IMAGE: DockerCapability(True, True, "27", image, True, True, None),
    )

    def fake_execute_plan(**kwargs):
        networks.append(bool(kwargs["network"]))
        if len(networks) == 1:
            return CommandExecutionResult("isolated_runner", 0, "completed", 1), [
                CommandExecutionResult("setup_venv", 0, "completed", 1),
                CommandExecutionResult("setup", 0, "completed", 1),
            ]
        return CommandExecutionResult("isolated_runner", 0, "completed", 1), [
            CommandExecutionResult("pytest", 0, "completed", 1, stdout="1 passed in 0.01s"),
            CommandExecutionResult("coverage", 0, "completed", 1),
        ]

    monkeypatch.setattr("drrepo.execution.docker_runner._execute_plan", fake_execute_plan)

    result = run_isolated_checks(
        IsolatedExecutionRequest(
            repository_path=tmp_path,
            source_type="local_path",
            install_dependencies=True,
            allow_install_network=True,
        )
    )

    assert result.status == "completed"
    assert networks == [True, False]
