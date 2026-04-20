import { get, post, put, del } from './client'

export interface WorkflowBrief {
  id: string
  name: string
  description: string
  namespace: string
  group_name: string
  status: string
  node_count: number
  created_at: string
  updated_at: string
}

export interface WorkflowFull extends WorkflowBrief {
  nodes_json: any[]
  edges_json: any[]
  trigger_config: Record<string, any>
}

export interface WorkflowExecution {
  id: string
  status: string
  triggered_by: string
  started_at: string
  finished_at: string | null
  error_message: string | null
  node_count: number
}

export const workflowApi = {
  list: (params?: { status?: string; group?: string }) =>
    get<WorkflowBrief[]>('/workflows', { params }),

  get: (id: string) => get<WorkflowFull>(`/workflows/${id}`),

  create: (data: { name: string; description?: string; namespace?: string; group_name?: string }) =>
    post<WorkflowFull>('/workflows', data),

  update: (id: string, data: Partial<WorkflowFull>) =>
    put<WorkflowFull>(`/workflows/${id}`, data),

  delete: (id: string) => del(`/workflows/${id}`),

  publish: (id: string) => post(`/workflows/${id}/publish`),

  listExecutions: (id: string) =>
    get<WorkflowExecution[]>(`/workflows/${id}/executions`),

  getExecution: (wid: string, eid: string) =>
    get(`/workflows/${wid}/executions/${eid}`),
}
