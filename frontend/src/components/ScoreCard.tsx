import { labelForScore, scoreColor } from '../lib/score'

interface ScoreCardProps {
  title: string
  score?: number | null
  subtitle?: string
  label?: string
  size?: 'default' | 'hero'
}

function displayLabel(label: string | undefined, score: number | null | undefined): string {
  return (label || labelForScore(score)).replace(/_/g, ' ')
}

export function ScoreCard({ title, score, subtitle, label, size = 'default' }: ScoreCardProps) {
  const display = score === null || score === undefined ? '-' : `${Math.round(score)}`

  if (size === 'hero') {
    const verdict = displayLabel(label, score)
    return (
      <div className="rounded-2xl border border-border bg-base p-4">
        <div className="mb-2 text-[11px] font-medium uppercase tracking-[0.16em] text-faint">
          {title}
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <span className={`font-mono text-5xl font-semibold leading-none tracking-tight ${scoreColor(score)}`}>
            {display}
          </span>
          <span className="mb-1 rounded-full border border-border bg-surface px-2 py-1 text-[11px] font-medium capitalize text-muted">
            {verdict}
          </span>
        </div>
        {subtitle && <p className="mt-3 text-xs leading-5 text-muted">{subtitle}</p>}
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
