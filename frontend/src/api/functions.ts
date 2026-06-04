import { get, post, put, del } from './client'

export interface FunctionItem {
  id: string
  entity_id: string | null
  entity_name: string
  name: string
  callable_name: string
  description: string
  return_type: string
  input_schema: any[] | null
  logic_type: string
  logic_body: string
  is_derived_property: boolean
  status: string
  execution_count: number
  last_executed: string | null
  tags: string[] | null
  ref_count: number
  created_at: string | null
  updated_at: string | null
}

export interface FunctionQuery {
  entity_id?: string
  status?: string
  is_derived?: boolean
  search?: string
}

export interface FunctionTestResult {
  success: boolean
  result: any
  error: string | null
  execution_ms: number
}

export const functionApi = {
  list(query?: FunctionQuery) {
    return get<FunctionItem[]>('/functions', { params: query })
  },

  detail(id: string) {
    return get<FunctionItem>(`/functions/${id}`)
  },

  create(data: Partial<FunctionItem>) {
    return post<FunctionItem>('/functions', data)
  },

  update(id: string, data: Partial<FunctionItem>) {
    return put<FunctionItem>(`/functions/${id}`, data)
  },

  remove(id: string) {
    return del<void>(`/functions/${id}`)
  },

  test(id: string, params: Record<string, any> = {}) {
    return post<FunctionTestResult>(`/functions/${id}/test`, { params })
  },
}
