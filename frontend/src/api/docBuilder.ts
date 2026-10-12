import client from './client'
import { post } from './client'
import { postJsonSse, readJsonSse } from './sse'

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

export async function downloadTemplate(): Promise<void> {
  const response = await client.get('/doc-builder/template', { responseType: 'blob' })
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a'); link.href = url; link.download = '本体建模业务文档模板.md'; link.click()
  URL.revokeObjectURL(url)
}

export function uploadDocuments(files: File[], signal?: AbortSignal): Promise<{ data: UploadResult }> {
  const fd = new FormData()
  for (const f of files) {
    fd.append('files', f, f.name)
  }
  return client.post('/doc-builder/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
    signal,
  })
}

export function docBuilderChat(
  sessionId: string,
  message: string,
  businessDesc: string,
  onEvent: (ev: { event: string; [key: string]: any }) => void,
  onDone: () => void,
  onError: (message: string) => void,
): { abort: () => void } {
  const ctrl = new AbortController()
  void postJsonSse('/doc-builder/chat', {
    session_id: sessionId, message, business_desc: businessDesc,
  }, ctrl.signal).then(response => readJsonSse(response, onEvent)).then(() => {
    if (!ctrl.signal.aborted) onDone()
  }).catch(error => {
    if (!ctrl.signal.aborted) onError(error.message || '请求失败')
  })

  return { abort: () => ctrl.abort() }
}

export async function readDocumentSession(sessionId: string) { return (await client.get<{ history: Array<{role:string;content:string}>; current_ontology:any }>(`/doc-builder/sessions/${encodeURIComponent(sessionId)}`)).data }

// ─── 映射持久化 ───────────────────────────────────────

export interface MappingPreviewItem {
  entity_name: string
  entity_id: string | null
  table_name: string | null
  asset_id: string | null
  backing_asset_ids?: string[]
  primary_key?: string | null
  id_column?: string | null
  enrichment_bindings?: import('../types/builder').OntologyObjectDraft['enrichment_bindings']
  conflict_action?: 'keep' | 'overwrite' | null
  asset_registered: boolean
  confidence: number
  conflict: { existing_binding_id: string; existing_asset_name: string } | null
  field_mappings: Array<{
    attribute_name: string
    attribute_id: string | null
    source_column: string | null
    source_asset_id?: string | null
    transform?: import('../types/builder').OntologyProperty['transform']
    type?: string
    required?: boolean
    description?: string | null
    confidence: number
  }>
}

export interface MappingPreviewResponse {
  items: MappingPreviewItem[]
}

export interface MappingApplyItem {
  entity_name: string
  entity_id: string | null
  asset_id: string | null
  conflict_action: 'overwrite' | 'keep' | null
  field_mappings: Array<{ attribute_id: string; source_column: string | null }>
}

export interface MappingApplyResponse {
  created: number
  updated: number
  skipped: number
  binding_ids: string[]
  items: MappingPreviewItem[]
}

export function previewMappingPersist(sessionId: string, mappingResult: any, ontologyId?: string): Promise<MappingPreviewResponse> {
  return post<MappingPreviewResponse>('/doc-builder/mapping/preview', { session_id: sessionId, mapping_result: mappingResult, ontology_id: ontologyId })
}

export function applyMappingPersist(sessionId: string, items: MappingApplyItem[], mappingResult?: any, ontologyId?: string): Promise<MappingApplyResponse> {
  return post<MappingApplyResponse>('/doc-builder/mapping/apply', { session_id: sessionId, items, mapping_result: mappingResult, ontology_id: ontologyId })
}
