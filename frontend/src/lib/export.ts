function repoSlug(sourceValue: string): string {
  let candidate = sourceValue.trim()

  try {
    const url = new URL(candidate)
    // Strip query/fragment and trailing slashes, then drop a .git suffix.
    candidate = url.pathname.replace(/\.git$/i, '').replace(/\/+$/, '')
  } catch {
    // Not a URL; use the raw value.
  }

  return (
    candidate
      .replace(/\\/g, '/')
      .split('/')
      .pop()
      ?.replace(/\.git$/i, '')
      ?.replace(/[^a-zA-Z0-9_-]+/g, '_')
      .replace(/^_+|_+$/g, '')
      .slice(0, 40) || ''
  )
}

export function safeFilenameBase(sourceValue: string): string {
  const slug = repoSlug(sourceValue)
  return slug.length > 0 ? slug : 'audit'
}

export function timestampSuffix(): string {
  const now = new Date()
  const date = now.toISOString().slice(0, 10)
  const time = now.toTimeString().slice(0, 8).replace(/:/g, '-')
  return `${date}_${time}`
}

export function downloadBlob(
  content: BlobPart,
  filename: string,
  type: string
): void {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

export async function copyTextToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}
