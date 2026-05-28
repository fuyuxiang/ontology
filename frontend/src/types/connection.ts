// Connection / Asset / Binding / Execution / Lineage / Quality 全套类型定义
// 与后端 app/schemas/data_plane.py 严格对齐

export type ConnectionCategory =
  | 'database' | 'object_storage' | 'file_transfer' | 'message_queue' | 'api'

export type ConnectionType = string  // 现在 type 是 free-form，由 capabilities 决定取值范围

export interface Connection {
  id: string
  name: string
  category: ConnectionCategory
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
  category?: ConnectionCategory
  type: ConnectionType
  host?: string
  port?: number
  database?: string
  username?: string
  password?: string
  params?: Record<string, unknown> | null
  credential?: Record<string, unknown> | null
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

export type Capabilities = Record<ConnectionCategory, string[]>

export interface ObjectEntry {
  key: string
  size: number
  last_modified: string | null
}

export interface PathEntry {
  name: string
  size: number
  is_dir: boolean
}
