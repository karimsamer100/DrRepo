import type { RecentAudit } from '../lib/recentAudits'
import { labelForScore, scoreColor } from '../lib/score'

interface RecentAuditsProps {
  items: RecentAudit[]
  onSelect: (item: RecentAudit) => void
  onClear: () => void
}

function formatWhen(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

export function RecentAudits({ items, onSelect, onClear }: RecentAuditsProps) {
  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs font-medium text-muted">Recent on this device</h3>
        {items.length > 0 && (
          <button
            type="button"
            onClick={onClear}
            className="text-[11px] text-faint hover:text-error transition-colors duration-150"
          >
            Clear
          </button>
        )}
      </div>

      {items.length === 0 ? (
        <p className="text-sm text-faint">No recent audits.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item, index) => {
            const verdict = item.verdictLabel || labelForScore(item.overallScore)
            const scoreText =
              item.overallScore === null ? '—' : `${Math.round(item.overallScore)}`

            return (
              <li key={`${item.sourceType}-${item.sourceLabel}-${item.profile}-${index}`}>
                <button
                  type="button"
                  onClick={() => onSelect(item)}
                  className="w-full text-left rounded-lg border border-border bg-base p-3 transition-colors duration-150 hover:border-brand/30 hover:bg-surface-2 group"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="rounded-full border border-border bg-surface px-1.5 py-0.5 text-[10px] text-faint uppercase">
                          {item.sourceType === 'github_url' ? 'GitHub' : 'Local'}
                        </span>
                        <span className="truncate font-mono text-xs text-primary">
                          {item.sourceLabel}
                        </span>
                      </div>
                      <div className="mt-1 flex items-center gap-2">
                        <span className="rounded-full border border-border bg-surface px-1.5 py-0.5 text-[10px] text-faint">
                          {item.profile}
                        </span>
                        <span className="text-[10px] text-faint">
                          {formatWhen(item.createdAt)}
                        </span>
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      <div
                        className={`text-lg font-mono font-semibold leading-none ${scoreColor(
                          item.overallScore
                        )}`}
                      >
                        {scoreText}
                      </div>
                      <div className="mt-1 text-[10px] text-faint capitalize">
                        {verdict}
                      </div>
                    </div>
                  </div>
                </button>
              </li>
            )
          })}
        </ul>
      )}

      <p className="mt-4 text-[10px] text-faint/70 leading-relaxed">
        Stored locally in your browser. Select an item to pre-fill the form and
        run it again.
      </p>
    </div>
  )
}
