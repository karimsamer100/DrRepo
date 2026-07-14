from pathlib import Path


def test_result_overview_uses_backend_diagnosis_label_for_visible_verdict():
    source = Path("frontend/src/components/ResultOverview.tsx").read_text(encoding="utf-8")
    assert "label={diagnosis?.repository_health?.label}" in source
    assert "diagnosis?.repository_health?.label === 'healthy'" in source


def test_frontend_evidence_labels_distinguish_findings_from_clean():
    source = Path("frontend/src/lib/presentation.ts").read_text(encoding="utf-8")
    assert "Verified clean" in source
    assert "Completed - ${findingCount}" in source
    assert "verified with findings" in source
    assert "verified clean" in source


def test_frontend_types_include_repository_intelligence_contracts():
    source = Path("frontend/src/types/api.ts").read_text(encoding="utf-8")

    assert "export interface ProjectUnderstanding" in source
    assert "export interface ExecutiveReport" in source
    assert "export interface StructuredRecommendation" in source
    assert "recommendations_v2?: StructuredRecommendation[]" in source
