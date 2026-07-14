from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .command_plan import build_runner_plan
from .models import CommandExecutionResult, IsolatedExecutionRequest, IsolatedExecutionResult
from .sanitizer import sanitize_output

DEFAULT_RUNNER_IMAGE = "drrepo/isolated-runner:python3.12-mvp"

COPY_IGNORE = shutil.ignore_patterns(
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "env",
)


@dataclass(frozen=True)
class DockerCapability:
    docker_cli_available: bool
    engine_reachable: bool
    docker_version: str | None
    runner_image: str
    runner_image_available: bool
    deep_isolated_supported: bool
    unavailable_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "supported": self.deep_isolated_supported,
            "docker_cli_available": self.docker_cli_available,
            "engine_reachable": self.engine_reachable,
            "docker_version": self.docker_version,
            "runner_image": self.runner_image,
            "runner_image_available": self.runner_image_available,
            "reason": self.unavailable_reason,
            "setup_command": f"docker build -t {self.runner_image} drrepo/execution/runner_image",
            "security_note": "deep_isolated runs supported verification inside a disposable DrRepo-controlled Docker container. It is not a multi-tenant SaaS sandbox.",
        }


def check_docker_capability(*, image: str = DEFAULT_RUNNER_IMAGE, timeout_seconds: int = 5) -> DockerCapability:
    try:
        version_proc = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError:
        return DockerCapability(False, False, None, image, False, False, "Docker CLI is not installed.")
    except subprocess.TimeoutExpired:
        return DockerCapability(True, False, None, image, False, False, "Docker engine check timed out.")
    except Exception as exc:
        return DockerCapability(True, False, None, image, False, False, f"Docker capability check failed: {exc}")

    if version_proc.returncode != 0:
        reason = sanitize_output(version_proc.stderr or version_proc.stdout) or "Docker engine is not reachable."
        return DockerCapability(True, False, None, image, False, False, reason)
    docker_version = (version_proc.stdout or "").strip() or None
    try:
        image_proc = subprocess.run(
            ["docker", "image", "inspect", image, "--format", "{{.Id}}"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return DockerCapability(True, True, docker_version, image, False, False, "Runner image check timed out.")
    except Exception as exc:
        return DockerCapability(True, True, docker_version, image, False, False, f"Runner image check failed: {exc}")
    image_available = image_proc.returncode == 0
    if not image_available:
        reason = f"Runner image {image} is not available. Build it with: docker build -t {image} drrepo/execution/runner_image"
        return DockerCapability(True, True, docker_version, image, False, False, reason)
    return DockerCapability(True, True, docker_version, image, True, True, None)


def _copy_repository(source: Path, destination: Path) -> Path:
    target = destination / "repo"
    shutil.copytree(source, target, ignore=COPY_IGNORE)
    return target


def _docker_run_command(*, image: str, container_name: str, repo_path: Path, results_path: Path, plan_path: Path, network: bool, timeout_seconds: int) -> list[str]:
    network_arg = "none" if not network else "bridge"
    return [
        "docker",
        "run",
        "--name",
        container_name,
        "--label",
        "com.drrepo.runner=isolated",
        "--rm",
        "--network",
        network_arg,
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "256",
        "--memory",
        "512m",
        "--cpus",
        "1.0",
        "--user",
        "10001:10001",
        "--workdir",
        "/workspace",
        "--mount",
        f"type=bind,src={repo_path},dst=/workspace",
        "--mount",
        f"type=bind,src={results_path},dst=/results",
        "--mount",
        f"type=bind,src={plan_path},dst=/plan.json,readonly",
        image,
        "--plan",
        "/plan.json",
        "--timeout",
        str(timeout_seconds),
    ]


def _run_container_command(command: list[str], *, timeout_seconds: int, repository_path: Path) -> CommandExecutionResult:
    started = time.perf_counter()
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds)
        status = "completed" if proc.returncode == 0 else "failed"
        return CommandExecutionResult(
            command_id="isolated_runner",
            exit_code=proc.returncode,
            status=status,
            duration_ms=int((time.perf_counter() - started) * 1000),
            stdout=sanitize_output(proc.stdout, repository_path=repository_path),
            stderr=sanitize_output(proc.stderr, repository_path=repository_path),
            timeout=False,
        )
    except subprocess.TimeoutExpired as exc:
        return CommandExecutionResult(
            command_id="isolated_runner",
            exit_code=None,
            status="timeout",
            duration_ms=int((time.perf_counter() - started) * 1000),
            stdout=sanitize_output(exc.stdout.decode("utf-8", "ignore") if isinstance(exc.stdout, bytes) else exc.stdout, repository_path=repository_path),
            stderr=sanitize_output(exc.stderr.decode("utf-8", "ignore") if isinstance(exc.stderr, bytes) else exc.stderr, repository_path=repository_path),
            timeout=True,
            reason="Container execution timed out.",
        )


def _load_command_results(results_path: Path, repository_path: Path) -> list[CommandExecutionResult]:
    path = results_path / "results.json"
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = raw.get("commands") if isinstance(raw, dict) else None
    if not isinstance(items, list):
        return []
    parsed: list[CommandExecutionResult] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        parsed.append(CommandExecutionResult(
            command_id=str(item.get("id", "unknown")),
            exit_code=item.get("exit_code") if isinstance(item.get("exit_code"), int) else None,
            status=str(item.get("status", "failed")),
            duration_ms=int(item.get("duration_ms", 0) or 0),
            stdout=sanitize_output(str(item.get("stdout", "") or ""), repository_path=repository_path),
            stderr=sanitize_output(str(item.get("stderr", "") or ""), repository_path=repository_path),
            timeout=bool(item.get("timeout", False)),
            reason=str(item.get("reason")) if item.get("reason") else None,
        ))
    return parsed


def _write_plan(path: Path, plan: dict[str, Any]) -> None:
    path.write_text(json.dumps(plan), encoding="utf-8")


def _execute_plan(
    *,
    image: str,
    repo_copy: Path,
    results_path: Path,
    plan_path: Path,
    network: bool,
    timeout_seconds: int,
) -> tuple[CommandExecutionResult, list[CommandExecutionResult]]:
    container_name = f"drrepo-isolated-{uuid.uuid4().hex[:12]}"
    docker_cmd = _docker_run_command(
        image=image,
        container_name=container_name,
        repo_path=repo_copy,
        results_path=results_path,
        plan_path=plan_path,
        network=network,
        timeout_seconds=timeout_seconds,
    )
    command_result = _run_container_command(docker_cmd, timeout_seconds=timeout_seconds, repository_path=repo_copy)
    commands = _load_command_results(results_path, repo_copy)
    if not commands:
        commands = [command_result]
    return command_result, commands


def run_isolated_checks(request: IsolatedExecutionRequest, *, image: str = DEFAULT_RUNNER_IMAGE) -> IsolatedExecutionResult:
    capability = check_docker_capability(image=image)
    if not capability.deep_isolated_supported:
        return IsolatedExecutionResult(
            status="docker_unavailable",
            image=image,
            docker_version=capability.docker_version,
            source_type=request.source_type,
            limitations=[capability.unavailable_reason or "Docker isolated execution is unavailable."],
            cleanup_status="not_needed",
        )

    workspace = Path(tempfile.mkdtemp(prefix="drrepo-isolated-"))
    cleanup_status = "not_started"
    repo_copy = workspace / "repo"
    results_path = workspace / "results"
    plan_path = workspace / "plan.json"
    results_path.mkdir(parents=True, exist_ok=True)
    command_result: CommandExecutionResult | None = None
    result: IsolatedExecutionResult | None = None
    try:
        repo_copy = _copy_repository(request.repository_path, workspace)
        commands: list[CommandExecutionResult] = []
        if request.install_dependencies:
            setup_plan = build_runner_plan(
                repository_path=repo_copy,
                requested_checks=(),
                install_dependencies=True,
                allow_install_network=request.allow_install_network,
                per_command_timeout_seconds=request.per_command_timeout_seconds,
                include_setup=True,
                include_checks=False,
            )
            _write_plan(plan_path, setup_plan)
            command_result, setup_commands = _execute_plan(
                image=image,
                repo_copy=repo_copy,
                results_path=results_path,
                plan_path=plan_path,
                network=request.allow_install_network,
                timeout_seconds=request.total_timeout_seconds,
            )
            commands.extend(setup_commands)

        if not commands or not any(item.command_id.startswith("setup") and item.status in {"failed", "timeout"} for item in commands):
            check_plan = build_runner_plan(
                repository_path=repo_copy,
                requested_checks=request.requested_checks,
                install_dependencies=False,
                allow_install_network=False,
                per_command_timeout_seconds=request.per_command_timeout_seconds,
                include_setup=False,
                include_checks=True,
                python_bin="/workspace/.drrepo_venv/bin/python" if request.install_dependencies else "python",
            )
            _write_plan(plan_path, check_plan)
            command_result, check_commands = _execute_plan(
                image=image,
                repo_copy=repo_copy,
                results_path=results_path,
                plan_path=plan_path,
                network=False,
                timeout_seconds=request.total_timeout_seconds,
            )
            commands.extend(check_commands)
        status = "completed"
        if any(item.timeout for item in commands):
            status = "timeout"
        elif any(item.command_id.startswith("setup") and item.status == "failed" for item in commands):
            status = "setup_failed"
        elif command_result and command_result.status == "failed" and not _load_command_results(results_path, repo_copy):
            status = "failed_to_run"
        metadata: dict[str, Any] = {"runner_image": image}
        coverage_json = results_path / "coverage.json"
        if coverage_json.exists():
            metadata["coverage_json"] = sanitize_output(coverage_json.read_text(encoding="utf-8", errors="ignore"), repository_path=repo_copy)
        result = IsolatedExecutionResult(
            status=status,  # type: ignore[arg-type]
            image=image,
            docker_version=capability.docker_version,
            source_type=request.source_type,
            setup=next((item for item in commands if item.command_id == "setup"), None),
            commands=commands,
            durations_ms={item.command_id: item.duration_ms for item in commands},
            limitations=[],
            cleanup_status="pending",
            metadata=metadata,
        )
        return result
    finally:
        try:
            shutil.rmtree(workspace, ignore_errors=True)
            cleanup_status = "cleaned"
        except Exception:
            cleanup_status = "cleanup_failed"
        if command_result is not None:
            command_result.reason = command_result.reason or f"cleanup_status={cleanup_status}"
        if result is not None:
            result.cleanup_status = cleanup_status
