import { get, post } from './client'

export interface BroadbandOverview {
  total: number
  pending: number
  analyzing: number
  pending_todo: number
  completed: number
  error_count: number
  accuracy_rate: number
  avg_confidence: number
  today_new: number
}

export interface ChurnListItem {
  churn_id: string
  related_order_no: string
  churn_time: string | null
  churn_reason_text: string | null
  churn_category_l1: string | null
  churn_category_l2: string | null
  churn_phase: string | null
  audit_status: string | null
  root_cause_code: string | null
  root_cause_level_one: string | null
  root_cause_level_two: string | null
  root_cause_confidence: number | null
  biz_type: string | null
  install_address: string | null
  customer_name: string | null
  contact_phone: string | null
  engineer_name: string | null
}

export interface PaginatedList<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface CallSummary {
  total_call_count: number
  failed_call_count: number
  distinct_call_days: number
  has_valid_recording: boolean
  meets_unreachable_threshold: boolean
}

export interface ChurnDetail {
  churn: Record<string, any>
  order: Record<string, any> | null
  customer: Record<string, any> | null
  engineer: Record<string, any> | null
  address: Record<string, any> | null
  dispatch: Record<string, any> | null
  channel: Record<string, any> | null
  product: Record<string, any> | null
  call_summary: CallSummary | null
  engineer_calls: Record<string, any>[]
  callback_calls: Record<string, any>[]
  competitor_calls: Record<string, any>[]
  pending_pool: Record<string, any>[]
}

export interface BroadbandStats {
  cause_distribution: { name: string; value: number }[]
  subcategory_distribution: { name: string; category: string; value: number }[]
  trend_daily: { date: string; count: number }[]
  engineer_ranking: Record<string, any>[]
  channel_stats: Record<string, any>[]
  address_hotspots: Record<string, any>[]
  audit_status_distribution: { name: string; value: number }[]
}

export interface ListQuery {
  page?: number
  page_size?: number
  keyword?: string
  audit_status?: string
  root_cause_level_one?: string
  churn_phase?: string
  start_time?: string
  end_time?: string
}

export interface EvidenceItem {
  evidence_id: string
  churn_id: string
  evidence_code: string
  evidence_type: 'nlp' | 'rule' | 'manual'
  source_type: string | null
  source_id: string | null
  content: string | null
  raw_text: string | null
  hit: boolean
  confidence: number | null
  extracted_at: string
}

export interface LogicHit {
  hit_id: string
  churn_id: string
  evidence_id: string | null
  logic_function_id: string
  logic_function_name: string | null
  rule_expression: string | null
  hit_result: string | null
  confidence_delta: number
  executed_at: string
}

export interface AuditAction {
  action_id: string
  churn_id: string
  action_type_code: string
  action_name: string
  description: string | null
  priority: 'high' | 'medium' | 'low'
  status: 'pending_confirm' | 'pending_feedback' | 'feedback_submitted' | 'rejected'
  assignee: string | null
  created_at: string
  approved_at: string | null
  approved_by: string | null
  rejected_at: string | null
  rejected_by: string | null
  reject_reason: string | null
  params_json: Record<string, any> | null
}

export interface ActionExecution {
  execution_id: string
  action_id: string
  step_name: string | null
  status: 'executing' | 'completed' | 'failed'
  result_text: string | null
  writeback_content: string | null
  started_at: string
  completed_at: string | null
  executor: string | null
  log_text: string | null
}

export interface AuditTrailItem {
  trail_id: string
  churn_id: string
  event_type: string
  event_detail: string | null
  operator: string
  created_at: string
}

export interface AuditChain {
  perception: {
    source_types: Record<string, number>
    total_sources: number
    lf_001_status: string
  }
  recognition: {
    nlp_evidence: EvidenceItem[]
    rule_evidence: EvidenceItem[]
    nlp_count: number
    rule_count: number
    hit_count: number
    lf_002_status: string
    lf_003_status: string
  }
  reasoning: {
    logic_hits: LogicHit[]
    hypothesis_scores: Record<string, number>
    lf_004_status: string
    lf_005_status: string
  }
  output: {
    root_cause_code: string | null
    root_cause_level_one: string | null
    root_cause_level_two: string | null
    root_cause_confidence: number | null
    actions: AuditAction[]
    lf_007_status: string
  }
}

export interface InboxItem extends AuditAction {
  churn_time: string | null
  churn_reason_text: string | null
  churn_category_l1: string | null
  root_cause_level_one: string | null
  root_cause_level_two: string | null
  root_cause_confidence: number | null
  customer_name: string | null
}

export interface WorkbenchItem extends AuditAction {
  churn_time: string | null
  root_cause_level_one: string | null
  customer_name: string | null
  exec_count: number
}

export interface InboxQuery {
  page?: number
  page_size?: number
  action_type?: string
  priority?: string
  assignee?: string
  status?: string
}

export interface WorkbenchQuery {
  page?: number
  page_size?: number
  status?: string
}

export type SSEStepKey = 'perception' | 'recognition' | 'reasoning' | 'attribution' | 'todo' | 'done' | 'error'
export type SSEStatus = 'start' | 'progress' | 'streaming' | 'complete' | 'skip' | 'error'

export interface SSEEvent {
  step: SSEStepKey
  status: SSEStatus
  message?: string
  data?: unknown
}

export interface TodoAction {
  action_id: string
  churn_id: string
  todo_type: string
  action_type_code: string
  action_name: string
  description: string | null
  priority: string
  status: string
  trigger_rule: string
  expected_effect: string
  support_evidences: { code: string; name: string; role: string }[]
  display_data: Record<string, any>
  related_info: string
  feedback_data: Record<string, any> | null
  feedback_time: string | null
  assignee: string | null
  params_json: Record<string, any> | null
}


