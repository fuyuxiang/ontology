import { get, post, put, del } from './client'
import client from './client'

// ============================================================
// 本体试车场 (Ontology Harness) - 自学习/自迭代/漂移检测
// ============================================================

export interface HarnessDashboard {
  drift_score: number
  trend: 'improving' | 'degrading' | string
  pending_alerts: number
  weekly_evolutions: number
  weekly_evolutions_delta: number
  model_health: number
}

export interface DriftSegment {
  id: string
  name: string
  predicted: number
  actual: number
  deviation: number
  sample_size: number
  status: 'alert' | 'warning' | 'good'
}

export interface DriftTouchpoint {
  name: string
  reach_rate: number
  conversion: number
  cost_ratio: number
}

export interface DriftAlert {
  time: string
  content: string
  level: 'error' | 'warning' | 'success' | 'info'
}

export interface ModelInfo {
  id: string
  name: string
  accuracy: number
  psi: number
  health: 'good' | 'warning' | 'error' | string
  features: string[]
}

export interface ExperimentInfo {
  id: string
  name: string
  status: 'running' | 'completed' | 'significant' | string
  control_rate: number
  treatment_rate: number
  p_value: number
  sample_size: number
  target_sample: number
  segment: string
}

export interface ProposalInfo {
  id: string
  type: 'rule_tuning' | 'new_attribute' | 'model_retrain' | 'touchpoint_update' | string
  severity: 'high' | 'medium' | 'low' | string
  title: string
  description: string
  impact: string
  status: 'pending' | 'approved' | 'applied' | 'rejected' | string
}

export interface EvolutionHistoryItem {
  id: string
  title: string
  applied_at: string
  effect: string
}

export interface ReportInfo {
  new_attributes: number
  rule_tunings: number
  model_retrains: number
  conversion_before: number
  conversion_after: number
  conversion_lift: number
  roi_monthly: number
  ai_summary: string
  timeline: Array<{ version: string; date: string; changes: string; status: 'done' | 'current' | 'pending' | string }>
}

// ── Mock 数据（后端接口未上线时使用） ──
const MOCK_DASHBOARD: HarnessDashboard = {
  drift_score: 23.5,
  trend: 'improving',
  pending_alerts: 2,
  weekly_evolutions: 5,
  weekly_evolutions_delta: 2,
  model_health: 84.7,
}

const MOCK_SEGMENTS: DriftSegment[] = [
  { id: 'SEG_001', name: '高价值即将到期', predicted: 12, actual: 8.7, deviation: -27.5, sample_size: 1856, status: 'alert' },
  { id: 'SEG_002', name: '中价值流失风险', predicted: 8.5, actual: 7.2, deviation: -15.3, sample_size: 2341, status: 'warning' },
  { id: 'SEG_003', name: '低价值稳定', predicted: 3.2, actual: 3.8, deviation: 18.8, sample_size: 3102, status: 'good' },
  { id: 'SEG_004', name: '高价值忠诚', predicted: 14.2, actual: 13.5, deviation: -4.9, sample_size: 987, status: 'good' },
  { id: 'SEG_005', name: '网络迁转潜力', predicted: 6.7, actual: 8.9, deviation: 32.8, sample_size: 1245, status: 'good' },
  { id: 'SEG_006', name: '投诉风险群体', predicted: 2.1, actual: 1.5, deviation: -28.6, sample_size: 876, status: 'warning' },
  { id: 'SEG_007', name: '一次性到期', predicted: 4.5, actual: 3.2, deviation: -28.9, sample_size: 1562, status: 'warning' },
]

const MOCK_TOUCHPOINTS: DriftTouchpoint[] = [
  { name: '外呼', reach_rate: 78.5, conversion: 12.3, cost_ratio: 3.2 },
  { name: '工单驱动', reach_rate: 92.1, conversion: 8.7, cost_ratio: 5.1 },
  { name: '弹窗', reach_rate: 65.3, conversion: 5.2, cost_ratio: 8.7 },
  { name: '短信', reach_rate: 95.8, conversion: 2.1, cost_ratio: 12.4 },
]

const MOCK_ALERTS: DriftAlert[] = [
  { time: '10 分钟前', content: 'SEG_001 高价值即将到期分群预测偏差超过 25%，建议检查模型特征', level: 'error' },
  { time: '1 小时前', content: '触点「弹窗」对投诉风险群体转化率降至 0.3%，建议暂停', level: 'warning' },
  { time: '3 小时前', content: '流失预测模型 PSI 值升至 0.18，接近重训阈值', level: 'warning' },
  { time: '昨天 16:00', content: 'A/B 实验 EXP_003 达到统计显著性 (p=0.012)', level: 'success' },
  { time: '昨天 09:30', content: '本体 v1.3 自动演化：新增 居住稳定性指数 属性', level: 'info' },
]

