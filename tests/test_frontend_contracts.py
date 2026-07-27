import struct
from pathlib import Path


def png_dimensions(path: Path) -> tuple[int, int]:
    return struct.unpack(">II", path.read_bytes()[16:24])


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


def test_frontend_root_layout_allows_page_vertical_scrolling():
    css = Path("frontend/src/index.css").read_text(encoding="utf-8")
    app = Path("frontend/src/App.tsx").read_text(encoding="utf-8")

    assert "overflow: hidden" not in css
    assert "overflow-x: hidden" in css
    assert "min-height: 100%" in css
    assert "min-h-dvh" in app
    assert "flex h-dvh" not in app
    assert "overflow-y-auto" not in app
    assert "max-w-[1220px]" in app


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
    assert card.index('type="submit"') < card.index("<AdvancedAuditSettings")


def test_launcher_density_keeps_primary_action_above_advanced_without_tiny_text():
    app = Path("frontend/src/App.tsx").read_text(encoding="utf-8")
    card = Path("frontend/src/components/AuditInputCard.tsx").read_text(encoding="utf-8")
    advanced = Path("frontend/src/components/AdvancedAuditSettings.tsx").read_text(encoding="utf-8")
    css = Path("frontend/src/index.css").read_text(encoding="utf-8")

    assert "sm:px-6 sm:py-5" in app
    assert 'className="py-0"' in app
    assert 'className="mb-4"' in card
    assert "space-y-4" in card
    assert "surface-raised self-start rounded-xl p-4 sm:p-5" in card
    assert "inline-flex min-h-11 w-full" in card
    assert "flex min-h-11 cursor-pointer" in advanced
    assert "min-h-10" in card
    assert "min-h-8" in card
    assert "scale-" not in app
    assert "scale-" not in card
    assert "zoom:" not in css


def test_launcher_columns_use_content_driven_height():
    card = Path("frontend/src/components/AuditInputCard.tsx").read_text(encoding="utf-8")

    assert "items-start" in card
    assert "self-start rounded-xl" in card
    assert "lg:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]" in card
    assert "h-full" not in card


def test_header_has_compact_logo_wordmark_status_and_new_audit_action():
    header = Path("frontend/src/components/AuditConsoleHeader.tsx").read_text(encoding="utf-8")
    mark = Path("frontend/src/components/DrRepoMark.tsx").read_text(encoding="utf-8")
    app = Path("frontend/src/App.tsx").read_text(encoding="utf-8")

    assert "import { DrRepoMark } from './DrRepoMark'" in header
    assert '<DrRepoMark className="h-11 w-11 shrink-0 object-contain" />' in header
    assert "export function DrRepoMark" in mark
    assert 'src="/brand/drrepo-favicon.png"' in mark
    assert "viewBox" not in mark
    assert "<svg" not in mark
    assert "<image" not in mark
    assert "drrepo-logo-horizontal" not in header
    assert "drrepo-logo-stacked" not in header
    assert "drrepo-favicon" not in header
    assert "Repository Audit" in header
    assert "API online" in header
    assert "New audit" in header
    assert "min-h-[52px]" in header
    assert "h-11 w-11" in header
    assert "object-contain" in header
    assert "bg-surface/45" not in header
    assert "border-brand/20" not in header
    assert "gap-3" in header
    assert "text-[22px]" in header
    assert "text-[15px]" in header
    assert "tracking-[0.16em]" in header
    assert "text-info" in header
    assert 'aria-label="Return to new audit"' in header
    assert "onNew={handleNewAudit}" in app
    assert "window.scrollTo" in app


