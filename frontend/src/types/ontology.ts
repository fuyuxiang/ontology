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

// ── 本体实体（完整对象）──
export interface OntologyEntity {
  id: string
  name: string
  nameCn: string
  tier: Tier
  status: EntityStatus
  description?: string
  schemaJson?: Record<string, unknown>
  attributes: EntityAttribute[]
  relations: EntityRelation[]
  rules: BusinessRule[]
  actions: EntityAction[]
  createdAt: string
  updatedAt: string
  createdBy: string
}

// ── 实体列表项（轻量版，用于侧边栏/搜索）──
export interface EntityListItem {
  id: string
  name: string
  nameCn: string
  tier: Tier
  status: EntityStatus
  attrCount: number
  relationCount: number
  ruleCount: number
}

// ── 图遍历结果 ──
export interface GraphNode {
  id: string
  name: string
  nameCn: string
  tier: Tier
  status: EntityStatus
  relationCount: number
}

export interface GraphEdge {
  fromId: string
  fromName: string
  toId: string
  toName: string
  label: string
  cardinality: Cardinality
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
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
