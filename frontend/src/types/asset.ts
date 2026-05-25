// Asset 三种 kind：table / sql_view / document
// document 由 source_type 区分：file / oss / directory / api / mq

export type AssetKind = 'table' | 'sql_view' | 'document'
export type DocumentSourceType = 'file' | 'oss' | 'directory' | 'api' | 'mq'

export interface SchemaColumn {
  name: string
  type: string
  nullable: boolean
  is_pk?: boolean
  comment?: string
}

export interface AssetProfile {
  row_count?: number
  max_updated_at?: string | null
  null_ratio?: Record<string, number>
  sampled_at?: string | null
}

export interface Asset {
  id: string
  name: string
  alias: string | null
  description: string | null
  kind: AssetKind
  connection_id: string | null
  locator: Record<string, unknown>
  schema_snapshot: SchemaColumn[] | null
  schema_synced_at: string | null
  primary_key: string[] | null
  profile: AssetProfile | null
  document_source_type: DocumentSourceType | null
  parsed_summary: string | null
  embedding_index_ref: string | null
  refresh_policy: 'on_demand' | 'hourly' | 'daily'
  cache_ttl_seconds: number
  sensitivity_tags: Record<string, string> | null
  domain: string | null
  tags: string[] | null
  owner: string | null
  status: 'active' | 'deprecated' | 'broken'
  legacy_datasource_id: string | null
  legacy_business_document_id: string | null
  created_at: string
  updated_at: string
}

export interface AssetCreate {
  name: string
  alias?: string | null
  kind: AssetKind
  connection_id?: string | null
  locator: Record<string, unknown>
  description?: string | null
  domain?: string | null
  tags?: string[]
  owner?: string | null
  sensitivity_tags?: Record<string, string>
  refresh_policy?: 'on_demand' | 'hourly' | 'daily'
  cache_ttl_seconds?: number
}

export type AssetUpdate = Partial<Omit<AssetCreate, 'kind' | 'connection_id' | 'locator'>>

export interface AssetUsageEntry {
  id: string
  note?: string | null
}

export interface AssetUsage {
  bindings: AssetUsageEntry[]
  builder_sessions: AssetUsageEntry[]
  rules: AssetUsageEntry[]
  actions: AssetUsageEntry[]
}

export interface AssetWithUsage {
  asset: Asset
  usage: AssetUsage
  ref_count: number
}

export interface SchemaSyncResult {
  diff: {
    added: string[]
    removed: string[]
    type_changed: { name: string; old: string; new: string }[]
  }
  schema_snapshot: SchemaColumn[]
}

// Document 5 种接入入参 ─────────────────────────────────────

export interface OssDocCreate {
  name: string
  endpoint: string
  bucket: string
  access_key: string
  secret_key: string
  prefix?: string
  description?: string | null
  domain?: string | null
  tags?: string[]
}

export interface DirectoryDocCreate {
  name: string
  directory_path: string
  file_extensions?: string[]
  description?: string | null
  domain?: string | null
  tags?: string[]
}

export interface ApiDocCreate {
  name: string
  api_url: string
  api_method?: string
  api_headers?: Record<string, string> | null
  api_body?: string | null
  poll_interval?: number
  description?: string | null
  domain?: string | null
  tags?: string[]
}

export interface MqDocCreate {
  name: string
  host: string
  port?: number
  topic: string
  group?: string
  username?: string
  password?: string
  poll_interval?: number
  description?: string | null
  domain?: string | null
  tags?: string[]
}

// Preview 多形态 ──────────────────────────────────────────

export interface PreviewResult {
  // 结构化
  columns?: string[]
  rows?: unknown[][]
  rows_returned?: number
  // document
  file_path?: string
  file_type?: string
  summary?: string
  files?: string[]
  directory_path?: string
  endpoint?: string
  bucket?: string
  prefix?: string
  api_url?: string
  host?: string
  topic?: string
  note?: string
  error?: string
}