export interface OntologyNode {
  id: string
  type: string
  name: string
  attributes: Record<string, unknown>
}

export interface OntologyEdge {
  source: string
  target: string
  relation: string
}

export interface OntologyGraphData {
  nodes: OntologyNode[]
  edges: OntologyEdge[]
}

export interface VoiceAuditDimension {
  name: string
  result: 'pass' | 'fail' | 'na'
  comment: string
}

export interface VoiceAuditResult {
  call_id: string
  call_type: string
  overall: 'pass' | 'fail' | 'warning' | 'error'
  score: number
  summary: string
  dimensions: VoiceAuditDimension[]
  risk_flags: string[]
  skipped?: boolean
  error?: string
}

export const broadbandApi = {
  overview: () => get<BroadbandOverview>('/scenes/broadband/overview'),
  list: (params?: ListQuery) => get<PaginatedList<ChurnListItem>>('/scenes/broadband/list', { params }),
  detail: (id: string) => get<ChurnDetail>(`/scenes/broadband/detail/${id}`),
  stats: () => get<BroadbandStats>('/scenes/broadband/stats'),
  audit: (id: string, data: { action: string; override_label?: string; reason?: string }) =>
    post<{ ok: boolean }>(`/scenes/broadband/audit/${id}`, data),

  evidence: (id: string) =>
    get<{ items: EvidenceItem[]; total: number }>(`/scenes/broadband/detail/${id}/evidence`),
  chain: (id: string) =>
    get<AuditChain>(`/scenes/broadband/detail/${id}/chain`),
  logicHits: (id: string) =>
    get<{ items: LogicHit[]; total: number }>(`/scenes/broadband/detail/${id}/logic-hits`),
  actions: (id: string) =>
    get<{ items: AuditAction[]; total: number }>(`/scenes/broadband/detail/${id}/actions`),
  approveAction: (churnId: string, actionId: string, approvedBy?: string) =>
    post<{ ok: boolean }>(`/scenes/broadband/detail/${churnId}/actions/${actionId}/approve`, { approved_by: approvedBy || 'admin' }),
  rejectAction: (churnId: string, actionId: string, reason?: string, rejectedBy?: string) =>
    post<{ ok: boolean }>(`/scenes/broadband/detail/${churnId}/actions/${actionId}/reject`, { rejected_by: rejectedBy || 'admin', reason: reason || '' }),
  confirmAction: (churnId: string, actionId: string) =>
    post<{ ok: boolean }>(`/scenes/broadband/detail/${churnId}/actions/${actionId}/confirm`),
  submitFeedback: (churnId: string, actionId: string, data: { feedback_type: string; feedback_value: string; feedback_text: string }) =>
    post<{ ok: boolean; feedback_data: Record<string, any> }>(`/scenes/broadband/detail/${churnId}/actions/${actionId}/feedback`, data),
  reAttribute: (churnId: string) =>
    post<{ ok: boolean; updated_evidences: string[]; message: string }>(`/scenes/broadband/detail/${churnId}/re-attribute`),
  trail: (id: string) =>
    get<{ items: AuditTrailItem[]; total: number }>(`/scenes/broadband/detail/${id}/trail`),

  inbox: (params?: InboxQuery) =>
    get<PaginatedList<InboxItem>>('/scenes/broadband/inbox', { params }),
  batchApprove: (actionIds: string[], approvedBy?: string) =>
    post<{ ok: boolean; approved_count: number }>('/scenes/broadband/inbox/batch-approve', { action_ids: actionIds, approved_by: approvedBy || 'admin' }),
  workbench: (params?: WorkbenchQuery) =>
    get<PaginatedList<WorkbenchItem>>('/scenes/broadband/workbench', { params }),
  executionDetail: (actionId: string) =>
    get<{ action: AuditAction; executions: ActionExecution[] }>(`/scenes/broadband/workbench/${actionId}/execution`),

  ontologyGraph: (id: string) =>
    get<OntologyGraphData>(`/scenes/broadband/detail/${id}/ontology-graph`),

  voiceAudit: (id: string, calls: { call_id: string; call_type: string; asr_text: string; engineer_name?: string }[]) =>
    post<{ results: VoiceAuditResult[] }>(`/scenes/broadband/detail/${id}/voice-audit`, { calls }),

  startAnalysis: (
    churnId: string,
    onEvent: (event: SSEEvent) => void,
    onError: (err: Error) => void,
  ): AbortController => {
    const controller = new AbortController()
    const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'
    ;(async () => {
      try {
        const token = localStorage.getItem('token')
        const headers: Record<string, string> = { 'Content-Type': 'application/json' }
        if (token) headers['Authorization'] = `Bearer ${token}`
        const res = await fetch(`${baseURL}/scenes/broadband/analyze/${churnId}`, {
          method: 'POST',
          headers,
          signal: controller.signal,
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        if (!res.body) throw new Error('No response body')
        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const parts = buffer.split('\n\n')
          buffer = parts.pop() ?? ''
          for (const part of parts) {
            const lines = part.split('\n')
            let dataLine = ''
            for (const line of lines) {
              if (line.startsWith('data: ')) dataLine += line.slice(6)
            }
            if (dataLine) {
              try {
                const event = JSON.parse(dataLine) as SSEEvent
                onEvent(event)
              } catch { /* ignore parse errors */ }
            }
          }
        }
      } catch (err) {
        if ((err as Error).name !== 'AbortError') onError(err as Error)
      }
    })()
    return controller
  },
}
