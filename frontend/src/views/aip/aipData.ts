/**
 * AIP 场景平台 — 静态元数据（场景列表 / 节点工具箱 / 模型选项 / 触发预设）
 * 移植自 /Users/fuyuxiang/Desktop/html/assets/StrategyEngine-NcqpHMXC.js
 */

export type SceneStatus = 'published' | 'draft'

export interface SceneMeta {
  id: string
  name: string
  group: string
  status: SceneStatus
  description: string
  ontologyBindings: string[]
  stats: Record<string, string | number>
  triggerConfig: TriggerConfig
  createdAt: string
  updatedAt: string
}

export interface TriggerConfig {
  type: 'schedule' | 'event' | 'webhook' | 'manual'
  enabled: boolean
  schedule?: { frequency: 'daily' | 'weekly' | 'monthly' | 'custom'; hour: number; minute: number; timezone: string; cron?: string }
  event?: { objectType: string; trigger: 'created' | 'updated' | 'deleted' }
  webhook?: { url: string; secret: string }
}

export interface ExecHistory {
  id: string
  startedAt: string
  durationSec: number
  status: 'success' | 'error' | 'running'
  trigger: string
  nodes: number
}

export const SCENE_GROUPS = [
  { label: '退单智能归因', sceneIds: ['refund_attribution'] },
  { label: '政企智能问数', sceneIds: ['ge_insight_qa'] },
  { label: 'FTTR续约策划', sceneIds: ['fttr_renewal'] },
] as const

export const SCENE_LIST: SceneMeta[] = [
  {
    id: 'refund_attribution',
    name: '宽带装机退单智能归因',
    group: '退单智能归因',
    status: 'published',
    description: '基于装机工单和 4 类外呼通话记录，37 条证据抽取（26 条大模型理解 + 11 条规则计算）配合 23 项二级 / 4 项一级分层归因推理，识别资源 / 施工 / 用户 / 业务四类根因，驱动自动归档 / 现场核实 / 强制回访 / 营销外呼 4 条动作闭环',
    ontologyBindings: ['InstallOrder', 'InstallChurn', 'Customer', 'Product', 'Channel', 'DispatchRecord', 'Engineer', 'Address', 'PendingPool', 'EngineerCall', 'CallbackCall', 'MarketingCall', 'CompetitorCall'],
    stats: { orders: 8536, accuracy: '90%+', functions: 37, reasons: 23 },
    triggerConfig: { type: 'schedule', enabled: true, schedule: { frequency: 'daily', hour: 10, minute: 0, timezone: 'Asia/Shanghai' } },
    createdAt: '2026-02-15',
    updatedAt: '2026-04-17',
  },
  {
    id: 'ge_insight_qa',
    name: '政企智能问数及归因分析',
    group: '政企智能问数',
    status: 'published',
    description: '4 节点流水线：本体语义理解与上下文组装（9 类政企本体）→ 政企数据分析 Agent（3 技能：语义化查询/异动检测/多维归因融合）→ 政企归因推理 Agent（2 技能 + 4 函数：交叉归因 + 根因置信度评估）→ 业务规则分支（5 条）→ 5 个动作执行（数据稽核/澄清定责/催缴升级/综合研判/归档结论）',
    ontologyBindings: ['KPIIndicatorDef', 'GeCustomerSegment', 'GeProject', 'GeOpportunity', 'Contract', 'GeProductService', 'GeAccountManager', 'GeBusinessEvent', 'GeRegionOrg'],
    stats: { queries: 1247, branches: 5, actions: 5 },
    triggerConfig: { type: 'schedule', enabled: true, schedule: { frequency: 'daily', hour: 9, minute: 0, timezone: 'Asia/Shanghai' } },
    createdAt: '2026-03-10',
    updatedAt: '2026-04-23',
  },
  {
    id: 'fttr_renewal',
    name: '包头 FTTR 或组网到期续约',
    group: 'FTTR续约策划',
    status: 'published',
    description: 'FTTR 到期客户续约智能策划 v1.3：⓪ 本体查询（BR-MOMENT-001~004 四类时机）→ ① 客群洞察 → ② 产品推荐 → ③ 触点选择 → ④ 八段式话术 → ⑤ 续约策略执行包',
    ontologyBindings: ['Customer', 'Segment', 'Contract', 'FTTRSubscription', 'Product', 'Strategy', 'Script', 'Channel', 'TouchEvent', 'WorkOrder', 'RenewalStrategyPackage', 'Order'],
    stats: { users: 40929, conversion: '4.64%', strategies: 7 },
    triggerConfig: { type: 'schedule', enabled: true, schedule: { frequency: 'daily', hour: 8, minute: 0, timezone: 'Asia/Shanghai' } },
    createdAt: '2025-12-01',
    updatedAt: '2026-04-26',
  },
]

