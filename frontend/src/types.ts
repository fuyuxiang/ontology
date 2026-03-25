export type RiskLevel = "HIGH" | "MEDIUM" | "LOW";

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  x?: number;
  y?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  label: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  totalPrimaryEntities?: number;
  totalInteractions?: number;
  displayedPrimaryEntities?: number;
}

export interface FieldDisplay {
  label: string;
  value: string | number | boolean | null;
}

export interface Summary {
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
  warnings: string[];
}

export interface Alert {
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
}

export interface EvidenceItem {
  category: string;
  title: string;
  summary: string;
  riskLevel?: RiskLevel;
  facts: string[];
}

export interface InferenceSummary {
  headline: string;
  riskLevel: RiskLevel;
  recommendedAction: string;
  factorCount: number;
  ruleCount: number;
  eventCount: number;
  summary: string;
}

export interface EntityDetail {
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
  error?: string;
}

export type SubscriberListItem = Alert;
export type SubscriberDetail = EntityDetail;

export interface SparqlResult {
  query: string;
  variables: string[];
  rowCount: number;
  rows: Array<Record<string, string>>;
}

export interface InferenceTriggerResult {
  deductionTriples: number;
  owlrlTriples: number;
  riskDistribution: Record<RiskLevel, number>;
}
