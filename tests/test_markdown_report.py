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
    assert "## Errors" in md


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
    audit = {"static_analysis": [{"tool": "ruff", "errors": ["No module named ruff"]}]}
    md = render_markdown_report(audit)
    assert "No module named ruff" in md


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
