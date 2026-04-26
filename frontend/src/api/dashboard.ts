import { get, put } from './client'

export interface DashboardStatsEx {
  entity_count: number
  relation_count: number
  rule_count: number
  active_rule_count: number
  action_count: number
  attr_count: number
  datasource_count: number
  tier_distribution: { tier: number; name: string; count: number; pct: number }[]
  ns_distribution: { ns: string; count: number }[]
  rule_priority: { priority: string; count: number }[]
  top_rules: { id: string; name: string; trigger_count: number; status: string; priority: string }[]
  health_status: { id: string; name: string; name_cn: string; tier: number; status: string }[]
  recent_activities: { id: string; type: string; target_type: string; target_name: string; user: string; time: string }[]
  datasources: { id: string; name: string; type: string; status: string }[]
}

export interface CardItemConfig {
  type: 'dynamic' | 'static' | 'top_rules' | 'datasources' | 'rule_priority' | 'recent_activities'
  field?: string
  label?: string
  text?: string
  count?: number
}

export interface CardConfig {
  key: string
  title: string
  enabled: boolean
  items: CardItemConfig[]
}

export interface DashboardConfig {
  cards_config: CardConfig[]
  refresh_interval: number
}

export const dashboardApi = {
  stats() {
    return get<DashboardStatsEx>('/dashboard/stats')
  },
  getConfig() {
    return get<DashboardConfig>('/dashboard/config')
  },
  saveConfig(data: DashboardConfig) {
    return put<{ ok: boolean }>('/dashboard/config', data)
  },
}

