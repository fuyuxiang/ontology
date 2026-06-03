import { get, post } from './client'

export interface ResourceMetrics {
  cpu_percent: number
  memory_percent: number
  memory_used_gb: number
  memory_total_gb: number
  disk_percent: number
  disk_used_gb: number
  disk_total_gb: number
}

export interface ServiceStatus {
  name: string
  status: string
  response_ms: number | null
}

export interface ResponseHistoryPoint {
  service_name: string
  response_ms: number | null
  status: string
  collected_at: string
}

export interface AlertItem {
  id: number
  level: string
  service_name: string
  message: string
  resolved: boolean
  created_at: string
  resolved_at: string | null
}

export interface LLMStatsResponse {
  total_24h: number
  by_module: Record<string, {
    count: number
    total_prompt_tokens: number
    total_completion_tokens: number
    avg_latency_ms: number
  }>
}

export interface OntologyStatsResponse {
  total_entities: number
  by_type: Record<string, number>
}

export interface AgentActivityResponse {
  total_agents: number
  published_agents: number
  total_skills: number
}

export interface DashboardOverview {
  resources: ResourceMetrics
  services: ServiceStatus[]
  alerts: AlertItem[]
  llm_stats: LLMStatsResponse
  ontology_stats: OntologyStatsResponse
  agent_activity: AgentActivityResponse
}

export const monitorApi = {
  overview() {
    return get<DashboardOverview>('/monitor/overview')
  },
  resources() {
    return get<ResourceMetrics>('/monitor/resources')
  },
  services() {
    return get<ServiceStatus[]>('/monitor/services')
  },
  responseHistory(hours: number = 1, service?: string) {
    const params = new URLSearchParams({ hours: String(hours) })
    if (service) params.set('service', service)
    return get<ResponseHistoryPoint[]>(`/monitor/response-history?${params}`)
  },
  alerts(limit = 20, resolved?: boolean, level?: string) {
    const params = new URLSearchParams({ limit: String(limit) })
    if (resolved !== undefined) params.set('resolved', String(resolved))
    if (level) params.set('level', level)
    return get<AlertItem[]>(`/monitor/alerts?${params}`)
  },
  resolveAlert(id: number) {
    return post<AlertItem>(`/monitor/alerts/${id}/resolve`)
  },
  llmStats() {
    return get<LLMStatsResponse>('/monitor/llm-stats')
  },
  ontologyStats() {
    return get<OntologyStatsResponse>('/monitor/ontology-stats')
  },
  agentActivity() {
    return get<AgentActivityResponse>('/monitor/agent-activity')
  },
  systemInfo() {
    return get<Record<string, any>>('/monitor/system-info')
  },
}
