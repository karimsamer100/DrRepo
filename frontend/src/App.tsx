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

export default function App() {
  const { state, execute, reset } = useAudit()
  const [recentAudits, setRecentAudits] = useState<RecentAudit[]>([])

  useEffect(() => {
    setRecentAudits(loadRecentAudits())
  }, [])

  useEffect(() => {
    if (state.status !== 'done' || !state.data) return

    const item: RecentAudit = {
      sourceLabel: state.data.source_value,
      profile: state.data.profile_id,
      createdAt: new Date().toISOString(),
      overallScore: state.data.audit.scoring?.overall_score ?? null,
      verdictLabel: state.data.audit.diagnosis?.repository_health?.label ?? null,
    }

    setRecentAudits((current) => addRecentAudit(current, item))
  }, [state.status, state.data])

  const analyzerSections =
    state.status === 'done' && state.data
      ? {
          static_analysis: state.data.audit.static_analysis,
          test_analysis: state.data.audit.test_analysis,
          repository_analysis: state.data.audit.repository_analysis,
        }
      : undefined

  const metadata = state.status === 'done' && state.data ? state.data.audit.metadata : undefined
  const markdown = state.status === 'done' && state.data ? state.data.markdown : null

  const handleClearRecent = () => {
    setRecentAudits(clearRecentAudits())
  }

  return (
    <div className="flex h-screen w-full bg-base text-primary antialiased">
      <Sidebar onReset={reset} />
      <div className="flex flex-col flex-1 min-w-0">
        <AuditConsoleHeader onNew={state.status !== 'idle' ? reset : undefined} />
        <main className="flex-1 overflow-y-auto p-6">
          <div className="mx-auto max-w-6xl">
            {state.status === 'idle' && (
              <div className="flex items-center justify-center min-h-[60vh]">
                <AuditInputCard
                  onSubmit={execute}
                  recentAudits={recentAudits}
                  onClearRecent={handleClearRecent}
                />
              </div>
            )}

            {state.status === 'loading' && (
              <div className="flex items-center justify-center min-h-[60vh]">
                <LoadingState />
              </div>
            )}

            {state.status === 'error' && (
              <div className="flex flex-col items-center justify-center min-h-[60vh] animate-fade-up">
                <div className="w-full max-w-xl rounded-xl border border-error/30 bg-error/5 p-6 text-center">
                  <h2 className="text-sm font-semibold text-error mb-2">
                    Diagnostic failed
                  </h2>
                  <p className="text-sm text-primary mb-4">{state.error}</p>
                  <button
                    type="button"
                    onClick={reset}
                    className="rounded-md border border-error/30 px-4 py-2 text-xs font-medium text-error hover:bg-error/10 transition-colors duration-150 ease-out-strong"
                  >
                    Try again
                  </button>
                </div>
              </div>
            )}

            {state.status === 'done' && state.data && (
              <>
                <div className="mb-6 pb-4 border-b border-border">
                  <h1 className="text-xl font-semibold text-primary tracking-tight">Diagnostic result</h1>
                  <p className="text-xs text-faint mt-1 font-mono">{state.data.source_value}</p>
                </div>

                {/* Desktop two-column layout */}
                <div className="hidden lg:grid lg:grid-cols-3 lg:gap-8 pb-12">
                  <div className="col-span-2 space-y-6">
                    <ResultOverview data={state.data} />
                    <FindingsList audit={state.data.audit} />
                    <AdvisorPanel
                      advisor={state.data.advisor}
                      profileId={state.data.profile_id}
                    />
                  </div>
                  <div className="col-span-1">
                    <div className="lg:sticky lg:top-6 space-y-6">
                      <ExportActions data={state.data} />
                      <AnalyzerStatusGrid sections={analyzerSections} />
                      <MetadataCard metadata={metadata} />
                      <MarkdownPreview content={markdown} />
                    </div>
                  </div>
                </div>

                {/* Mobile single-column layout */}
                <div className="lg:hidden space-y-6 pb-12">
                  <ResultOverview data={state.data} />
                  <FindingsList audit={state.data.audit} />
                  <AdvisorPanel
                    advisor={state.data.advisor}
                    profileId={state.data.profile_id}
                  />
                  <ExportActions data={state.data} />
                  <AnalyzerStatusGrid sections={analyzerSections} />
                  <MetadataCard metadata={metadata} />
                  <MarkdownPreview content={markdown} />
                </div>
              </>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
