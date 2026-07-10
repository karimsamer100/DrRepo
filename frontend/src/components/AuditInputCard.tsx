import { useEffect, useState, type FormEvent } from 'react'
import type { ProfileInfo, SourceType } from '../types/api'
import { listProfiles } from '../api/client'
import type { RecentAudit } from '../lib/recentAudits'
import { RecentAudits } from './RecentAudits'

interface AuditInputCardProps {
  onSubmit: (
    sourceType: SourceType,
    sourceValue: string,
    profileId: string,
    includeMarkdown: boolean
  ) => void
  recentAudits?: RecentAudit[]
  onSelectRecent?: (item: RecentAudit) => void
  onClearRecent?: () => void
  disabled?: boolean
}

const EXAMPLE_PATH = 'examples/sample_good_repo'
const EXAMPLE_GITHUB_URL = 'https://github.com/pypa/sampleproject'

const SOURCE_LABELS: Record<SourceType, string> = {
  local_path: 'Local path',
  github_url: 'GitHub URL',
}

const SOURCE_PLACEHOLDERS: Record<SourceType, string> = {
  local_path: 'e.g. ./my-project',
  github_url: 'https://github.com/owner/repo',
}

export function AuditInputCard({
  onSubmit,
  recentAudits = [],
  onSelectRecent,
  onClearRecent,
  disabled,
}: AuditInputCardProps) {
  const [profiles, setProfiles] = useState<ProfileInfo[]>([])
  const [sourceType, setSourceType] = useState<SourceType>('local_path')
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
          setProfilesError(null)
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

  const apiUnreachable = !!profilesError
  const canSubmit = sourceValue.trim().length > 0 && !disabled && !apiUnreachable

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (canSubmit) {
      onSubmit(sourceType, sourceValue.trim(), profileId, includeMarkdown)
    }
  }

  const handleSelectRecent = (item: RecentAudit) => {
    setSourceType(item.sourceType)
    setSourceValue(item.sourceLabel)
    if (profiles.some((p) => p.profile_id === item.profile)) {
      setProfileId(item.profile)
    }
    onSelectRecent?.(item)
  }

  const setExample = () => {
    if (sourceType === 'local_path') {
      setSourceValue(EXAMPLE_PATH)
    } else {
      setSourceValue(EXAMPLE_GITHUB_URL)
    }
  }

  return (
    <div className="w-full max-w-5xl">
      <div className="mb-8 text-center">
        <h1 className="text-2xl sm:text-3xl font-semibold text-primary tracking-tight mb-3">
          Diagnose your Python repository
        </h1>
        <p className="text-sm text-muted max-w-lg mx-auto">
          Run an evidence-driven audit on a local directory or a public GitHub repository.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <form
          onSubmit={handleSubmit}
          className="lg:col-span-2 surface-raised rounded-xl p-6 lg:p-8"
        >
          {apiUnreachable && (
            <div className="mb-5 rounded-md border border-error/30 bg-error/5 p-3">
              <p className="text-sm text-error">
                API unreachable — start the DrRepo API server and retry.
              </p>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-muted mb-1.5">
                Source
              </label>
              <div className="flex rounded-md border border-border bg-base p-1">
                {(Object.keys(SOURCE_LABELS) as SourceType[]).map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    onClick={() => {
                      setSourceType(mode)
                      setSourceValue('')
                    }}
                    className={`flex-1 rounded px-3 py-1.5 text-xs font-medium transition-colors duration-150 ${
                      sourceType === mode
                        ? 'bg-brand/10 text-brand'
                        : 'text-muted hover:text-primary'
                    }`}
                  >
                    {SOURCE_LABELS[mode]}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label htmlFor="sourceValue" className="block text-xs font-medium text-muted mb-1.5">
                {sourceType === 'local_path' ? 'Local repository path' : 'Public GitHub repository URL'}
              </label>
              <input
                id="sourceValue"
                type="text"
                value={sourceValue}
                onChange={(e) => setSourceValue(e.target.value)}
                placeholder={SOURCE_PLACEHOLDERS[sourceType]}
                autoFocus
                className="w-full rounded-md border border-border bg-base px-3 py-2.5 text-sm text-primary placeholder:text-faint focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand/50"
              />
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <span className="text-[11px] text-faint">Try an example:</span>
                <button
                  type="button"
                  onClick={setExample}
                  className="inline-flex items-center rounded-full border border-border bg-base px-2.5 py-0.5 text-[11px] font-mono text-muted hover:border-brand/30 hover:text-brand transition-colors"
                >
                  {sourceType === 'local_path' ? EXAMPLE_PATH : EXAMPLE_GITHUB_URL}
                </button>
              </div>
              {sourceType === 'github_url' && (
                <p className="mt-2 text-[11px] text-faint">
                  Public GitHub repositories only. Private repos and tokens are not supported in this step.
                </p>
              )}
            </div>

            <div>
              <label htmlFor="profileId" className="block text-xs font-medium text-muted mb-1.5">
                Advisor profile
              </label>
              <select
                id="profileId"
                value={profileId}
                onChange={(e) => setProfileId(e.target.value)}
                disabled={apiUnreachable}
                className="w-full rounded-md border border-border bg-base px-3 py-2.5 text-sm text-primary focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand/50 disabled:opacity-50"
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

            <label className="flex items-center gap-3 rounded-md border border-border bg-base px-3 py-2.5 cursor-pointer">
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
            className="mt-6 w-full rounded-md bg-brand px-4 py-2.5 text-sm font-semibold text-base shadow shadow-brand/20 hover:bg-brand-hover focus:outline-none focus:ring-2 focus:ring-brand/50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors duration-150 ease-out-strong"
          >
            Run Diagnostic
          </button>
        </form>

        <div className="lg:col-span-1 space-y-6">
          <div className="rounded-xl border border-border bg-surface p-5">
            <h3 className="text-xs font-medium text-muted mb-4">How it works</h3>
            <ol className="space-y-4">
              <li className="flex items-start gap-3">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-border bg-base text-[10px] font-mono text-brand">
                  1
                </span>
                <span className="text-sm text-muted">Collect evidence from tests, linters, security scanners, and structure checks.</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-border bg-base text-[10px] font-mono text-brand">
                  2
                </span>
                <span className="text-sm text-muted">Score repository health and portfolio readiness with explainable rules.</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-border bg-base text-[10px] font-mono text-brand">
                  3
                </span>
                <span className="text-sm text-muted">Build a prioritized remediation plan tailored to your profile.</span>
              </li>
            </ol>
          </div>

          <RecentAudits
            items={recentAudits}
            onSelect={handleSelectRecent}
            onClear={onClearRecent ?? (() => {})}
          />
        </div>
      </div>
    </div>
  )
}
