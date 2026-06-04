import { get, post, put, del } from './client'

export type RuleKind =
  | 'freshness' | 'row_count_min' | 'row_count_max'
  | 'null_ratio_max' | 'pk_uniqueness' | 'schema_stable'

export type HealthStatusValue = 'healthy' | 'warning' | 'failure' | 'unknown'

export interface QualityRule {
  id: string
  asset_id: string
  name: string
  kind: RuleKind
  column_name: string | null
  params: Record<string, unknown>
  severity: 'warning' | 'failure'
  enabled: boolean
  description: string | null
  created_at: string
  updated_at: string
}

export interface HealthStatus {
  id: string
  rule_id: string
  asset_id: string
  status: HealthStatusValue
  value_numeric: number | null
  message: string | null
  ran_at: string
}

export interface RuleKindTemplate {
  kind: RuleKind
  defaults: Record<string, unknown>
}

export interface AssetHealth {
  asset_id: string
  asset_name: string
  asset_kind: string
  domain: string | null
  status: HealthStatusValue
  rule_count: number
  by_status: Record<HealthStatusValue, number>
}

export interface RuleWithStatus {
  rule: QualityRule
  latest: HealthStatus | null
}

export interface AssetHealthDetail {
  asset: { id: string; name: string; alias: string | null; kind: string; domain: string | null }
  aggregate: { status: HealthStatusValue; rule_count: number; by_status: Record<HealthStatusValue, number> }
  rules: RuleWithStatus[]
}

export interface RuleCreate {
  asset_id: string
  name: string
  kind: RuleKind
  column_name?: string | null
  params?: Record<string, unknown>
  severity?: 'warning' | 'failure'
  description?: string | null
}

export interface RuleUpdate {
  name?: string
  params?: Record<string, unknown>
  severity?: 'warning' | 'failure'
  enabled?: boolean
  description?: string | null
}

// Dashboard types
export interface DashboardEntity {
  entity_id: string
  entity_name: string
  score: number
  dimensions: Record<string, HealthStatusValue>
  rule_count: number
  pass_count: number
}

export interface DashboardTrend {
  date: string
  score: number
  warnings: number
  failures: number
}

export interface DashboardIssue {
  id: string
  entity_name: string
  asset_name: string
  rule_kind: string
  column_name: string | null
  severity: string
  value: number | null
  threshold: number | null
  message: string
  occurred_at: string
}

export interface QualityDashboard {
  overall_score: number
  summary: Record<HealthStatusValue, number>
  entities: DashboardEntity[]
  trend: DashboardTrend[]
  recent_issues: DashboardIssue[]
}

export const qualityApi = {
  // Dashboard
  dashboard: () => get<QualityDashboard>('/data-plane/quality/dashboard'),
  evaluateAll: () => post<{ evaluated: number }>('/data-plane/quality/evaluate-all'),

  // Legacy
  ruleKinds: () => get<RuleKindTemplate[]>('/quality/rule_kinds'),
  listRules: (asset_id?: string) =>
    get<QualityRule[]>('/quality/rules', { params: asset_id ? { asset_id } : {} }),
  createRule: (body: RuleCreate) => post<QualityRule>('/quality/rules', body),
  updateRule: (id: string, body: RuleUpdate) => put<QualityRule>(`/quality/rules/${id}`, body),
  deleteRule: (id: string) => del<void>(`/quality/rules/${id}`),
  evaluateRule: (id: string) => post<HealthStatus>(`/quality/rules/${id}/evaluate`),
  evaluateAsset: (asset_id: string) => post<HealthStatus[]>(`/quality/assets/${asset_id}/evaluate`),
  overview: () => get<AssetHealth[]>('/quality/health/overview'),
  assetHealth: (asset_id: string) => get<AssetHealthDetail>(`/quality/health/asset/${asset_id}`),
  ruleHistory: (rule_id: string, limit = 100) =>
    get<HealthStatus[]>(`/quality/health/rules/${rule_id}/history`, { params: { limit } }),
}
