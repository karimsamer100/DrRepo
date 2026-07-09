import type { AuditRequest, AuditResponse, HealthCheckResponse, ProfileInfo } from '../types/api'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

  const data = (await response.json().catch(() => ({}))) as { detail?: string }

  if (!response.ok) {
    const message =
      typeof data.detail === 'string'
        ? data.detail
        : `Request failed with status ${response.status}`
    throw new Error(message)
  }

  return data as T
}

export function getHealth(): Promise<HealthCheckResponse> {
  return apiFetch<HealthCheckResponse>('/health')
}

export function listProfiles(): Promise<ProfileInfo[]> {
  return apiFetch<{ profiles: ProfileInfo[] }>('/api/profiles').then(
    (res) => res.profiles
  )
}

export function runAudit(request: AuditRequest): Promise<AuditResponse> {
  return apiFetch<AuditResponse>('/api/audits', {
    method: 'POST',
    body: JSON.stringify(request),
  })
}
