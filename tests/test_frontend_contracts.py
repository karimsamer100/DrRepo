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


def test_frontend_types_include_devops_readiness_contracts():
    source = Path("frontend/src/types/api.ts").read_text(encoding="utf-8")
    panel = Path("frontend/src/components/DevOpsReadinessPanel.tsx").read_text(encoding="utf-8")

    assert "export interface DevOpsReadiness" in source
    assert "devops_readiness?: DevOpsReadiness" in source
    assert "DevOps & release readiness" in panel


def test_frontend_contracts_include_deep_isolated_controls():
    types = Path("frontend/src/types/api.ts").read_text(encoding="utf-8")
    card = Path("frontend/src/components/AuditInputCard.tsx").read_text(encoding="utf-8")
    hook = Path("frontend/src/state/useAudit.ts").read_text(encoding="utf-8")

    assert "'deep_isolated'" in types
    assert "export interface IsolatedOptions" in types
    assert "isolated_options?: IsolatedOptions | null" in types
    assert "Deep Isolated" in card
    assert "dockerSupported" in card
    assert "install_dependencies" in card
    assert "allow_install_network" in card
    assert "isolated_options" in hook


def test_frontend_ai_advisor_types_exist():
    types = Path("frontend/src/types/api.ts").read_text(encoding="utf-8")
    assert "export interface AIAdvisorResult" in types
    assert "ai: boolean" in types
    assert "ai_advisor: AIAdvisorResult | null" in types


def test_frontend_audit_input_card_has_ai_toggle_and_disclosure():
    card = Path("frontend/src/components/AuditInputCard.tsx").read_text(encoding="utf-8")
    assert "AI Advisor" in card
    assert "aiEnabled" in card
    assert "privacy_note" in card
    assert "provider_configured" in card


def test_frontend_use_audit_sends_actual_ai_value():
    hook = Path("frontend/src/state/useAudit.ts").read_text(encoding="utf-8")
    assert "ai," in hook
    assert "ai: boolean" in hook or "ai: false" in hook or "ai: true" in hook or "ai," in hook


def test_frontend_advisor_panel_renders_ai_advisor():
    panel = Path("frontend/src/components/AdvisorPanel.tsx").read_text(encoding="utf-8")
    assert "aiAdvisor" in panel
    assert "AI advisor guidance" in panel
    assert "AI-generated" in panel
    assert "Deterministic fallback" in panel
    assert "Grounding:" in panel
    assert "violation_codes" in panel


def test_frontend_app_passes_ai_advisor_to_panel():
    app = Path("frontend/src/App.tsx").read_text(encoding="utf-8")
    assert "aiAdvisor={data.ai_advisor}" in app
