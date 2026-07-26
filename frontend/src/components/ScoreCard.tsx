import { labelForScore, scoreColor } from '../lib/score'

interface ScoreCardProps {
  title: string
  score?: number | null
  subtitle?: string
  label?: string
  size?: 'default' | 'hero'
  evidenceLabel?: string
  assessedWeightRatio?: number | null
  unassessedCount?: number
}

function displayLabel(label: string | undefined, score: number | null | undefined): string {
  return (label || labelForScore(score)).replace(/_/g, ' ')
}

export function ScoreCard({
  title,
  score,
  subtitle,
  label,
  size = 'default',
  evidenceLabel,
  assessedWeightRatio,
  unassessedCount = 0,
}: ScoreCardProps) {
  const display = score === null || score === undefined ? '-' : `${Math.round(score)}`
  const limited = evidenceLabel && evidenceLabel !== 'full'
  const coverage = typeof assessedWeightRatio === 'number' ? `${Math.round(assessedWeightRatio * 100)}% assessed` : null
  const summaryText = limited ? 'Observed score based on limited evidence.' : subtitle

  if (size === 'hero') {
    const verdict = displayLabel(label, score)
    return (
      <div className={`rounded-xl border bg-base p-3.5 ${limited ? 'border-warning/25' : 'border-border'}`}>
        <div className="mb-1.5 text-[12px] font-medium uppercase tracking-[0.12em] text-faint">
          {title}
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <span className={`font-mono text-4xl font-semibold leading-none tracking-tight ${scoreColor(score)}`}>
            {display}
          </span>
          <span className="mb-0.5 rounded-full border border-border bg-surface px-2 py-1 text-[12px] font-medium capitalize text-muted">
            {verdict}
          </span>
        </div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {evidenceLabel && (
            <span className="rounded-full border border-border bg-surface px-2 py-1 text-[12.5px] font-medium text-muted">
              Evidence: {evidenceLabel}
            </span>
          )}
          {coverage && (
            <span className="rounded-full border border-border bg-surface px-2 py-1 text-[12.5px] font-medium text-muted">
              {coverage}
            </span>
          )}
          {unassessedCount > 0 && (
            <span className="rounded-full border border-warning/25 bg-warning/5 px-2 py-1 text-[12.5px] font-medium text-warning">
              {unassessedCount} unverified
            </span>
          )}
        </div>
        {summaryText && <p className="mt-2 text-sm leading-5 text-muted">{summaryText}</p>}
      </div>
    )
  }

  return (
    <div className="rounded-2xl border border-border bg-surface p-4">
      <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-faint">
        {title}
      </div>
      <div className={`mt-2 font-mono text-3xl font-semibold ${scoreColor(score)}`}>{display}</div>
      {subtitle && <div className="mt-2 text-xs leading-5 text-muted">{subtitle}</div>}
    </div>
  )
}
