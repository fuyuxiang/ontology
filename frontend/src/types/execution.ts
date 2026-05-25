// /execute 入参/响应 + ExecutionLog 审计

export interface ExecuteRequest {
  asset_id: string
  sql: string
  params?: Record<string, unknown>
  purpose: string
  timeout_ms?: number
  bypass_cache?: boolean
}

export interface ExecuteResult {
  columns: string[]
  rows: unknown[][]
  rows_returned: number
  duration_ms: number
  cache_hit: boolean
}

export interface ExecuteBlocked {
  blocked: true
  reason: string
  detail?: string
}

export interface DryRunResult {
  compiled_sql: string
  referenced_tables: string[]
  placeholders: string[]
  is_select: boolean
  is_dml: boolean
}

export interface ExecutionLog {
  id: string
  asset_id: string | null
  connection_id: string | null
  purpose: string
  sql_hash: string
  sql_preview: string
  params_redacted: Record<string, string> | null
  rows_returned: number
  duration_ms: number
  cache_hit: boolean
  blocked: boolean
  block_reason: string | null
  user_id: string | null
  started_at: string
}

export interface ExecutionStats {
  total: number
  cache_hit_rate: number
  blocked_rate: number
  avg_duration_ms: number
}
