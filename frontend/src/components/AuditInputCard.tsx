import { useEffect, useState, type FormEvent } from 'react'
import type { ProfileInfo } from '../types/api'
import { listProfiles } from '../api/client'

interface AuditInputCardProps {
  onSubmit: (sourceValue: string, profileId: string, includeMarkdown: boolean) => void
  disabled?: boolean
}

export function AuditInputCard({ onSubmit, disabled }: AuditInputCardProps) {
  const [profiles, setProfiles] = useState<ProfileInfo[]>([])
  const [sourceValue, setSourceValue] = useState('')
  const [profileId, setProfileId] = useState('student_portfolio')
  const [includeMarkdown, setIncludeMarkdown] = useState(false)
  const [profilesError, setProfilesError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    listProfiles()
      .then((data) => {
        if (!cancelled) {
          setProfiles(data)
          if (data.length > 0 && !data.some((p) => p.profile_id === profileId)) {
            setProfileId(data[0].profile_id)
          }
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setProfilesError(err instanceof Error ? err.message : 'Could not load profiles')
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  const canSubmit = sourceValue.trim().length > 0 && !disabled

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (canSubmit) {
      onSubmit(sourceValue.trim(), profileId, includeMarkdown)
    }
  }

  return (
    <div className="w-full max-w-xl">
      <form
        onSubmit={handleSubmit}
        className="rounded-xl border border-border bg-surface p-8 shadow-lg shadow-black/20 transition-all"
      >
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-primary">Run repository diagnostic</h2>
          <p className="mt-1 text-sm text-muted">
            Audit a local Python repository and get an evidence-driven readiness report.
          </p>
        </div>

        <div className="space-y-4">
          <div>
            <label htmlFor="sourceValue" className="block text-xs font-medium text-muted mb-1.5">
              Local repository path
            </label>
            <input
              id="sourceValue"
              type="text"
              value={sourceValue}
              onChange={(e) => setSourceValue(e.target.value)}
              placeholder="e.g. ./my-project"
              autoFocus
              className="w-full rounded-md border border-border bg-base px-3 py-2 text-sm text-primary placeholder:text-faint focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand/50"
            />
            <p className="mt-1.5 text-[11px] text-faint">
              Path must be readable by the DrRepo API server.
            </p>
          </div>

          <div>
            <label htmlFor="profileId" className="block text-xs font-medium text-muted mb-1.5">
              Advisor profile
            </label>
            <select
              id="profileId"
              value={profileId}
              onChange={(e) => setProfileId(e.target.value)}
              className="w-full rounded-md border border-border bg-base px-3 py-2 text-sm text-primary focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand/50"
            >
              {profiles.map((p) => (
                <option key={p.profile_id} value={p.profile_id}>
                  {p.display_name}
                </option>
              ))}
            </select>
            {profilesError && (
              <p className="mt-1.5 text-[11px] text-error">{profilesError}</p>
            )}
          </div>

          <label className="flex items-center gap-3 rounded-md border border-border bg-base px-3 py-2 cursor-pointer">
            <input
              type="checkbox"
              checked={includeMarkdown}
              onChange={(e) => setIncludeMarkdown(e.target.checked)}
              className="h-4 w-4 rounded border-border bg-surface-2 text-brand focus:ring-brand/50"
            />
            <span className="text-sm text-primary">Include markdown report preview</span>
          </label>
        </div>

        <button
          type="submit"
          disabled={!canSubmit}
          className="mt-6 w-full rounded-md bg-brand px-4 py-2.5 text-sm font-semibold text-base shadow shadow-brand/20 hover:bg-brand-hover focus:outline-none focus:ring-2 focus:ring-brand/50 disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-[0.98]"
        >
          Run Diagnostic
        </button>
      </form>

      <div className="mt-6 border-t border-border pt-5">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-faint mb-3">
          How it works
        </div>
        <div className="flex items-start gap-6 text-xs text-muted">
          <div className="flex-1 flex items-start gap-2">
            <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-surface-2 text-[10px] font-mono text-brand">
              1
            </span>
            <span>Collect evidence from tests, linters, security scanners, and structure checks</span>
          </div>
          <div className="flex-1 flex items-start gap-2">
            <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-surface-2 text-[10px] font-mono text-brand">
              2
            </span>
            <span>Score repository health and portfolio readiness with explainable rules</span>
          </div>
          <div className="flex-1 flex items-start gap-2">
            <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-surface-2 text-[10px] font-mono text-brand">
              3
            </span>
            <span>Build a prioritized remediation plan tailored to your profile</span>
          </div>
        </div>
      </div>
    </div>
  )
}
