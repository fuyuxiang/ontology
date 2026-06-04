import type {
  AgentActivityResponse,
  AlertItem,
  LLMStatsResponse,
  OntologyStatsResponse,
  PlatformStatsResponse,
  ResourceMetrics,
  ServiceStatus,
} from '../../api/monitor'

export interface DashboardStateSnapshot {
  resources: ResourceMetrics | null
  services: ServiceStatus[]
  alerts: AlertItem[]
  llmStats: LLMStatsResponse | null
  ontologyStats: OntologyStatsResponse | null
  agentActivity: AgentActivityResponse | null
  platformStats: PlatformStatsResponse | null
}

export interface DashboardFetchSettled {
  resources: PromiseSettledResult<ResourceMetrics>
  services: PromiseSettledResult<ServiceStatus[]>
  alerts: PromiseSettledResult<AlertItem[]>
  llmStats: PromiseSettledResult<LLMStatsResponse>
  ontologyStats: PromiseSettledResult<OntologyStatsResponse>
  agentActivity: PromiseSettledResult<AgentActivityResponse>
  platformStats: PromiseSettledResult<PlatformStatsResponse>
}

function pickValue<T>(
  key: string,
  previous: T,
  result: PromiseSettledResult<T>,
  failedKeys: string[],
): T {
  if (result.status === 'fulfilled') {
    return result.value
  }
  failedKeys.push(key)
  return previous
}

export function mergeDashboardFetchState(
  previous: DashboardStateSnapshot,
  settled: DashboardFetchSettled,
): { next: DashboardStateSnapshot; failedKeys: string[] } {
  const failedKeys: string[] = []

  return {
    next: {
      resources: pickValue('resources', previous.resources, settled.resources, failedKeys),
      services: pickValue('services', previous.services, settled.services, failedKeys),
      alerts: pickValue('alerts', previous.alerts, settled.alerts, failedKeys),
      llmStats: pickValue('llmStats', previous.llmStats, settled.llmStats, failedKeys),
      ontologyStats: pickValue('ontologyStats', previous.ontologyStats, settled.ontologyStats, failedKeys),
      agentActivity: pickValue('agentActivity', previous.agentActivity, settled.agentActivity, failedKeys),
      platformStats: pickValue('platformStats', previous.platformStats, settled.platformStats, failedKeys),
    },
    failedKeys,
  }
}
