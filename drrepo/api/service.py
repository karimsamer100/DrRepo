from __future__ import annotations

from pathlib import Path
from typing import Any


def run_audit_service(
    source_type: str,
    source_value: str,
    profile_id: str = "student_portfolio",
    ai: bool = False,
    include_markdown: bool = False,
) -> dict[str, Any]:
    if ai:
        raise ValueError("AI advisor mode is not supported via the API yet.")

    from drrepo.advisor.profiles import validate_profile_id

    validate_profile_id(profile_id)

    workspace: Path | None = None
    audit_path: str | Path

    if source_type == "local_path":
        audit_path = source_value
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

    from drrepo.audit import build_audit

    try:
        audit = build_audit(audit_path)
    finally:
        if workspace is not None:
            from drrepo.input.workspace import cleanup_workspace

            try:
                cleanup_workspace(workspace)
            except Exception:
                # Best-effort cleanup: a failure here (e.g. Windows file lock)
                # must not override a successful audit response.
                pass

    from drrepo.advisor.service import build_advisor_result

    advisor_result = build_advisor_result(
        audit, profile_id=profile_id, include_prompt_bundle=False
    )
    advisor_report = advisor_result.get("advisor_report")

    markdown: str | None = None
    if include_markdown:
        from drrepo.reports.markdown_report import render_markdown_report

        markdown = render_markdown_report(audit)

    return {
        "status": audit.get("status", "ok"),
        "source_type": source_type,
        "source_value": source_value,
        "profile_id": profile_id,
        "audit": audit,
        "advisor": advisor_report,
        "markdown": markdown,
    }
