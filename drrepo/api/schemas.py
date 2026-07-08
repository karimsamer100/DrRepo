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


class AuditRequest(BaseModel):
    source_type: Literal["local_path"]
    source_value: str = Field(..., min_length=1)
    profile_id: str = "student_portfolio"
    ai: bool = False
    include_markdown: bool = False


class AuditResponse(BaseModel):
    status: str
    source_type: str
    source_value: str
    profile_id: str
    audit: dict[str, Any]
    advisor: dict[str, Any] | None
    markdown: str | None
