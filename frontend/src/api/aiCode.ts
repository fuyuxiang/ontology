import { authenticatedFetch } from './authenticatedFetch'
import { get, post } from './client'
import { authHeaders } from '../utils/authHeaders'

export interface AiCodeGenerateRequest {
  target_type: 'function' | 'action'
  target_id: string
  message: string
  extra_entity_ids?: string[]
  execution_mode?: 'expression' | 'sql' | 'python' | 'custom_script'
}

export interface Violation {
  line: number
  reason: string
}

export interface ValidateResponse {
  safe: boolean
  violations: Violation[]
}

export interface ConversationMessage {
  execution_mode?: 'expression' | 'sql' | 'python' | 'custom_script'
  role: string
  content: string
  timestamp: string
}

export interface Conversation {
  id: string
  target_type: string
  target_id: string
  messages: ConversationMessage[]
  context_entity_ids: string[]
  updated_at: string | null
}

export const aiCodeApi = {
  async generatePost(req: AiCodeGenerateRequest, signal?: AbortSignal): Promise<Response> {
    const resp = await authenticatedFetch(`${import.meta.env.VITE_API_BASE_URL || "/api/v1"}/ai-code/generate`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(req),
      signal,
    })
    return resp
  },

  getConversation(targetType: string, targetId: string) {
    return get<Conversation | null>(`/ai-code/conversations/${targetType}/${targetId}`)
  },

  validate(code: string, executionMode: 'expression' | 'sql' | 'python' | 'custom_script' = 'python') {
    return post<ValidateResponse>('/ai-code/validate', { code, execution_mode:executionMode })
  },
}
