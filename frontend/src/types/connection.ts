// Connection / Asset / Binding / Execution / Lineage / Quality 全套类型定义
// 与后端 app/schemas/data_plane.py 严格对齐

export type ConnectionType =
  | 'mysql' | 'postgresql' | 'oracle' | 'sqlserver' | 'hive' | 'clickhouse' | 'fake'

export interface Connection {
  id: string
  name: string
  type: ConnectionType
  host: string
  port: number
  database: string
  params: Record<string, unknown> | null
  writable: boolean
  pool_size: number
  rate_limit_qps: number
  description: string | null
  status: 'active' | 'inactive' | 'error'
  enabled: boolean
  last_test_at: string | null
  last_test_ok: boolean
  last_test_message: string | null
  created_at: string
  updated_at: string
}

export interface ConnectionCreate {
  name: string
  type: ConnectionType
  host: string
  port: number
  database?: string
  username: string
  password: string
  params?: Record<string, unknown> | null
  writable?: boolean
  pool_size?: number
  rate_limit_qps?: number
  description?: string | null
}

export type ConnectionUpdate = Partial<ConnectionCreate> & { enabled?: boolean }

export interface TestResult {
  success: boolean
  message: string
  latency_ms?: number | null
}
