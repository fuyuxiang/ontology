import { get, post, put, del } from './client'

export interface ParameterDef {
  name: string
  type: string
  required: boolean
  default_value?: string
  description?: string
  entity_attribute_id?: string
}

export interface OutputFieldDef {
  name: string
  type: string
  description?: string
}

export interface ActionItem {
  id: string
  name: string
  description?: string
  category: 'domain' | 'system'
  entity_id?: string
  ontology_id?: string | null
  entity_name?: string
  action_type: string
  type_config?: Record<string, any>
  parameters_json?: ParameterDef[]
  output_schema?: OutputFieldDef[]
  status: string
  impact_count: number
  created_at: string
  updated_at?: string
}

export interface ActionQuery {
  entity_id?: string
  status?: string
  action_type?: string
  category?: string
  search?: string
  ontology_id?: string
}

export interface ActionTypeInfo {
  type_key: string
  label: string
  description: string
  config_schema: Record<string, any>
}

export interface ActionExecuteResult {
  success: boolean
  message: string
  output?: Record<string, any>
  execution_id?: string
  state?: string
}

export const actionApi = {
  list: (params?: ActionQuery) => get<ActionItem[]>('/actions', { params }),
  detail: (id: string) => get<ActionItem>(`/actions/${id}`),
  create: (data: Partial<ActionItem>) => post<ActionItem>('/actions', data),
  update: (id: string, data: Partial<ActionItem>) => put<ActionItem>(`/actions/${id}`, data),
  remove: (id: string) => del(`/actions/${id}`),
  execute: (id: string, params: Record<string, any>, dryRun = false, idempotencyKey?:string) =>
    post<ActionExecuteResult>(`/actions/${id}/execute`, { params, dry_run: dryRun, ...(idempotencyKey ? {idempotency_key:idempotencyKey}: {}) }),
  executionByKey: (id:string, key:string) => get<ActionExecuteResult & {params:Record<string, unknown>}>(`/actions/${id}/executions/by-key`, {params:{key}}),
  reconcile: (id:string,executionId:string,body:{resolution:'succeeded'|'failed';evidence:string;receipt_id?:string}) => post<ActionExecuteResult>(`/actions/${id}/executions/${executionId}/reconcile`,body),
  types: () => get<ActionTypeInfo[]>('/actions/types'),
  openWorkspace: (id: string) => post<{ folder: string; port: number; public_url?: string; registration_error?: string }>(`/actions/${id}/workspace`),
}
