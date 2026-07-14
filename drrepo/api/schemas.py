from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"


class ProfileInfo(BaseModel):
    profile_id: str
    display_name: str
    description: str


class ProfilesResponse(BaseModel):
    profiles: list[ProfileInfo]


class IsolatedOptionsRequest(BaseModel):
    install_dependencies: bool = False
    allow_install_network: bool = False
    total_timeout_seconds: int = 300
    per_command_timeout_seconds: int = 120
    python_version: Literal["3.11", "3.12"] = "3.12"


class AuditRequest(BaseModel):
    source_type: Literal["local_path", "github_url"]
    source_value: str = Field(..., min_length=1)
    analysis_mode: Literal["quick_safe", "deep_local", "deep_isolated"] | None = None
    isolated_options: IsolatedOptionsRequest | None = None
    profile_id: str = "student_portfolio"
    ai: bool = False
    include_markdown: bool = False


class AuditResponse(BaseModel):
    status: str
    source_type: str
    source_value: str
    analysis_mode: str
    profile_id: str
    audit: dict[str, Any]
    advisor: dict[str, Any] | None
    markdown: str | None


class CapabilitiesResponse(BaseModel):
    supported_analysis_modes: list[dict[str, Any]]
    supported_source_types: list[str]
    analyzers: list[dict[str, Any]]
    docker_isolated_execution: dict[str, Any]
    remote_execution_safety_policy: str
    setup: dict[str, Any]
