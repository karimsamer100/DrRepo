from __future__ import annotations

from typing import Any


def run_audit_service(
    source_value: str,
    profile_id: str = "student_portfolio",
    ai: bool = False,
    include_markdown: bool = False,
) -> dict[str, Any]:
    if ai:
        raise ValueError("AI advisor mode is not supported via the API yet.")

    from drrepo.advisor.profiles import validate_profile_id

    validate_profile_id(profile_id)

    from drrepo.audit import build_audit

    audit = build_audit(source_value)

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
        "source_type": "local_path",
        "source_value": str(source_value),
        "profile_id": profile_id,
        "audit": audit,
        "advisor": advisor_report,
        "markdown": markdown,
    }
