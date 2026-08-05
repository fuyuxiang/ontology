import { get, post, put, del } from './client'

export interface Scenario {
  id: string
  code: string
  name: string
  color: string | null
  description: string | null
  sort_order: number
  created_at: string
  updated_at: string
  // 本体下各类组件数量，由后端列表接口聚合返回
  entity_count: number
  relation_count: number
  logic_count: number
  action_count: number
}

export interface ScenarioCreate {
  code: string
  name: string
  color?: string | null
  description?: string | null
  sort_order?: number
}

export interface ScenarioUpdate {
  name?: string
  color?: string | null
  description?: string | null
  sort_order?: number
}

export const scenarioApi = {
  list() {
    return get<Scenario[]>('/scenarios')
  },
  create(data: ScenarioCreate) {
    return post<Scenario>('/scenarios', data)
  },
  update(id: string, data: ScenarioUpdate) {
    return put<Scenario>(`/scenarios/${id}`, data)
  },
  remove(id: string) {
    return del<void>(`/scenarios/${id}`)
  },
}
