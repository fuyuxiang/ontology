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
