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
  const recommendations = data.audit.recommendations_v2 || []
  const supportingActions = recommendations.slice(1, 3)
  const nextMove = executive?.recommended_next_move
  const unassessed = scoring?.unassessed_categories || diagnosis?.repository_health?.unassessed_categories || []
  const analyzerResults = [
    ...(data.audit.static_analysis || []),
    ...(data.audit.test_analysis || []),
    ...(data.audit.repository_analysis || []),
  ]
  const completedAnalyzers = analyzerResults.filter((result) => result.status === 'completed').length
  const limitedAnalyzers = analyzerResults.length - completedAnalyzers
  const claim =
    diagnosis?.repository_health?.claim ||
    executive?.readiness_claim ||
    executive?.headline ||
    formatVerdict(diagnosis?.repository_health?.label)

  return (
    <section className="space-y-5" aria-label="Audit summary">
      <div className="surface-raised overflow-hidden rounded-2xl">
        <div className="grid gap-5 p-5 sm:p-6 lg:grid-cols-[1fr_240px]">
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

            <h2 className="text-2xl font-semibold tracking-tight text-primary">{claim}</h2>
            <p className="mt-2 break-all font-mono text-xs text-faint">
              {compactSource(data.source_value)}
            </p>
            {(diagnosis?.repository_health?.summary || executive?.one_sentence_summary) && (
              <p className="mt-4 max-w-2xl text-sm leading-6 text-muted">
                {diagnosis?.repository_health?.summary || executive?.one_sentence_summary}
              </p>
            )}

            {hardFlags.length > 0 ? (
              <div className="mt-5 rounded-xl border border-error/30 bg-error/5 p-4">
                <div className="text-xs font-medium text-error">Confirmed blockers</div>
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
                No confirmed hard blockers reported.
              </div>
            )}
          </div>

          <ScoreCard
            title="Observed score"
            score={scoring?.observed_score ?? scoring?.overall_score}
            label={diagnosis?.repository_health?.label}
            subtitle={evidenceLabel !== 'full' ? 'Unavailable checks were not assumed clean.' : 'Based on assessed audit evidence.'}
            size="hero"
            evidenceLabel={evidenceLabel}
            assessedWeightRatio={scoring?.assessed_weight_ratio ?? diagnosis?.repository_health?.assessed_weight_ratio}
            unassessedCount={unassessed.length}
          />
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.25fr)_minmax(260px,0.75fr)]">
        <div className="rounded-2xl border border-border bg-surface p-4 sm:p-5">
          <h3 className="text-sm font-semibold text-primary">Recommended next move</h3>
          {nextMove ? (
            <div className="mt-4 rounded-xl border border-brand/25 bg-brand/5 p-3">
              <div className="text-sm font-semibold text-primary">{nextMove.title}</div>
              {nextMove.reason && <p className="mt-2 text-sm leading-6 text-muted">{nextMove.reason}</p>}
              {nextMove.first_step && <p className="mt-3 text-sm leading-6 text-primary">{nextMove.first_step}</p>}
              {nextMove.success_check && (
                <p className="mt-2 text-xs leading-5 text-faint">Success check: {nextMove.success_check}</p>
              )}
            </div>
          ) : (
            <p className="mt-3 text-sm leading-6 text-muted">Review the fix plan and evidence limitations.</p>
          )}
          {supportingActions.length > 0 && (
            <ol className="mt-4 space-y-2">
              {supportingActions.map((action) => (
                <li key={action.id || action.title} className="text-sm leading-6 text-muted">
                  <span className="font-medium text-primary">{action.title}</span>
                  {action.why_it_matters ? ` - ${action.why_it_matters}` : ''}
                </li>
              ))}
            </ol>
          )}
          <div className="mt-4 flex flex-wrap gap-2">
            <SummaryLink label="Open full fix plan" view="fix_plan" onNavigate={onNavigate} />
            <SummaryLink label="Review issues" view="issues" onNavigate={onNavigate} />
            <SummaryLink label="View technical details" view="technical_details" onNavigate={onNavigate} />
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-surface p-4 sm:p-5">
          <h3 className="text-sm font-semibold text-primary">Project identity</h3>
          <p className="mt-3 text-sm leading-6 text-muted">
            {identity?.project_type || 'Project type not identified'}
            {identity?.primary_language ? ` - ${identity.primary_language}` : ''}
            {identity?.architecture_type ? ` - ${identity.architecture_type}` : ''}
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

      {unassessed.length > 0 && (
        <div className="rounded-2xl border border-warning/25 bg-warning/5 p-4">
          <h3 className="text-sm font-semibold text-warning">Could not be verified</h3>
          <p className="mt-2 text-sm leading-6 text-muted">
            {unassessed.slice(0, 5).join(', ')} were not assessed and were not counted as clean evidence.
          </p>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-border bg-surface p-4">
          <h3 className="text-sm font-semibold text-primary">What DrRepo checked</h3>
          <p className="mt-2 text-sm text-muted">
            <span className="font-mono text-primary">{completedAnalyzers}</span> of{' '}
            <span className="font-mono text-primary">{analyzerResults.length}</span> analyzers completed.
          </p>
          <p className="mt-1 text-xs text-faint">{limitedAnalyzers} skipped, partial, unavailable, or failed.</p>
        </div>
        <div className="rounded-2xl border border-border bg-surface p-4">
          <h3 className="text-sm font-semibold text-primary">Fix plan</h3>
          <p className="mt-2 text-sm text-muted">
            {recommendations.length} canonical action{recommendations.length === 1 ? '' : 's'} ranked for {data.profile_id.replace(/_/g, ' ')}.
          </p>
        </div>
        <div className="rounded-2xl border border-border bg-surface p-4">
          <h3 className="text-sm font-semibold text-primary">Raw issues</h3>
          <p className="mt-2 text-sm text-muted">
            Findings are grouped separately so low-priority issues do not dominate the first action.
          </p>
        </div>
      </div>
    </section>
  )
}
