import { useCallback, useState } from 'react'
import type { AuditResponse, ProfileInfo } from '../types/api'
import { runAudit } from '../api/client'

type AuditStatus = 'idle' | 'loading' | 'error' | 'done'

export interface AuditState {
  status: AuditStatus
  data: AuditResponse | null
  error: string | null
}

export function useAudit() {
  const [state, setState] = useState<AuditState>({
    status: 'idle',
    data: null,
    error: null,
  })

  const execute = useCallback(
    async (sourceValue: string, profileId: string, includeMarkdown: boolean) => {
      setState({ status: 'loading', data: null, error: null })
      try {
        const data = await runAudit({
          source_type: 'local_path',
          source_value: sourceValue,
          profile_id: profileId,
          ai: false,
          include_markdown: includeMarkdown,
        })
        setState({ status: 'done', data, error: null })
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'An unexpected error occurred'
        setState({ status: 'error', data: null, error: message })
      }
    },
    []
  )

  const reset = useCallback(() => {
    setState({ status: 'idle', data: null, error: null })
  }, [])

  return { state, execute, reset }
}

export type { AuditResponse, ProfileInfo }
