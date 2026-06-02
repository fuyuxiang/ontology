import client from './client'

export interface DomainMatchResult {
  domains: string[]
  reason: string
  all_domains: string[]
}

export interface TableInfo {
  table_name: string
  table_desc: string
  layering: string
  cycle: string
}

export interface FieldInfo {
  field_name: string
  field_desc: string
  field_type: string
  field_length: string
  is_partition: string
  field_handle: string
  field_source_desc: string
}

export interface DocInfo {
  key: string
  title: string
  size: number
  last_modified: string | null
}

export function getDomains() {
  return client.get<{ domains: string[] }>('/ai-builder/domains')
}

export function getSubDomains(domain1: string) {
  return client.get<{ sub_domains: string[] }>(`/ai-builder/domains/${encodeURIComponent(domain1)}/sub-domains`)
}

export function getThemes(domain1: string, domain2: string) {
  return client.get<{ themes: string[] }>(`/ai-builder/domains/${encodeURIComponent(domain1)}/${encodeURIComponent(domain2)}/themes`)
}

export function getTables(domain1: string, domain2: string, domain3?: string) {
  const params: Record<string, string> = { domain1, domain2 }
  if (domain3) params.domain3 = domain3
  return client.get<{ tables: TableInfo[] }>('/ai-builder/tables', { params })
}

export function getTableSchema(tableName: string) {
  return client.get<{ table_name: string; fields: FieldInfo[] }>(`/ai-builder/tables/${encodeURIComponent(tableName)}/schema`)
}

export function matchDomain(businessDesc: string) {
  return client.post<DomainMatchResult>('/ai-builder/match-domain', { business_desc: businessDesc })
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