def test_theme_system_sets_document_theme_before_react_and_persists_preference():
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    app = Path("frontend/src/App.tsx").read_text(encoding="utf-8")
    header = Path("frontend/src/components/AuditConsoleHeader.tsx").read_text(encoding="utf-8")
    css = Path("frontend/src/index.css").read_text(encoding="utf-8")
    tailwind = Path("frontend/tailwind.config.ts").read_text(encoding="utf-8")

    assert 'data-theme="dark"' in html
    assert "drrepo.themePreference" in html
    assert "prefers-color-scheme: dark" in html
    assert "document.documentElement.dataset.theme" in html
    assert "drrepo.themePreference" in app
    assert "ThemePreference = 'system' | 'light' | 'dark'" in app
    assert "setThemePreference" in app
    assert "theme-switch" in header
    assert "aria-pressed" in header
    assert "Switch to" in header
    assert "onThemePreferenceChange" in header
    assert "[data-theme='light']" in css
    assert "--color-base: 238 233 225" in css
    assert "--color-panel: 246 241 232" in css
    assert "--color-surface: 251 248 242" in css
    assert "--color-raised: 255 253 248" in css
    assert "--color-surface-2: 226 238 242" in css
    assert "--color-brand: 21 95 122" in css
    assert "rgb(var(--color-base)" in tailwind
    assert "on-brand" in tailwind
    assert "text-on-brand" in app or "text-on-brand" in Path("frontend/src/components/ResultNavigation.tsx").read_text(encoding="utf-8")


def test_warm_light_theme_has_distinct_surfaces_and_azure_interactions():
    css = Path("frontend/src/index.css").read_text(encoding="utf-8")

    assert "--color-base: 238 233 225" in css
    assert "--color-panel: 246 241 232" in css
    assert "--color-surface: 251 248 242" in css
    assert "--color-raised: 255 253 248" in css
    assert "--color-surface-2: 226 238 242" in css
    assert "--color-border: 183 199 203" in css
    assert "--color-primary: 20 39 45" in css
    assert "--color-muted: 64 92 101" in css
    assert "--color-faint: 83 107 115" in css
    assert "--color-brand: 21 95 122" in css
    assert "--color-health: 22 132 92" in css
    assert "--color-base: 255 255 255" not in css
    assert "[data-theme='light'] .repository-scan-ring" in css


def test_browser_metadata_and_prepaint_theme_are_publish_ready():
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    favicon = Path("frontend/public/brand/drrepo-favicon.png")

    assert "<title>DrRepo — Repository Audit</title>" in html
    assert 'name="description"' in html
    assert "Evidence-driven repository auditing and prioritized remediation." in html
    assert html.count('rel="icon"') == 1
    assert "shortcut icon" not in html
    assert "apple-touch-icon" not in html
    assert 'rel="icon" type="image/png" href="/brand/drrepo-favicon.png"' in html
    assert "drrepo-favicon.svg" not in html
    assert "drrepo-header-mark" not in html
    assert 'name="theme-color"' in html
    assert 'content="#EEE9E1"' in html
    assert "document.documentElement.dataset.theme" in html
    assert "document.documentElement.dataset.themePreference" in html
    assert favicon.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert png_dimensions(favicon) == (1024, 1024)


def test_drrepo_brand_assets_are_centralized_without_new_dependencies():
    header = Path("frontend/src/components/AuditConsoleHeader.tsx").read_text(encoding="utf-8")
    mark = Path("frontend/src/components/DrRepoMark.tsx").read_text(encoding="utf-8")
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    package = Path("frontend/package.json").read_text(encoding="utf-8")

    assert "function HeaderMark" not in header
    assert "DrRepoMark" in header
    assert "DrRepo</span>" in header
    assert "Repository Audit" in header
    assert "decorative = true" in mark
    assert "aria-hidden={decorative ? 'true' : undefined}" in mark
    assert "alt={decorative ? '' : title}" in mark
    assert "/brand/drrepo-favicon.png" in html
    assert "styled-components" not in package
    assert "lucide" not in package


def test_drrepo_brand_assets_use_supplied_pngs_without_generated_svgs():
    asset_paths = [
        Path("frontend/public/brand/drrepo-header-mark-compact.png"),
        Path("frontend/public/brand/drrepo-header-mark.png"),
        Path("frontend/public/brand/drrepo-mark.png"),
        Path("frontend/public/brand/drrepo-logo-horizontal.png"),
        Path("frontend/public/brand/drrepo-logo-stacked.png"),
        Path("frontend/public/brand/drrepo-favicon.png"),
    ]

    for path in asset_paths:
        assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

    assert not Path("frontend/public/brand/drrepo-mark.svg").exists()
    assert not Path("frontend/public/brand/drrepo-logo-horizontal.svg").exists()
    assert not Path("frontend/public/brand/drrepo-logo-stacked.svg").exists()
    assert png_dimensions(Path("frontend/public/brand/drrepo-header-mark-compact.png")) == (524, 524)
    assert Path("frontend/public/brand/drrepo-header-mark-compact.png").stat().st_size == 341213
    assert Path("frontend/public/brand/drrepo-mark.png").stat().st_size == 2171837
    assert Path("frontend/public/brand/drrepo-logo-horizontal.png").stat().st_size == 2134696
    assert Path("frontend/public/brand/drrepo-logo-stacked.png").stat().st_size == 1347937
    assert png_dimensions(Path("frontend/public/brand/drrepo-favicon.png")) == (1024, 1024)


