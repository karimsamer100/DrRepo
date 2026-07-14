import { useState } from 'react'

interface MarkdownPreviewProps {
  content: string | null
}

export function MarkdownPreview({ content }: MarkdownPreviewProps) {
  const [copyStatus, setCopyStatus] = useState<'idle' | 'copied' | 'failed'>('idle')

  if (!content) return null

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content)
      setCopyStatus('copied')
      setTimeout(() => setCopyStatus('idle'), 1500)
    } catch {
      setCopyStatus('failed')
      setTimeout(() => setCopyStatus('idle'), 2000)
    }
  }

  return (
    <section>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-medium uppercase tracking-[0.16em] text-faint">Markdown report</h3>
        <button
          type="button"
          onClick={handleCopy}
          className={`inline-flex items-center gap-1.5 text-[11px] transition-colors duration-150 ease-out-strong ${
            copyStatus === 'copied'
              ? 'text-brand'
              : copyStatus === 'failed'
              ? 'text-error'
              : 'text-muted hover:text-primary'
          }`}
        >
          {copyStatus === 'copied' && (
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
          <span>{copyStatus === 'copied' ? 'Copied' : copyStatus === 'failed' ? 'Failed' : 'Copy'}</span>
        </button>
        <span className="sr-only" aria-live="polite">
          {copyStatus === 'copied'
            ? 'Markdown report copied'
            : copyStatus === 'failed'
            ? 'Markdown report copy failed'
            : ''}
        </span>
      </div>
      <div className="rounded-2xl border border-border bg-surface overflow-hidden max-w-full">
        <div className="flex items-center justify-between border-b border-border bg-base px-3 py-1.5">
          <span className="font-mono text-[11px] text-faint">REPORT.md</span>
        </div>
        <pre className="max-h-[55vh] overflow-auto whitespace-pre-wrap break-words p-3 font-mono text-xs leading-relaxed text-primary sm:max-h-[70vh]">
          {content}
        </pre>
      </div>
    </section>
  )
}
