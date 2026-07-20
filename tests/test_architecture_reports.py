from drrepo.reports.terminal_summary import render_terminal_summary


def test_terminal_summary_includes_concise_architecture_signal():
    audit = {
        "architecture_assessment": {
            "confidence": "high",
            "summary": "Static evidence suggests app/routes.py imports app/service.py.",
            "hotspots": [{"path": "app/service.py", "risk_level": "medium", "risk_score": 42}],
            "cycles": [{"id": "cycle:1"}],
        }
    }

    summary = render_terminal_summary(audit)

    assert "Architecture: high confidence" in summary
    assert "Top architecture hotspots: app/service.py (medium 42)" in summary
    assert "Architecture cycles: 1 detected" in summary