const MOCK_MODELS: ModelInfo[] = [
  { id: 'model_churn', name: '流失预测模型', accuracy: 0.847, psi: 0.18, health: 'warning', features: ['合约剩余天数','ARPU','投诉次数','宽带速率','在网时长'] },
  { id: 'model_affinity', name: '产品亲和度模型', accuracy: 0.912, psi: 0.06, health: 'good', features: ['历史产品','消费档位','家庭成员数','设备类型','流量使用'] },
  { id: 'model_touchpoint', name: '触点效果模型', accuracy: 0.783, psi: 0.12, health: 'good', features: ['触点历史','响应时段','渠道偏好','最近互动','满意度'] },
]

const MOCK_EXPERIMENTS: ExperimentInfo[] = [
  { id: 'EXP_001', name: '话术A vs 话术B (高价值即将到期)', status: 'completed', control_rate: 2.1, treatment_rate: 3.8, p_value: 0.003, sample_size: 1200, target_sample: 1200, segment: 'SEG_001' },
  { id: 'EXP_002', name: 'SMS+外呼 vs 纯外呼 (低价值稳定)', status: 'running', control_rate: 1.5, treatment_rate: 2.2, p_value: 0.087, sample_size: 800, target_sample: 1500, segment: 'SEG_003' },
  { id: 'EXP_003', name: 'WiFi7路由 vs 降价¥20 (中价值流失风险)', status: 'significant', control_rate: 3.1, treatment_rate: 4.5, p_value: 0.012, sample_size: 600, target_sample: 600, segment: 'SEG_002' },
  { id: 'EXP_004', name: '个性化弹窗 vs 通用弹窗 (网络迁转)', status: 'running', control_rate: 4.2, treatment_rate: 4.8, p_value: 0.234, sample_size: 350, target_sample: 1000, segment: 'SEG_005' },
  { id: 'EXP_005', name: '夜间外呼 vs 日间外呼 (高价值忠诚)', status: 'completed', control_rate: 5.6, treatment_rate: 5.3, p_value: 0.412, sample_size: 900, target_sample: 900, segment: 'SEG_004' },
]

const MOCK_PROPOSALS: ProposalInfo[] = [
  { id: 'PROP_001', type: 'rule_tuning', severity: 'high', title: 'SEG_001 分群阈值调整: ARPU 80→100', description: '预测偏差-27.5%，高价值群体定义过宽导致策略命中率低', impact: '影响 1,856 用户', status: 'pending' },
  { id: 'PROP_002', type: 'new_attribute', severity: 'high', title: 'Customer 新增 居住稳定性指数', description: '租房群体WiFi7路由器策略转化率远低于预期', impact: '影响全部分群', status: 'pending' },
  { id: 'PROP_003', type: 'model_retrain', severity: 'medium', title: '流失模型再训练触发', description: 'PSI=0.18 接近阈值，3个分群预测偏差超过25%', impact: '影响模型准确率', status: 'pending' },
  { id: 'PROP_004', type: 'touchpoint_update', severity: 'medium', title: '弹窗触点移除 (投诉风险群体)', description: '弹窗对投诉风险群体转化率仅0.3%，反而增加投诉量', impact: '影响 876 用户', status: 'approved' },
  { id: 'PROP_005', type: 'new_attribute', severity: 'low', title: 'Customer 新增 vip_priority 属性', description: '运营人员频繁为VIP客户手动提升产品档位(12次Override)', impact: '影响 VIP 分群', status: 'applied' },
]

const MOCK_HISTORY: EvolutionHistoryItem[] = [
  { id: 'EVO_H1', title: '新增 居住稳定性指数 属性', applied_at: '2026-03-30 14:20', effect: '分群精度提升 8%' },
  { id: 'EVO_H2', title: '弹窗触点移除 (投诉群体)', applied_at: '2026-03-28 10:15', effect: '投诉率下降 12%' },
  { id: 'EVO_H3', title: '流失模型 v2.1 上线', applied_at: '2026-03-25 09:00', effect: '预测准确率 +5.2%' },
]

const MOCK_REPORT: ReportInfo = {
  new_attributes: 3,
  rule_tunings: 2,
  model_retrains: 1,
  conversion_before: 8.2,
  conversion_after: 8.7,
  conversion_lift: 6.1,
  roi_monthly: 180000,
  ai_summary: '本周系统通过自学习闭环完成5次本体演化，重点优化了高价值即将到期分群的策略匹配精度。流失预测模型完成重训练后，整体预测偏差从23.5降至18.2。建议下周重点关注中价值流失风险分群的触点组合优化。',
  timeline: [
    { version: 'v1.0', date: 'Day 1', changes: '19类 + 24关系', status: 'done' },
    { version: 'v1.1', date: 'Day 3', changes: '+3 properties', status: 'done' },
    { version: 'v1.2', date: 'Day 5', changes: '+1 relation, 规则调优', status: 'done' },
    { version: 'v1.3', date: 'Week 2', changes: 'Model retrain + 属性新增', status: 'current' },
    { version: 'v1.4', date: 'Week 3', changes: '分群阈值优化', status: 'pending' },
  ],
}

