from drrepo.reports.terminal_summary import render_terminal_summary


def test_terminal_summary_contains_basic_fields():
    audit = {
        "path": "/repo/path",
        "scoring": {"overall_score": 90},
        "diagnosis": {"repository_health": {"label": "healthy", "summary": "ok"}},
        "remediation_suggestions": [
            {"title": "One", "action": "Do one"},
            {"title": "Two", "action": "Do two"},
        ],
        "static_analysis": [{"tool": "ruff", "status": "not_available"}],
    }
    out = render_terminal_summary(audit)
    assert "DrRepo Audit Summary" in out
    assert "Path: /repo/path" in out
    assert "Overall score: 90" in out
    assert "Diagnosis: healthy" in out
    assert "Suggestions: 2" in out
    assert "1. [unknown] One — Do one" in out


def test_terminal_summary_hard_flags_and_limitations_and_suggestions_limit():
    audit = {
        "diagnosis": {"hard_flags": ["A", "B"], "limitations": ["L1"]},
        "remediation_suggestions": [
            {"title": "T1", "action": "A1"},
            {"title": "T2", "action": "A2"},
            {"title": "T3", "action": "A3"},
            {"title": "T4", "action": "A4"},
        ],
    }
    out = render_terminal_summary(audit)
    assert "Hard flags:" in out
    assert "A, B" in out
    assert "Limitations:" in out
    assert "L1" in out
    # only top 3 shown and suggestions total reported
    assert "Suggestions: 4" in out
    assert "1. [unknown] T1 — A1" in out
    assert "3. [unknown] T3 — A3" in out
    assert "4. [unknown] T4 — A4" not in out


def test_terminal_summary_no_suggestions_renders_none():
    out = render_terminal_summary({})
    assert "Suggestions: 0" in out
    assert "Top actions:" in out
    assert "None" in out


def test_terminal_summary_analyzer_statuses_render():
    audit = {
        "static_analysis": [{"tool": "ruff", "status": "not_available"}, {"tool": "bandit", "status": "completed"}],
        "test_analysis": [{"tool": "pytest", "status": "completed"}],
        "repository_analysis": [],
    }
    out = render_terminal_summary(audit)
    assert "static_analysis" in out
    assert "ruff=not_available" in out
    assert "bandit=completed" in out