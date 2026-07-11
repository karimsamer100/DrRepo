from pathlib import Path


def test_result_overview_uses_backend_diagnosis_label_for_visible_verdict():
    source = Path("frontend/src/components/ResultOverview.tsx").read_text(encoding="utf-8")
    assert "label={diagnosis?.repository_health?.label}" in source
    assert "diagnosis?.repository_health?.label === 'healthy'" in source
