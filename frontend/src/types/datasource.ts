export interface DataSource {
  id: string
  name: string
  type: string
  host: string
  port: number
  database: string
  username: string
  password: string
  params: Record<string, unknown> | null
  description: string | null
  status: string
  table_name: string
  record_count: number
  enabled: boolean
  created_at: string
  updated_at: string
  created_by: string | null
}

export interface DataSourceCreate {
  type: string
  host: string
  port: number
  database: string
  username: string
  password: string
  params?: Record<string, unknown> | null
  description?: string | null
}

export interface DataSourceUpdate {
  name?: string
  type?: string
  host?: string
  port?: number
  database?: string
  username?: string
  password?: string
  params?: Record<string, unknown> | null
  description?: string | null
  status?: string
}

export interface TestConnectionResult {
  success: boolean
  message: string
}
