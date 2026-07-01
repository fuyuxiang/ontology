import client from './client'

export interface ModelRegistry {
  id: string
  name: string
  provider: string
  model_name: string
  api_base: string | null
  api_key: string | null
  capabilities: string[]
  config_json: Record<string, any>
  status: string
  created_at: string
}

export interface ReferencedScene {
  id: string
  name: string
}

export interface OntologyBreakingChange {
  entity_name: string
  change_type: 'deleted' | 'renamed'
  new_name?: string
}

export interface OntologyStaleDetail {
  breaking_changes: OntologyBreakingChange[]
  affected_scenes?: number
  affected_agents?: number
}

export interface AgentItem {
  id: string
  name: string
  description: string
  tags: string[]
  model_id: string | null
  model_name: string | null
  system_prompt: string
  kb_ids: string[]
  entity_ids: string[]
  tools_config: Record<string, any>
  status: string
  api_key: string | null
  created_at: string
  updated_at: string
  referenced_scenes?: ReferencedScene[]
  ontology_stale?: boolean
  ontology_stale_detail?: OntologyStaleDetail | null
}

export interface ApiInfo {
  endpoint: string
  api_key: string
  curl: string
}

export interface ConversationSummary {
  id: string
  agent_id: string
  title: string
  created_at: string
  updated_at: string
}

export interface ConversationMessage {
  role: 'user' | 'assistant'
  content: string
  ts?: string
}

export interface ConversationDetail extends ConversationSummary {
  messages: ConversationMessage[]
}

export const modelsApi = {
  list: () => client.get<ModelRegistry[]>('/models').then(r => r.data),
  create: (data: Partial<ModelRegistry>) => client.post<ModelRegistry>('/models', data).then(r => r.data),
  update: (id: string, data: Partial<ModelRegistry>) => client.put<ModelRegistry>(`/models/${id}`, data).then(r => r.data),
  delete: (id: string) => client.delete(`/models/${id}`).then(r => r.data),
  test: (id: string) => client.post<{ ok: boolean; reply?: string; error?: string }>(`/models/${id}/test`).then(r => r.data),
}

export const agentsApi = {
  list: () => client.get<AgentItem[]>('/agents').then(r => r.data),
  create: (data: Partial<AgentItem>) => client.post<AgentItem>('/agents', data).then(r => r.data),
  get: (id: string) => client.get<AgentItem>(`/agents/${id}`).then(r => r.data),
  update: (id: string, data: Partial<AgentItem>) => client.put<AgentItem>(`/agents/${id}`, data).then(r => r.data),
  delete: (id: string) => client.delete(`/agents/${id}`).then(r => r.data),
  publish: (id: string) => client.post<AgentItem>(`/agents/${id}/publish`).then(r => r.data),
  apiInfo: (id: string) => client.get<ApiInfo>(`/agents/${id}/api-info`).then(r => r.data),
  chatUrl: (id: string) => `/api/v1/agents/${id}/chat`,
  acknowledgeStale: (id: string) =>
    client.post(`/agents/${id}/acknowledge-stale`).then(r => r.data),
  listConversations: (aid: string) =>
    client.get<ConversationSummary[]>(`/agents/${aid}/conversations`).then(r => r.data),
  createConversation: (aid: string) =>
    client.post<ConversationDetail>(`/agents/${aid}/conversations`).then(r => r.data),
  getConversation: (aid: string, cid: string) =>
    client.get<ConversationDetail>(`/agents/${aid}/conversations/${cid}`).then(r => r.data),
  deleteConversation: (aid: string, cid: string) =>
    client.delete(`/agents/${aid}/conversations/${cid}`).then(r => r.data),
}