export const EXEC_HISTORY: Record<string, ExecHistory[]> = {
  fttr_renewal: [
    { id: 'h1', startedAt: '2026-04-15 08:00:23', durationSec: 16, status: 'success', trigger: 'schedule', nodes: 4 },
    { id: 'h2', startedAt: '2026-04-14 08:00:15', durationSec: 14, status: 'success', trigger: 'schedule', nodes: 4 },
    { id: 'h3', startedAt: '2026-04-13 14:32:08', durationSec: 8, status: 'error', trigger: 'manual', nodes: 4 },
    { id: 'h4', startedAt: '2026-04-12 08:00:11', durationSec: 15, status: 'success', trigger: 'schedule', nodes: 4 },
    { id: 'h5', startedAt: '2026-04-11 08:00:19', durationSec: 17, status: 'success', trigger: 'schedule', nodes: 4 },
  ],
  refund_attribution: [
    { id: 'rfh1', startedAt: '2026-04-17 10:00:32', durationSec: 22, status: 'success', trigger: 'schedule', nodes: 8 },
    { id: 'rfh2', startedAt: '2026-04-16 10:00:18', durationSec: 19, status: 'success', trigger: 'schedule', nodes: 8 },
    { id: 'rfh3', startedAt: '2026-04-15 10:00:25', durationSec: 25, status: 'error', trigger: 'schedule', nodes: 8 },
  ],
  ge_insight_qa: [
    { id: 'geh1', startedAt: '2026-04-23 09:00:12', durationSec: 12, status: 'success', trigger: 'schedule', nodes: 9 },
    { id: 'geh2', startedAt: '2026-04-22 09:00:09', durationSec: 14, status: 'success', trigger: 'schedule', nodes: 9 },
  ],
}

/* ========== 节点工具箱 ========== */
export interface NodeTypeMeta {
  type: string
  label: string
  group: string
  color: string
  icon: string
  description: string
}

export const NODE_TYPES: NodeTypeMeta[] = [
  { type: 'ontologyQuery', label: '本体查询', group: '数据节点', color: '#2E5BFF', description: '查询本体对象实例', icon: 'database' },
  { type: 'datasource', label: '数据源查询', group: '数据节点', color: '#2E5BFF', description: '直接 SQL 查询', icon: 'database' },
  { type: 'llmAgent', label: '模型节点', group: '逻辑节点', color: '#FF8900', description: '大模型推理', icon: 'brain' },
  { type: 'function', label: 'Function 计算', group: '函数节点', color: '#0EA5E9', description: '调用 OntologyFunction', icon: 'tool' },
  { type: 'agentNode', label: 'Agent 节点', group: 'Agent 节点', color: '#10B981', description: '本体驱动 ReAct 推理', icon: 'robot' },
  { type: 'skillNode', label: 'Skill 节点', group: 'Agent 子节点', color: '#10B981', description: 'Skill 注册', icon: 'thunder' },
  { type: 'toolNode', label: 'Tool 节点', group: 'Agent 子节点', color: '#0EA5E9', description: 'Tool 注册', icon: 'tool' },
  { type: 'condition', label: '条件分支', group: '控制节点', color: '#64748B', description: '条件判断分流', icon: 'branch' },
  { type: 'parallel', label: '并行网关', group: '控制节点', color: '#64748B', description: '下游并行执行', icon: 'branch' },
  { type: 'loop', label: '循环节点', group: '控制节点', color: '#64748B', description: '对列表逐项执行', icon: 'branch' },
  { type: 'writebackOntology', label: '写回本体', group: '动作节点', color: '#059669', description: '写回本体对象', icon: 'save' },
  { type: 'actionSystem', label: '动作执行', group: '动作节点', color: '#059669', description: '调用 EntityAction', icon: 'send' },
  { type: 'httpCall', label: 'HTTP 调用', group: '动作节点', color: '#059669', description: '调用外部 API', icon: 'send' },
  { type: 'subscene', label: '子场景', group: '编排节点', color: '#7C3AED', description: '嵌套执行其他场景', icon: 'robot' },
]

export const NODE_GROUPS = ['数据节点', '逻辑节点', '函数节点', 'Agent 节点', 'Agent 子节点', '控制节点', '动作节点', '编排节点']

/* ========== LLM / ML 模型选项 ========== */
export const LLM_MODELS = [
  { value: 'deepseek-v3', label: '元景大模型 DeepSeek-V3-0324', color: '#7C3AED' },
  { value: 'qwen2.5-72b', label: 'Qwen2.5-72B', color: '#0EA5E9' },
  { value: 'minimax', label: 'MiniMax', color: '#F59E0B' },
  { value: 'glm-4', label: 'GLM-4', color: '#10B981' },
]

export const ML_MODELS = [
  { value: 'churn_predictor_v2', label: '流失预测 v2 (AUC 0.821)' },
  { value: 'product_affinity_v1', label: '产品亲和度 v1 (AUC 0.791)' },
  { value: 'touchpoint_effect_v1', label: '触点效果 v1' },
  { value: 'arpu_predictor_v1', label: 'ARPU 预测 v1' },
  { value: 'kpi_anomaly_detector_v1', label: 'KPI 异动检测 v1' },
  { value: 'kpi_contribution_decomposer_v1', label: '贡献度分解 v1' },
  { value: 'install_success_predictor_v1', label: '装机成功率预测 v1' },
  { value: 'refund_risk_classifier_v1', label: '退单风险分类 v1' },
]

export const OPERATORS = ['==', '!=', '>', '<', '>=', '<=', 'IN', 'NOT_IN', 'BETWEEN', 'switch']

export const ACTION_TYPES = [
  { value: 'sms', label: '短信通知' },
  { value: 'app_push', label: 'APP 推送' },
  { value: 'work_order', label: '生成工单' },
  { value: 'api_call', label: 'API 调用' },
  { value: 'email', label: '邮件通知' },
]

export const HTTP_METHODS = [
  { value: 'GET', label: 'GET' },
  { value: 'POST', label: 'POST' },
  { value: 'PUT', label: 'PUT' },
  { value: 'DELETE', label: 'DELETE' },
  { value: 'PATCH', label: 'PATCH' },
]
