/**
 * AIP 场景平台 — 编辑器静态元数据（节点工具箱 / 模型选项 / 控件枚举）
 *
 * 注意：场景列表、执行历史等业务数据一律来自后端 API（GET /aip/scenes），
 * 不得在此文件中预置。
 */

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

/* ========== ML 模型选项 ========== */
export const ML_MODELS = [
  { value: 'churn_predictor_v2', label: '流失预测 v2' },
  { value: 'product_affinity_v1', label: '产品亲和度 v1' },
  { value: 'touchpoint_effect_v1', label: '触点效果 v1' },
  { value: 'arpu_predictor_v1', label: 'ARPU 预测 v1' },
  { value: 'kpi_anomaly_detector_v1', label: 'KPI 异动检测 v1' },
  { value: 'kpi_contribution_decomposer_v1', label: '贡献度分解 v1' },
  { value: 'install_success_predictor_v1', label: '装机成功率预测 v1' },
  { value: 'refund_risk_classifier_v1', label: '退单风险分类 v1' },
]

/* ========== 控件枚举 ========== */
export const OPERATORS = ['==', '!=', '>', '<', '>=', '<=', 'IN', 'NOT_IN', 'BETWEEN', 'switch']

export const HTTP_METHODS = [
  { value: 'GET', label: 'GET' },
  { value: 'POST', label: 'POST' },
  { value: 'PUT', label: 'PUT' },
  { value: 'DELETE', label: 'DELETE' },
  { value: 'PATCH', label: 'PATCH' },
]
