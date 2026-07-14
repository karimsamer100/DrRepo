import type { RecentAudit } from '../lib/recentAudits'
import { labelForScore, scoreColor } from '../lib/score'
import { shortSourceMode } from '../lib/presentation'

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
    <div className="rounded-2xl border border-border bg-surface p-5">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-xs font-medium uppercase tracking-[0.16em] text-faint">
            Rerun shortcuts
          </h3>
          <p className="mt-1 text-xs text-muted">Stored only in this browser.</p>
        </div>
        {items.length > 0 && (
          <button
            type="button"
            onClick={onClear}
            className="inline-flex min-h-8 items-center rounded-lg px-2 text-[11px] text-faint transition-colors duration-150 hover:text-error"
          >
            Clear
          </button>
        )}
      </div>

      {items.length === 0 ? (
        <p className="text-sm text-faint">No rerun shortcuts yet.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item, index) => {
            const verdict = item.verdictLabel || labelForScore(item.overallScore)
            const scoreText =
              item.overallScore === null ? '-' : `${Math.round(item.overallScore)}`

            return (
              <li key={`${item.sourceType}-${item.sourceLabel}-${item.profile}-${index}`}>
                <button
                  type="button"
                  onClick={() => onSelect(item)}
                  className="group w-full rounded-xl border border-border bg-base p-3 text-left transition-colors duration-150 hover:border-brand/30 hover:bg-surface-2"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex min-w-0 items-center gap-2">
                        <span className="rounded-full border border-border bg-surface px-1.5 py-0.5 text-[10px] text-faint uppercase">
                          {shortSourceMode(item.sourceType)}
                        </span>
                        <span className="truncate font-mono text-xs text-primary" title={item.sourceLabel}>
                          {item.sourceLabel}
                        </span>
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <span className="rounded-full border border-border bg-surface px-1.5 py-0.5 text-[10px] text-faint">
                          {item.profile}
                        </span>
                        {item.analysisMode && (
                          <span className="rounded-full border border-border bg-surface px-1.5 py-0.5 text-[10px] text-faint">
                            {item.analysisMode.replace(/_/g, ' ')}
                          </span>
                        )}
                        {item.evidenceLabel && (
                          <span className="rounded-full border border-border bg-surface px-1.5 py-0.5 text-[10px] text-faint">
                            {item.evidenceLabel} evidence
                          </span>
                        )}
                        {!!item.blockerCount && (
                          <span className="rounded-full border border-error/30 bg-error/10 px-1.5 py-0.5 text-[10px] text-error">
                            {item.blockerCount} blocker{item.blockerCount === 1 ? '' : 's'}
                          </span>
                        )}
                        <span className="text-[10px] text-faint">
                          {formatWhen(item.createdAt)}
                        </span>
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      <div className={`font-mono text-lg font-semibold leading-none ${scoreColor(item.overallScore)}`}>
                        {scoreText}
                      </div>
                      <div className="mt-1 text-[10px] capitalize text-faint">{verdict}</div>
                    </div>
                  </div>
                </button>
              </li>
            )
          })}
        </ul>
      )}

      <p className="mt-4 text-[10px] leading-relaxed text-faint/70">
        This is not cloud history. Selecting an item only pre-fills the launcher so you can rerun it.
      </p>
    </div>
  )
}
