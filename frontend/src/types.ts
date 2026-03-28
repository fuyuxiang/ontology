/** 前后端共享的数据结构类型定义。 */

export type RiskLevel = "HIGH" | "MEDIUM" | "LOW";

export interface GraphNode {
  /** 图谱节点。 */
  id: string;
  label: string;
  type: string;
  x?: number;
  y?: number;
}

export interface GraphEdge {
  /** 图谱边。 */
  source: string;
  target: string;
  label: string;
}

export interface GraphData {
  /** 图谱数据载荷。 */
  nodes: GraphNode[];
  edges: GraphEdge[];
  totalPrimaryEntities?: number;
  totalInteractions?: number;
  displayedPrimaryEntities?: number;
}

export interface FieldDisplay {
  /** 前端展示字段。 */
  label: string;
  value: string | number | boolean | null;
}

export interface Summary {
  /** 首页概览接口返回值。 */
  scenarioKey: string;
  scenario: string;
  appTitle: string;
  headerTitle: string;
  dashboardSubtitle: string;
  tripleCount: number;
  primaryEntityLabel: string;
  primaryEntityPluralLabel: string;
  primaryEntityCount: number;
  interactionLabel: string;
  interactionCount: number;
  relationCount: number;
  riskDistribution: Record<RiskLevel, number>;
  topRules: Array<{
    rule: string;
    count: number;
  }>;
  sampleQuery: string;
  questionSuggestions: string[];
  ontologyGraph: GraphData;
  architecture: Array<{
    title: string;
    subtitle: string;
    items: string[];
  }>;
  validation: {
    status: string;
    conforms?: boolean;
    reason?: string;
    reportPath?: string;
    reportText?: string;
  };
  persistence: {
    storeBackend?: string;
    datasetPath?: string;
    storePath?: string;
    reason?: string;
    error?: string;
  };
  sourceCards: Array<{
    key: string;
    label: string;
    file: string;
    count: number;
    icon: string;
    tone: string;
  }>;
  ontologyFiles: Array<{
    name: string;
    desc: string;
    tone: "ttl" | "rules";
  }>;
  ruleCards: Array<{
    label: string;
    desc: string;
    tone: string;
  }>;
  mappingExamples: Array<{
    label: string;
    code: string;
  }>;
  operationalMetrics: {
    caseCount: number;
    openCaseCount: number;
    taskCount: number;
    todoTaskCount: number;
    actionRunCount: number;
    eventCount: number;
    caseDistribution: Record<string, number>;
    taskDistribution: Record<string, number>;
    alertDistribution: Record<string, number>;
    actionCatalog: ActionDefinition[];
  };
  operationsWorkbench: OperationsWorkbench;
  ontologyObjects: Array<{
    key: string;
    label: string;
    ontologyType: string;
    identityField: string;
    description: string;
    attributes: string[];
  }>;
  toolCatalog: Array<{
    name: string;
    description: string;
    inputs: string[];
  }>;
  agentProfile: {
    name: string;
    mode: string;
    planner: string;
    objectCount: number;
    toolCount: number;
  };
  caseDistribution: Record<string, number>;
  taskDistribution: Record<string, number>;
  alertDistribution: Record<string, number>;
  actionCatalog: ActionDefinition[];
  warnings: string[];
}

export interface Alert {
  /** 告警列表项。 */
  entityId: string;
  nodeId: string;
  displayName: string;
  riskLevel: RiskLevel;
  recommendedAction: string;
  factors: string[];
  summaryFields: FieldDisplay[];
  detailFields: FieldDisplay[];
  highlightFields: FieldDisplay[];
  metrics: Record<string, string | number | boolean | null>;
  alertState?: string;
  caseId?: string;
  caseState?: string;
  taskCount?: number;
  availableActions?: ActionDefinition[];
}

export interface EvidenceItem {
  /** 详情页中的证据项。 */
  category: string;
  title: string;
  summary: string;
  riskLevel?: RiskLevel;
  facts: string[];
}

export interface InferenceSummary {
  /** 推理摘要信息。 */
  headline: string;
  riskLevel: RiskLevel;
  recommendedAction: string;
  factorCount: number;
  ruleCount: number;
  eventCount: number;
  summary: string;
}

export interface EntityDetail {
  /** 实体详情接口返回值。 */
  entityId: string;
  displayName: string;
  riskLevel: RiskLevel;
  recommendedAction: string;
  metrics: Record<string, string | number | boolean | null>;
  factors: string[];
  rules: string[];
  summaryFields: FieldDisplay[];
  detailFields: FieldDisplay[];
  relatedData: Record<string, Array<Record<string, string | number | boolean | null>>>;
  inference: InferenceSummary;
  evidence: EvidenceItem[];
  graph: GraphData;
  alertState?: string;
  case?: OperationalCase;
  tasks?: TaskItem[];
  timeline?: TimelineItem[];
  actionRuns?: ActionRun[];
  availableActions?: ActionDefinition[];
  error?: string;
}

