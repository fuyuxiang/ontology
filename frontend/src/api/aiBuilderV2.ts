import client from './client'
import { postJsonSse, readJsonSse } from './sse'

export interface TableInfo {
  asset_id: string
  table_name: string
  table_desc: string
  kind: string
  domain: string | null
}

export interface FieldInfo {
  field_name: string
  field_desc: string
  field_type: string
}

export interface DocInfo {
  key: string
  title: string
  size: number
  last_modified: string | null
}

export function listTables() {
  return client.get<{ tables: TableInfo[] }>('/ai-builder/tables')
}

export function getTableSchema(tableName: string) {
  return client.get<{ table_name: string; fields: FieldInfo[] }>(`/ai-builder/tables/${encodeURIComponent(tableName)}/schema`)
}

export interface RecommendTablesResult {
  tables: TableInfo[]
  recommended: string[]
}

export function recommendTables(businessDesc: string) {
  return client.post<RecommendTablesResult>('/ai-builder/recommend-tables', {
    business_desc: businessDesc,
  })
}

export function getDocuments(prefix?: string) {
  return client.get<{ documents: DocInfo[]; warning?: string | null }>('/ai-builder/documents', { params: { prefix: prefix || '' } })
}

export function extractOntologySSE(tableNames: string[], documentKeys: string[], businessDesc: string) {
  const controller = new AbortController()
  const target = new EventTarget()
  void postJsonSse('/ai-builder/extract-ontology', {
    table_names: tableNames, document_keys: documentKeys, business_desc: businessDesc,
  }, controller.signal).then(response => readJsonSse(response, event => {
    target.dispatchEvent(new CustomEvent('message', { detail: event }))
  }, true)).then(() => {
    if (!controller.signal.aborted) target.dispatchEvent(new CustomEvent('done'))
  }).catch(error => {
    if (!controller.signal.aborted) target.dispatchEvent(new CustomEvent('error', { detail: error.message }))
  })
  return {
    addEventListener: target.addEventListener.bind(target),
    abort: () => controller.abort(),
  }
}
