import { get } from './client'

export interface MnpUserBrief {
  user_id: string
  name?: string
  phone?: string
  innet_months?: number
  is_5g?: boolean
  pay_mode?: string
}

export interface MnpRuleCondition {
  condition: string
  sourceEntity: string
  sourceAttribute: string
  operator: string
  threshold: string
  actual: string
  matched: boolean
}

export interface MnpRuleResult {
  ruleName: string
  riskLevel: string | null
  triggered: boolean
  matchedCount: number
  totalCount: number
  conditions: MnpRuleCondition[]
}

export interface MnpExecuteResult {
  user_id: string
  entities: Record<string, Record<string, any>>
  ruleResults: MnpRuleResult[]
  finalRiskLevel: string
  riskScore: number
  churnReasonTop3: string[]
  recommendedActions: string[]
  assignedChannel: string
}

export interface MnpCaseUser {
  user_id: string
  name?: string
  phone?: string
  innet_months?: number
  is_5g?: boolean
  pay_mode?: string
  finalRiskLevel: string
  riskScore: number
}

export const sceneApi = {
  mnpUsers(limit = 10) {
    return get<MnpUserBrief[]>('/scenes/mnp/users', { params: { limit } })
  },

  mnpCaseUsers() {
    return get<MnpCaseUser[]>('/scenes/mnp/case-users')
  },

  mnpExecute(userId: string) {
    return get<MnpExecuteResult>('/scenes/mnp/execute', { params: { user_id: userId } })
  },
}
