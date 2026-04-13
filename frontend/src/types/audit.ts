// ── 审计日志（借鉴 clawhub append-only 模式）──

export type AuditAction = 'create' | 'update' | 'delete' | 'execute' | 'rollback'
export type AuditTargetType = 'entity' | 'attribute' | 'relation' | 'rule' | 'action' | 'strategy'

export interface FieldChange {
  field: string
  oldValue: unknown
  newValue: unknown
}

export interface AuditEntry {
  id: string
  timestamp: string
  userId: string
  userName: string
  action: AuditAction
  targetType: AuditTargetType
  targetId: string
  targetName: string
  changes: FieldChange[]
  snapshotBefore?: Record<string, unknown>
  snapshotAfter?: Record<string, unknown>
}

export interface AuditQuery {
  page?: number
  pageSize?: number
  action?: AuditAction
  targetType?: AuditTargetType
  targetId?: string
  userId?: string
  startTime?: string
  endTime?: string
}
