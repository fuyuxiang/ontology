// ── 本体核心类型定义 ──

export type Tier = 1 | 2 | 3
export type EntityStatus = 'active' | 'warning' | 'error'
export type RuleStatus = 'active' | 'warning' | 'disabled'
export type Priority = 'high' | 'medium' | 'low'
export type Cardinality = '1:1' | '1:N' | 'N:1' | 'N:N'
export type RelationType = 'has_one' | 'has_many' | 'belongs_to' | 'many_to_many'
export type AttrType = 'string' | 'number' | 'boolean' | 'date' | 'ref' | 'computed' | 'enum' | 'json'

// ── 属性约束（借鉴 clawhub schema-driven 模式）──
export interface AttributeConstraint {
  minLength?: number
  maxLength?: number
  min?: number
  max?: number
  pattern?: string
  enumValues?: string[]
  refTarget?: string
}

export interface EntityAttribute {
  id: string
  name: string
  type: AttrType
  description: string
  required: boolean
  example?: string
  constraints?: AttributeConstraint
}

export interface EntityRelation {
  id: string
  name: string
  type: RelationType
  fromEntityId: string
  fromEntityName: string
  toEntityId: string
  toEntityName: string
  toEntityTier: Tier
  cardinality: Cardinality
  acyclic: boolean
  description?: string
}

export interface BusinessRule {
  id: string
  name: string
  entityId: string
  entityName: string
  condition: string
  action: string
  status: RuleStatus
  priority: Priority
  triggerCount: number
  lastTriggered: string | null
  createdAt: string
  updatedAt: string
}

export interface EntityAction {
  id: string
  name: string
  type: 'automation' | 'notification' | 'campaign' | 'upsell' | 'lifecycle' | 'compute' | 'navigation'
  status: 'active' | 'inactive' | 'warning'
  impactCount?: number
}

// ── 本体实体（完整对象，匹配后端 snake_case）──
export interface OntologyEntity {
  id: string
  name: string
  name_cn: string
  tier: Tier
  status: EntityStatus
  description?: string
  schema_json?: Record<string, unknown>
  attributes: EntityAttribute[]
  relations: EntityRelationDetail[]
  rules: RuleDetail[]
  actions: ActionDetail[]
  created_at: string
  updated_at: string
  created_by: string | null
}

// 后端返回的关系详情
export interface EntityRelationDetail {
  id: string
  name: string
  rel_type: string
  from_entity_id: string
  from_entity_name: string
  to_entity_id: string
  to_entity_name: string
  to_entity_tier: number
  cardinality: Cardinality
  acyclic: boolean
  description?: string
}

// 后端返回的规则详情
export interface RuleDetail {
  id: string
  name: string
  entity_id: string
  entity_name: string
  condition_expr: string
  action_desc: string
  status: string
  priority: string
  trigger_count: number
  last_triggered: string | null
}

// 后端返回的动作详情
export interface ActionDetail {
  id: string
  name: string
  type: string
  status: string
  impact_count: number | null
}

// ── 实体列表项（轻量版，匹配后端 snake_case）──
export interface EntityListItem {
  id: string
  name: string
  name_cn: string
  tier: Tier
  status: EntityStatus
  attr_count: number
  relation_count: number
  rule_count: number
  datasource_name: string | null
}

// ── 图遍历结果（匹配后端 snake_case）──
export interface GraphNode {
  id: string
  name: string
  name_cn: string
  tier: Tier
  status: EntityStatus
  relation_count: number
}

export interface GraphEdge {
  from_id: string
  from_name: string
  to_id: string
  to_name: string
  label: string
  cardinality: string
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

// ── 文件导入结果 ──
export interface FileImportResult {
  entities_created: number
  entities_skipped: number
  attributes_created: number
  relations_created: number
  rules_created: number
  actions_created: number
  errors: string[]
}

// ── 看板统计 ──
export interface DashboardStats {
  entityCount: number
  relationCount: number
  ruleCount: number
  activeStrategyCount: number
  tierDistribution: { tier: Tier; name: string; count: number; pct: number }[]
  recentActivities: ActivityItem[]
  healthStatus: { id: string; name: string; tier: Tier; status: EntityStatus }[]
}

export interface ActivityItem {
  id: string
  type: 'create' | 'update' | 'execute' | 'warning'
  title: string
  description: string
  time: string
}