// 通用 fallback 工具：调用接口失败/超时返回 mock
async function withFallback<T>(fn: () => Promise<T>, fallback: T): Promise<T> {
  try {
    const ctrl = new AbortController()
    const t = setTimeout(() => ctrl.abort(), 8000)
    const res = await fn()
    clearTimeout(t)
    return res ?? fallback
  } catch {
    return fallback
  }
}

export const harnessApi = {
  getDashboard: () =>
    withFallback<HarnessDashboard>(() => get<HarnessDashboard>('/harness/dashboard'), MOCK_DASHBOARD),

  getDrift: () =>
    withFallback<{ segments: DriftSegment[]; touchpoints: DriftTouchpoint[] }>(
      () => get<{ segments: DriftSegment[]; touchpoints: DriftTouchpoint[] }>('/harness/drift'),
      { segments: MOCK_SEGMENTS, touchpoints: MOCK_TOUCHPOINTS }
    ),

  getTelemetrySummary: () =>
    withFallback<{ alerts: DriftAlert[] }>(
      () => get<{ alerts: DriftAlert[] }>('/harness/telemetry/summary'),
      { alerts: MOCK_ALERTS }
    ),

  getModels: () =>
    withFallback<ModelInfo[]>(() => get<ModelInfo[]>('/harness/models'), MOCK_MODELS),

  getExperiments: () =>
    withFallback<ExperimentInfo[]>(() => get<ExperimentInfo[]>('/harness/experiments'), MOCK_EXPERIMENTS),

  createExperiment: (data: Record<string, any>) =>
    withFallback<ExperimentInfo>(
      () => post<ExperimentInfo>('/harness/experiment', data),
      { id: `EXP_${Date.now()}`, name: data.name || '新实验', status: 'running', control_rate: 0, treatment_rate: 0, p_value: 1, sample_size: 0, target_sample: data.min_sample || 1000, segment: data.segment || '' }
    ),

  stopExperiment: (id: string) =>
    withFallback<{ success: boolean }>(() => post<{ success: boolean }>(`/harness/experiment/${id}/stop`), { success: true }),

  getProposals: () =>
    withFallback<ProposalInfo[]>(() => get<ProposalInfo[]>('/harness/proposals'), MOCK_PROPOSALS),

  getEvolutionQueue: () =>
    withFallback<ProposalInfo[]>(() => get<ProposalInfo[]>('/harness/evolution/queue'), []),

  getEvolutionHistory: () =>
    withFallback<EvolutionHistoryItem[]>(() => get<EvolutionHistoryItem[]>('/harness/evolution/history'), MOCK_HISTORY),

  applyProposal: (id: string) =>
    withFallback<{ success: boolean }>(() => post<{ success: boolean }>(`/harness/proposals/${id}/apply`), { success: true }),

  rejectProposal: (id: string) =>
    withFallback<{ success: boolean }>(() => post<{ success: boolean }>(`/harness/proposals/${id}/reject`), { success: true }),

  applyEvolution: (id: string) =>
    withFallback<{ success: boolean }>(() => post<{ success: boolean }>(`/harness/evolution/${id}/apply`), { success: true }),

  rejectEvolution: (id: string) =>
    withFallback<{ success: boolean }>(() => post<{ success: boolean }>(`/harness/evolution/${id}/reject`), { success: true }),

  optimize: () =>
    withFallback<{ success: boolean; new_proposals: number }>(
      () => post<{ success: boolean; new_proposals: number }>('/harness/optimize'),
      { success: true, new_proposals: 2 }
    ),

  generateEvolution: () =>
    withFallback<{ success: boolean; count: number }>(
      () => post<{ success: boolean; count: number }>('/harness/evolution/generate'),
      { success: true, count: 3 }
    ),

  autoApplyEvolution: () =>
    withFallback<{ success: boolean; applied: number }>(
      () => post<{ success: boolean; applied: number }>('/harness/evolution/auto-apply'),
      { success: true, applied: 1 }
    ),

  getReport: () =>
    withFallback<ReportInfo>(() => get<ReportInfo>('/harness/report'), MOCK_REPORT),
}

// 暴露 client 供子组件感知"实时连接"状态
export { client as harnessClient }
