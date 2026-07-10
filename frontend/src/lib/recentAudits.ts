export interface RecentAudit {
  sourceLabel: string
  profile: string
  createdAt: string
  overallScore: number | null
  verdictLabel: string | null
}

const STORAGE_KEY = 'drrepo:recentAudits'
const MAX_ITEMS = 5

export function loadRecentAudits(): RecentAudit[] {
  if (typeof window === 'undefined' || !window.localStorage) {
    return []
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as unknown
    if (Array.isArray(parsed)) {
      return parsed.filter(isRecentAudit)
    }
  } catch {
    // Ignore corrupt localStorage data.
  }
  return []
}

export function saveRecentAudits(items: RecentAudit[]): void {
  if (typeof window === 'undefined' || !window.localStorage) {
    return
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  } catch {
    // Ignore storage errors (e.g. private browsing mode).
  }
}

export function addRecentAudit(
  current: RecentAudit[],
  item: RecentAudit
): RecentAudit[] {
  const withoutDuplicate = current.filter(
    (existing) =>
      !(
        existing.sourceLabel === item.sourceLabel &&
        existing.profile === item.profile
      )
  )
  const next = [item, ...withoutDuplicate].slice(0, MAX_ITEMS)
  saveRecentAudits(next)
  return next
}

export function clearRecentAudits(): RecentAudit[] {
  saveRecentAudits([])
  return []
}

function isRecentAudit(value: unknown): value is RecentAudit {
  if (typeof value !== 'object' || value === null) return false
  const candidate = value as Record<string, unknown>
  return (
    typeof candidate.sourceLabel === 'string' &&
    typeof candidate.profile === 'string' &&
    typeof candidate.createdAt === 'string'
  )
}
