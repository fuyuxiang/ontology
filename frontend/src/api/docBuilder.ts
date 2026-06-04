import client from './client'
import { post } from './client'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export interface DocFileInfo {
  name: string
  size: number
  type: string
  content_preview: string
}

export interface UploadResult {
  session_id: string
  files: DocFileInfo[]
}

export function downloadTemplate(): void {
  window.open(`${baseURL}/doc-builder/template`, '_blank')
}

export function uploadDocuments(files: File[]): Promise<{ data: UploadResult }> {
  const fd = new FormData()
  for (const f of files) {
    fd.append('files', f, f.name)
  }
  return client.post('/doc-builder/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function docBuilderChat(
  sessionId: string,
  message: string,
  businessDesc: string,
  onEvent: (ev: { event: string; [key: string]: any }) => void,
  onDone: () => void,
  onError: () => void,
): { abort: () => void } {
  const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'
  const body = JSON.stringify({ session_id: sessionId, message, business_desc: businessDesc })

  const ctrl = new AbortController()

  fetch(`${baseURL}/doc-builder/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(localStorage.getItem('token') ? { Authorization: `Bearer ${localStorage.getItem('token')}` } : {}),
    },
    body,
    signal: ctrl.signal,
  }).then(async res => {
    const reader = res.body!.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const lines = buf.split('\n')
      buf = lines.pop() ?? ''
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') {
            onDone()
          } else {
            try {
              onEvent(JSON.parse(data))
            } catch { /* skip */ }
          }
        }
      }
    }
    onDone()
  }).catch(() => onError())

  return { abort: () => ctrl.abort() }
}

// ─── 映射持久化 ───────────────────────────────────────

export interface MappingPreviewItem {
  entity_name: string
  entity_id: string | null
  table_name: string | null
  asset_id: string | null
  asset_registered: boolean
  confidence: number
  conflict: { existing_binding_id: string; existing_asset_name: string } | null
  field_mappings: Array<{
    attribute_name: string
    attribute_id: string | null
    source_column: string | null
    confidence: number
  }>
}

export interface MappingPreviewResponse {
  items: MappingPreviewItem[]
}

export interface MappingApplyItem {
  entity_id: string | null
  asset_id: string | null
  conflict_action: 'overwrite' | 'keep' | null
  register_asset: boolean
  table_name: string | null
  field_mappings: Array<{ attribute_id: string; source_column: string | null }>
}

export interface MappingApplyResponse {
  created: number
  updated: number
  skipped: number
  binding_ids: string[]
}

export function previewMappingPersist(sessionId: string, mappingResult: any): Promise<MappingPreviewResponse> {
  return post<MappingPreviewResponse>('/doc-builder/mapping/preview', { session_id: sessionId, mapping_result: mappingResult })
}

export function applyMappingPersist(sessionId: string, items: MappingApplyItem[]): Promise<MappingApplyResponse> {
  return post<MappingApplyResponse>('/doc-builder/mapping/apply', { session_id: sessionId, items })
}
