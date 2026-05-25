import { get } from './client'
import type { ExecutionLog, ExecutionStats } from '../types/execution'

export interface AuditFilters {
  asset_id?: string
  purpose?: string
  blocked?: boolean
  since?: string
  until?: string
  limit?: number
  offset?: number
}

export function listExecutionLogs(params?: AuditFilters) {
  return get<ExecutionLog[]>('/audit/executions', { params })
}

export function getExecutionLog(id: string) {
  return get<ExecutionLog>(`/audit/executions/${id}`)
}

export function getExecutionStats() {
  return get<ExecutionStats>('/audit/stats')
}
