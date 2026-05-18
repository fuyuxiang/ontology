import client from './client'

export interface TraceItem {
  id: string
  agent_id: string
  agent_name: string
  input_text: string
  output_text: string
  latency_ms: number | null
  tokens_used: number | null
  status: string
  created_at: string | null
}

export interface TraceListResponse {
  total: number
  page: number
  page_size: number
  items: TraceItem[]
}

export interface EvalSuiteItem {
  id: string
  agent_id: string
  agent_name: string
  name: string
  case_count: number
  created_at: string | null
}

export interface EvalCaseItem {
  id: string
  input_prompt: string
  expected_keywords: string[]
  created_at: string | null
}

export interface EvalRunItem {
  id: string
  status: string
  metrics: { total: number; passed: number; pass_rate: number; avg_latency_ms: number } | null
  started_at: string | null
  finished_at: string | null
}

export interface EvalResultItem {
  id: string
  case_id: string
  input_prompt?: string
  actual_output: string
  passed: boolean
  latency_ms: number | null
  tokens_used: number | null
}

export interface EvalSuiteDetail {
  id: string
  agent_id: string
  agent_name: string
  name: string
  created_at: string | null
  cases: EvalCaseItem[]
  runs: EvalRunItem[]
}

export interface EvalRunDetail {
  id: string
  suite_id: string
  status: string
  metrics: { total: number; passed: number; pass_rate: number; avg_latency_ms: number } | null
  started_at: string | null
  finished_at: string | null
  results: EvalResultItem[]
}

export const tracesApi = {
  list: (params?: { agent_id?: string; status?: string; date_from?: string; date_to?: string; page?: number; page_size?: number }) =>
    client.get<TraceListResponse>('/traces', { params }).then(r => r.data),
  get: (id: string) =>
    client.get<TraceItem>(`/traces/${id}`).then(r => r.data),
}

export const evalsApi = {
  listSuites: (agentId?: string) =>
    client.get<EvalSuiteItem[]>('/evals/suites', { params: agentId ? { agent_id: agentId } : undefined }).then(r => r.data),
  createSuite: (data: { agent_id: string; name: string }) =>
    client.post<{ id: string }>('/evals/suites', data).then(r => r.data),
  getSuite: (id: string) =>
    client.get<EvalSuiteDetail>(`/evals/suites/${id}`).then(r => r.data),
  updateSuite: (id: string, data: { name: string }) =>
    client.put(`/evals/suites/${id}`, data).then(r => r.data),
  deleteSuite: (id: string) =>
    client.delete(`/evals/suites/${id}`).then(r => r.data),
  createCase: (suiteId: string, data: { input_prompt: string; expected_keywords?: string[] }) =>
    client.post<EvalCaseItem>(`/evals/suites/${suiteId}/cases`, data).then(r => r.data),
  updateCase: (caseId: string, data: { input_prompt?: string; expected_keywords?: string[] }) =>
    client.put(`/evals/cases/${caseId}`, data).then(r => r.data),
  deleteCase: (caseId: string) =>
    client.delete(`/evals/cases/${caseId}`).then(r => r.data),
  runSuite: (suiteId: string) =>
    client.post<EvalRunDetail>(`/evals/suites/${suiteId}/run`, null, { timeout: 120000 }).then(r => r.data),
  getRun: (runId: string) =>
    client.get<EvalRunDetail>(`/evals/runs/${runId}`).then(r => r.data),
}
