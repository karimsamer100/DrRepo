import type { AnalysisMode, CapabilitiesResponse, SourceType } from '../types/api'

interface AdvancedAuditSettingsProps {
  sourceType: SourceType
  analysisMode: AnalysisMode
  onAnalysisModeChange: (mode: AnalysisMode) => void
  aiEnabled: boolean
  onAiEnabledChange: (enabled: boolean) => void
  includeMarkdown: boolean
  onIncludeMarkdownChange: (enabled: boolean) => void
  installDependencies: boolean
  onInstallDependenciesChange: (enabled: boolean) => void
  allowInstallNetwork: boolean
  onAllowInstallNetworkChange: (enabled: boolean) => void
  capabilities?: CapabilitiesResponse | null
}

export const ANALYSIS_MODE_LABELS: Record<AnalysisMode, string> = {
  quick_safe: 'Quick Safe',
  deep_local: 'Deep Local',
  deep_isolated: 'Deep Isolated',
}

const MODE_DESCRIPTIONS: Record<AnalysisMode, string> = {
  quick_safe: 'Static analysis only. Safe for public GitHub repositories.',
  deep_local: 'Runs tests and coverage on this machine.',
  deep_isolated: 'Runs supported verification in a disposable Docker container.',
}

function sanitizedDockerReason(reason?: string) {
  if (!reason) return 'Docker capability has not been confirmed by the API.'
  if (/npipe|docker_engine|named pipe/i.test(reason)) {
    return 'The Docker engine is not reachable from the DrRepo API process.'
  }
  return reason.split(/\r?\n/, 1)[0].slice(0, 180)
}

