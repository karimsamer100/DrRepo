from drrepo.reports.markdown_report import render_markdown_report


def test_basic_report_sections_present():
    audit = {
        "status": "ok",
        "path": "/repo/path",
        "metadata": {},
        "static_analysis": [],
        "test_analysis": [],
        "repository_analysis": [],
        "scoring": {},
    }
    md = render_markdown_report(audit)
    assert "# DrRepo Audit Report" in md
    assert "## Repository" in md
    assert "## Score Summary" in md
    assert "## Metadata Summary" in md
    assert "## Analyzer Summary" in md
    assert "## Findings" in md
    assert "## Evidence Limitations / Unavailable Tools" in md
    assert "## Errors" in md


def test_markdown_report_prefers_source_for_github_audits():
    audit = {
        "path": "C:/temp/drrepo-123/repo",
        "source": {"type": "github_url", "value": "https://github.com/owner/repo"},
        "diagnosis": {
            "evidence_confidence": {
                "label": "partial",
                "summary": "Partial evidence: 3 of 5 optional tools were available.",
            }
        },
    }
    md = render_markdown_report(audit)
    assert "https://github.com/owner/repo" in md
    assert "C:/temp/drrepo-123/repo" not in md
    assert "Evidence confidence: partial; Partial evidence: 3 of 5 optional tools were available." in md


def test_markdown_report_uses_path_for_local_audits():
    audit = {"path": "C:/projects/local-repo", "status": "ok"}
    md = render_markdown_report(audit)
    assert "- **Path**: C:/projects/local-repo" in md
    assert "- **Source**:" not in md


def test_scoring_values_rendered():
    audit = {"scoring": {"overall_score": 94, "sections": {"static_analysis": {"score": 100}, "test_analysis": {"score": 85}, "repository_analysis": {"score": 97}}}}
    md = render_markdown_report(audit)
    assert "Overall score" in md
    assert "94" in md
    assert "100" in md
    assert "85" in md
    assert "97" in md


def test_analyzer_table_includes_tools_and_statuses():
    audit = {
        "static_analysis": [{"tool": "ruff", "status": "completed", "findings": [], "errors": []}],
        "test_analysis": [{"tool": "pytest", "status": "completed", "findings": [], "errors": []}],
        "repository_analysis": [{"tool": "readme", "status": "completed", "findings": [], "errors": []}],
    }
    md = render_markdown_report(audit)
    assert "ruff" in md
    assert "pytest" in md
    assert "readme" in md
    assert "completed" in md


def test_findings_rendered():
    audit = {
        "test_analysis": [
            {
                "tool": "pytest",
                "status": "completed",
                "findings": [
                    {
                        "severity": "high",
                        "code": "PYTEST-FAILED",
                        "message": "1 test failed",
                        "file_path": "tests/test_app.py",
                        "line": 10,
                    }
                ],
                "errors": [],
            }
        ]
    }
    md = render_markdown_report(audit)
    assert "high" in md
    assert "PYTEST-FAILED" in md
    assert "1 test failed" in md
    assert "tests/test_app.py" in md
    assert "10" in md


def test_errors_rendered():
    audit = {"static_analysis": [{"tool": "ruff", "status": "failed_to_run", "errors": ["ruff crashed"]}]}
    md = render_markdown_report(audit)
    assert "ruff crashed" in md


def test_failed_analyzer_renders_concise_limitation_reason():
    audit = {"static_analysis": [{"tool": "radon", "status": "failed_to_run", "errors": ["radon crashed"], "findings": []}]}
    md = render_markdown_report(audit)
    assert "radon: analyzer failed to run (radon crashed)" in md


def test_not_available_tools_render_as_limitations_not_errors():
    audit = {
        "static_analysis": [
            {"tool": "ruff", "status": "not_available", "errors": ["No module named ruff"]},
            {"tool": "bandit", "status": "not_available", "errors": ["No module named bandit"]},
            {"tool": "radon", "status": "not_available", "errors": ["No module named radon"]},
        ],
        "test_analysis": [
            {"tool": "coverage", "status": "not_available", "errors": ["No module named coverage"]},
            {
                "tool": "pytest",
                "status": "skipped_by_config",
                "summary": {"reason": "Skipped for remote GitHub audit safety."},
            },
        ],
    }
    md = render_markdown_report(audit)
    assert "ruff: tool unavailable in this environment." in md
    assert "bandit: tool unavailable in this environment." in md
    assert "radon: tool unavailable in this environment." in md
    assert "coverage: tool unavailable in this environment." in md
    assert "pytest: Skipped for remote GitHub audit safety." in md
    assert "No module named ruff" not in md
    assert "No module named bandit" not in md
    assert "No module named radon" not in md
    assert "No module named coverage" not in md
    assert "No analyzer errors reported." in md


