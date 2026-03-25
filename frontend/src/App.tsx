import { type KeyboardEvent, startTransition, useEffect, useState } from "react";

import { GraphCanvas, NODE_TYPE_COLORS, NODE_TYPE_LABELS, RISK_COLORS } from "./components/GraphCanvas";
import { getAlerts, getSubscriber, getSummary, runSparql, triggerInference } from "./services/api";
import type { Alert, GraphData, RiskLevel, SparqlResult, SubscriberDetail, Summary } from "./types";

type PageKey = "dashboard" | "ontology" | "graph" | "qa" | "settings";
type GraphRiskFilter = "ALL" | RiskLevel;

interface ChatMessage {
  id: string;
  role: "assistant" | "user";
  content: string;
}

interface FeedbackState {
  tone: "success" | "error";
  text: string;
}

const TELECOM_NS = "http://example.com/telecom#";
const RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#";
const RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#";

const NAV_ITEMS: Array<{ key: PageKey; label: string; icon: IconName }> = [
  { key: "dashboard", label: "仪表盘", icon: "dashboard" },
  { key: "ontology", label: "本体构建", icon: "globe" },
  { key: "graph", label: "图谱探索", icon: "graph" },
  { key: "qa", label: "智能问答", icon: "chat" },
  { key: "settings", label: "设置", icon: "settings" },
];

const RECOMMENDED_QUESTIONS = [
  "哪些用户属于高风险携转预警？",
  "哪些规则被命中最多？",
  "最近有哪些携转资格查询或投诉记录？",
];

const GRAPH_RISK_FILTERS: Array<{ key: GraphRiskFilter; label: string }> = [
  { key: "ALL", label: "全部风险" },
  { key: "HIGH", label: "高风险" },
  { key: "MEDIUM", label: "中风险" },
  { key: "LOW", label: "低风险" },
];

const ICON_PATHS = {
  dashboard: "M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z",
  globe:
    "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z",
  graph: "M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z",
  chat: "M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z",
  settings:
    "M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z",
  refresh:
    "M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z",
  user: "M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z",
  interaction: "M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 14H4V6h16v12z",
  alert: "M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z",
  relation:
    "M17.66 7.93 12 2.27 6.34 7.93c-3.12 3.12-3.12 8.19 0 11.31C7.9 20.8 9.95 21.58 12 21.58c2.05 0 4.1-.78 5.66-2.34 3.12-3.12 3.12-8.19 0-11.31zM12 19.59c-1.6 0-3.11-.62-4.24-1.76C6.62 16.69 6 15.19 6 13.59s.62-3.11 1.76-4.24L12 5.1v14.49z",
  send: "M2.01 21 23 12 2.01 3 2 10l15 2-15 2z",
  bot:
    "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z",
  data: "M4 6h18V4H4c-1.1 0-2 .9-2 2v11H0v3h14v-3H4V6zm19 2h-6c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h6c.55 0 1-.45 1-1V9c0-.55-.45-1-1-1zm-1 9h-4v-7h4v7z",
  money:
    "M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z",
  event: "M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z",
  file: "M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6z",
} as const;

type IconName = keyof typeof ICON_PATHS;

function makeId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

function formatCompactNumber(value: number) {
  if (value >= 10000) {
    return `${(value / 10000).toFixed(1)}w`;
  }
  return `${value}`;
}

function formatFieldLine(fields: Array<{ label: string; value: string | number | boolean | null }>, separator = " | ") {
  return fields
    .filter((field) => field.value !== "" && field.value !== null && field.value !== undefined)
    .map((field) => `${field.label}: ${field.value}`)
    .join(separator);
}

function riskLabel(level: RiskLevel) {
  if (level === "HIGH") {
    return "高风险";
  }
  if (level === "MEDIUM") {
    return "中风险";
  }
  return "低风险";
}

function riskTone(level: RiskLevel) {
  if (level === "HIGH") {
    return "high";
  }
  if (level === "MEDIUM") {
    return "medium";
  }
  return "low";
}

function buildRiskScopedGraph(graph: GraphData | null, alerts: Alert[], riskFilter: GraphRiskFilter): GraphData | null {
  if (!graph || riskFilter === "ALL") {
    return graph;
  }

  const matchedUserNodeIds = new Set(alerts.filter((item) => item.riskLevel === riskFilter).map((item) => item.nodeId));
  if (!matchedUserNodeIds.size) {
    return {
      ...graph,
      nodes: [],
      edges: [],
      displayedPrimaryEntities: 0,
    };
  }

  const includedNodeIds = new Set<string>(matchedUserNodeIds);
  for (const edge of graph.edges) {
    if (matchedUserNodeIds.has(edge.source) || matchedUserNodeIds.has(edge.target)) {
      includedNodeIds.add(edge.source);
      includedNodeIds.add(edge.target);
    }
  }

  const nodes = graph.nodes.filter((node) => includedNodeIds.has(node.id));
  const edges = graph.edges.filter((edge) => includedNodeIds.has(edge.source) && includedNodeIds.has(edge.target));
  const displayedPrimaryEntities = nodes.filter((node) => matchedUserNodeIds.has(node.id)).length;

  return {
    ...graph,
    nodes,
    edges,
    displayedPrimaryEntities,
  };
}