export function AdvancedAuditSettings({
  sourceType,
  analysisMode,
  onAnalysisModeChange,
  aiEnabled,
  onAiEnabledChange,
  includeMarkdown,
  onIncludeMarkdownChange,
  installDependencies,
  onInstallDependenciesChange,
  allowInstallNetwork,
  onAllowInstallNetworkChange,
  capabilities,
}: AdvancedAuditSettingsProps) {
  const dockerSupported = !!capabilities?.docker_isolated_execution?.supported
  const aiSupported = !!capabilities?.ai_advisor?.supported
  const providerConfigured = !!capabilities?.ai_advisor?.provider_configured

  return (
    <details className="rounded-xl border border-border bg-base" data-testid="advanced-audit-settings">
      <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-medium text-primary transition-colors hover:text-brand [&::-webkit-details-marker]:hidden">
        <span>
          Advanced audit settings
          <span className="mt-0.5 block text-xs font-normal text-faint">
            Execution mode, optional guidance, and report output
          </span>
        </span>
        <span aria-hidden="true" className="text-lg leading-none text-faint">+</span>
      </summary>

      <div className="space-y-5 border-t border-border px-4 py-4">
        <div>
          <div id="analysis-mode-label" className="mb-2 text-xs font-medium text-faint">
            How thoroughly should DrRepo inspect this repository?
          </div>
          <div className="grid gap-2 sm:grid-cols-3" role="group" aria-labelledby="analysis-mode-label">
            {(Object.keys(ANALYSIS_MODE_LABELS) as AnalysisMode[]).map((mode) => {
              const disabled =
                (mode === 'deep_local' && sourceType === 'github_url') ||
                (mode === 'deep_isolated' && !dockerSupported)
              return (
                <button
                  key={mode}
                  type="button"
                  aria-pressed={analysisMode === mode}
                  disabled={disabled}
                  onClick={() => onAnalysisModeChange(mode)}
                  className={`rounded-xl border p-3 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-45 ${
                    analysisMode === mode
                      ? 'border-brand/30 bg-brand/10 text-brand'
                      : 'border-border bg-surface text-muted hover:text-primary'
                  }`}
                >
                  <span className="block text-sm font-semibold">{ANALYSIS_MODE_LABELS[mode]}</span>
                  <span className="mt-1 block text-xs leading-5 text-faint">{MODE_DESCRIPTIONS[mode]}</span>
                </button>
              )
            })}
          </div>

          {analysisMode === 'deep_local' && (
            <div className="mt-3 rounded-lg border border-warning/30 bg-warning/5 px-3 py-2 text-xs leading-5 text-warning">
              <div className="font-medium">Runs repository tests on this machine.</div>
              <div>Use only for local projects you trust.</div>
            </div>
          )}

          {sourceType === 'github_url' && (
            <p className="mt-3 text-xs leading-5 text-faint">
              Public GitHub repositories use Quick Safe by default. Deep Local remains unavailable for remote sources.
            </p>
          )}

          {!dockerSupported && (
            <div className="mt-3 rounded-lg border border-border bg-surface px-3 py-3">
              <p className="text-xs font-medium text-primary">Deep Isolated is unavailable.</p>
              <p className="mt-1 text-xs leading-5 text-muted">
                Start Docker Desktop to enable isolated execution.
              </p>
              <details className="mt-2">
                <summary className="cursor-pointer text-xs text-faint transition-colors hover:text-primary">
                  Why is it unavailable?
                </summary>
                <p className="mt-2 text-xs leading-5 text-faint">
                  {sanitizedDockerReason(capabilities?.docker_isolated_execution?.reason)}
                </p>
              </details>
            </div>
          )}

          {analysisMode === 'deep_isolated' && (
            <div className="mt-3 space-y-3 rounded-lg border border-warning/30 bg-warning/5 px-3 py-3 text-xs leading-5 text-muted">
              <p className="text-warning">
                Supported verification runs inside a disposable DrRepo-controlled container. This is not a production SaaS sandbox.
              </p>
              <label className="flex items-start gap-2">
                <input
                  type="checkbox"
                  checked={installDependencies}
                  onChange={(event) => onInstallDependenciesChange(event.target.checked)}
                  className="mt-1 h-3.5 w-3.5 rounded border-border bg-surface-2 text-brand focus:ring-brand/50"
                />
                Install dependencies inside the container before tests.
              </label>
              <label className="flex items-start gap-2">
                <input
                  type="checkbox"
                  checked={allowInstallNetwork}
                  disabled={!installDependencies}
                  onChange={(event) => onAllowInstallNetworkChange(event.target.checked)}
                  className="mt-1 h-3.5 w-3.5 rounded border-border bg-surface-2 text-brand focus:ring-brand/50 disabled:opacity-50"
                />
                Allow network only during dependency installation.
              </label>
            </div>
          )}
        </div>

        <div>
          <div className="mb-2 text-xs font-medium text-faint">Optional extras</div>
          <div className="space-y-2">
            <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-border bg-surface px-3.5 py-3">
              <input
                type="checkbox"
                checked={aiEnabled}
                disabled={!aiSupported}
                onChange={(event) => onAiEnabledChange(event.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-border bg-surface-2 text-brand focus:ring-brand/50 disabled:opacity-50"
              />
              <span>
                <span className="block text-sm font-medium text-primary">AI Advisor</span>
                <span className="block text-xs leading-5 text-faint">
                  {providerConfigured
                    ? 'Use the configured provider for grounded, prioritized guidance.'
                    : aiSupported
                      ? 'No provider is configured. DrRepo will return deterministic fallback guidance.'
                      : 'AI guidance is unavailable in this API build.'}
                </span>
              </span>
            </label>
            {aiEnabled && (
              <p className="rounded-lg border border-warning/25 bg-warning/5 px-3 py-2 text-xs leading-5 text-warning">
                {capabilities?.ai_advisor?.privacy_note ||
                  'AI mode sends a bounded, redacted summary of audit evidence to a configured provider.'}
              </p>
            )}

            <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-border bg-surface px-3.5 py-3">
              <input
                type="checkbox"
                checked={includeMarkdown}
                onChange={(event) => onIncludeMarkdownChange(event.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-border bg-surface-2 text-brand focus:ring-brand/50"
              />
              <span>
                <span className="block text-sm font-medium text-primary">Create a downloadable Markdown report</span>
                <span className="block text-xs leading-5 text-faint">
                  Adds report preview, copy, and download after the audit.
                </span>
              </span>
            </label>
          </div>
        </div>
      </div>
    </details>
  )
}
