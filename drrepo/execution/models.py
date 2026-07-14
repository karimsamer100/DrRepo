from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

ALLOWED_PYTHON_VERSIONS = ("3.11", "3.12")
DEFAULT_PYTHON_VERSION = "3.12"
MAX_TOTAL_TIMEOUT_SECONDS = 900
MAX_PER_COMMAND_TIMEOUT_SECONDS = 300

IsolatedStatus = Literal[
    "completed",
    "setup_failed",
    "docker_unavailable",
    "failed_to_run",
    "timeout",
    "partial",
]


@dataclass(frozen=True)
class IsolatedExecutionOptions:
    install_dependencies: bool = False
    allow_install_network: bool = False
    total_timeout_seconds: int = 300
    per_command_timeout_seconds: int = 120
    python_version: str = DEFAULT_PYTHON_VERSION


@dataclass(frozen=True)
class IsolatedExecutionRequest:
    repository_path: Path
    source_type: str
    python_version: str = DEFAULT_PYTHON_VERSION
    install_dependencies: bool = False
    allow_install_network: bool = False
    requested_checks: tuple[str, ...] = ("syntax", "pytest", "coverage")
    total_timeout_seconds: int = 300
    per_command_timeout_seconds: int = 120


@dataclass
class CommandExecutionResult:
    command_id: str
    exit_code: int | None
    status: str
    duration_ms: int
    stdout: str = ""
    stderr: str = ""
    timeout: bool = False
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_id": self.command_id,
            "exit_code": self.exit_code,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "timeout": self.timeout,
            "reason": self.reason,
        }


@dataclass
class IsolatedExecutionResult:
    status: IsolatedStatus
    image: str
    docker_version: str | None = None
    source_type: str = "local_path"
    setup: CommandExecutionResult | None = None
    commands: list[CommandExecutionResult] = field(default_factory=list)
    durations_ms: dict[str, int] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    cleanup_status: str = "not_started"
    metadata: dict[str, Any] = field(default_factory=dict)

    def command(self, command_id: str) -> CommandExecutionResult | None:
        return next((item for item in self.commands if item.command_id == command_id), None)


def validate_isolated_options(options: IsolatedExecutionOptions) -> None:
    if options.python_version not in ALLOWED_PYTHON_VERSIONS:
        allowed = ", ".join(ALLOWED_PYTHON_VERSIONS)
        raise ValueError(f"Unsupported isolated Python version: {options.python_version}. Allowed versions: {allowed}.")
    if options.allow_install_network and not options.install_dependencies:
        raise ValueError("allow_install_network requires install_dependencies.")
    if options.total_timeout_seconds < 30 or options.total_timeout_seconds > MAX_TOTAL_TIMEOUT_SECONDS:
        raise ValueError(f"isolated total timeout must be between 30 and {MAX_TOTAL_TIMEOUT_SECONDS} seconds.")
    if options.per_command_timeout_seconds < 10 or options.per_command_timeout_seconds > MAX_PER_COMMAND_TIMEOUT_SECONDS:
        raise ValueError(f"isolated command timeout must be between 10 and {MAX_PER_COMMAND_TIMEOUT_SECONDS} seconds.")
    if options.per_command_timeout_seconds > options.total_timeout_seconds:
        raise ValueError("isolated command timeout cannot exceed total timeout.")


def options_from_dict(raw: dict[str, Any] | None) -> IsolatedExecutionOptions:
    if raw is None:
        return IsolatedExecutionOptions()
    options = IsolatedExecutionOptions(
        install_dependencies=bool(raw.get("install_dependencies", False)),
        allow_install_network=bool(raw.get("allow_install_network", False)),
        total_timeout_seconds=int(raw.get("total_timeout_seconds", 300)),
        per_command_timeout_seconds=int(raw.get("per_command_timeout_seconds", 120)),
        python_version=str(raw.get("python_version", DEFAULT_PYTHON_VERSION)),
    )
    validate_isolated_options(options)
    return options
