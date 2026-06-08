import { get } from './client'

// ---- 审计日志 ----

export interface AuditLogItem {
  id: string
  timestamp: string
  user_id: string | null
  user_name: string | null
  action: string
  target_type: string
  target_id: string
  target_name: string
  details: string | null
  status: string
  changes_json: Array<{ field: string; before: unknown; after: unknown }> | null
  snapshot_before: Record<string, unknown> | null
  snapshot_after: Record<string, unknown> | null
}

export interface AuditLogPage {
  items: AuditLogItem[]
  total: number
  page: number
  page_size: number
}

export interface AuditLogParams {
  page?: number
  page_size?: number
  action?: string
  target_type?: string
  user_name?: string
  keyword?: string
  date_from?: string
  date_to?: string
}

export const governanceApi = {
  /** 审计日志列表（分页 + 筛选） */
  listAuditLogs: (params?: AuditLogParams) =>
    get<AuditLogPage>('/governance/audit-logs', { params }),

  /** 获取所有出现过的操作类型（用于筛选下拉） */
  listAuditActions: () =>
    get<string[]>('/governance/audit-logs/actions'),
}
