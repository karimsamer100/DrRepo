import { useCallback, useRef, useState } from 'react'
import type { AnalysisMode, AuditRequest, AuditResponse, ProfileInfo, SourceType } from '../types/api'
import { runAudit } from '../api/client'

type AuditStatus = 'idle' | 'loading' | 'error' | 'done'

export interface AuditState {
  status: AuditStatus
  data: AuditResponse | null
  error: string | null
  lastRequest: AuditRequest | null
}

export function useAudit() {
  const requestIdRef = useRef(0)
  const [state, setState] = useState<AuditState>({
    status: 'idle',
    data: null,
    error: null,
    lastRequest: null,
  })

  const execute = useCallback(
    async (
      sourceType: SourceType,
      sourceValue: string,
      analysisMode: AnalysisMode,
      profileId: string,
      includeMarkdown: boolean
    ) => {
      const requestId = requestIdRef.current + 1
      requestIdRef.current = requestId
      const request: AuditRequest = {
        source_type: sourceType,
        source_value: sourceValue,
        analysis_mode: analysisMode,
        profile_id: profileId,
        ai: false,
        include_markdown: includeMarkdown,
      }
      setState({ status: 'loading', data: null, error: null, lastRequest: request })
      try {
        const data = await runAudit(request)
        if (requestIdRef.current !== requestId) return
        setState({ status: 'done', data, error: null, lastRequest: request })
      } catch (err) {
        if (requestIdRef.current !== requestId) return
        const message =
          err instanceof Error ? err.message : 'An unexpected error occurred'
        setState({ status: 'error', data: null, error: message, lastRequest: request })
      }
    },
    []
  )

  const reset = useCallback(() => {
    requestIdRef.current += 1
    setState({ status: 'idle', data: null, error: null, lastRequest: null })
  }, [])

  return { state, execute, reset }
}

export type { AuditResponse, ProfileInfo }