def test_missing_keys_do_not_crash():
    md = render_markdown_report({})
    assert isinstance(md, str)
    assert len(md) > 0
    assert "N/A" in md or "No findings reported." in md


def test_prioritized_action_plan_rendering_and_summary():
    audit = {
        "remediation_suggestions": [
            {"section": "static_analysis", "tool": "ruff", "severity": "low", "title": "Install ruff", "action": "pip install ruff"}
        ],
        "remediation_summary": {"total": 1, "by_severity": {"low": 1}},
    }
    md = render_markdown_report(audit)
    assert "## Prioritized Action Plan" in md
    assert "Install ruff" in md
    assert "pip install ruff" in md
    assert "Total suggestions: 1" in md
    assert "By severity: low=1" in md


def test_prioritized_action_plan_handles_empty():
    audit = {"remediation_suggestions": [], "remediation_summary": {"total": 0}}
    md = render_markdown_report(audit)
    assert "## Prioritized Action Plan" in md
    assert "No remediation suggestions generated." in md


def test_prioritized_action_plan_escapes_pipes():
    audit = {
        "remediation_suggestions": [
            {"section": "test_analysis", "tool": "pytest", "severity": "high", "title": "Fix A | B", "action": "Do X | Y"}
        ],
        "remediation_summary": {"total": 1, "by_severity": {"high": 1}},
    }
    md = render_markdown_report(audit)
    # ensure pipe characters are escaped in the table cells
    assert "Fix A \\| B" in md or "Fix A \\|" in md
    assert "Do X \\| Y" in md or "Do X \\|" in md


def _ai_advisor() -> dict[str, object]:
    return {
        "requested": True,
        "status": "completed",
        "source": "llm",
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "advisor_response": {
            "summary": "Fix the highest-impact issues first.",
            "profile_context": "Student portfolio",
            "top_priorities": [
                {
                    "title": "Improve tests",
                    "why_it_matters": "Raises confidence",
                    "evidence": ["PYTEST-FAILED"],
                    "suggested_fix": "Add more tests",
                    "priority": "high",
                }
            ],
            "lower_priority_items": [
                {"title": "Add docs", "why_it_matters": "x", "evidence": [], "suggested_fix": "y", "priority": "low"}
            ],
            "limitations": ["No coverage data"],
            "next_steps": ["Run pytest"],
        },
        "grounding_result": {
            "valid": True,
            "checked_claims": 3,
            "validated_references": 3,
            "violations": [],
        },
        "fallback_reason": None,
        "duration_ms": 100,
    }


def test_markdown_includes_ai_advisor_guidance_when_requested():
    audit = {"status": "ok", "path": "repo", "metadata": {}}
    md = render_markdown_report(audit, ai_advisor=_ai_advisor())
    assert "## AI Advisor Guidance" in md
    assert "**Source**: llm" in md
    assert "**Status**: completed" in md
    assert "**Provider**: gemini" in md
    assert "**Grounding**: valid" in md
    assert "Fix-first action" in md
    assert "Ordered plan" in md
    assert "Success checks / next steps" in md


def test_markdown_ai_section_only_when_requested():
    audit = {"status": "ok", "path": "repo", "metadata": {}}
    no_ai = render_markdown_report(audit)
    assert "## AI Advisor Guidance" not in no_ai
    requested = render_markdown_report(audit, ai_advisor=_ai_advisor())
    assert "## AI Advisor Guidance" in requested


def test_markdown_grounding_rejected_shown():
    ai_advisor = _ai_advisor()
    ai_advisor["status"] = "grounding_rejected"
    ai_advisor["source"] = "deterministic"
    ai_advisor["grounding_result"] = {
        "valid": False,
        "checked_claims": 3,
        "validated_references": 2,
        "violations": ["unknown evidence reference: x"],
    }
    ai_advisor["fallback_reason"] = "AI response contradicted the audit evidence"
    audit = {"status": "ok", "path": "repo", "metadata": {}}
    md = render_markdown_report(audit, ai_advisor=ai_advisor)
    assert "**Grounding**: rejected" in md
    assert "Fallback reason" in md
    assert "unknown evidence reference" in md
