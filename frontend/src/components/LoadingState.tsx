import type { AuditRequest } from '../types/api'
import { compactSource, shortSourceMode } from '../lib/presentation'

interface LoadingStateProps {
  request?: AuditRequest | null
}

export function LoadingState({ request }: LoadingStateProps) {
  const isGitHub = request?.source_type === 'github_url'

  return (
    <div className="w-full max-w-xl mx-auto animate-fade-up" role="status" aria-live="polite">
      <div className="relative overflow-hidden rounded-2xl border border-border bg-surface p-6 text-left shadow-raised">
        <div className="scan-line" aria-hidden="true" />
        <div className="relative flex items-start gap-4">
          <div className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl border border-brand/25 bg-brand/10 text-brand">
            <svg
              className="h-7 w-7 animate-[shimmer_1.6s_ease-in-out_infinite]"
              viewBox="0 0 28 28"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <rect x="1" y="1" width="26" height="26" rx="5" stroke="currentColor" strokeWidth="2" />
              <path d="M14 7v14M7 14h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              <path d="M20 9.5h3.5M20 14h2.5M20 18.5h3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-brand">
              Running diagnostic
            </div>
            <h2 className="mt-1 text-lg font-semibold text-primary">
              Collecting repository evidence
            </h2>
            {request && (
              <p className="mt-2 break-all font-mono text-xs text-faint">
                {shortSourceMode(request.source_type)} - {compactSource(request.source_value)}
              </p>
            )}
            <p className="mt-3 text-sm leading-6 text-muted">
              {isGitHub
                ? 'Cloning the public repository and skipping test execution for remote safety.'
                : 'Inspecting project structure and running available local analyzers.'}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
