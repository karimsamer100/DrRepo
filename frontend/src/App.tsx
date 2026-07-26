import { useEffect, useRef, useState } from 'react'
import { AuditConsoleHeader } from './components/AuditConsoleHeader'
import { AuditInputCard } from './components/AuditInputCard'
import { LoadingState } from './components/LoadingState'
import { ResultOverview } from './components/ResultOverview'
import { AnalyzerStatusGrid } from './components/AnalyzerStatusGrid'
import { FindingsList } from './components/FindingsList'
import { AdvisorPanel } from './components/AdvisorPanel'
import { MarkdownPreview } from './components/MarkdownPreview'
import { MetadataCard } from './components/MetadataCard'
import { ExportActions } from './components/ExportActions'
import { DevOpsReadinessPanel } from './components/DevOpsReadinessPanel'
import { ArchitecturePanel } from './components/ArchitecturePanel'
import { ResultNavigation, type ResultView } from './components/ResultNavigation'
import { useAudit } from './state/useAudit'
import type { RecentAudit } from './lib/recentAudits'
import {
  addRecentAudit,
  clearRecentAudits,
  loadRecentAudits,
} from './lib/recentAudits'
import { classifyError } from './lib/presentation'
import { getFindingFamilies } from './lib/score'
import { getCapabilities } from './api/client'
import type { AuditResponse, CapabilitiesResponse } from './types/api'

export type ThemePreference = 'system' | 'light' | 'dark'
export type ResolvedTheme = 'light' | 'dark'

const THEME_STORAGE_KEY = 'drrepo.themePreference'

function themePreferenceFromStorage(): ThemePreference {
  if (typeof window === 'undefined') return 'system'
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY)
  return stored === 'light' || stored === 'dark' || stored === 'system' ? stored : 'system'
}

