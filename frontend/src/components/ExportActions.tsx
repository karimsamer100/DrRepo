import { useState } from 'react'
import type { AuditResponse } from '../types/api'
import {
  copyTextToClipboard,
  downloadBlob,
  safeFilenameBase,
  timestampSuffix,
} from '../lib/export'

interface ExportActionsProps {
  data: AuditResponse
}

export function ExportActions({ data }: ExportActionsProps) {
  const [copyStatus, setCopyStatus] = useState<'idle' | 'copied' | 'failed'>('idle')

  const handleDownloadJson = () => {
    const base = safeFilenameBase(data.source_value)
    const suffix = timestampSuffix()
    const content = JSON.stringify(data, null, 2)
    downloadBlob(content, `${base}_${suffix}.drrepo.json`, 'application/json')
  }

  const handleDownloadMarkdown = () => {
    if (!data.markdown) return
    const base = safeFilenameBase(data.source_value)
    const suffix = timestampSuffix()
    downloadBlob(data.markdown, `${base}_${suffix}.md`, 'text/markdown')
  }

  const handleCopyMarkdown = async () => {
    if (!data.markdown) return
    const ok = await copyTextToClipboard(data.markdown)
    if (ok) {
      setCopyStatus('copied')
      setTimeout(() => setCopyStatus('idle'), 1500)
    } else {
      setCopyStatus('failed')
      setTimeout(() => setCopyStatus('idle'), 2000)
    }
  }

  const hasMarkdown = !!data.markdown

  const buttonClass =
    'inline-flex w-full items-center justify-center gap-2 rounded-md border border-border bg-base px-3 py-2 text-xs font-medium text-primary transition-colors duration-150 ease-out-strong hover:border-brand/30 hover:text-brand disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-border disabled:hover:text-primary'

  return (
    <section className="rounded-2xl border border-border bg-surface p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-xs font-medium uppercase tracking-[0.16em] text-faint">
            Export
          </h3>
          <p className="mt-1 text-xs text-muted">Save the observed result data.</p>
        </div>
      </div>

      <div className="space-y-2">
        <button type="button" onClick={handleDownloadJson} className={buttonClass}>
          <svg
            className="h-3.5 w-3.5"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          Download JSON
        </button>

        {hasMarkdown ? (
          <>
            <button
              type="button"
              onClick={handleDownloadMarkdown}
              className={buttonClass}
            >
              <svg
                className="h-3.5 w-3.5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Download Markdown
            </button>

            <button
              type="button"
              onClick={handleCopyMarkdown}
              className={buttonClass}
            >
              {copyStatus === 'copied' ? (
                <svg
                  className="h-3.5 w-3.5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              ) : (
                <svg
                  className="h-3.5 w-3.5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
              )}
              {copyStatus === 'copied' ? 'Copied' : copyStatus === 'failed' ? 'Copy failed' : 'Copy Markdown'}
            </button>
            <span className="sr-only" aria-live="polite">
              {copyStatus === 'copied'
                ? 'Markdown copied to clipboard'
                : copyStatus === 'failed'
                ? 'Markdown copy failed'
                : ''}
            </span>
          </>
        ) : (
          <p className="rounded-md border border-border bg-base px-3 py-2 text-[11px] text-faint">
            Markdown report was not included in this run.
          </p>
        )}
      </div>
    </section>
  )
}
