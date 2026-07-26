import { useEffect, useState } from 'react'
import type { AuditRequest } from '../types/api'
import { compactSource, shortSourceMode } from '../lib/presentation'

interface LoadingStateProps {
  request?: AuditRequest | null
}

const STATUS_MESSAGES = [
  'Review in progress',
  'Still checking available evidence',
  'Preparing your results',
]

export function LoadingState({ request }: LoadingStateProps) {
  const isGitHub = request?.source_type === 'github_url'
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [statusIndex, setStatusIndex] = useState(0)

  useEffect(() => {
    const startedAt = Date.now()
    const timer = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    const reducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reducedMotion) return

    const timer = window.setInterval(() => {
      setStatusIndex((current) => (current + 1) % STATUS_MESSAGES.length)
    }, 3600)
    return () => window.clearInterval(timer)
  }, [])

  const mode = request?.analysis_mode
  const secondaryCopy =
    mode === 'quick_safe' || isGitHub
      ? 'Inspecting repository files without executing project code.'
      : mode === 'deep_isolated'
        ? 'Running selected checks in an isolated environment. This can take several minutes.'
        : 'Running configured checks for a local repository you trust.'

  return (
    <div className="mx-auto w-full max-w-xl animate-fade-up" role="status" aria-live="polite">
      <div className="diagnostic-loader-card rounded-xl border p-5 text-left shadow-raised sm:p-6">
        <div className="flex flex-col items-center gap-4 text-center sm:flex-row sm:items-start sm:text-left">
          <div className="repository-scan-indicator shrink-0" aria-hidden="true">
            <div className="repository-scan-ring" />
            <div className="repository-scan-core">
              <svg viewBox="0 0 32 32" fill="none" aria-hidden="true">
                <rect x="7" y="8" width="14" height="13" rx="2.5" />
                <path d="M10.5 12h6M10.5 15.5h4" />
                <path d="M17 19l2.2 2.2 5.3-6.4" />
              </svg>
            </div>
            <span className="repository-scan-status" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-[12px] font-medium uppercase tracking-[0.12em] text-brand">
              Running audit
            </div>
            <h2 className="mt-1 text-xl font-semibold text-primary">
              Reviewing repository evidence...
            </h2>
            {request && (
              <p className="mt-2 break-anywhere font-mono text-[13px] leading-5 text-muted">
                {shortSourceMode(request.source_type)} - {compactSource(request.source_value)}
              </p>
            )}
            <p className="mt-2.5 text-sm leading-5 text-muted">
              {secondaryCopy}
            </p>
            <p className="mt-1.5 text-sm leading-5 text-muted">
              Keep this tab open while DrRepo finishes the review.
            </p>
            <p className="mt-3 font-mono text-[13px] text-faint">
              Elapsed {elapsedSeconds}s
            </p>
            <div className="mt-2 flex items-center gap-2 text-[13px] text-faint" aria-hidden="true">
              <span className="loading-status-dot" />
              <span className="loading-status-text" key={STATUS_MESSAGES[statusIndex]}>
                {STATUS_MESSAGES[statusIndex]}
              </span>
            </div>
            <p className="sr-only">Review in progress.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
