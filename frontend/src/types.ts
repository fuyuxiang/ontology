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
  totalSubscribers?: number;
  totalInteractions?: number;
}

export interface Summary {
  scenario: string;
  tripleCount: number;
  subscriberCount: number;
  interactionCount: number;
  relationCount: number;
  riskDistribution: Record<RiskLevel, number>;
  topRules: Array<{
    rule: string;
    count: number;
  }>;
  sampleQuery: string;
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
}

export interface AlertMetrics {
  dataUsageDropPct: number;
  complaintCount30d: number;
  competitorContactCount30d: number;
  portingCodeRequestCount30d: number;
  contractRemainingDays: number;
  vipFlag: number;
}

export interface SubscriberListItem {
  subscriberId: string;
  name: string;
  msisdn: string;
  city: string;
  segment: string;
  planName: string;
  riskLevel: RiskLevel;
  recommendedAction: string;
  factors: string[];
}

export interface Alert extends SubscriberListItem {
  metrics: AlertMetrics;
  complaint: number;
  competitor: number;
  porting: number;
  plan: string;
}

export interface EventItem {
  eventId: string;
  eventType: string;
  channel: string;
  daysAgo: number;
  severity: string;
  detail: string;
}

export interface EvidenceItem {
  category: string;
  title: string;
  summary: string;
  factor?: string;
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

export interface SubscriberDetail {
  subscriberId: string;
  name: string;
  city: string;
  segment: string;
  planName: string;
  msisdn: string;
  riskLevel: RiskLevel;
  recommendedAction: string;
  metrics: Record<string, number | string>;
  factors: string[];
  rules: string[];
  events: EventItem[];
  inference: InferenceSummary;
  evidence: EvidenceItem[];
  graph: GraphData;
  error?: string;
}

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
