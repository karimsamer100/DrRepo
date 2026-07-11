import { labelForScore, scoreColor } from '../lib/score'

interface StatusBadgeProps {
  label?: string
  score?: number | null
}

export function StatusBadge({ label, score }: StatusBadgeProps) {
  const text = (label || labelForScore(score)).replace(/_/g, ' ')
  const colorClass = scoreColor(score)

  let border = 'border-border bg-surface-2 text-muted'
  if (text === 'healthy') border = 'border-health/30 bg-health/10 text-health'
  else if (text === 'needs attention')
    border = 'border-attention/30 bg-attention/10 text-attention'
  else if (text === 'needs improvement')
    border = 'border-warning/30 bg-warning/10 text-warning'
  else if (text === 'needs major improvement')
    border = 'border-error/30 bg-error/10 text-error'

  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${border} ${colorClass}`}>
      {text}
    </span>
  )
}
