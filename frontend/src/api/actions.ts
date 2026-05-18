import { get, post, put, del } from './client'

export interface ActionItem {
  id: string
  entity_id: string
  entity_name: string
  name: string
  type: string
  status: string
  impact_count: number | null
  parameters_json: any[] | null
  preconditions_json: any[] | null
  effects_json: any[] | null
  action_meta_json: Record<string, any> | null
  created_at: string | null
}

export interface ActionQuery {
  entity_id?: string
  status?: string
  type?: string
  search?: string
}

export interface ActionExecuteResult {
  success: boolean
  message: string
  effects: any[]
}

export const actionApi = {
  list(query?: ActionQuery) {
    return get<ActionItem[]>('/actions', { params: query })
  },

  detail(id: string) {
    return get<ActionItem>(`/actions/${id}`)
  },

  create(data: Partial<ActionItem>) {
    return post<ActionItem>('/actions', data)
  },

  update(id: string, data: Partial<ActionItem>) {
    return put<ActionItem>(`/actions/${id}`, data)
  },

  remove(id: string) {
    return del<void>(`/actions/${id}`)
  },

  execute(id: string, params: Record<string, any> = {}, dryRun = false) {
    return post<ActionExecuteResult>(`/actions/${id}/execute`, { params, dry_run: dryRun })
  },
}
