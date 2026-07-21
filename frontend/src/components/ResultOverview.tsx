import type { AuditResponse } from '../types/api'
import type { ResultView } from './ResultNavigation'
import { ScoreCard } from './ScoreCard'
import { StatusBadge } from './StatusBadge'
import { attentionAreaFromFlag } from '../lib/score'
import { compactSource, formatVerdict, shortSourceMode } from '../lib/presentation'

interface ResultOverviewProps {
  data: AuditResponse
  onNavigate: (view: ResultView) => void
}

function SummaryLink({
  label,
  view,
  onNavigate,
}: {
  label: string
  view: ResultView
  onNavigate: (view: ResultView) => void
}) {
  return (
    <button
      type="button"
      onClick={() => onNavigate(view)}
      className="inline-flex min-h-10 items-center justify-center rounded-lg border border-border px-3 text-xs font-medium text-muted transition-colors hover:border-brand/30 hover:text-brand"
    >
      {label}
    </button>
  )
}

export function ResultOverview({ data, onNavigate }: ResultOverviewProps) {
  const scoring = data.audit.scoring
  const diagnosis = data.audit.diagnosis
  const executive = data.audit.executive_report
  const identity = data.audit.project_understanding?.project_identity
  const hardFlags = diagnosis?.hard_flags || []
  const evidenceConfidence = diagnosis?.evidence_confidence
  const evidenceLabel = evidenceConfidence?.label || 'unknown'
  const recommendations = (data.audit.recommendations_v2 || []).slice(0, 3)
  const readiness = data.audit.devops_readiness
  const architecture = data.audit.architecture_assessment
  const analyzerResults = [
    ...(data.audit.static_analysis || []),
    ...(data.audit.test_analysis || []),
    ...(data.audit.repository_analysis || []),
  ]
  const completedAnalyzers = analyzerResults.filter((result) => result.status === 'completed').length
  const limitedAnalyzers = analyzerResults.length - completedAnalyzers
  const topHotspot = architecture?.hotspots?.[0]
  const strongestSignal = executive?.strongest_signals?.[0]

  return (
    <section className="space-y-5" aria-label="Audit overview">
      <div className="surface-raised overflow-hidden rounded-2xl">
        <div className="grid gap-5 p-5 sm:p-6 lg:grid-cols-[1fr_220px]">
          <div className="min-w-0">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-border bg-base px-2.5 py-1 text-[11px] font-medium text-faint">
                {shortSourceMode(data.source_type)}
              </span>
              <span className="rounded-full border border-border bg-base px-2.5 py-1 text-[11px] font-medium text-faint">
                {(data.audit.analysis?.mode || data.analysis_mode).replace(/_/g, ' ')}
              </span>
              {diagnosis?.repository_health && (
                <StatusBadge
                  label={diagnosis.repository_health.label}
                  score={diagnosis.repository_health.score ?? undefined}
                />
              )}
              <span className="rounded-full border border-warning/30 bg-warning/10 px-2.5 py-1 text-[11px] font-medium text-warning">
                Evidence: {evidenceLabel}
              </span>
            </div>

            <h2 className="text-2xl font-semibold tracking-tight text-primary">
              {executive?.headline || formatVerdict(diagnosis?.repository_health?.label)}
            </h2>
            <p className="mt-2 break-all font-mono text-xs text-faint">
              {compactSource(data.source_value)}
            </p>
            {(executive?.one_sentence_summary || diagnosis?.repository_health?.summary) && (
              <p className="mt-4 max-w-2xl text-sm leading-6 text-muted">
                {executive?.one_sentence_summary || diagnosis?.repository_health?.summary}
              </p>
            )}

            {hardFlags.length > 0 ? (
              <div className="mt-5 rounded-xl border border-error/30 bg-error/5 p-4">
                <div className="text-xs font-medium text-error">Hard blockers</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {hardFlags.map((flag) => (
                    <span
                      key={flag}
                      className="rounded-full border border-error/30 bg-error/10 px-2.5 py-1 text-[11px] font-medium text-error"
                    >
                      {attentionAreaFromFlag(flag)}
                    </span>
                  ))}
                </div>
              </div>
            ) : (
              <div className="mt-5 rounded-xl border border-health/25 bg-health/5 p-3 text-sm font-medium text-health">
                No hard blockers reported.
              </div>
            )}
          </div>

          <ScoreCard
            title="Observed score"
            score={scoring?.overall_score}
            label={diagnosis?.repository_health?.label}
            subtitle="Quality of evidence DrRepo could verify."
            size="hero"
          />
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.25fr)_minmax(260px,0.75fr)]">
        <div className="rounded-2xl border border-border bg-surface p-4 sm:p-5">
          <h3 className="text-sm font-semibold text-primary">What matters first</h3>
          <div className="mt-4 space-y-3">
            {strongestSignal && (
              <div>
                <div className="text-xs font-medium text-faint">Strongest signal</div>
                <p className="mt-1 text-sm leading-6 text-muted">{strongestSignal}</p>
              </div>
            )}
            {executive?.biggest_gap && (
              <div>
                <div className="text-xs font-medium text-faint">Biggest gap</div>
                <p className="mt-1 text-sm leading-6 text-muted">{executive.biggest_gap}</p>
              </div>
            )}
            {executive?.next_best_step && (
              <div className="rounded-xl border border-brand/25 bg-brand/5 p-3">
                <div className="text-xs font-medium text-brand">Next best step</div>
                <p className="mt-1 text-sm leading-6 text-primary">{executive.next_best_step}</p>
              </div>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-surface p-4 sm:p-5">
          <h3 className="text-sm font-semibold text-primary">Project identity</h3>
          <p className="mt-3 text-sm leading-6 text-muted">
            {identity?.project_type || 'Project type not identified'}
            {identity?.primary_language ? ` · ${identity.primary_language}` : ''}
            {identity?.architecture_type ? ` · ${identity.architecture_type}` : ''}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {[...(identity?.frameworks || []), ...(identity?.interfaces || [])].slice(0, 6).map((item) => (
              <span key={item} className="rounded-full border border-border bg-base px-2 py-1 text-[10px] text-faint">
                {item}
              </span>
            ))}
          </div>
          <p className="mt-3 text-xs text-faint">Identity confidence: {identity?.confidence || 'unknown'}</p>
        </div>
      </div>

      <div className="rounded-2xl border border-border bg-surface p-4 sm:p-5">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h3 className="text-sm font-semibold text-primary">Top recommended actions</h3>
            <p className="mt-1 text-xs text-muted">The first three deterministic priorities from this audit.</p>
          </div>
          <SummaryLink label="View full action plan" view="actions" onNavigate={onNavigate} />
        </div>
        {recommendations.length > 0 ? (
          <ol className="mt-4 divide-y divide-border/60">
            {recommendations.map((recommendation, index) => (
              <li key={recommendation.id || recommendation.title || index} className="flex gap-3 py-3 first:pt-0 last:pb-0">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-border bg-base font-mono text-[10px] text-brand">
                  {index + 1}
                </span>
                <div className="min-w-0">
                  <div className="text-sm font-medium text-primary">{recommendation.title || 'Recommended action'}</div>
                  {recommendation.why_it_matters && (
                    <p className="mt-1 text-xs leading-5 text-muted">{recommendation.why_it_matters}</p>
                  )}
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <p className="mt-4 text-sm text-muted">No structured recommendations were returned.</p>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-border bg-surface p-4">
          <h3 className="text-sm font-semibold text-primary">Evidence coverage</h3>
          <p className="mt-2 text-sm text-muted">
            <span className="font-mono text-primary">{completedAnalyzers}</span> of{' '}
            <span className="font-mono text-primary">{analyzerResults.length}</span> analyzers completed.
          </p>
          <p className="mt-1 text-xs text-faint">{limitedAnalyzers} skipped, partial, unavailable, or failed.</p>
          <div className="mt-3">
            <SummaryLink label="Inspect evidence" view="evidence" onNavigate={onNavigate} />
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-surface p-4">
          <h3 className="text-sm font-semibold text-primary">DevOps readiness</h3>
          {readiness && readiness.applicability !== 'not_applicable' ? (
            <>
              <p className="mt-2 text-sm text-muted">
                {readiness.verdict?.replace(/_/g, ' ') || 'Unknown'} ·{' '}
                <span className="font-mono text-primary">{readiness.observed_score ?? 'not scored'}</span>
              </p>
              <p className="mt-1 text-xs text-faint">{readiness.blockers?.length || 0} release blockers</p>
            </>
          ) : (
            <p className="mt-2 text-sm text-muted">Not applicable to this project.</p>
          )}
          <div className="mt-3">
            <SummaryLink label="Open DevOps" view="devops" onNavigate={onNavigate} />
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-surface p-4">
          <h3 className="text-sm font-semibold text-primary">Architecture</h3>
          {architecture ? (
            <>
              <p className="mt-2 text-sm text-muted">
                {architecture.layers?.length || 0} layers · {architecture.cycles?.length || 0} cycles
              </p>
              <p className="mt-1 truncate text-xs text-faint">
                {topHotspot ? `Top hotspot: ${topHotspot.path}` : 'No ranked hotspots returned.'}
              </p>
            </>
          ) : (
            <p className="mt-2 text-sm text-muted">Architecture evidence unavailable.</p>
          )}
          <div className="mt-3">
            <SummaryLink label="Open architecture" view="architecture" onNavigate={onNavigate} />
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <SummaryLink label="Review findings" view="findings" onNavigate={onNavigate} />
        <SummaryLink label="Inspect evidence" view="evidence" onNavigate={onNavigate} />
      </div>
    </section>
  )
}
