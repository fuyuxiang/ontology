import { get } from './client'
import type { AuditEntry, AuditQuery } from '../types'

export interface PaginatedResult<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}

export const auditApi = {
  list(query?: AuditQuery) {
    return get<PaginatedResult<AuditEntry>>('/audit-log', { params: query })
  },

  detail(id: string) {
    return get<AuditEntry>(`/audit-log/${id}`)
  },
}
