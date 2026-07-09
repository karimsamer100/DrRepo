import { labelForScore, scoreBgColor, scoreColor } from '../lib/score'

interface ScoreCardProps {
  title: string
  score?: number | null
  subtitle?: string
  size?: 'default' | 'hero'
}

export function ScoreCard({ title, score, subtitle, size = 'default' }: ScoreCardProps) {
  if (size === 'hero') {
    const display = score === null || score === undefined ? '—' : `${Math.round(score)}`
    return (
      <div className="rounded-lg border border-border bg-surface-2 p-5">
        <div className="text-[11px] font-medium uppercase tracking-wider text-faint mb-2">
          {title}
        </div>
        <div className="flex flex-col sm:flex-row sm:items-end gap-4">
          <div className="flex items-baseline gap-3">
            <span className={`text-5xl font-bold tracking-tight ${scoreColor(score)}`}>
              {display}
            </span>
            <span
              className={`text-sm font-semibold px-2 py-0.5 rounded border ${scoreBgColor(score)} ${scoreColor(score)}`}
            >
              {labelForScore(score)}
            </span>
          </div>
          {subtitle && (
            <p className="text-sm text-muted leading-relaxed sm:max-w-xl">{subtitle}</p>
          )}
        </div>
      </div>
    )
  }

  const display = score === null || score === undefined ? '—' : `${score}`
  return (
    <div className={`rounded-lg border p-3 ${scoreBgColor(score)}`}>
      <div className="text-[11px] font-medium uppercase tracking-wider text-faint mb-1">
        {title}
      </div>
      <div className={`text-2xl font-mono font-semibold ${scoreColor(score)}`}>{display}</div>
      {subtitle && <div className="mt-1 text-[10px] text-faint">{subtitle}</div>}
    </div>
  )
}
