import { get, post } from './client'

export interface AiCodeGenerateRequest {
  target_type: 'function' | 'action'
  target_id: string
  message: string
  extra_entity_ids?: string[]
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
  async generatePost(req: AiCodeGenerateRequest): Promise<Response> {
    const resp = await fetch('/api/v1/ai-code/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    })
    return resp
  },

  getConversation(targetType: string, targetId: string) {
    return get<Conversation | null>(`/ai-code/conversations/${targetType}/${targetId}`)
  },

  validate(code: string) {
    return post<ValidateResponse>('/ai-code/validate', { code })
  },
}
