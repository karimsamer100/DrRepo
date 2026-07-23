from __future__ import annotations

from pathlib import Path
from typing import Any

from drrepo.advisor.reporting import build_deterministic_advisor_report
from drrepo.advisor.service import build_advisor_for_audit
from drrepo.analyzers.registry import validate_analysis_mode
from drrepo.api.local_paths import validate_local_source_path
from drrepo.audit import build_audit


def run_audit_service(
    source_type: str,
    source_value: str,
    profile_id: str = "student_portfolio",
    ai: bool = False,
    include_markdown: bool = False,
    analysis_mode: str | None = None,
    isolated_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from drrepo.advisor.profiles import validate_profile_id

    validate_profile_id(profile_id)
    mode = validate_analysis_mode(source_type, analysis_mode)
    if mode == "deep_isolated":
        from drrepo.execution import check_docker_capability
        from drrepo.execution.models import options_from_dict

        options_from_dict(isolated_options)
        docker_capability = check_docker_capability()
        if not docker_capability.deep_isolated_supported:
            raise ValueError(docker_capability.unavailable_reason or "Docker isolated execution is unavailable.")

    workspace: Path | None = None
    audit_path: str | Path

    if source_type == "local_path":
        audit_path = validate_local_source_path(source_value)
    elif source_type == "github_url":
        from drrepo.input.git import is_public_github_repo_url
        from drrepo.input.workspace import (
            cleanup_workspace,
            clone_public_github_repo,
            create_temp_workspace,
        )

        if not is_public_github_repo_url(source_value):
            raise ValueError(
                f"Invalid or unsupported GitHub repository URL: {source_value}"
            )

        workspace = create_temp_workspace()
        try:
            audit_path = clone_public_github_repo(source_value, workspace)
        except Exception:
            cleanup_workspace(workspace)
            raise
    else:
        raise ValueError(f"Unsupported source_type: {source_type}")

    try:
        audit = build_audit(audit_path, source_type=source_type, analysis_mode=mode, profile_id=profile_id, isolated_options=isolated_options)
    finally:
        if workspace is not None:
            from drrepo.input.workspace import cleanup_workspace

            try:
                cleanup_workspace(workspace)
            except Exception:
                # Best-effort cleanup: a failure here (e.g. Windows file lock)
                # must not override a successful audit response.
                pass

    audit["source"] = {"type": source_type, "value": source_value}

    try:
        advisor_package = build_advisor_for_audit(
            audit, profile_id=profile_id, ai=ai
        )
    except Exception as exc:
        advisor_report = build_deterministic_advisor_report(audit, profile_id=profile_id)
        deterministic_response = advisor_report.get("advisor_response", {})
        advisor_package = {
            "advisor_report": advisor_report,
            "ai": {
                "requested": ai,
                "status": "internal_advisor_error" if ai else "not_requested",
                "source": "deterministic",
                "provider": None,
                "model": "deterministic-advisor",
                "advisor_response": deterministic_response,
                "grounding_result": None,
                "limitations": list(deterministic_response.get("limitations", [])) if isinstance(deterministic_response, dict) else [],
                "fallback_reason": f"Advisor failed safely: {type(exc).__name__}" if ai else None,
                "duration_ms": 0,
            },
        }
    advisor_report = advisor_package.get("advisor_report")
    ai_advisor = advisor_package.get("ai")

    markdown: str | None = None
    if include_markdown:
        from drrepo.reports.markdown_report import render_markdown_report

        markdown = render_markdown_report(audit, ai_advisor=ai_advisor)

    return {
        "status": audit.get("status", "ok"),
        "source_type": source_type,
        "source_value": source_value,
        "analysis_mode": mode,
        "profile_id": profile_id,
        "audit": audit,
        "advisor": advisor_report,
        "ai_advisor": ai_advisor,
        "markdown": markdown,
    }
