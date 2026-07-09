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
import { useAudit } from './state/useAudit'

export default function App() {
  const { state, execute, reset } = useAudit()

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

  return (
    <div className="flex h-screen w-full bg-base text-primary antialiased">
      <Sidebar onReset={reset} />
      <div className="flex flex-col flex-1 min-w-0">
        <AuditConsoleHeader onNew={state.status !== 'idle' ? reset : undefined} />
        <main className="flex-1 overflow-y-auto p-6">
          <div className="mx-auto max-w-6xl">
            {state.status === 'idle' && (
              <div className="flex items-center justify-center min-h-[60vh]">
                <AuditInputCard onSubmit={execute} />
              </div>
            )}

            {state.status === 'loading' && (
              <div className="flex items-center justify-center min-h-[60vh]">
                <LoadingState />
              </div>
            )}

            {state.status === 'error' && (
              <div className="flex flex-col items-center justify-center min-h-[60vh] animate-fade-up">
                <div className="w-full max-w-xl rounded-lg border border-error/30 bg-error/10 p-6 text-center">
                  <h2 className="text-sm font-semibold text-error mb-2">
                    Diagnostic failed
                  </h2>
                  <p className="text-sm text-primary mb-4">{state.error}</p>
                  <button
                    type="button"
                    onClick={reset}
                    className="rounded-md border border-error/30 bg-error/10 px-4 py-2 text-xs font-medium text-error hover:bg-error/20 transition-colors"
                  >
                    Try again
                  </button>
                </div>
              </div>
            )}

            {state.status === 'done' && state.data && (
              <>
                {/* Desktop two-column layout */}
                <div className="hidden lg:grid lg:grid-cols-3 lg:gap-6 pb-12">
                  <div className="col-span-2 space-y-6">
                    <ResultOverview data={state.data} />
                    <FindingsList audit={state.data.audit} />
                    <AdvisorPanel
                      advisor={state.data.advisor}
                      profileId={state.data.profile_id}
                    />
                  </div>
                  <div className="col-span-1 space-y-6">
                    <AnalyzerStatusGrid sections={analyzerSections} />
                    <MetadataCard metadata={metadata} />
                    <MarkdownPreview content={markdown} />
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