function resolveTheme(preference: ThemePreference): ResolvedTheme {
  if (preference !== 'system') return preference
  if (typeof window === 'undefined') return 'dark'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyDocumentTheme(preference: ThemePreference) {
  if (typeof document === 'undefined') return
  document.documentElement.dataset.themePreference = preference
  document.documentElement.dataset.theme = resolveTheme(preference)
}

function ResultLayout({
  data,
  activeView,
  onViewChange,
}: {
  data: AuditResponse
  activeView: ResultView
  onViewChange: (view: ResultView) => void
}) {
  const analyzerSections = {
    static_analysis: data.audit.static_analysis,
    test_analysis: data.audit.test_analysis,
    repository_analysis: data.audit.repository_analysis,
  }
  const findingCount = getFindingFamilies(data.audit).filter((family) => family.count > 0).length
  const actionCount = data.audit.recommendations_v2?.length || 0
  const releaseHasBlockers = (data.audit.devops_readiness?.blockers?.length || 0) > 0
  const resultTopRef = useRef<HTMLDivElement | null>(null)

  const handleViewChange = (view: ResultView) => {
    onViewChange(view)
    window.requestAnimationFrame(() => {
      resultTopRef.current?.scrollIntoView({ block: 'start', behavior: 'smooth' })
    })
  }

  const renderActiveView = () => {
    switch (activeView) {
      case 'fix_plan':
        return (
          <AdvisorPanel
            advisor={data.advisor}
            aiAdvisor={data.ai_advisor}
            profileId={data.profile_id}
            recommendations={data.audit.recommendations_v2}
          />
        )
      case 'issues':
        return <FindingsList audit={data.audit} />
      case 'technical_details':
        return (
          <div className="space-y-2.5">
            <details open={releaseHasBlockers || undefined} className="rounded-xl border border-border bg-surface p-3.5">
              <summary className="cursor-pointer text-sm font-semibold text-primary">
                Release and operational readiness
                {releaseHasBlockers && <span className="ml-2 text-sm font-medium text-error">blockers found</span>}
              </summary>
              <div className="mt-3">
                <DevOpsReadinessPanel readiness={data.audit.devops_readiness} />
              </div>
            </details>
            <details className="rounded-xl border border-border bg-surface p-3.5">
              <summary className="cursor-pointer text-sm font-semibold text-primary">Project structure and risk areas</summary>
              <div className="mt-3">
                <ArchitecturePanel assessment={data.audit.architecture_assessment} />
              </div>
            </details>
            <details open={!releaseHasBlockers || undefined} className="rounded-xl border border-border bg-surface p-3.5">
              <summary className="cursor-pointer text-sm font-semibold text-primary">What DrRepo checked</summary>
              <div className="mt-3 space-y-4">
                {data.audit.diagnosis?.evidence_confidence && (
                  <section className="rounded-xl border border-border bg-base p-3.5">
                    <h2 className="text-sm font-semibold text-primary">Evidence confidence</h2>
                    <p className="mt-1.5 text-sm leading-5 text-muted">
                      {data.audit.diagnosis.evidence_confidence.summary ||
                        `Confidence is ${data.audit.diagnosis.evidence_confidence.label || 'unknown'} based on completed and limited analyzers.`}
                    </p>
                  </section>
                )}
                <AnalyzerStatusGrid sections={analyzerSections} />
                <MetadataCard
                  metadata={data.audit.metadata}
                  dependencyEnvironment={data.audit.dependency_environment}
                  projectUnderstanding={data.audit.project_understanding}
                />
              </div>
            </details>
            <details className="rounded-xl border border-border bg-surface p-3.5">
              <summary className="cursor-pointer text-sm font-semibold text-primary">Export and report</summary>
              <div className="mt-3 space-y-3">
                <ExportActions data={data} />
                <details className="rounded-xl border border-border bg-base p-3">
                  <summary className="cursor-pointer text-sm font-semibold text-primary">Markdown preview</summary>
                  <div className="mt-3">
                    <MarkdownPreview content={data.markdown} />
                  </div>
                </details>
              </div>
            </details>
          </div>
        )
      case 'summary':
      default:
        return <ResultOverview data={data} onNavigate={handleViewChange} />
    }
  }

  return (
    <div className="pb-10">
      <div ref={resultTopRef} />
      <ResultNavigation
        activeView={activeView}
        onViewChange={handleViewChange}
        counts={{ fix_plan: actionCount, issues: findingCount }}
      />
      <div
        id={`result-panel-${activeView}`}
        role="tabpanel"
        aria-labelledby={`result-tab-${activeView}`}
        tabIndex={0}
        className="min-w-0 animate-fade-up"
      >
        {renderActiveView()}
      </div>
    </div>
  )
}

export default function App() {
  const { state, execute, reset } = useAudit()
  const [recentAudits, setRecentAudits] = useState<RecentAudit[]>([])
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse | null>(null)
  const [capabilityError, setCapabilityError] = useState<string | null>(null)
  const [activeResultView, setActiveResultView] = useState<ResultView>('summary')
  const [themePreference, setThemePreference] = useState<ThemePreference>(() => themePreferenceFromStorage())
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() => resolveTheme(themePreferenceFromStorage()))

  useEffect(() => {
    setRecentAudits(loadRecentAudits())
  }, [])

  useEffect(() => {
    applyDocumentTheme(themePreference)
    setResolvedTheme(resolveTheme(themePreference))
    window.localStorage.setItem(THEME_STORAGE_KEY, themePreference)

    if (themePreference !== 'system') return
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = () => {
      applyDocumentTheme('system')
      setResolvedTheme(resolveTheme('system'))
    }
    media.addEventListener('change', handleChange)
    return () => media.removeEventListener('change', handleChange)
  }, [themePreference])

  useEffect(() => {
    let cancelled = false
    getCapabilities()
      .then((data) => {
        if (!cancelled) {
          setCapabilities(data)
          setCapabilityError(null)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setCapabilityError(err instanceof Error ? err.message : 'Could not load capabilities')
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (state.status !== 'done' || !state.data) return

    const item: RecentAudit = {
      sourceType: state.data.source_type,
      sourceLabel: state.data.source_value,
      analysisMode: state.data.analysis_mode,
      profile: state.data.profile_id,
      createdAt: new Date().toISOString(),
      overallScore: state.data.audit.scoring?.overall_score ?? null,
      verdictLabel: state.data.audit.diagnosis?.repository_health?.label ?? null,
      evidenceLabel: state.data.audit.diagnosis?.evidence_confidence?.label ?? null,
      blockerCount: state.data.audit.diagnosis?.hard_flags?.length ?? 0,
    }

    setRecentAudits((current) => addRecentAudit(current, item))
  }, [state.status, state.data])

  useEffect(() => {
    if (state.status === 'loading' || state.status === 'done') {
      setActiveResultView('summary')
    }
  }, [state.status, state.data])

  const handleClearRecent = () => {
    setRecentAudits(clearRecentAudits())
  }

  const handleNewAudit = () => {
    reset()
    setActiveResultView('summary')
    window.requestAnimationFrame(() => {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    })
  }

  const handleRetry = () => {
    const request = state.lastRequest
    if (!request) return
    execute(
      request.source_type,
      request.source_value,
      request.analysis_mode || (request.source_type === 'github_url' ? 'quick_safe' : 'deep_local'),
      request.profile_id,
      request.ai,
      request.include_markdown,
      request.isolated_options || null
    )
  }

  const errorInfo = state.status === 'error' ? classifyError(state.error) : null

  return (
    <div className="flex min-h-dvh w-full flex-col bg-base text-primary antialiased">
      <a href="#main-content" className="skip-link">
        Skip to diagnostic
      </a>
      <div className="flex min-w-0 flex-1 flex-col">
        <AuditConsoleHeader
          onNew={handleNewAudit}
          themePreference={themePreference}
          resolvedTheme={resolvedTheme}
          onThemePreferenceChange={setThemePreference}
        />
        <main
          id="main-content"
          className="min-w-0 flex-1 px-4 py-4 sm:px-6 sm:py-5"
          aria-busy={state.status === 'loading'}
        >
          <div className="mx-auto max-w-[1220px]">
            {state.status === 'idle' && (
              <div className="py-0">
                <AuditInputCard
                  onSubmit={execute}
                  recentAudits={recentAudits}
                  onClearRecent={handleClearRecent}
                  capabilities={capabilities}
                  capabilityError={capabilityError}
                />
              </div>
            )}

            {state.status === 'loading' && (
              <div className="flex min-h-[60vh] items-center justify-center">
                <LoadingState request={state.lastRequest} />
              </div>
            )}

            {state.status === 'error' && errorInfo && (
              <div className="flex min-h-[60vh] flex-col items-center justify-center animate-fade-up">
                <div className="w-full max-w-2xl rounded-2xl border border-error/30 bg-error/5 p-5 sm:p-6" role="alert">
                  <div className="mb-3 inline-flex rounded-full border border-error/30 bg-error/10 px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.16em] text-error">
                    Audit stopped
                  </div>
                  <h1 className="text-xl font-semibold text-primary">{errorInfo.title}</h1>
                  <p className="mt-2 text-sm leading-6 text-muted">{errorInfo.summary}</p>
                  {errorInfo.detail && (
                    <details className="mt-4 rounded-xl border border-border bg-base p-3">
                      <summary className="cursor-pointer text-sm font-medium text-muted transition-colors hover:text-primary">
                        Technical error detail
                      </summary>
                      <pre className="mt-3 max-h-36 overflow-auto whitespace-pre-wrap break-anywhere font-mono text-[12.5px] leading-5 text-faint">
                        {errorInfo.detail}
                      </pre>
                    </details>
                  )}
                  <p className="mt-4 text-sm text-primary">{errorInfo.nextAction}</p>
                  <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                    {state.lastRequest && (
                      <button
                        type="button"
                        onClick={handleRetry}
                        className="inline-flex min-h-11 items-center justify-center rounded-xl bg-brand px-4 py-2 text-sm font-semibold text-on-brand transition-colors hover:bg-brand-hover"
                      >
                        Retry same diagnostic
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={reset}
                      className="inline-flex min-h-11 items-center justify-center rounded-xl border border-border px-4 py-2 text-sm font-medium text-primary transition-colors hover:border-brand/30 hover:text-brand"
                    >
                      Edit source
                    </button>
                  </div>
                </div>
              </div>
            )}

            {state.status === 'done' && state.data && (
              <>
                <div className="mb-3 border-b border-border pb-3">
                  <div className="text-[12px] font-medium uppercase tracking-[0.12em] text-faint">
                    Diagnostic result
                  </div>
                  <h1 className="mt-0.5 text-lg font-semibold tracking-tight text-primary">
                    Repository evidence review
                  </h1>
                  <p className="mt-0.5 break-anywhere font-mono text-[12.5px] leading-5 text-faint">
                    {state.data.source_value}
                  </p>
                </div>
                <ResultLayout
                  data={state.data}
                  activeView={activeResultView}
                  onViewChange={setActiveResultView}
                />
              </>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
