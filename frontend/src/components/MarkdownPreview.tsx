import { useState } from 'react'

interface MarkdownPreviewProps {
  content: string | null
}

export function MarkdownPreview({ content }: MarkdownPreviewProps) {
  const [copied, setCopied] = useState(false)

  if (!content) return null

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // Ignore clipboard errors.
    }
  }

  return (
    <section>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-medium text-muted">Markdown report</h3>
        <button
          type="button"
          onClick={handleCopy}
          className={`inline-flex items-center gap-1.5 text-[11px] transition-colors duration-150 ease-out-strong ${
            copied
              ? 'text-brand'
              : 'text-muted hover:text-primary'
          }`}
          aria-live="polite"
        >
          {copied && (
            <svg
              className="h-3.5 w-3.5 animate-[pulse_0.3s_ease-in-out]"
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
          )}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>
      <div className="rounded-lg border border-border bg-surface-2 overflow-hidden max-w-full">
        <div className="flex items-center justify-between border-b border-border bg-base px-3 py-1.5">
          <span className="font-mono text-[11px] text-faint">REPORT.md</span>
        </div>
        <pre className="p-3 font-mono text-xs leading-relaxed text-primary whitespace-pre-wrap overflow-auto max-h-[70vh]">
          {content}
        </pre>
      </div>
    </section>
  )
}
