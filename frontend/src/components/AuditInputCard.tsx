import { useEffect, useState, type FormEvent } from 'react'
import type { AnalysisMode, CapabilitiesResponse, IsolatedOptions, ProfileInfo, SourceType } from '../types/api'
import { listProfiles } from '../api/client'
import type { RecentAudit } from '../lib/recentAudits'
import { RecentAudits } from './RecentAudits'
import { AdvancedAuditSettings, ANALYSIS_MODE_LABELS } from './AdvancedAuditSettings'

interface AuditInputCardProps {
  onSubmit: (
    sourceType: SourceType,
    sourceValue: string,
    analysisMode: AnalysisMode,
    profileId: string,
    ai: boolean,
    includeMarkdown: boolean,
    isolatedOptions?: IsolatedOptions | null
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
  local_path: 'Local repository',
  github_url: 'Public GitHub repository',
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
  const [aiEnabled, setAiEnabled] = useState(false)
  const [includeMarkdown, setIncludeMarkdown] = useState(false)
  const [installDependencies, setInstallDependencies] = useState(false)
  const [allowInstallNetwork, setAllowInstallNetwork] = useState(false)
  const [profilesError, setProfilesError] = useState<string | null>(null)
  const [clipboardMessage, setClipboardMessage] = useState<string | null>(null)

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
  const dockerSupported = !!capabilities?.docker_isolated_execution?.supported
  const localPathEnabled = capabilities?.local_path?.enabled !== false
  const canSubmit = sourceValue.trim().length > 0 && !disabled && !apiUnreachable && (analysisMode !== 'deep_isolated' || dockerSupported)
  const recommendedMode: AnalysisMode = sourceType === 'github_url' ? 'quick_safe' : 'deep_local'
  const selectedProfile = profiles.find((profile) => profile.profile_id === profileId)
  const isRecommendedMode = analysisMode === recommendedMode
  const submitLabel = isRecommendedMode
    ? 'Run recommended audit'
    : `Run ${ANALYSIS_MODE_LABELS[analysisMode]} audit`

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (canSubmit) {
      onSubmit(
        sourceType,
        sourceValue.trim(),
        analysisMode,
        profileId,
        aiEnabled,
        includeMarkdown,
        analysisMode === 'deep_isolated'
          ? {
              install_dependencies: installDependencies,
              allow_install_network: installDependencies && allowInstallNetwork,
              total_timeout_seconds: 300,
              per_command_timeout_seconds: 120,
              python_version: '3.12',
            }
          : null
      )
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
    if (mode === 'local_path' && !localPathEnabled) return
    setSourceType(mode)
    setAnalysisMode(mode === 'github_url' ? 'quick_safe' : 'deep_local')
    setSourceValue(value)
  }

  const missingAnalyzers =
    capabilities?.analyzers.filter((analyzer) => !analyzer.available && !analyzer.core) || []

  const selectSourceType = (mode: SourceType) => {
    if (mode === 'local_path' && !localPathEnabled) return
    setSourceType(mode)
    setAnalysisMode(mode === 'github_url' ? 'quick_safe' : 'deep_local')
    setSourceValue('')
    setClipboardMessage(null)
  }

  const pasteGitHubUrl = async () => {
    setClipboardMessage(null)
    if (!navigator.clipboard?.readText) {
      setClipboardMessage('Clipboard access is not available in this browser.')
      return
    }
    try {
      const pasted = await navigator.clipboard.readText()
      if (pasted.trim().length > 0) {
        setSourceValue(pasted.trim())
      }
    } catch {
      setClipboardMessage('Paste was blocked by the browser. You can type the URL instead.')
    }
  }

  useEffect(() => {
    if (sourceType === 'local_path' && !localPathEnabled) {
      setSourceType('github_url')
      setAnalysisMode('quick_safe')
      setSourceValue('')
    }
  }, [localPathEnabled, sourceType])

  return (
    <div className="w-full max-w-6xl animate-fade-up">
      <div className="mb-4">
        <div>
          <div className="mb-1 text-[12px] font-medium uppercase tracking-[0.12em] text-brand">
            Repository diagnostic
          </div>
          <h1 className="text-[22px] font-semibold leading-tight tracking-tight text-primary sm:text-2xl">
            Diagnose repository readiness without pretending certainty.
          </h1>
          <p className="mt-1.5 max-w-2xl text-sm leading-5 text-muted">
            DrRepo audits Python projects with observed evidence, calibrated verdicts, confidence limits, and a prioritized remediation plan.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <form
          onSubmit={handleSubmit}
          className="surface-raised self-start rounded-xl p-4 sm:p-5"
        >
          {apiUnreachable && (
            <div className="mb-5 rounded-xl border border-error/30 bg-error/5 p-4" role="alert">
              <div className="text-sm font-medium text-error">API unavailable</div>
              <p className="mt-1 text-sm text-error/90">
                Start the DrRepo API server, then return here to run a diagnostic.
              </p>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <div className="mb-1.5">
                <label id="source-mode-label" className="text-xs font-medium text-faint">
                  Where is the repository?
                </label>
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
                    disabled={mode === 'local_path' && !localPathEnabled}
                    onClick={() => selectSourceType(mode)}
                    className={`min-h-11 rounded-lg px-3 text-sm font-medium transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-45 ${
                      sourceType === mode
                        ? 'bg-surface-2 text-brand ring-1 ring-brand/30'
                        : 'text-muted hover:bg-surface-2/65 hover:text-primary'
                    }`}
                  >
                    {SOURCE_LABELS[mode]}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label htmlFor="sourceValue" className="mb-1.5 block text-xs font-medium uppercase tracking-[0.12em] text-faint">
                {sourceType === 'local_path' ? 'Local repository path' : 'Public GitHub repository URL'}
              </label>
              <input
                id="sourceValue"
                type="text"
                value={sourceValue}
                onChange={(e) => setSourceValue(e.target.value)}
                placeholder={SOURCE_PLACEHOLDERS[sourceType]}
                autoFocus
                className="w-full min-w-0 rounded-xl border border-border bg-base px-3.5 py-2.5 text-sm text-primary placeholder:text-faint focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand/50"
              />
              {sourceType === 'github_url' && (
                <div className="mt-2 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={pasteGitHubUrl}
                    className="inline-flex min-h-10 items-center rounded-lg border border-border bg-surface px-3 text-sm font-medium text-muted transition-colors hover:border-brand/35 hover:text-brand"
                  >
                    Paste URL
                  </button>
                  {sourceValue.trim().length > 0 && (
                    <button
                      type="button"
                      onClick={() => {
                        setSourceValue('')
                        setClipboardMessage(null)
                      }}
                      className="inline-flex min-h-10 items-center rounded-lg border border-border bg-surface px-3 text-sm font-medium text-muted transition-colors hover:border-brand/35 hover:text-brand"
                    >
                      Clear
                    </button>
                  )}
                  {clipboardMessage && (
                    <span className="flex min-h-10 items-center text-sm leading-5 text-faint">
                      {clipboardMessage}
                    </span>
                  )}
                </div>
              )}
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <span className="text-[13px] text-faint">Use sample:</span>
                <button
                  type="button"
                  onClick={() => setExample(EXAMPLE_PATH, 'local_path')}
                  className="inline-flex min-h-8 items-center rounded-full border border-border bg-base px-3 font-mono text-[12.5px] text-muted transition-colors hover:border-health/30 hover:text-health"
                >
                  good local
                </button>
                <button
                  type="button"
                  onClick={() => setExample(EXAMPLE_BAD_PATH, 'local_path')}
                  className="inline-flex min-h-8 items-center rounded-full border border-border bg-base px-3 font-mono text-[12.5px] text-muted transition-colors hover:border-warning/30 hover:text-warning"
                >
                  bad local
                </button>
                <button
                  type="button"
                  onClick={() => setExample(EXAMPLE_GITHUB_URL, 'github_url')}
                  className="inline-flex min-h-8 items-center rounded-full border border-border bg-base px-3 font-mono text-[12.5px] text-muted transition-colors hover:border-brand/30 hover:text-brand"
                >
                  public GitHub
                </button>
              </div>
              {sourceType === 'github_url' ? (
                <p className="mt-2 rounded-lg border border-warning/25 bg-warning/5 px-3 py-1.5 text-[13px] leading-5 text-muted">
                  Public repositories only. DrRepo skips remote test execution for safety,
                  so evidence confidence may be partial or limited.
                </p>
              ) : (
                <p className="mt-2 text-[13px] leading-5 text-faint">
                  Local audits can run project test evidence on the API server machine.
                  Use a path that exists where the backend is running.
                </p>
              )}
              {!localPathEnabled && (
                <p className="mt-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-[13px] leading-5 text-muted">
                  {capabilities?.local_path?.limitation || 'Local repository audits are disabled on this API instance. Public GitHub repository audits remain available.'}
                </p>
              )}
            </div>

            <div>
              <label htmlFor="profileId" className="mb-1.5 block text-xs font-medium text-faint">
                What are you preparing this project for?
              </label>
              <select
                id="profileId"
                value={profileId}
                onChange={(e) => setProfileId(e.target.value)}
                disabled={apiUnreachable}
                className="w-full rounded-xl border border-border bg-base px-3.5 py-2.5 text-sm text-primary focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand/50 disabled:opacity-50"
              >
                {profiles.map((p) => (
                  <option key={p.profile_id} value={p.profile_id}>
                    {p.display_name}
                  </option>
                ))}
              </select>
              {profilesError && <p className="mt-1.5 text-[13px] text-error">{profilesError}</p>}
              <p className="mt-1.5 text-[13px] leading-5 text-faint">
                {selectedProfile?.description || 'The goal changes remediation emphasis only; repository evidence stays the same.'}
              </p>
            </div>

            <div className="rounded-xl border border-brand/20 bg-brand/5 px-3.5 py-2.5">
              <div className="text-sm font-semibold text-primary">
                Recommended audit: {ANALYSIS_MODE_LABELS[recommendedMode]}
              </div>
              <p className="mt-0.5 text-[13px] leading-5 text-muted">
                {sourceType === 'local_path'
                  ? 'Runs tests and coverage for a local repository you trust.'
                  : 'Analyzes the repository without running its tests.'}
              </p>
              {!isRecommendedMode && (
                <p className="mt-1 text-[13px] text-brand">
                  Current selection: {ANALYSIS_MODE_LABELS[analysisMode]}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={!canSubmit}
              className="inline-flex min-h-11 w-full items-center justify-center rounded-xl bg-brand px-4 py-2.5 text-sm font-semibold text-on-brand shadow shadow-brand/20 transition-colors duration-150 ease-out-strong hover:bg-brand-hover focus:outline-none focus:ring-2 focus:ring-brand/50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {submitLabel}
            </button>

            <AdvancedAuditSettings
              sourceType={sourceType}
              analysisMode={analysisMode}
              onAnalysisModeChange={setAnalysisMode}
              aiEnabled={aiEnabled}
              onAiEnabledChange={setAiEnabled}
              includeMarkdown={includeMarkdown}
              onIncludeMarkdownChange={setIncludeMarkdown}
              installDependencies={installDependencies}
              onInstallDependenciesChange={(enabled) => {
                setInstallDependencies(enabled)
                if (!enabled) setAllowInstallNetwork(false)
              }}
              allowInstallNetwork={allowInstallNetwork}
              onAllowInstallNetworkChange={setAllowInstallNetwork}
              capabilities={capabilities}
            />
          </div>
        </form>

        <aside className="self-start rounded-xl border border-border bg-surface p-4" aria-label="Launcher support">
          <section>
            <h3 className="text-xs font-medium uppercase tracking-[0.16em] text-faint">
              What happens next
            </h3>
            <p className="mt-1.5 text-sm leading-5 text-muted">
              DrRepo scans the source, records what it could verify, and returns a verdict with the first repository action.
            </p>
          </section>

          <section className="mt-4 border-t border-border pt-4">
            <h3 className="mb-2 text-xs font-medium uppercase tracking-[0.14em] text-faint">
              Diagnostic flow
            </h3>
            <ol className="space-y-2">
              {[
                'Resolve the source and collect repository metadata.',
                'Run available analyzers and record skipped or unavailable evidence.',
                'Separate verdict, confidence, findings, and next fixes.',
              ].map((step, index) => (
                <li key={step} className="flex items-start gap-3">
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-border bg-base font-mono text-[12px] text-brand">
                    {index + 1}
                  </span>
                  <span className="text-sm leading-5 text-muted">{step}</span>
                </li>
              ))}
            </ol>
          </section>

          <section className="mt-4 border-t border-border pt-4">
            <h3 className="mb-2 text-xs font-medium uppercase tracking-[0.14em] text-faint">
              Analyzer capability
            </h3>
            {capabilityError ? (
              <p className="text-xs leading-5 text-error">
                Capability preflight unavailable: {capabilityError}
              </p>
            ) : capabilities ? (
              <>
                <div className="space-y-2 text-xs leading-5">
                  <p className="text-primary">
                    <span className="font-mono text-brand">{capabilities.analyzers.filter((a) => a.available).length}</span> of{' '}
                    <span className="font-mono">{capabilities.analyzers.length}</span> analyzers ready
                  </p>
                  <p className={dockerSupported ? 'text-health' : 'text-faint'}>
                    Docker isolated runner {dockerSupported ? 'ready' : 'unavailable'}
                  </p>
                  <p className={capabilities.ai_advisor?.provider_configured ? 'text-health' : 'text-faint'}>
                    AI advisor {capabilities.ai_advisor?.provider_configured ? 'available' : 'unavailable'}
                  </p>
                </div>
                {missingAnalyzers.length > 0 && (
                  <p className="mt-2 text-xs leading-5 text-faint">
                    Missing optional tools limit confidence: {missingAnalyzers.map((a) => a.analyzer_id).join(', ')}.
                  </p>
                )}
                {(capabilities.setup.install_command || capabilities.docker_isolated_execution.setup_command) && (
                  <details className="mt-3 rounded-lg border border-border bg-base px-3 py-2">
                    <summary className="cursor-pointer text-xs font-medium text-muted transition-colors hover:text-primary">
                      Setup details
                    </summary>
                    <div className="mt-2 space-y-2">
                      {capabilities.setup.install_command && (
                        <code className="block break-anywhere font-mono text-[12.5px] leading-5 text-faint">
                          {capabilities.setup.install_command}
                        </code>
                      )}
                      {capabilities.docker_isolated_execution.setup_command && (
                        <code className="block break-anywhere font-mono text-[12.5px] leading-5 text-faint">
                          {capabilities.docker_isolated_execution.setup_command}
                        </code>
                      )}
                    </div>
                  </details>
                )}
              </>
            ) : (
              <p className="text-xs leading-5 text-faint">Checking analyzer availability...</p>
            )}
          </section>

          <div className="mt-4 border-t border-border pt-4">
          <RecentAudits
            items={recentAudits}
            onSelect={handleSelectRecent}
            onClear={onClearRecent ?? (() => {})}
          />
          </div>
        </aside>
      </div>
    </div>
  )
}
