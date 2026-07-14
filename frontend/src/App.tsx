import { useEffect, useState } from 'react'
import { AuditConsoleHeader } from './components/AuditConsoleHeader'
import { Sidebar } from './components/Sidebar'
import { AuditInputCard } from './components/AuditInputCard'
import { LoadingState } from './components/LoadingState'
import { ResultOverview } from './components/ResultOverview'
import { AnalyzerStatusGrid } from './components/AnalyzerStatusGrid'
import { FindingsList } from './components/FindingsList'
import { AdvisorPanel } from './components/AdvisorPanel'
import { MarkdownPreview } from './components/MarkdownPreview'
import { MetadataCard } from './components/MetadataCard'
import { ExportActions } from './components/ExportActions'
import { useAudit } from './state/useAudit'
import type { RecentAudit } from './lib/recentAudits'
import {
  addRecentAudit,
  clearRecentAudits,
  loadRecentAudits,
} from './lib/recentAudits'
import { classifyError } from './lib/presentation'
import { getCapabilities } from './api/client'
import type { AuditResponse, CapabilitiesResponse } from './types/api'

function ResultLayout({ data }: { data: AuditResponse }) {
  const analyzerSections = {
    static_analysis: data.audit.static_analysis,
    test_analysis: data.audit.test_analysis,
    repository_analysis: data.audit.repository_analysis,
  }

  return (
    <div className="grid gap-6 pb-12 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-start">
      <div className="min-w-0 space-y-6">
        <ResultOverview data={data} />
        <FindingsList audit={data.audit} />
        <AdvisorPanel
          advisor={data.advisor}
          profileId={data.profile_id}
          recommendations={data.audit.recommendations_v2}
        />
      </div>
      <aside className="min-w-0 space-y-5 lg:sticky lg:top-6">
        <AnalyzerStatusGrid sections={analyzerSections} />
        <MetadataCard
          metadata={data.audit.metadata}
          dependencyEnvironment={data.audit.dependency_environment}
          projectUnderstanding={data.audit.project_understanding}
        />
        <ExportActions data={data} />
        <MarkdownPreview content={data.markdown} />
      </aside>
    </div>
  )
}

export default function App() {
  const { state, execute, reset } = useAudit()
  const [recentAudits, setRecentAudits] = useState<RecentAudit[]>([])
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse | null>(null)
  const [capabilityError, setCapabilityError] = useState<string | null>(null)

  useEffect(() => {
    setRecentAudits(loadRecentAudits())
  }, [])

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

  const handleClearRecent = () => {
    setRecentAudits(clearRecentAudits())
  }

  const handleRetry = () => {
    const request = state.lastRequest
    if (!request) return
    execute(
      request.source_type,
      request.source_value,
      request.analysis_mode || (request.source_type === 'github_url' ? 'quick_safe' : 'deep_local'),
      request.profile_id,
      request.include_markdown
    )
  }

  const errorInfo = state.status === 'error' ? classifyError(state.error) : null

  return (
    <div className="flex h-dvh w-full flex-col bg-base text-primary antialiased sm:flex-row">
      <a href="#main-content" className="skip-link">
        Skip to diagnostic
      </a>
      <Sidebar onReset={reset} />
      <div className="flex min-w-0 flex-1 flex-col">
        <AuditConsoleHeader onNew={state.status !== 'idle' ? reset : undefined} />
        <main
          id="main-content"
          className="flex-1 overflow-y-auto px-4 py-5 sm:p-6"
          aria-busy={state.status === 'loading'}
        >
          <div className="mx-auto max-w-6xl">
            {state.status === 'idle' && (
              <div className="flex min-h-[calc(100dvh-9rem)] items-center justify-center sm:min-h-[60vh]">
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
              <div className="flex min-h-[calc(100dvh-9rem)] items-center justify-center sm:min-h-[60vh]">
                <LoadingState request={state.lastRequest} />
              </div>
            )}

            {state.status === 'error' && errorInfo && (
              <div className="flex min-h-[calc(100dvh-9rem)] flex-col items-center justify-center sm:min-h-[60vh] animate-fade-up">
                <div className="w-full max-w-2xl rounded-2xl border border-error/30 bg-error/5 p-5 sm:p-6" role="alert">
                  <div className="mb-3 inline-flex rounded-full border border-error/30 bg-error/10 px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.16em] text-error">
                    Audit stopped
                  </div>
                  <h1 className="text-xl font-semibold text-primary">{errorInfo.title}</h1>
                  <p className="mt-2 text-sm leading-6 text-muted">{errorInfo.summary}</p>
                  {errorInfo.detail && (
                    <pre className="mt-4 max-h-36 overflow-auto whitespace-pre-wrap break-words rounded-xl border border-border bg-base p-3 font-mono text-xs leading-5 text-faint">
                      {errorInfo.detail}
                    </pre>
                  )}
                  <p className="mt-4 text-sm text-primary">{errorInfo.nextAction}</p>
                  <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                    {state.lastRequest && (
                      <button
                        type="button"
                        onClick={handleRetry}
                        className="inline-flex min-h-11 items-center justify-center rounded-xl bg-brand px-4 py-2 text-sm font-semibold text-base transition-colors hover:bg-brand-hover"
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
                <div className="mb-6 border-b border-border pb-4">
                  <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-faint">
                    Diagnostic result
                  </div>
                  <h1 className="mt-1 text-xl font-semibold tracking-tight text-primary">
                    Repository evidence review
                  </h1>
                  <p className="mt-1 break-all font-mono text-xs text-faint">
                    {state.data.source_value}
                  </p>
                </div>
                <ResultLayout data={state.data} />
              </>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
