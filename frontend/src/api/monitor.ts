import { get } from './client'

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
  uptime_hours: number | null
}

export interface SecurityEvent {
  id: string
  event_type: string
  user_name: string | null
  target: string
  timestamp: string
  severity: string
}

export interface MonitorOverview {
  resources: ResourceMetrics
  services: ServiceStatus[]
  security_events: SecurityEvent[]
  system_info: Record<string, any>
}

export const monitorApi = {
  overview() {
    return get<MonitorOverview>('/monitor/overview')
  },
  resources() {
    return get<ResourceMetrics>('/monitor/resources')
  },
  services() {
    return get<ServiceStatus[]>('/monitor/services')
  },
  securityEvents() {
    return get<SecurityEvent[]>('/monitor/security-events')
  },
  systemInfo() {
    return get<Record<string, any>>('/monitor/system-info')
  },
}
