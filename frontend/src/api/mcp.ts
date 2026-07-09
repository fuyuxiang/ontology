import { get } from './client'

export interface McpOverview {
  total_calls_today: number
  total_calls_yesterday: number
  avg_response_ms: number
  error_rate: number
  active_connections: number
}

export interface McpTrendPoint { time: string; count: number }
export interface McpTrendResponse { range: string; data: McpTrendPoint[] }

export interface McpToolStat {
  tool_name: string
  call_count: number
  avg_ms: number
  error_count: number
  last_called: string | null
  percentage: number
}

export interface McpToolSchema {
  name: string
  description: string
  inputSchema: {
    type: string
    properties: Record<string, any>
    required?: string[]
  }
}

export function getMcpOverview() {
  return get<McpOverview>('/mcp/stats/overview')
}

export function getMcpTrend(range: '1h' | '24h' | '7d' = '24h') {
  return get<McpTrendResponse>(`/mcp/stats/trend?range=${range}`)
}

export function getMcpToolStats() {
  return get<McpToolStat[]>('/mcp/stats/tools')
}

export function getMcpTools() {
  return get<{ tools: McpToolSchema[] }>('/mcp/tools')
}
