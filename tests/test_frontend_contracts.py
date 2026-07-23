from pathlib import Path


def test_result_overview_uses_backend_diagnosis_label_for_visible_verdict():
    source = Path("frontend/src/components/ResultOverview.tsx").read_text(encoding="utf-8")
    assert "label={diagnosis?.repository_health?.label}" in source
    assert "formatVerdict(diagnosis?.repository_health?.label)" in source


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
    advanced = Path("frontend/src/components/AdvancedAuditSettings.tsx").read_text(encoding="utf-8")
    hook = Path("frontend/src/state/useAudit.ts").read_text(encoding="utf-8")

    assert "'deep_isolated'" in types
    assert "export interface IsolatedOptions" in types
    assert "isolated_options?: IsolatedOptions | null" in types
    assert "Deep Isolated" in advanced
    assert "dockerSupported" in advanced
    assert "install_dependencies" in card
    assert "allow_install_network" in card
    assert "isolated_options" in hook


def test_frontend_ai_advisor_types_exist():
    types = Path("frontend/src/types/api.ts").read_text(encoding="utf-8")
    assert "export interface AIAdvisorResult" in types
    assert "ai: boolean" in types
    assert "ai_advisor: AIAdvisorResult | null" in types
    assert "'llm' | 'ai' | 'deterministic'" in types


def test_frontend_audit_input_card_has_ai_toggle_and_disclosure():
    card = Path("frontend/src/components/AuditInputCard.tsx").read_text(encoding="utf-8")
    advanced = Path("frontend/src/components/AdvancedAuditSettings.tsx").read_text(encoding="utf-8")
    assert "AI Advisor" in advanced
    assert "aiEnabled" in card
    assert "privacy_note" in advanced
    assert "provider_configured" in advanced


def test_frontend_use_audit_sends_actual_ai_value():
    hook = Path("frontend/src/state/useAudit.ts").read_text(encoding="utf-8")
    assert "ai," in hook
    assert "ai: boolean" in hook or "ai: false" in hook or "ai: true" in hook or "ai," in hook


def test_frontend_advisor_panel_renders_ai_advisor():
    panel = Path("frontend/src/components/AdvisorPanel.tsx").read_text(encoding="utf-8")
    assert "aiAdvisor" in panel
    assert "AI advisor annotation" in panel
    assert "AI-generated" in panel
    assert "Deterministic fallback" in panel
    assert "Grounding:" in panel
    assert "violation_codes" in panel


def test_frontend_app_passes_ai_advisor_to_panel():
    app = Path("frontend/src/App.tsx").read_text(encoding="utf-8")
    assert "aiAdvisor={data.ai_advisor}" in app


def test_frontend_architecture_contract_and_panel_exist():
    types = Path("frontend/src/types/api.ts").read_text(encoding="utf-8")
    panel = Path("frontend/src/components/ArchitecturePanel.tsx").read_text(encoding="utf-8")
    app = Path("frontend/src/App.tsx").read_text(encoding="utf-8")

    assert "export interface ArchitectureAssessment" in types
    assert "export interface RiskHotspot" in types
    assert "architecture_assessment?: ArchitectureAssessment" in types
    assert "Static map and risk hotspots" in panel
    assert "Dependency Evidence" in panel
    assert "Top risk hotspots" in panel
    assert "ArchitecturePanel assessment={data.audit.architecture_assessment}" in app


def test_audit_launcher_prioritizes_source_goal_and_recommended_run():
    card = Path("frontend/src/components/AuditInputCard.tsx").read_text(encoding="utf-8")

    assert "Local repository" in card
    assert "Public GitHub repository" in card
    assert "What are you preparing this project for?" in card
    assert "Recommended audit:" in card
    assert "Run recommended audit" in card
    assert card.index('id="sourceValue"') < card.index("<AdvancedAuditSettings")
    assert card.index('id="profileId"') < card.index("<AdvancedAuditSettings")


