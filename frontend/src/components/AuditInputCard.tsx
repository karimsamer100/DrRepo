import { useEffect, useState, type FormEvent } from 'react'
import type { AnalysisMode, CapabilitiesResponse, ProfileInfo, SourceType } from '../types/api'
import { listProfiles } from '../api/client'
import type { RecentAudit } from '../lib/recentAudits'
import { RecentAudits } from './RecentAudits'
import { sourceTypeLabel } from '../lib/presentation'

interface AuditInputCardProps {
  onSubmit: (
    sourceType: SourceType,
    sourceValue: string,
    analysisMode: AnalysisMode,
    profileId: string,
    includeMarkdown: boolean
  ) => void
  recentAudits?: RecentAudit[]
  onSelectRecent?: (item: RecentAudit) => void
  onClearRecent?: () => void
  disabled?: boolean
  capabilities?: CapabilitiesResponse | null
  capabilityError?: string | null
}

const EXAMPLE_PATH = 'examples/sample_good_repo'
const EXAMPLE_BAD_PATH = 'examples/sample_bad_repo'
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
  capabilities,
  capabilityError,
}: AuditInputCardProps) {
  const [profiles, setProfiles] = useState<ProfileInfo[]>([])
  const [sourceType, setSourceType] = useState<SourceType>('local_path')
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>('deep_local')
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
      onSubmit(sourceType, sourceValue.trim(), analysisMode, profileId, includeMarkdown)
    }
  }

  const handleSelectRecent = (item: RecentAudit) => {
    setSourceType(item.sourceType)
    setAnalysisMode(item.analysisMode || (item.sourceType === 'github_url' ? 'quick_safe' : 'deep_local'))
    setSourceValue(item.sourceLabel)
    if (profiles.some((p) => p.profile_id === item.profile)) {
      setProfileId(item.profile)
    }
    onSelectRecent?.(item)
  }

  const setExample = (value: string, mode: SourceType) => {
    setSourceType(mode)
    setAnalysisMode(mode === 'github_url' ? 'quick_safe' : 'deep_local')
    setSourceValue(value)
  }

  const missingAnalyzers =
    capabilities?.analyzers.filter((analyzer) => !analyzer.available && !analyzer.core) || []

  const selectSourceType = (mode: SourceType) => {
    setSourceType(mode)
    if (mode === 'github_url') setAnalysisMode('quick_safe')
    setSourceValue('')
  }

  return (
    <div className="w-full max-w-6xl animate-fade-up">
      <div className="mb-6 grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end">
        <div>
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-brand/20 bg-brand/10 px-3 py-1 text-[11px] font-medium uppercase tracking-[0.18em] text-brand">
            Evidence console
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-primary sm:text-3xl">
            Diagnose repository readiness without pretending certainty.
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
            DrRepo audits Python projects with observed evidence, calibrated verdicts,
            confidence limits, and a prioritized remediation plan.
          </p>
        </div>
        <div className="rounded-2xl border border-border bg-surface/80 p-4 text-xs text-muted lg:w-72">
          <div className="font-medium text-primary">What happens next</div>
          <p className="mt-1 leading-5">
            The API scans the source, records what was verified, and returns JSON plus
            an optional Markdown report.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <form
          onSubmit={handleSubmit}
          className="surface-raised rounded-2xl p-5 sm:p-6 lg:col-span-2 lg:p-7"
        >
          {apiUnreachable && (
            <div className="mb-5 rounded-xl border border-error/30 bg-error/5 p-4" role="alert">
              <div className="text-sm font-medium text-error">API unavailable</div>
              <p className="mt-1 text-sm text-error/90">
                Start the DrRepo API server, then return here to run a diagnostic.
              </p>
            </div>
          )}

          <div className="space-y-5">
            <div>
              <div className="mb-2 flex items-center justify-between gap-3">
                <label id="source-mode-label" className="text-xs font-medium uppercase tracking-[0.16em] text-faint">
                  Source mode
                </label>
                <span className="text-[11px] text-faint">{sourceTypeLabel(sourceType)}</span>
              </div>
              <div
                className="grid grid-cols-2 rounded-xl border border-border bg-base p-1"
                role="group"
                aria-labelledby="source-mode-label"
              >
                {(Object.keys(SOURCE_LABELS) as SourceType[]).map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    aria-pressed={sourceType === mode}
                    onClick={() => selectSourceType(mode)}
                    className={`min-h-11 rounded-lg px-3 text-sm font-medium transition-colors duration-150 ${
                      sourceType === mode
                        ? 'bg-brand/10 text-brand shadow-[0_0_0_1px_rgba(34,211,238,0.16)_inset]'
                        : 'text-muted hover:bg-white/[0.03] hover:text-primary'
                    }`}
                  >
                    {SOURCE_LABELS[mode]}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label id="analysis-mode-label" className="mb-2 block text-xs font-medium uppercase tracking-[0.16em] text-faint">
                Analysis mode
              </label>
              <div className="grid gap-2 sm:grid-cols-2" role="group" aria-labelledby="analysis-mode-label">
                <button
                  type="button"
                  aria-pressed={analysisMode === 'quick_safe'}
                  onClick={() => setAnalysisMode('quick_safe')}
                  className={`rounded-xl border p-3 text-left transition-colors ${
                    analysisMode === 'quick_safe'
                      ? 'border-brand/30 bg-brand/10 text-brand'
                      : 'border-border bg-base text-muted hover:text-primary'
                  }`}
                >
                  <span className="block text-sm font-semibold">Quick Safe</span>
                  <span className="mt-1 block text-xs leading-5 text-faint">No target code execution. Safe for public GitHub URLs.</span>
                </button>
                <button
                  type="button"
                  aria-pressed={analysisMode === 'deep_local'}
                  disabled={sourceType === 'github_url'}
                  onClick={() => setAnalysisMode('deep_local')}
                  className={`rounded-xl border p-3 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                    analysisMode === 'deep_local'
                      ? 'border-warning/30 bg-warning/10 text-warning'
                      : 'border-border bg-base text-muted hover:text-primary'
                  }`}
                >
                  <span className="block text-sm font-semibold">Deep Local</span>
                  <span className="mt-1 block text-xs leading-5 text-faint">Runs pytest and coverage. Project code may execute locally.</span>
                </button>
              </div>
              {analysisMode === 'deep_local' && (
                <p className="mt-2 rounded-lg border border-warning/30 bg-warning/5 px-3 py-2 text-xs leading-5 text-warning">
                  Deep Local can execute target repository code through pytest/coverage. Use it only for local repositories you trust.
                </p>
              )}
              {sourceType === 'github_url' && (
                <p className="mt-2 text-xs leading-5 text-faint">
                  GitHub URL audits are locked to Quick Safe until isolated remote execution is implemented.
                </p>
              )}
            </div>

            <div>
              <label htmlFor="sourceValue" className="mb-2 block text-xs font-medium uppercase tracking-[0.16em] text-faint">
                {sourceType === 'local_path' ? 'Local repository path' : 'Public GitHub repository URL'}
              </label>
              <input
                id="sourceValue"
                type="text"
                value={sourceValue}
                onChange={(e) => setSourceValue(e.target.value)}
                placeholder={SOURCE_PLACEHOLDERS[sourceType]}
                autoFocus
                className="w-full rounded-xl border border-border bg-base px-3.5 py-3 text-sm text-primary placeholder:text-faint focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand/50"
              />
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span className="text-[11px] text-faint">Use sample:</span>
                <button
                  type="button"
                  onClick={() => setExample(EXAMPLE_PATH, 'local_path')}
                  className="inline-flex min-h-8 items-center rounded-full border border-border bg-base px-3 text-[11px] font-mono text-muted transition-colors hover:border-health/30 hover:text-health"
                >
                  good local
                </button>
                <button
                  type="button"
                  onClick={() => setExample(EXAMPLE_BAD_PATH, 'local_path')}
                  className="inline-flex min-h-8 items-center rounded-full border border-border bg-base px-3 text-[11px] font-mono text-muted transition-colors hover:border-warning/30 hover:text-warning"
                >
                  bad local
                </button>
                <button
                  type="button"
                  onClick={() => setExample(EXAMPLE_GITHUB_URL, 'github_url')}
                  className="inline-flex min-h-8 items-center rounded-full border border-border bg-base px-3 text-[11px] font-mono text-muted transition-colors hover:border-brand/30 hover:text-brand"
                >
                  public GitHub
                </button>
              </div>
              {sourceType === 'github_url' ? (
                <p className="mt-3 rounded-lg border border-warning/25 bg-warning/5 px-3 py-2 text-xs leading-5 text-muted">
                  Public repositories only. DrRepo skips remote test execution for safety,
                  so evidence confidence may be partial or limited.
                </p>
              ) : (
                <p className="mt-3 text-xs leading-5 text-faint">
                  Local audits can run project test evidence on the API server machine.
                  Use a path that exists where the backend is running.
                </p>
              )}
            </div>

            <div>
              <label htmlFor="profileId" className="mb-2 block text-xs font-medium uppercase tracking-[0.16em] text-faint">
                Advisor profile
              </label>
              <select
                id="profileId"
                value={profileId}
                onChange={(e) => setProfileId(e.target.value)}
                disabled={apiUnreachable}
                className="w-full rounded-xl border border-border bg-base px-3.5 py-3 text-sm text-primary focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand/50 disabled:opacity-50"
              >
                {profiles.map((p) => (
                  <option key={p.profile_id} value={p.profile_id}>
                    {p.display_name}
                  </option>
                ))}
              </select>
              {profilesError && <p className="mt-1.5 text-[11px] text-error">{profilesError}</p>}
              <p className="mt-2 text-xs leading-5 text-faint">
                The profile changes remediation emphasis only; it does not change repository evidence.
              </p>
            </div>

            <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-border bg-base px-3.5 py-3">
              <input
                type="checkbox"
                checked={includeMarkdown}
                onChange={(e) => setIncludeMarkdown(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-border bg-surface-2 text-brand focus:ring-brand/50"
              />
              <span>
                <span className="block text-sm font-medium text-primary">Include Markdown report</span>
                <span className="block text-xs leading-5 text-faint">
                  Adds a readable report preview and enables Markdown download/copy after the audit.
                </span>
              </span>
            </label>
          </div>

          <button
            type="submit"
            disabled={!canSubmit}
            className="mt-6 inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-brand px-4 py-3 text-sm font-semibold text-base shadow shadow-brand/20 transition-colors duration-150 ease-out-strong hover:bg-brand-hover focus:outline-none focus:ring-2 focus:ring-brand/50 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Run diagnostic
          </button>
        </form>

        <div className="space-y-6 lg:col-span-1">
          <div className="rounded-2xl border border-border bg-surface p-5">
            <h3 className="mb-4 text-xs font-medium uppercase tracking-[0.16em] text-faint">
              Diagnostic flow
            </h3>
            <ol className="space-y-4">
              {[
                'Resolve the source and collect repository metadata.',
                'Run available analyzers and record skipped or unavailable evidence.',
                'Separate verdict, confidence, findings, and next fixes.',
              ].map((step, index) => (
                <li key={step} className="flex items-start gap-3">
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-border bg-base text-[10px] font-mono text-brand">
                    {index + 1}
                  </span>
                  <span className="text-sm leading-5 text-muted">{step}</span>
                </li>
              ))}
            </ol>
          </div>

          <div className="rounded-2xl border border-border bg-surface p-5">
            <h3 className="mb-3 text-xs font-medium uppercase tracking-[0.16em] text-faint">
              Analyzer capability
            </h3>
            {capabilityError ? (
              <p className="text-xs leading-5 text-error">
                Capability preflight unavailable: {capabilityError}
              </p>
            ) : capabilities ? (
              <>
                <p className="text-xs leading-5 text-muted">
                  {capabilities.analyzers.filter((a) => a.available).length} of {capabilities.analyzers.length} analyzers available.
                </p>
                {missingAnalyzers.length > 0 && (
                  <p className="mt-2 text-xs leading-5 text-faint">
                    Missing optional tools limit confidence: {missingAnalyzers.map((a) => a.analyzer_id).join(', ')}.
                  </p>
                )}
                {capabilities.setup.install_command && (
                  <code className="mt-3 block break-all rounded-lg border border-border bg-base p-2 font-mono text-[10px] text-faint">
                    {capabilities.setup.install_command}
                  </code>
                )}
              </>
            ) : (
              <p className="text-xs leading-5 text-faint">Checking analyzer availability...</p>
            )}
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