function buildDefaultQuestionQuery(defaultQuery?: string) {
  if (defaultQuery?.trim()) {
    return defaultQuery;
  }
  return [
    `PREFIX rdf: <${RDF_NS}>`,
    `PREFIX rdfs: <${RDFS_NS}>`,
    `PREFIX telecom: <${TELECOM_NS}>`,
    "SELECT ?userId ?deviceNumber ?riskLevel ?areaId",
    "WHERE {",
    "  ?user a telecom:User ;",
    "        telecom:userId ?userId ;",
    "        telecom:deviceNumber ?deviceNumber ;",
    "        telecom:inferredRiskLevel ?riskLevel .",
    "  OPTIONAL { ?user telecom:areaId ?areaId }",
    "}",
    "ORDER BY DESC(?riskLevel) ?userId",
    "LIMIT 10",
  ].join("\n");
}

function convertQuestionToSparql(question: string, defaultQuery?: string) {
  const q = question.toLowerCase();
  const prefixes = [
    `PREFIX rdf: <${RDF_NS}>`,
    `PREFIX rdfs: <${RDFS_NS}>`,
    `PREFIX telecom: <${TELECOM_NS}>`,
  ].join("\n");

  if (q.includes("风险因子") || q.includes("因子有哪些")) {
    return `${prefixes}
SELECT ?factor ?label
WHERE {
  ?factor a telecom:RiskFactor .
  OPTIONAL { ?factor rdfs:label ?label }
}
ORDER BY ?label
LIMIT 20`;
  }

  if (q.includes("高风险") || (q.includes("风险") && q.includes("用户"))) {
    return `${prefixes}
SELECT ?userId ?deviceNumber ?areaId ?riskLevel
WHERE {
  ?user a telecom:User ;
        telecom:userId ?userId ;
        telecom:deviceNumber ?deviceNumber ;
        telecom:inferredRiskLevel ?riskLevel .
  OPTIONAL { ?user telecom:areaId ?areaId }
  FILTER(?riskLevel = "HIGH")
}
ORDER BY ?userId
LIMIT 10`;
  }

  if (q.includes("交互") || q.includes("事件") || q.includes("interaction")) {
    return `${prefixes}
SELECT ?deviceNumber ?queryTime ?servContent
WHERE {
  {
    ?query a telecom:PortingQuery ;
           telecom:deviceNumber ?deviceNumber ;
           telecom:queryTime ?queryTime .
  }
  UNION
  {
    ?service a telecom:CustomerServiceInteraction ;
             telecom:deviceNumber ?deviceNumber ;
             telecom:servContent ?servContent .
  }
}
ORDER BY ?deviceNumber
LIMIT 10`;
  }

  if (q.includes("规则") || q.includes("rule")) {
    return `${prefixes}
SELECT ?userId ?ruleLabel
WHERE {
  ?user a telecom:User ;
     telecom:userId ?userId ;
     <http://purl.org/doim/1.0#taggedByRule> ?rule .
  ?rule rdfs:label ?ruleLabel .
}
ORDER BY ?userId ?ruleLabel
LIMIT 15`;
  }

  if (q.includes("用户") || q.includes("subscriber")) {
    return `${prefixes}
SELECT ?userId ?deviceNumber ?areaId ?userType
WHERE {
  ?user a telecom:User ;
        telecom:userId ?userId ;
        telecom:deviceNumber ?deviceNumber .
  OPTIONAL { ?user telecom:areaId ?areaId }
  OPTIONAL { ?user telecom:userType ?userType }
}
ORDER BY ?userId
LIMIT 10`;
  }

  return buildDefaultQuestionQuery(defaultQuery);
}

function formatAnswer(result: SparqlResult, question: string) {
  const rows = result.rows ?? [];
  if (rows.length === 0) {
    return "根据当前知识图谱，没有检索到匹配结果。可以试试询问高风险用户、风险因子或交互事件。";
  }

  const q = question.toLowerCase();
  if (q.includes("风险因子") || q.includes("因子有哪些")) {
    return `系统中定义的风险因子共 ${rows.length} 类：\n\n${rows
      .map((row, index) => `${index + 1}. ${row.label || row.factor || "-"}`)
      .join("\n")}`;
  }

  if (q.includes("高风险") || (q.includes("风险") && q.includes("用户"))) {
    return `找到 ${rows.length} 个高风险用户：\n\n${rows
      .map((row, index) => `${index + 1}. ${row.deviceNumber || row.userId || "-"} · ${row.areaId || "-"} · ${row.riskLevel || "HIGH"}`)
      .join("\n")}`;
  }

  if (q.includes("交互") || q.includes("事件")) {
    return `最近的关键交互事件如下：\n\n${rows
      .map((row, index) => `${index + 1}. ${row.deviceNumber || "-"} · ${row.queryTime || row.servContent || "-"}`)
      .join("\n")}`;
  }

  if (q.includes("规则")) {
    return `规则命中样例如下：\n\n${rows
      .map((row, index) => `${index + 1}. ${row.userId || "-"} · ${row.ruleLabel || "-"}`)
      .join("\n")}`;
  }

  if (q.includes("用户") || q.includes("subscriber")) {
    return `找到 ${rows.length} 个用户：\n\n${rows
      .map((row, index) => `${index + 1}. ${row.deviceNumber || row.userId || "-"} · ${row.areaId || "-"} · ${row.userType || "-"}`)
      .join("\n")}`;
  }

  return `查询返回 ${result.rowCount} 条记录：\n\n${rows
    .slice(0, 5)
    .map((row, index) => `${index + 1}. ${result.variables.map((variable) => `${variable}: ${row[variable] || "-"}`).join(" | ")}`)
    .join("\n")}`;
}