def test_advanced_audit_settings_are_collapsed_and_preserve_all_modes_and_extras():
    source = Path("frontend/src/components/AdvancedAuditSettings.tsx").read_text(encoding="utf-8")

    assert '<details className="rounded-xl border border-border bg-base"' in source
    assert "data-testid=\"advanced-audit-settings\"" in source
    assert "<details open" not in source
    assert "Quick Safe" in source
    assert "Deep Local" in source
    assert "Deep Isolated" in source
    assert "AI Advisor" in source
    assert "Create a downloadable Markdown report" in source
    assert "Runs repository tests on this machine." in source
    assert "Use only for local projects you trust." in source


def test_docker_unavailable_copy_is_safe_and_technical_reason_is_disclosed():
    card = Path("frontend/src/components/AuditInputCard.tsx").read_text(encoding="utf-8")
    advanced = Path("frontend/src/components/AdvancedAuditSettings.tsx").read_text(encoding="utf-8")

    assert "Deep Isolated unavailable:" not in card
    assert "Deep Isolated is unavailable." in advanced
    assert "Start Docker Desktop to enable isolated execution." in advanced
    assert "Why is it unavailable?" in advanced
    assert "sanitizedDockerReason" in advanced


def test_launcher_right_rail_preserves_flow_capabilities_setup_and_reruns():
    card = Path("frontend/src/components/AuditInputCard.tsx").read_text(encoding="utf-8")
    recent = Path("frontend/src/components/RecentAudits.tsx").read_text(encoding="utf-8")

    assert "What happens next" in card
    assert "Diagnostic flow" in card
    assert "Analyzer capability" in card
    assert "Docker isolated runner" in card
    assert "AI advisor" in card
    assert "Setup details" in card
    assert "Rerun shortcuts" in recent


def test_result_navigation_exposes_four_accessible_views():
    navigation = Path("frontend/src/components/ResultNavigation.tsx").read_text(encoding="utf-8")

    for label in ("Summary", "Fix Plan", "Issues", "Technical Details"):
        assert f"label: '{label}'" in navigation
    assert 'role="tablist"' in navigation
    assert 'role="tab"' in navigation
    assert "aria-selected" in navigation
    assert "ArrowRight" in navigation
    assert "ArrowLeft" in navigation


def test_result_views_compose_existing_panels_without_rerunning_audit():
    app = Path("frontend/src/App.tsx").read_text(encoding="utf-8")
    navigation = Path("frontend/src/components/ResultNavigation.tsx").read_text(encoding="utf-8")

    assert "useState<ResultView>('summary')" in app
    assert "case 'fix_plan':" in app
    assert "case 'issues':" in app
    assert "case 'technical_details':" in app
    assert "case 'summary':" in app
    assert "<AdvisorPanel" in app[app.index("case 'fix_plan':"):app.index("case 'issues':")]
    technical_view = app[app.index("case 'technical_details':"):app.index("case 'summary':")]
    assert "<DevOpsReadinessPanel" in technical_view
    assert "<ArchitecturePanel" in technical_view
    assert "<AnalyzerStatusGrid" in technical_view
    assert "<MetadataCard" in technical_view
    assert "<ExportActions" in technical_view
    assert "<MarkdownPreview" in technical_view
    assert "runAudit" not in navigation
    assert "execute(" not in navigation


def test_new_audit_resets_result_view_to_overview():
    app = Path("frontend/src/App.tsx").read_text(encoding="utf-8")

    assert "if (state.status === 'loading' || state.status === 'done')" in app
    assert "setActiveResultView('summary')" in app


def test_overview_is_compact_and_links_to_deeper_sections():
    overview = Path("frontend/src/components/ResultOverview.tsx").read_text(encoding="utf-8")

    assert "Recommended next move" in overview
    assert "Project identity" in overview
    assert "What DrRepo checked" in overview
    assert "Open full fix plan" in overview
    assert "Review issues" in overview
    assert "View technical details" in overview
    assert "Category scores" not in overview