def test_compact_header_and_favicon_do_not_use_full_detail_logo():
    mark = Path("frontend/src/components/DrRepoMark.tsx").read_text(encoding="utf-8")
    header = Path("frontend/src/components/AuditConsoleHeader.tsx").read_text(encoding="utf-8")

    assert 'src="/brand/drrepo-favicon.png"' in mark
    assert "drrepo-header-mark-light" not in mark
    assert "drrepo-header-mark-image-dark" not in mark
    assert "drrepo-header-mark-image-light" not in mark
    assert "h-11 w-11" in header
    assert "object-contain" in header
    assert "drrepo-logo-horizontal" not in header
    assert "drrepo-logo-stacked" not in header


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
    assert "visibleItems = items.slice(0, 2)" in recent
    assert "Show more rerun shortcuts" in recent


def test_result_navigation_exposes_four_accessible_views():
    navigation = Path("frontend/src/components/ResultNavigation.tsx").read_text(encoding="utf-8")

    for label in ("Summary", "Fix Plan", "Issues", "Technical Details"):
        assert f"label: '{label}'" in navigation
    assert 'role="tablist"' in navigation
    assert 'role="tab"' in navigation
    assert "aria-selected" in navigation
    assert "ArrowRight" in navigation
    assert "ArrowLeft" in navigation
    assert "bg-brand text-on-brand" in navigation
    assert "mb-3" in navigation
    assert "py-1.5" in navigation


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
    assert "Release and operational readiness" in technical_view
    assert "Project structure and risk areas" in technical_view
    assert "What DrRepo checked" in technical_view
    assert "Export and report" in technical_view
    assert "handleViewChange" in app
    assert "scrollIntoView" in app
    assert "runAudit" not in navigation
    assert "execute(" not in navigation


def test_new_audit_resets_result_view_to_overview():
    app = Path("frontend/src/App.tsx").read_text(encoding="utf-8")

    assert "if (state.status === 'loading' || state.status === 'done')" in app
    assert "setActiveResultView('summary')" in app


def test_overview_is_compact_and_links_to_deeper_sections():
    overview = Path("frontend/src/components/ResultOverview.tsx").read_text(encoding="utf-8")
    score = Path("frontend/src/components/ScoreCard.tsx").read_text(encoding="utf-8")

    assert "Recommended next move" in overview
    assert "Additional actions" in overview
    assert "Observed score based on limited evidence." in overview
    assert "Project identity" in overview
    assert "Open fix plan" in overview
    assert "Review issues" in overview
    assert "View technical details" in overview
    assert "Could not be verified" in overview
    assert "Category scores" not in overview
    assert "space-y-3" in overview
    assert "p-4 sm:p-5" in overview
    assert "text-xl font-semibold" in overview
    assert "text-4xl" in score


def test_issues_view_uses_priority_groups_and_keeps_raw_evidence_collapsed():
    findings = Path("frontend/src/components/FindingsList.tsx").read_text(encoding="utf-8")

    for label in ("must_fix", "important", "minor"):
        assert label in findings
    assert "Issue groups" in findings
    assert "must-fix issue group" in findings
    assert "minor technical finding" in findings
    assert "No important issues were found in the checks DrRepo could run." in findings
    assert "occurrence" in findings
    assert "affected file" in findings
    assert "More filters" in findings
    assert "Open minor technical evidence" in findings
    assert "Review grouped evidence" in findings


