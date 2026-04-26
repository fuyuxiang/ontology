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
}

export interface ApiInfo {
  endpoint: string
  api_key: string
  curl: string
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
}