export type SubscriberListItem = Alert;
export type SubscriberDetail = EntityDetail;

export interface SparqlResult {
  /** SPARQL 查询结果。 */
  query: string;
  variables: string[];
  rowCount: number;
  rows: Array<Record<string, string>>;
}

export interface InferenceTriggerResult {
  /** 手动触发推理后的统计结果。 */
  deductionTriples: number;
  owlrlTriples: number;
  riskDistribution: Record<RiskLevel, number>;
  operationalMetrics?: Summary["operationalMetrics"];
}

export interface ActionDefinition {
  id: string;
  label: string;
  description: string;
  allowed_roles: string[];
  allowed_states: string[];
  allowed_risk_levels: string[];
  side_effect: string;
  queue_hint: string;
}

export interface TaskItem {
  id: string;
  case_id: string;
  entity_id: string;
  action_id: string;
  title: string;
  status: string;
  assignee_role: string;
  queue_name: string;
  due_sla_hours: number;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
  output: Record<string, string | number | boolean | null>;
  displayName?: string;
  riskLevel?: RiskLevel | "";
  caseState?: string;
  priority?: string;
  recommendedAction?: string;
  summaryFields?: FieldDisplay[];
}

export interface ActionRun {
  id: string;
  action_id: string;
  case_id: string;
  entity_id: string;
  actor_role: string;
  actor_id: string;
  status: string;
  policy_reason: string;
  created_at: string;
  updated_at: string;
  parameters: Record<string, string | number | boolean | null>;
  output: Record<string, string | number | boolean | null>;
}

export interface TimelineItem {
  kind: string;
  time: string;
  title: string;
  eventType?: string;
  subjectType?: string;
  subjectId?: string;
  payload?: Record<string, string | number | boolean | null>;
  fromState?: string;
  toState?: string;
  reason?: string;
}

export interface OperationalCaseSummary {
  id: string;
  entityId: string;
  caseId: string;
  state: string;
  risk_level: string;
  priority: string;
  queue_name: string;
  owner_role: string;
  area_id?: string | null;
  created_at: string;
  updated_at: string;
  alertState: string;
  availableActions: ActionDefinition[];
  openTaskCount: number;
  displayName?: string;
  summaryFields?: FieldDisplay[];
  detailFields?: FieldDisplay[];
  recommendedAction?: string;
  nextAction?: ActionDefinition | null;
  lastActivityTitle?: string;
  lastActivityTime?: string;
}

export interface OperationalCase extends OperationalCaseSummary {
  timeline: TimelineItem[];
  tasks: TaskItem[];
  actionRuns: ActionRun[];
}

export interface OperationsWorkbench {
  focusCases: OperationalCaseSummary[];
  queueLanes: Array<{
    queueName: string;
    label: string;
    caseCount: number;
    taskCount: number;
    highRiskCount: number;
    owners: string[];
  }>;
  priorityBands: Array<{
    priority: string;
    label: string;
    caseCount: number;
    openTaskCount: number;
    actionableCount: number;
  }>;
  recentActions: Array<{
    id: string;
    caseId: string;
    entityId: string;
    displayName: string;
    actionId: string;
    label: string;
    actorRole: string;
    status: string;
    time: string;
  }>;
}

export interface AgentToolRun {
  tool: string;
  arguments: Record<string, unknown>;
  summary: string;
  resultCount: number;
}

export interface PendingAction {
  actionId: string;
  actionLabel: string;
  caseId: string;
  entityId: string;
  actorRole: string;
  actorId: string;
  actorAreaId: string;
}

export interface AgentResponse {
  mode: string;
  question: string;
  answer: string;
  toolRuns: AgentToolRun[];
  suggestions: string[];
  primaryObjectType: string;
  objects: Array<Record<string, unknown>>;
  requiresConfirmation: boolean;
  pendingAction: PendingAction | null;
}

export interface PlatformScenario {
  key: string;
  name: string;
  version: string;
  description: string;
  scenarioPath: string;
  dataDir: string;
  mappingPath: string;
  ontologyCorePath: string;
  ontologyDomainPath: string;
  ontologyShapesPath: string;
  rulesPath: string;
  active: boolean;
}

export interface PlatformSummary {
  activeScenarioKey: string;
  activeScenarioName: string;
  scenarioCount: number;
  statePath: string;
  scenarios: PlatformScenario[];
  capabilities: string[];
}

export interface ActionExecutionResult {
  actionRun: ActionRun;
  case: OperationalCase;
  alert: Record<string, string | number | boolean | null>;
  availableActions: ActionDefinition[];
  owlrlTriples: number;
  operationalMetrics: Summary["operationalMetrics"];
  workbench: OperationsWorkbench;
}
