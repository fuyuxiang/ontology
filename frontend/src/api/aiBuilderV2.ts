import client from './client'

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
  return client.get<{ documents: DocInfo[] }>('/ai-builder/documents', { params: { prefix: prefix || '' } })
}

export function extractOntologySSE(tableNames: string[], documentKeys: string[], businessDesc: string): EventSource {
  const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'
  const body = JSON.stringify({ table_names: tableNames, document_keys: documentKeys, business_desc: businessDesc })
  const url = `${baseURL}/ai-builder/extract-ontology`

  const xhr = new XMLHttpRequest()
  xhr.open('POST', url, true)
  xhr.setRequestHeader('Content-Type', 'application/json')
  const token = localStorage.getItem('token')
  if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)

  const eventTarget = new EventTarget()
  let buffer = ''

  xhr.onprogress = () => {
    const newData = xhr.responseText.slice(buffer.length)
    buffer = xhr.responseText
    const lines = newData.split('\n')
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6)
        if (data === '[DONE]') {
          eventTarget.dispatchEvent(new CustomEvent('done'))
        } else {
          try {
            const parsed = JSON.parse(data)
            eventTarget.dispatchEvent(new CustomEvent('message', { detail: parsed }))
          } catch { /* skip */ }
        }
      }
    }
  }

  xhr.onerror = () => eventTarget.dispatchEvent(new CustomEvent('error'))
  xhr.onloadend = () => eventTarget.dispatchEvent(new CustomEvent('done'))

  xhr.send(body)

  return { addEventListener: eventTarget.addEventListener.bind(eventTarget), xhr } as any
}
