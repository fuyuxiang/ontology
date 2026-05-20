// ── 本体构建器类型定义 ──

export type ScenarioId = 'refund-root-cause' | 'enterprise-qa' | 'fttr-renewal' | string
export type SceneTone = 'slate' | 'purple' | 'blue'

export interface ScenarioCard {
  id: ScenarioId
  short: string
  title: string
  description: string
  meta: string
  tone: SceneTone
}

// ── 用户故事 ──
export interface UserStory {
  id: string
  asRole: string
  iWant: string
  soThat: string
  keywords: string[]
  confirmed: boolean
}

// ── 资产 ──
export type AssetCategory = 'structured' | 'unstructured' | 'image'
export interface DataAsset {
  id: string
  name: string
  type: string
  domain: string
  rating?: number
  subscribed: boolean
  category: AssetCategory
  fileType?: string
  fileSize?: string
  ontologyTarget?: 'T-box' | 'R-box' | 'A-box'
  description: string
  distilledRules?: string[]
  fields?: { name: string; en?: string; type?: string; sample?: string }[]
  source?: string
  linkText?: string
  linkUrl?: string
}

// ── 本体类与属性 ──
export interface OntologyProperty {
  id: string
  name: string
  displayName: string
  type: 'string' | 'number' | 'date' | 'boolean' | 'enum' | string
  required: boolean
  description?: string
}

export interface OntologyClassDraft {
  id: string
  name: string
  displayName: string
  tier: 1 | 2 | 3
  namespace?: string
  description: string
  primaryKey: string
  icon: string
  instanceCount: number
  properties: OntologyProperty[]
  rules: string[]
  actions: string[]
  approved?: boolean
}

// ── 关系 ──
export interface OntologyRelationDraft {
  id: string
  name: string
  displayName: string
  source: string
  target: string
  cardinality: '1:1' | '1:N' | 'N:N'
  description: string
  relationType: 'ObjectProperty' | 'SymmetricProperty' | 'TransitiveProperty' | 'FunctionalProperty'
  semanticType: 'composition' | 'event' | 'inheritance' | 'dependency' | 'association'
}

// ── 会话 ──
export type BuildMethod = 'ai' | 'upload'
export type SessionStatus =
  | 'drafting'
  | 'pending_review'
  | 'reviewing'
  | 'pending_hydration'
  | 'hydrating'
  | 'pending_publish'
  | 'publishing'
  | 'published'

export interface ReviewLogEntry {
  storyId: string
  storyName: string
  action: 'approved' | 'rejected' | 'revised'
  reviewer: string
  reviewedAt: string
  comment: string
}

export interface ThresholdChange {
  field: string
  oldValue: string
  newValue: string
}

export interface DrillLogLine {
  ts: string
  level: 'OK' | 'RUN' | 'ERR'
  msg: string
}

export type DrillPhaseKey = 'ingest' | 'instantiate' | 'match' | 'strategy'
export interface DrillPhase {
  key: DrillPhaseKey
  label: string
  status: 'pending' | 'running' | 'pass' | 'warn' | 'error'
  metrics: { label: string; value: string; tone?: 'pass' | 'warn' | 'error' }[]
  segments?: { name: string; count: number; ratio: number; note?: string }[]
}

export interface DrillResult {
  phases: DrillPhase[]
  logs: DrillLogLine[]
  selectedRows: number
  selectedColumns: number
  selectedSources: number
  entityCount: number
  relationCount: number
  attributionAccuracy?: string
  highConfidenceAttribution?: number
  manualReview?: number
}

export interface BuilderSession {
  sessionId: string
  ontologyName: string
  scenarioId: string
  scenarioName: string
  buildMethod: BuildMethod
  status: SessionStatus
  createdBy: string
  createdAt: string
  updatedAt: string
  ontologyClasses: OntologyClassDraft[]
  ontologyRelations: OntologyRelationDraft[]
  selectedAssetIds: string[]
  selectedSampleSourceIds: string[]
  approvedScenarios: string[]
  thresholdChanges: ThresholdChange[]
  reviewLog: ReviewLogEntry[]
  businessRules: string[]
  drillStatus?: 'pass' | 'warn' | 'error'
  drillResult?: DrillResult
  publishedVersion?: string
  publishedAt?: string
}

// ── 上传素材记录 ──
export interface UploadRecord {
  id: string
  fileName: string
  fileType: string
  fileSize: string
  sourceOntology: string
  scenarioName: string
  uploadedAt: string
  status: 'parsing' | 'completed' | 'failed'
  statusText: string
  extractedSummary: string
  extractedRules: number
  extractedFields: number
  mimeCategory: AssetCategory
}

// ── 数据源样例 ──
export interface SampleDataSource {
  id: string
  fileName: string
  rows: number
  columns: number
  system: string
  targetClass?: string
  selected?: boolean
}

// ── 发布门禁 ──
export interface PublishGate {
  key: string
  label: string
  desc: string
  pass: boolean
}

// ── 消费方对接 ──
export interface ConsumerTarget {
  name: string
  usage: string
  status: string
}

// ── 监控基线 ──
export interface MonitoringBaseline {
  label: string
  value: string
  target: string
  level: 'success' | 'warning' | 'info'
}

// ── 对话消息 ──
export interface CopilotMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  thinkingSeconds?: number
  note?: string
  createdAt: string
}

// ── 附件（输入栏） ──
export interface CopilotAttachment {
  id: string
  fileName: string
  fileType: string
  fileSize: string
  status: 'pending' | 'parsing' | 'parsed'
  mimeCategory: AssetCategory
}

// ── Step1 阶段机 ──
export type Step1Phase =
  | 'idle'
  | 'scene_analyzing'
  | 'scene_confirm'
  | 'story_split'
  | 'asset_scanning'
  | 'assets_ready'
  | 'graph_building'
  | 'graph_done'
