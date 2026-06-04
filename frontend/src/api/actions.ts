import request from '@/utils/request'

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
}

export const actionApi = {
  list: (params?: ActionQuery) => request.get<ActionItem[]>('/actions', { params }),
  detail: (id: string) => request.get<ActionItem>(`/actions/${id}`),
  create: (data: Partial<ActionItem>) => request.post<ActionItem>('/actions', data),
  update: (id: string, data: Partial<ActionItem>) => request.put<ActionItem>(`/actions/${id}`, data),
  remove: (id: string) => request.delete(`/actions/${id}`),
  execute: (id: string, params: Record<string, any>, dryRun = false) =>
    request.post<ActionExecuteResult>(`/actions/${id}/execute`, { params, dry_run: dryRun }),
  types: () => request.get<ActionTypeInfo[]>('/actions/types'),
}