def test_technical_details_are_progressively_disclosed():
    app = Path("frontend/src/App.tsx").read_text(encoding="utf-8")
    technical_view = app[app.index("case 'technical_details':"):app.index("case 'summary':")]

    assert "releaseHasBlockers" in app
    assert "open={releaseHasBlockers || undefined}" in technical_view
    assert "open={!releaseHasBlockers || undefined}" in technical_view
    assert "Markdown preview" in technical_view
    assert "space-y-2.5" in technical_view
    assert "p-3.5" in technical_view


def test_fix_plan_keeps_one_canonical_order_and_ai_secondary():
    advisor = Path("frontend/src/components/AdvisorPanel.tsx").read_text(encoding="utf-8")
    css = Path("frontend/src/index.css").read_text(encoding="utf-8")

    assert "Canonical fix plan" in advisor
    assert "Deterministic recommendations, in the order DrRepo returned them." in advisor
    assert "First actions" in advisor
    assert "Show more actions" in advisor
    assert "Audit-environment limitations and improvements" in advisor
    assert "it does not replace the action order above" in advisor
    assert "Provider output was not accepted" in advisor
    assert "fix-plan-section rounded-xl border border-border bg-surface" in advisor
    assert "fix-plan-action-card" in advisor
    assert "fix-plan-action-card-primary" in advisor
    assert "bg-surface-2/35" not in advisor
    assert "inset 3px 0 0 rgb(var(--color-brand)" in css


def test_repository_scan_loader_is_mode_aware_and_accessible():
    loading = Path("frontend/src/components/LoadingState.tsx").read_text(encoding="utf-8")
    css = Path("frontend/src/index.css").read_text(encoding="utf-8")
    package = Path("frontend/package.json").read_text(encoding="utf-8")

    assert "diagnostic-drum" not in loading
    assert "repository-scan-indicator" in loading
    assert "repository-scan-ring" in loading
    assert "repository-scan-core" in loading
    assert "repository-scan-status" in loading
    assert "Reviewing repository evidence" in loading
    assert "Inspecting repository files without executing project code." in loading
    assert "Running configured checks for a local repository you trust." in loading
    assert "Running selected checks in an isolated environment." in loading
    assert "Keep this tab open while DrRepo finishes the review." in loading
    assert "Elapsed" in loading
    assert "STATUS_MESSAGES" in loading
    assert "Review in progress" in loading
    assert "Still checking available evidence" in loading
    assert "Preparing your results" in loading
    assert "3600" in loading
    assert "prefers-reduced-motion: reduce" in loading
    assert "setStatusIndex" in loading
    assert 'aria-live="polite"' in loading
    assert 'aria-hidden="true"' in loading
    assert "loading-status-dot" in loading
    assert "loading-status-text" in loading
    assert 'role="progressbar"' not in loading
    assert "Uploading" not in loading
    assert "Building" not in loading
    assert "0%" not in loading
    assert "diagnostic-drum" not in css
    assert "@keyframes scanRingRotate" in css
    assert "animation: scanRingRotate 2.1s linear infinite" in css
    assert "@keyframes loadingStatusFade" in css
    assert "@keyframes loadingStatusPulse" in css
    assert ".repository-scan-ring" in css
    assert "conic-gradient" in css
    assert "prefers-reduced-motion" in css
    assert "styled-components" not in package


def test_github_input_has_mobile_safe_paste_clear_without_auto_submit():
    card = Path("frontend/src/components/AuditInputCard.tsx").read_text(encoding="utf-8")

    assert "Paste URL" in card
    assert "Clear" in card
    assert "navigator.clipboard.readText" in card
    assert "Clipboard access is not available in this browser." in card
    assert "onClick={pasteGitHubUrl}" in card
    assert "handleSubmit" in card
    assert "pasteGitHubUrl" in card


def test_long_content_guards_and_readable_metadata_tokens_exist():
    css = Path("frontend/src/index.css").read_text(encoding="utf-8")
    card = Path("frontend/src/components/AuditInputCard.tsx").read_text(encoding="utf-8")
    loading = Path("frontend/src/components/LoadingState.tsx").read_text(encoding="utf-8")

    assert "overflow-wrap: anywhere" in css
    assert "break-anywhere" in card
    assert "break-anywhere" in loading
    assert "text-[10px]" not in card