function SvgIcon({ name, size = 20, color = "currentColor" }: { name: IconName; size?: number; color?: string }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill={color} aria-hidden="true">
      <path d={ICON_PATHS[name]} />
    </svg>
  );
}

function PageHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="page-header">
      <h1 className="page-title">{title}</h1>
      <p className="page-subtitle">{subtitle}</p>
    </div>
  );
}

function RiskStatus({ level }: { level: RiskLevel }) {
  return <span className={`risk-status ${riskTone(level)}`}>{riskLabel(level)}</span>;
}

function StatCard({
  label,
  value,
  icon,
  iconBg,
  iconColor,
}: {
  label: string;
  value: string;
  icon: IconName;
  iconBg: string;
  iconColor: string;
}) {
  return (
    <div className="stat-card">
      <div className="stat-icon" style={{ background: iconBg }}>
        <SvgIcon name={icon} size={24} color={iconColor} />
      </div>
      <div className="stat-info">
        <span className="stat-label">{label}</span>
        <span className="stat-value">{value}</span>
      </div>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="empty-state">
      <SvgIcon name="graph" size={48} />
      <p>{message}</p>
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState<PageKey>("dashboard");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [appError, setAppError] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [graphRiskFilter, setGraphRiskFilter] = useState<GraphRiskFilter>("ALL");
  const [subscriberDetails, setSubscriberDetails] = useState<Record<string, SubscriberDetail>>({});
  const [detailLoadingId, setDetailLoadingId] = useState<string | null>(null);
  const [detailError, setDetailError] = useState("");
  const [questionInput, setQuestionInput] = useState("");
  const [askingQuestion, setAskingQuestion] = useState(false);
  const [runningInference, setRunningInference] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "您好，我是本体问答助手。您可以询问高风险用户、规则命中、风险因子或交互事件。",
    },
  ]);

  async function loadAppData() {
    setLoading(true);
    setAppError("");
    setSubscriberDetails({});
    setDetailLoadingId(null);
    setDetailError("");
    const [summaryResult, alertsResult] = await Promise.allSettled([getSummary(), getAlerts()]);

    if (summaryResult.status === "fulfilled") {
      setSummary(summaryResult.value);
    } else {
      setAppError(summaryResult.reason instanceof Error ? summaryResult.reason.message : "加载 summary 失败");
    }

    if (alertsResult.status === "fulfilled") {
      setAlerts(alertsResult.value);
    } else {
      setAppError((current) => current || (alertsResult.reason instanceof Error ? alertsResult.reason.message : "加载 alerts 失败"));
    }

    setLoading(false);
  }

  useEffect(() => {
    void loadAppData();
  }, []);

  useEffect(() => {
    const nodes = buildRiskScopedGraph(summary?.ontologyGraph ?? null, alerts, graphRiskFilter)?.nodes ?? [];
    if (!nodes.length) {
      if (selectedNodeId) {
        setSelectedNodeId(null);
      }
      return;
    }
    if (!selectedNodeId || !nodes.some((node) => node.id === selectedNodeId)) {
      const defaultUserNode = nodes.find((node) => alerts.some((item) => item.nodeId === node.id));
      setSelectedNodeId((defaultUserNode ?? nodes[0]).id);
    }
  }, [alerts, graphRiskFilter, selectedNodeId, summary]);

  async function handleRefresh() {
    setFeedback(null);
    await loadAppData();
  }

  async function handleRunInference() {
    setRunningInference(true);
    setFeedback(null);
    try {
      const result = await triggerInference();
      await loadAppData();
      setFeedback({
        tone: "success",
        text: `推理完成，当前共有 ${result.deductionTriples} 条推理三元组，OWL-RL 新增 ${result.owlrlTriples} 条。`,
      });
    } catch (error) {
      setFeedback({
        tone: "error",
        text: error instanceof Error ? error.message : "推理执行失败",
      });
    } finally {
      setRunningInference(false);
    }
  }

  async function handleAskQuestion(questionOverride?: string) {
    const question = (questionOverride ?? questionInput).trim();
    if (!question || askingQuestion) {
      return;
    }

    const assistantId = makeId("assistant");
    setMessages((current) => [
      ...current,
      { id: makeId("user"), role: "user", content: question },
      { id: assistantId, role: "assistant", content: "正在检索知识图谱，请稍候..." },
    ]);
    setQuestionInput("");
    setAskingQuestion(true);

    try {
      const query = convertQuestionToSparql(question, summary?.sampleQuery);
      const result = await runSparql(query);
      const answer = formatAnswer(result, question);
      setMessages((current) => current.map((message) => (message.id === assistantId ? { ...message, content: answer } : message)));
    } catch (error) {
      const failureText = error instanceof Error ? error.message : "问答执行失败";
      setMessages((current) => current.map((message) => (message.id === assistantId ? { ...message, content: `抱歉，检索失败：${failureText}` } : message)));
    } finally {
      setAskingQuestion(false);
    }
  }

  function handleQuestionKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleAskQuestion();
    }
  }

  function openAlertInGraph(alert: Alert) {
    startTransition(() => {
      setPage("graph");
      setGraphRiskFilter(alert.riskLevel);
      setSelectedNodeId(alert.nodeId);
    });
  }

  const graph = buildRiskScopedGraph(summary?.ontologyGraph ?? null, alerts, graphRiskFilter);
  const graphNodes = graph?.nodes ?? [];
  const graphEdges = graph?.edges ?? [];
  const selectedNode = graphNodes.find((node) => node.id === selectedNodeId) ?? null;
  const selectedNodeEdges = selectedNode
    ? graphEdges.filter((edge) => edge.source === selectedNode.id || edge.target === selectedNode.id)
    : [];
  const selectedEntityAlert = selectedNode ? alerts.find((item) => item.nodeId === selectedNode.id) : undefined;
  const selectedEntityId = selectedEntityAlert?.entityId ?? null;
  const selectedSubscriber = selectedEntityId ? subscriberDetails[selectedEntityId] ?? null : null;
  const detailLoading = selectedEntityId !== null && detailLoadingId === selectedEntityId;
  const riskByNodeId = Object.fromEntries(alerts.map((item) => [item.nodeId, item.riskLevel] as const));
  const relatedAlerts = selectedNode
    ? Array.from(
        new Map(
          selectedNodeEdges
            .map((edge) => {
              const relatedNodeId = edge.source === selectedNode.id ? edge.target : edge.source;
              const relatedAlert = alerts.find((item) => item.nodeId === relatedNodeId);
              return relatedAlert ? [relatedAlert.entityId, relatedAlert] : null;
            })
            .filter((item): item is [string, Alert] => item !== null),
        ).values(),
      )
    : [];

  const legendTypes = Array.from(new Set(graphNodes.map((node) => node.type)));
  const highRiskUsers = alerts.filter((item) => item.riskLevel !== "LOW").slice(0, 5);
  const topRules = summary?.topRules ?? [];
  const ruleCounts = Object.fromEntries(topRules.map((item) => [item.rule, item.count]));
  const dataSourceCards = summary?.sourceCards ?? [];
  const ontologyFiles = summary?.ontologyFiles ?? [];
  const ruleCards = summary?.ruleCards ?? [];
  const mappingExamples = summary?.mappingExamples ?? [];
  const suggestedQuestions = summary?.questionSuggestions?.length ? summary.questionSuggestions : RECOMMENDED_QUESTIONS;
  const visibleAlerts =
    graphRiskFilter === "ALL" ? alerts : alerts.filter((item) => item.riskLevel === graphRiskFilter);

  useEffect(() => {
    if (!selectedEntityId || subscriberDetails[selectedEntityId]) {
      setDetailError("");
      return;
    }

    let cancelled = false;
    setDetailLoadingId(selectedEntityId);
    setDetailError("");

    void getSubscriber(selectedEntityId)
      .then((detail) => {
        if (cancelled) {
          return;
        }
        setSubscriberDetails((current) => ({ ...current, [selectedEntityId]: detail }));
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }
        setDetailError(error instanceof Error ? error.message : "加载用户详情失败");
      })
      .finally(() => {
        if (cancelled) {
          return;
        }
        setDetailLoadingId((current) => (current === selectedEntityId ? null : current));
      });

    return () => {
      cancelled = true;
    };
  }, [selectedEntityId, subscriberDetails]);

  return (
    <div className="app-container">
      <header className="top-header">
        <div className="header-title">
          <SvgIcon name="globe" size={24} />
          <span>{summary?.headerTitle || "携号转网场景语义预警系统"}</span>
        </div>
        <div className="header-actions">
          <button className="action-btn" type="button" onClick={() => void handleRefresh()}>
            <SvgIcon name="refresh" size={16} />
            刷新
          </button>
        </div>
      </header>

      <div className="main-content">
        <aside className="sidebar">
          <nav className="sidebar-nav">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.key}
                type="button"
                className={`nav-item ${page === item.key ? "active" : ""}`}
                onClick={() => setPage(item.key)}
              >
                <SvgIcon name={item.icon} size={20} />
                <span>{item.label}</span>
              </button>
            ))}
          </nav>

          <div className="sidebar-footer">
            <div className="sidebar-hint">后端接口已接入 FastAPI / RDFLib / pySHACL</div>
          </div>
        </aside>

        <main className="content-area">
          {appError ? <div className="global-notice error">{appError}</div> : null}

          {page === "dashboard" ? (
            <div className="page active">
              <PageHeader title="仪表盘" subtitle={summary?.dashboardSubtitle || "实时监控携号转网风险态势"} />

              <div className="stats-grid">
                <StatCard
                  label={`${summary?.primaryEntityPluralLabel || "用户"}总数`}
                  value={summary ? formatCompactNumber(summary.primaryEntityCount) : "-"}
                  icon="user"
                  iconBg="#e6f7ff"
                  iconColor="#1890ff"
                />
                <StatCard
                  label={summary?.interactionLabel || "交互记录"}
                  value={summary ? formatCompactNumber(summary.interactionCount) : "-"}
                  icon="interaction"
                  iconBg="#fff7e6"
                  iconColor="#fa8c16"
                />
                <StatCard
                  label="风险告警"
                  value={summary ? formatCompactNumber(alerts.length) : "-"}
                  icon="alert"
                  iconBg="#fff1f0"
                  iconColor="#f5222d"
                />
                <StatCard
                  label="关系网络"
                  value={summary ? formatCompactNumber(summary.relationCount) : "-"}
                  icon="relation"
                  iconBg="#f6ffed"
                  iconColor="#52c41a"
                />
              </div>

              <div className="dashboard-grid">
                <div className="dashboard-card">
                  <div className="card-header">
                    <h3 className="card-title">近期风险告警</h3>
                  </div>
                  <div className="card-body">
                    {loading ? <div className="loading-state">加载中...</div> : null}
                    {!loading && alerts.length === 0 ? <EmptyState message="暂无告警数据" /> : null}
                    {!loading &&
                      alerts.slice(0, 6).map((alert) => (
                        <button key={alert.entityId} type="button" className="alert-item" onClick={() => openAlertInGraph(alert)}>
                          <div className="alert-icon">
                            <SvgIcon name="alert" size={20} color="#ff4d4f" />
                          </div>
                          <div className="alert-info">
                            <div className="alert-name">{alert.displayName || alert.entityId}</div>
                            <div className="alert-meta">{formatFieldLine(alert.summaryFields) || `动作: ${alert.recommendedAction}`}</div>
                          </div>
                          <RiskStatus level={alert.riskLevel} />
                        </button>
                      ))}
                  </div>
                </div>

                <div className="dashboard-card">
                  <div className="card-header">
                    <h3 className="card-title">高风险用户</h3>
                  </div>
                  <div className="card-body">
                    {loading ? <div className="loading-state">加载中...</div> : null}
                    {!loading && highRiskUsers.length === 0 ? <EmptyState message="暂无高风险用户" /> : null}
                    {!loading &&
                      highRiskUsers.map((alert) => (
                        <button key={alert.entityId} type="button" className="risk-user-item" onClick={() => openAlertInGraph(alert)}>
                          <div className="risk-user-icon">
                            <SvgIcon name="user" size={20} color="#1890ff" />
                          </div>
                          <div className="risk-user-info">
                            <div className="risk-user-name">{alert.displayName}</div>
                            <div className="risk-user-meta">{formatFieldLine(alert.summaryFields) || alert.recommendedAction}</div>
                          </div>
                          <div className="risk-user-right">
                            <div className="risk-user-amount">{alert.factors[0] || "-"}</div>
                            <RiskStatus level={alert.riskLevel} />
                          </div>
                        </button>
                      ))}
                  </div>
                </div>
              </div>
            </div>
          ) : null}

          {page === "ontology" ? (
            <div className="page active">
              <PageHeader title="本体构建流程" subtitle="展示从原始数据到知识图谱的完整构建过程" />

              <div className="ontology-flow">
                <div className="flow-step">
                  <div className="step-header">
                    <div className="step-number">1</div>
                    <h3 className="step-title">数据源接入</h3>
                  </div>
                  <div className="step-content">
                    <div className="step-desc">从多个业务模型 CSV 数据源加载当前场景的核心实体与行为信号。</div>
                    <div className="data-sources-grid">
                      {dataSourceCards.map((item) => (
                        <div key={item.key} className="data-source-card">
                          <div className={`source-icon ${item.tone}`}>
                            <SvgIcon name={item.icon as IconName} size={24} />
                          </div>
                          <div className="source-name">{item.label}</div>
                          <div className="source-file">{item.file}</div>
                          <div className="source-count">{item.count} 条</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="flow-step">
                  <div className="step-header">
                    <div className="step-number">2</div>
                    <h3 className="step-title">本体定义</h3>
                  </div>
                  <div className="step-content">
                    <div className="step-desc">加载 DOIM 核心本体、当前场景领域本体与风险规则文件。</div>
                    <div className="ontology-files">
                      {ontologyFiles.map((file) => (
                        <div key={file.name} className="ontology-file">
                          <div className={`file-icon ${file.tone}`}>
                            <SvgIcon name="file" size={20} />
                          </div>
                          <div className="file-info">
                            <div className="file-name">{file.name}</div>
                            <div className="file-desc">{file.desc}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="flow-step">
                  <div className="step-header">
                    <div className="step-number">3</div>
                    <h3 className="step-title">三元组映射</h3>
                  </div>
                  <div className="step-content">
                    <div className="step-desc">将多源业务数据映射为 RDF 三元组并持久化。</div>
                    <div className="mapping-stats">
                      <div className="stat-item">
                        <div className="stat-value">{summary?.tripleCount ?? "-"}</div>
                        <div className="stat-label">三元组总数</div>
                      </div>
                      <div className="stat-item">
                        <div className="stat-value">{summary ? summary.primaryEntityCount + summary.interactionCount : "-"}</div>
                        <div className="stat-label">实体数量</div>
                      </div>
                    </div>
                    <div className="mapping-example">
                      <div className="example-title">映射示例：</div>
                      {mappingExamples.map((item) => (
                        <div key={item.label} className="example-item">
                          <span className="example-label">{item.label}:</span>
                          <code>{item.code}</code>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="flow-step">
                  <div className="step-header">
                    <div className="step-number">4</div>
                    <h3 className="step-title">推理引擎</h3>
                  </div>
                  <div className="step-content">
                    <div className="step-desc">结合 OWL-RL 推导与配置化业务规则命中，形成当前场景风险判断。</div>
                    <div className="inference-rules">
                      {ruleCards.map((card) => (
                        <div key={card.label} className={`rule-item ${card.tone}`}>
                          <div className="rule-name">{card.label}</div>
                          <div className="rule-desc">{card.desc}</div>
                          <div className="rule-count">{ruleCounts[card.label] || 0} 次命中</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="flow-step">
                  <div className="step-header">
                    <div className="step-number">5</div>
                    <h3 className="step-title">推理结果</h3>
                  </div>
                  <div className="step-content">
                    <div className="step-desc">系统输出高、中、低风险分级，并保留命中规则分布。</div>
                    <div className="result-summary">
                      <div className="result-card high">
                        <div className="result-count">{summary?.riskDistribution.HIGH ?? "-"}</div>
                        <div className="result-label">高风险{summary?.primaryEntityLabel || "用户"}</div>
                      </div>
                      <div className="result-card medium">
                        <div className="result-count">{summary?.riskDistribution.MEDIUM ?? "-"}</div>
                        <div className="result-label">中风险{summary?.primaryEntityLabel || "用户"}</div>
                      </div>
                      <div className="result-card low">
                        <div className="result-count">{summary?.riskDistribution.LOW ?? "-"}</div>
                        <div className="result-label">低风险{summary?.primaryEntityLabel || "用户"}</div>
                      </div>
                    </div>
                    <div className="top-rules">
                      <div className="rules-title">TOP 规则命中：</div>
                      <div className="rules-list">
                        {topRules.slice(0, 5).map((item) => (
                          <div key={item.rule} className="rule-list-item">
                            <span className="rule-name">{item.rule}</span>
                            <span className="rule-count">{item.count} 次</span>
                          </div>
                        ))}
                        {topRules.length === 0 ? <div className="loading-state">暂无规则命中数据</div> : null}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="architecture-section">
                <h2 className="section-title">系统架构</h2>
                <div className="architecture-grid">
                  {(summary?.architecture ?? []).map((layer) => (
                    <div key={layer.title} className="architecture-card">
                      <div className="architecture-title">{layer.title}</div>
                      <div className="architecture-subtitle">{layer.subtitle}</div>
                      <div className="architecture-items">
                        {layer.items.map((item) => (
                          <div key={item} className="architecture-item">
                            {item}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : null}

          {page === "graph" ? (
            <div className="page active">
              <PageHeader title="图谱探索" subtitle="先看高、中、低风险分布，再下钻查看命中因子、规则与动作链路" />

              <div className="graph-container">
                <div className="graph-canvas">
                  <div className="graph-filters">
                    {GRAPH_RISK_FILTERS.map((item) => {
                      const count = item.key === "ALL" ? alerts.length : summary?.riskDistribution[item.key] ?? 0;
                      return (
                        <button
                          key={item.key}
                          type="button"
                          className={`graph-filter-chip ${graphRiskFilter === item.key ? "active" : ""} ${item.key.toLowerCase()}`}
                          onClick={() => setGraphRiskFilter(item.key)}
                        >
                          <span>{item.label}</span>
                          <strong>{count}</strong>
                        </button>
                      );
                    })}
                  </div>

                  {graph && graphNodes.length ? (
                    <>
                      <div className="graph-stats">
                        <span>总{summary?.primaryEntityPluralLabel || "用户"}: {graph.totalPrimaryEntities ?? summary?.primaryEntityCount ?? 0}</span> |
                        <span> 展示{summary?.primaryEntityLabel || "用户"}: {graph.displayedPrimaryEntities ?? 0}</span> |
                        <span> 实体: {graphNodes.length}</span> |
                        <span> 关系: {graphEdges.length}</span>
                      </div>

                      <div className="graph-legend">
                        <h4>实体类型</h4>
                        <div className="legend-items">
                          {legendTypes.map((type) => (
                            <div key={type} className="legend-item">
                              <span className="legend-color" style={{ background: NODE_TYPE_COLORS[type] || "#999999" }} />
                              <span>{NODE_TYPE_LABELS[type] || type}</span>
                            </div>
                          ))}
                        </div>
                        <h4 className="graph-legend-title">风险等级</h4>
                        <div className="legend-items">
                          {(["HIGH", "MEDIUM", "LOW"] as RiskLevel[]).map((level) => (
                            <div key={level} className="legend-item">
                              <span className="legend-ring" style={{ borderColor: RISK_COLORS[level] }} />
                              <span>{riskLabel(level)}用户外环</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      <GraphCanvas
                        graph={graph}
                        riskByNodeId={riskByNodeId}
                        selectedNodeId={selectedNodeId}
                        onSelectNode={(node) => {
                          setSelectedNodeId(node.id);
                        }}
                      />
                    </>
                  ) : (
                    <div className="graph-empty">
                      <SvgIcon name="graph" size={48} />
                      <p>{loading ? "加载图谱数据..." : graphRiskFilter === "ALL" ? "暂无图谱数据" : `当前没有${riskLabel(graphRiskFilter)}用户`}</p>
                    </div>
                  )}
                </div>

                <div className="node-detail-panel">
                  {!selectedNode ? (
                    <EmptyState message="在图谱中选择一个实体节点以查看详情" />
                  ) : (
                    <div className="node-detail-content">
                      <div className="detail-header">
                        <div className="detail-icon" style={{ background: NODE_TYPE_COLORS[selectedNode.type] || "#999999" }}>
                          <SvgIcon name="bot" size={28} color="#ffffff" />
                        </div>
                        <h3>{selectedNode.label || selectedNode.id}</h3>
                        <span className="node-type-tag">{NODE_TYPE_LABELS[selectedNode.type] || selectedNode.type}</span>
                        {selectedEntityAlert ? <RiskStatus level={selectedEntityAlert.riskLevel} /> : null}
                      </div>

                      <div className="detail-body">
                        {selectedEntityAlert ? (
                          <div className={`risk-hero ${riskTone(selectedEntityAlert.riskLevel)}`}>
                            <div className="risk-hero-label">{riskLabel(selectedEntityAlert.riskLevel)}</div>
                            <div className="risk-hero-title">{selectedSubscriber?.inference.headline || `${selectedNode.label} 风险判定`}</div>
                            <div className="risk-hero-summary">
                              {selectedSubscriber?.inference.summary || selectedEntityAlert.recommendedAction}
                            </div>
                          </div>
                        ) : null}

                        <div className="detail-property">
                          <span className="detail-property-key">ID</span>
                          <span className="detail-property-value">{selectedNode.id}</span>
                        </div>
                        <div className="detail-property">
                          <span className="detail-property-key">类型</span>
                          <span className="detail-property-value">{NODE_TYPE_LABELS[selectedNode.type] || selectedNode.type}</span>
                        </div>
                        <div className="detail-property">
                          <span className="detail-property-key">标签</span>
                          <span className="detail-property-value">{selectedNode.label || "-"}</span>
                        </div>
                        {selectedEntityAlert ? (
                          <>
                            {selectedEntityAlert.detailFields.map((field) => (
                              <div key={field.label} className="detail-property">
                                <span className="detail-property-key">{field.label}</span>
                                <span className="detail-property-value">{String(field.value ?? "-")}</span>
                              </div>
                            ))}
                            <div className="detail-property">
                              <span className="detail-property-key">动作</span>
                              <span className="detail-property-value">{selectedEntityAlert.recommendedAction}</span>
                            </div>
                          </>
                        ) : null}
                        <div className="detail-property">
                          <span className="detail-property-key">关联关系</span>
                          <span className="detail-property-value">{selectedNodeEdges.length} 条</span>
                        </div>
                        {selectedNodeEdges.slice(0, 6).map((edge) => {
                          const relatedNodeId = edge.source === selectedNode.id ? edge.target : edge.source;
                          const relatedNode = graphNodes.find((node) => node.id === relatedNodeId);
                          return (
                            <div key={`${edge.source}-${edge.target}-${edge.label}`} className="detail-property">
                              <span className="detail-property-key">→ {edge.label}</span>
                              <span className="detail-property-value">
                                {relatedNode?.label || relatedNodeId}
                                {relatedNode ? ` (${NODE_TYPE_LABELS[relatedNode.type] || relatedNode.type})` : ""}
                              </span>
                            </div>
                          );
                        })}

                        {selectedEntityAlert ? (
                          <div className="detail-section">
                            <div className="detail-section-title">风险信号</div>
                            <div className="signal-grid">
                              {selectedEntityAlert.highlightFields.map((field) => (
                                <div key={field.label} className="signal-card">
                                  <span className="signal-label">{field.label}</span>
                                  <strong>{String(field.value ?? "-")}</strong>
                                </div>
                              ))}
                            </div>
                          </div>
                        ) : null}

                        {selectedSubscriber?.factors.length ? (
                          <div className="detail-section">
                            <div className="detail-section-title">命中因子</div>
                            <div className="token-list">
                              {selectedSubscriber.factors.map((factor) => (
                                <span key={factor} className="token-chip factor">
                                  {factor}
                                </span>
                              ))}
                            </div>
                          </div>
                        ) : null}

                        {selectedSubscriber?.rules.length ? (
                          <div className="detail-section">
                            <div className="detail-section-title">命中规则</div>
                            <div className="token-list">
                              {selectedSubscriber.rules.map((rule) => (
                                <span key={rule} className="token-chip rule">
                                  {rule}
                                </span>
                              ))}
                            </div>
                          </div>
                        ) : null}

                        {detailLoading ? <div className="loading-state">正在加载规则解释图...</div> : null}
                        {detailError ? <div className="inline-error">{detailError}</div> : null}

                        {selectedSubscriber?.graph ? (
                          <div className="detail-section">
                            <div className="detail-section-title">规则解释图</div>
                            <div className="detail-graph-shell">
                              <GraphCanvas
                                graph={selectedSubscriber.graph}
                                riskByNodeId={selectedEntityAlert ? { [selectedEntityAlert.nodeId]: selectedEntityAlert.riskLevel } : undefined}
                                selectedNodeId={selectedSubscriber.graph.nodes[0]?.id}
                                showEdgeLabels
                                showControls={false}
                              />
                            </div>
                          </div>
                        ) : null}

                        {selectedSubscriber?.evidence.length ? (
                          <div className="detail-section">
                            <div className="detail-section-title">证据链</div>
                            <div className="evidence-list">
                              {selectedSubscriber.evidence.map((item) => (
                                <div key={`${item.category}-${item.title}`} className="evidence-card">
                                  <div className="evidence-title-row">
                                    <span className="evidence-title">{item.title}</span>
                                    {item.riskLevel ? <RiskStatus level={item.riskLevel} /> : null}
                                  </div>
                                  <div className="evidence-summary">{item.summary}</div>
                                  {item.facts.map((fact) => (
                                    <div key={fact} className="evidence-fact">
                                      {fact}
                                    </div>
                                  ))}
                                </div>
                              ))}
                            </div>
                          </div>
                        ) : null}

                        {!selectedEntityAlert && relatedAlerts.length ? (
                          <div className="detail-section">
                            <div className="detail-section-title">关联风险用户</div>
                            <div className="related-alert-list">
                              {relatedAlerts.map((alert) => (
                                <button
                                  key={alert.entityId}
                                  type="button"
                                  className="related-alert-item"
                                  onClick={() => setSelectedNodeId(alert.nodeId)}
                                >
                                  <span>{alert.displayName}</span>
                                  <RiskStatus level={alert.riskLevel} />
                                </button>
                              ))}
                            </div>
                          </div>
                        ) : null}

                        <div className="detail-section">
                          <div className="detail-section-title">当前筛选结果</div>
                          <div className="detail-muted">
                            当前展示 {visibleAlerts.length} 个{graphRiskFilter === "ALL" ? "" : riskLabel(graphRiskFilter)}用户，可在左侧图中继续下钻。
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : null}

          {page === "qa" ? (
            <div className="page active">
              <PageHeader title="智能问答" subtitle="基于本体知识与 SPARQL 查询的问答系统" />

              <div className="qa-container">
                <div className="qa-capability-card">
                  <div className="capability-left">
                    <div className="capability-icon">
                      <SvgIcon name="bot" size={32} color="#ffffff" />
                    </div>
                    <div className="capability-text">
                      <h3>本体增强问答</h3>
                      <p>根据问题自动生成 SPARQL 查询，并结合图谱返回结构化答案。</p>
                    </div>
                  </div>
                  <div className="capability-status">
                    <span className={`status-badge ${summary ? "success" : "error"}`}>{summary ? "图数据库已连接" : "等待后端连接"}</span>
                  </div>
                </div>

                <div className="chat-container">
                  {messages.map((message) => (
                    <div key={message.id} className={`chat-message ${message.role}`}>
                      <div className="message-avatar">
                        <SvgIcon name={message.role === "assistant" ? "bot" : "user"} size={20} color="currentColor" />
                      </div>
                      <div className="message-content">
                        <p>{message.content}</p>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="suggested-questions">
                  <span className="suggest-label">推荐问题：</span>
                  {suggestedQuestions.map((question) => (
                    <button
                      key={question}
                      className="suggest-btn"
                      type="button"
                      onClick={() => {
                        void handleAskQuestion(question);
                      }}
                    >
                      {question}
                    </button>
                  ))}
                </div>

                <div className="chat-input-area">
                  <textarea
                    value={questionInput}
                    onChange={(event) => setQuestionInput(event.target.value)}
                    onKeyDown={handleQuestionKeyDown}
                    placeholder="请输入您的问题..."
                    rows={1}
                  />
                  <button type="button" className="send-btn" disabled={askingQuestion} onClick={() => void handleAskQuestion()}>
                    <SvgIcon name="send" size={20} color="#ffffff" />
                  </button>
                </div>
              </div>
            </div>
          ) : null}

          {page === "settings" ? (
            <div className="page active">
              <PageHeader title="设置" subtitle="系统配置、校验状态与推理操作" />

              <div className="settings-container">
                <div className="settings-card">
                  <h3>系统信息</h3>
                  <div className="setting-item">
                    <span className="setting-label">场景</span>
                    <span className="setting-value">{summary?.scenario || "加载中..."}</span>
                  </div>
                  <div className="setting-item">
                    <span className="setting-label">三元组数量</span>
                    <span className="setting-value">{summary ? formatCompactNumber(summary.tripleCount) : "加载中..."}</span>
                  </div>
                  <div className="setting-item">
                    <span className="setting-label">SHACL 校验</span>
                    <span className="setting-value">
                      {summary?.validation.status === "ok"
                        ? summary.validation.conforms
                          ? "通过"
                          : "未通过"
                        : summary?.validation.reason || "加载中..."}
                    </span>
                  </div>
                  <div className="setting-item">
                    <span className="setting-label">持久化后端</span>
                    <span className="setting-value">{summary?.persistence.storeBackend || "加载中..."}</span>
                  </div>
                  <div className="setting-item multiline">
                    <span className="setting-label">数据集路径</span>
                    <span className="setting-value setting-path">{summary?.persistence.datasetPath || "-"}</span>
                  </div>

                  <button type="button" className="btn btn-primary" onClick={() => void handleRunInference()} disabled={runningInference}>
                    <SvgIcon name="refresh" size={16} color="#ffffff" />
                    {runningInference ? "推理中..." : "触发推理"}
                  </button>

                  {feedback ? <div className={`inference-result show ${feedback.tone === "success" ? "success" : "error"}`}>{feedback.text}</div> : null}
                </div>
              </div>
            </div>
          ) : null}
        </main>
      </div>
    </div>
  );
}
