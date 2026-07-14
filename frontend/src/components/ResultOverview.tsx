import { useEffect, useState } from 'react'
import type { AuditResponse } from '../types/api'
import { ScoreCard } from './ScoreCard'
import { StatusBadge } from './StatusBadge'
import {
  attentionAreaFromFlag,
  getFindingFamilies,
  scoreColor,
} from '../lib/score'
import {
  categoryEvidenceState,
  compactSource,
  formatVerdict,
  shortSourceMode,
} from '../lib/presentation'

interface ResultOverviewProps {
  data: AuditResponse
}

function CategoryBar({
  label,
  score,
  evidence,
}: {
  label: string
  score: number
  evidence: string | null
}) {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduceMotion) {
      setMounted(true)
      return
    }
    const raf = requestAnimationFrame(() => setMounted(true))
    return () => cancelAnimationFrame(raf)
  }, [])

  return (
    <div className="py-2">
      <div className="mb-1 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs text-muted capitalize">{label}</div>
          {evidence && (
            <div className="mt-0.5 text-[10px] uppercase tracking-[0.14em] text-faint">
              {evidence}
            </div>
          )}
        </div>
        <div className={`shrink-0 text-right text-xs font-mono font-medium ${scoreColor(score)}`}>
          {score}
        </div>
      </div>
      <div
        className="h-1.5 overflow-hidden rounded-full bg-surface-2"
        role="progressbar"
        aria-label={`${label} observed score`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={score}
      >
        <div
          className={`h-full origin-left rounded-full transition-transform duration-500 ease-out-strong ${
            score >= 85 ? 'bg-health' : score >= 70 ? 'bg-attention' : score >= 50 ? 'bg-warning' : 'bg-error'
          }`}
          style={{ transform: `scaleX(${mounted ? score / 100 : 0})` }}
        />
      </div>
    </div>
  )
}

export function ResultOverview({ data }: ResultOverviewProps) {
  const scoring = data.audit.scoring
  const diagnosis = data.audit.diagnosis
  const executive = data.audit.executive_report
  const hardFlags = diagnosis?.hard_flags || []
  const evidenceConfidence = diagnosis?.evidence_confidence
  const evidenceLabel = evidenceConfidence?.label || 'unknown'
  const families = getFindingFamilies(data.audit)
  const issueFamilies = families.filter((f) => f.count > 0)
  const isHealthy = diagnosis?.repository_health?.label === 'healthy' && hardFlags.length === 0

  const categories = scoring?.categories || {}
  const categoryEntries = Object.entries(categories).filter(
    ([, score]) => typeof score === 'number'
  ) as [string, number][]

  const attentionAreas = Array.from(
    new Set([
      ...hardFlags.map(attentionAreaFromFlag),
      ...issueFamilies.map((f) => f.family),
    ])
  )

  const missingTools = evidenceConfidence?.missing_optional_tools || []
  const skippedTools = evidenceConfidence?.skipped_optional_tools || []

  return (
    <section className="space-y-5">
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
              {evidenceConfidence && (
                <span className="rounded-full border border-warning/30 bg-warning/10 px-2.5 py-1 text-[11px] font-medium text-warning">
                  Evidence: {evidenceLabel}
                </span>
              )}
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
            {executive?.next_best_step && (
              <div className="mt-4 rounded-xl border border-brand/25 bg-brand/5 p-3">
                <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-brand">
                  Next best step
                </div>
                <p className="mt-1 text-sm leading-6 text-primary">{executive.next_best_step}</p>
              </div>
            )}

            {hardFlags.length > 0 ? (
              <div className="mt-5 rounded-xl border border-error/30 bg-error/5 p-4">
                <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-error">
                  Blockers preventing a healthy verdict
                </div>
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
              <div className="mt-5 rounded-xl border border-health/25 bg-health/5 p-4">
                <div className="text-sm font-medium text-health">
                  {isHealthy ? 'No hard blockers detected.' : 'No hard blockers reported.'}
                </div>
                <p className="mt-1 text-xs leading-5 text-muted">
                  Verdict is based on observed evidence; confidence describes how complete that evidence was.
                </p>
              </div>
            )}
          </div>

          <div className="min-w-0">
            <ScoreCard
              title="Observed score"
              score={scoring?.overall_score}
              label={diagnosis?.repository_health?.label}
              subtitle="Quality of evidence DrRepo could verify."
              size="hero"
            />
          </div>
        </div>
      </div>

      {evidenceConfidence && evidenceConfidence.label !== 'full' && (
        <div className="rounded-2xl border border-warning/30 bg-warning/5 p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-warning">
                Evidence confidence: {evidenceLabel}
              </div>
              <p className="mt-2 text-sm leading-6 text-primary">{evidenceConfidence.summary}</p>
            </div>
            {(missingTools.length > 0 || skippedTools.length > 0) && (
              <div className="flex shrink-0 flex-wrap gap-2 sm:max-w-xs sm:justify-end">
                {missingTools.map((tool) => (
                  <span key={`missing-${tool}`} className="rounded-full border border-border bg-base px-2 py-1 text-[10px] font-mono text-faint">
                    {tool} unavailable
                  </span>
                ))}
                {skippedTools.map((tool) => (
                  <span key={`skipped-${tool}`} className="rounded-full border border-warning/30 bg-warning/10 px-2 py-1 text-[10px] font-mono text-warning">
                    {tool} skipped
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {attentionAreas.length > 0 && (
        <div className="rounded-2xl border border-border bg-surface p-4">
          <div className="mb-3 text-[11px] font-medium uppercase tracking-[0.16em] text-faint">
            Attention map
          </div>
          <div className="flex flex-wrap gap-2">
            {attentionAreas.map((area) => (
              <span
                key={area}
                className="rounded-full border border-border bg-base px-2.5 py-1 text-[11px] font-medium text-muted"
              >
                {area}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <ScoreCard
          title="Repository health"
          score={scoring?.repository_health_score}
          subtitle="Code, tests, security, and maintainability."
        />
        <ScoreCard
          title="Portfolio readiness"
          score={scoring?.portfolio_readiness_score}
          subtitle="Documentation, structure, reproducibility, and presentation."
        />
      </div>

      {categoryEntries.length > 0 && (
        <div className="rounded-2xl border border-border bg-surface p-4">
          <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
            <h3 className="text-xs font-medium uppercase tracking-[0.16em] text-faint">
              Category scores
            </h3>
            <p className="text-xs text-muted">Observed scores, paired with evidence status.</p>
          </div>
          <div className="divide-y divide-border/50">
            {categoryEntries.map(([key, score]) => (
              <CategoryBar
                key={key}
                label={key.replace(/_/g, ' ')}
                score={score}
                evidence={categoryEvidenceState(key, data)}
              />
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
