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
  const [copied, setCopied] = useState(false)

  const base = safeFilenameBase(data.source_value)
  const suffix = timestampSuffix()

  const handleDownloadJson = () => {
    const content = JSON.stringify(data, null, 2)
    downloadBlob(content, `${base}_${suffix}.drrepo.json`, 'application/json')
  }

  const handleDownloadMarkdown = () => {
    if (!data.markdown) return
    downloadBlob(data.markdown, `${base}_${suffix}.md`, 'text/markdown')
  }

  const handleCopyMarkdown = async () => {
    if (!data.markdown) return
    const ok = await copyTextToClipboard(data.markdown)
    if (ok) {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    }
  }

  const hasMarkdown = !!data.markdown

  const buttonClass =
    'inline-flex w-full items-center justify-center gap-2 rounded-md border border-border bg-base px-3 py-2 text-xs font-medium text-primary transition-colors duration-150 ease-out-strong hover:border-brand/30 hover:text-brand disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-border disabled:hover:text-primary'

  return (
    <section className="rounded-lg border border-border bg-surface p-4">
      <h3 className="text-xs font-medium text-muted mb-3">Export result</h3>

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
              aria-live="polite"
            >
              {copied ? (
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
              {copied ? 'Copied' : 'Copy Markdown'}
            </button>
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
