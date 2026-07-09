import { scoreBgColor, scoreColor } from '../lib/score'

interface ScoreCardProps {
  title: string
  score?: number | null
  subtitle?: string
}

export function ScoreCard({ title, score, subtitle }: ScoreCardProps) {
  const display = score === null || score === undefined ? '—' : `${score}`
  return (
    <div className={`rounded-lg border p-3 ${scoreBgColor(score)}`}>
      <div className="text-[10px] font-semibold uppercase tracking-wider text-muted mb-1">
        {title}
      </div>
      <div className={`text-2xl font-mono font-semibold ${scoreColor(score)}`}>
        {display}
      </div>
      {subtitle && <div className="mt-1 text-[10px] text-faint">{subtitle}</div>}
    </div>
  )
}
