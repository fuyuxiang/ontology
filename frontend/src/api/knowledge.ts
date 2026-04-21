import { get, del } from './client'
import client from './client'

export interface KnowledgeBase {
  id: string
  name: string
  description: string
  tags: string[]
  status: string
  file_count: number
  created_at: string
  updated_at: string
  files?: KnowledgeFile[]
}

export interface KnowledgeFile {
  id: string
  kb_id: string
  name: string
  file_type: string
  size: number
  status: string
  created_at: string
  has_content: boolean
}

export interface SearchResult {
  kb_id: string
  kb_name: string
  file_id: string
  file_name: string
  snippet: string
}

export interface VoiceAuditDimension {
  name: string
  result: 'pass' | 'fail' | 'na'
  comment: string
}

export interface VoiceAuditResult {
  overall: 'pass' | 'fail' | 'warning' | 'error'
  score: number
  summary: string
  dimensions: VoiceAuditDimension[]
  risk_flags: string[]
}

export const knowledgeApi = {
  list(q?: string) {
    return get<KnowledgeBase[]>('/knowledge', { params: q ? { q } : {} })
  },
  create(name: string, description = '', tags = '') {
    const fd = new FormData()
    fd.append('name', name)
    fd.append('description', description)
    fd.append('tags', tags)
    return client.post<KnowledgeBase>('/knowledge', fd).then(r => r.data)
  },
  get(kbId: string) {
    return get<KnowledgeBase>(`/knowledge/${kbId}`)
  },
  update(kbId: string, name: string, description: string, tags: string) {
    const fd = new FormData()
    fd.append('name', name)
    fd.append('description', description)
    fd.append('tags', tags)
    return client.put<KnowledgeBase>(`/knowledge/${kbId}`, fd).then(r => r.data)
  },
  delete(kbId: string) {
    return del<{ ok: boolean }>(`/knowledge/${kbId}`)
  },
  uploadFile(kbId: string, file: File) {
    const fd = new FormData()
    fd.append('file', file)
    return client.post<KnowledgeFile>(`/knowledge/${kbId}/files`, fd).then(r => r.data)
  },
  deleteFile(kbId: string, fid: string) {
    return del<{ ok: boolean }>(`/knowledge/${kbId}/files/${fid}`)
  },
  getFileContent(kbId: string, fid: string) {
    return get<{ content: string; file_type: string; name: string }>(`/knowledge/${kbId}/files/${fid}/content`)
  },
  updateAsr(kbId: string, fid: string, asr_text: string) {
    return client.put<{ ok: boolean }>(`/knowledge/${kbId}/files/${fid}/asr`, { asr_text }).then(r => r.data)
  },
  voiceAudit(kbId: string, fid: string, asr_text: string, scenario = 'broadband') {
    return client.post<VoiceAuditResult>(`/knowledge/${kbId}/files/${fid}/voice-audit`, { asr_text, scenario }).then(r => r.data)
  },
  search(q: string) {
    return get<SearchResult[]>('/knowledge/search', { params: { q } })
  },
}
