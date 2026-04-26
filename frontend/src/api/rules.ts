import { get, post, put, del } from './client'
import type { BusinessRule, RuleStatus, Priority } from '../types'

export interface RuleQuery {
  entityId?: string
  status?: RuleStatus
  priority?: Priority
  search?: string
}

export interface RuleExecuteResult {
  success: boolean
  affectedCount: number
  message: string
}

export const ruleApi = {
  list(query?: RuleQuery) {
    return get<BusinessRule[]>('/rules', { params: query })
  },

  detail(id: string) {
    return get<BusinessRule>(`/rules/${id}`)
  },

  create(data: Partial<BusinessRule>) {
    return post<BusinessRule>('/rules', data)
  },

  update(id: string, data: Partial<BusinessRule>) {
    return put<BusinessRule>(`/rules/${id}`, data)
  },

  remove(id: string) {
    return del<void>(`/rules/${id}`)
  },

  execute(id: string) {
    return post<RuleExecuteResult>(`/rules/${id}/execute`)
  },
}
