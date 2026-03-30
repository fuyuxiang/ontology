/** 前端主页面，统一编排概览、图谱、问答和设置视图。 */

import { type KeyboardEvent, startTransition, useEffect, useRef, useState } from "react";

import { GraphCanvas, NODE_TYPE_COLORS, NODE_TYPE_LABELS, RISK_COLORS } from "./components/GraphCanvas";
import { OntologySimulationWorkbench } from "./components/OntologySimulationWorkbench";
import { OntologyWorkbench } from "./components/OntologyWorkbench";
import { OperationsWorkbench } from "./components/OperationsWorkbench";
import {
  activateScenario,
  askAgent,
  discardOntologyDraft,
  executeAction,
  getAlerts,
  getCase,
  getCases,
  getOntologyWorkspace,
  getPlatformSummary,
  publishOntologyDraft,
  revertOntologyDraftChange,
  saveOntologyDraftChange,
  getSubscriber,
  getSummary,
  getTasks,
  triggerInference,
} from "./services/api";
import type {
  Alert,
  GraphData,
  GraphNode,
  OntologyWorkspace,
  OperationalCase,
  OperationalCaseSummary,
  PendingAction,
  PlatformSummary,
  RiskLevel,
  SubscriberDetail,
  Summary,
  TaskItem,
} from "./types";

type PageKey =
  | "dashboard"
  | "ontologyStudio"
  | "simulation"
  | "operations"
  | "ontology"
  | "ontologyMap"
  | "graph"
  | "qa"
  | "settings";
type GraphRiskFilter = "ALL" | RiskLevel;
type OntologyKind = "entity" | "property" | "relation" | "rule" | "action";

interface ChatMessage {
  id: string;
  role: "assistant" | "user";
  content: string;
  toolSummary?: string;
  pendingAction?: PendingAction | null;
  requiresConfirmation?: boolean;
}

interface FeedbackState {
  tone: "success" | "error";
  text: string;
}

interface OntologyDetailItem {
  label: string;
  value: string;
}

interface OntologyCollection {
  title: string;
  items: string[];
  tone?: "neutral" | "rule" | "action";
}

interface OntologyGraphNode extends GraphNode {
  kind: OntologyKind;
  description: string;
  details: OntologyDetailItem[];
  collections?: OntologyCollection[];
}

interface OntologyGraphPayload {
  graph: GraphData;
  nodes: OntologyGraphNode[];
  counts: Record<OntologyKind, number>;
}

const NAV_ITEMS: Array<{ key: PageKey; label: string; icon: IconName }> = [
  { key: "dashboard", label: "仪表盘", icon: "dashboard" },
  { key: "ontologyStudio", label: "本体工作台", icon: "relation" },
  { key: "simulation", label: "本体模拟", icon: "event" },
  { key: "operations", label: "运营工作台", icon: "data" },
  { key: "ontology", label: "构建流水线", icon: "globe" },
  { key: "ontologyMap", label: "本体图谱", icon: "graph" },
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

const ONTOLOGY_KIND_LABELS: Record<OntologyKind, string> = {
  entity: "实体",
  property: "属性",
  relation: "关系",
  rule: "规则",
  action: "动作",
};

const ONTOLOGY_KIND_ORDER: Record<OntologyKind, number> = {
  entity: 0,
  property: 1,
  relation: 2,
  rule: 3,
  action: 4,
};

const ONTOLOGY_KIND_NOTES: Record<OntologyKind, string> = {
  entity: "对象模型骨架",
  property: "围绕实体的关键字段",
  relation: "实体之间的语义连接",
  rule: "风险判断规则",
  action: "后续处置动作",
};

const ONTOLOGY_RELATION_SPECS = [
  {
    key: "user-interaction",
    sourceKey: "User",
    targetKey: "InteractionEvent",
    label: "沉淀交互信号",
    description: "用户对象通过交互事件沉淀行为证据，作为后续风险识别的输入。",
  },
  {
    key: "user-rulehit",
    sourceKey: "User",
    targetKey: "RuleHit",
    label: "进入规则评估",
    description: "用户会被规则对象评估，产生命中结果与解释语义。",
  },
  {
    key: "rulehit-alert",
    sourceKey: "RuleHit",
    targetKey: "RiskAlert",
    label: "支撑风险告警",
    description: "规则命中结果被汇聚为风险告警，形成面向运营的统一风险视图。",
  },
  {
    key: "alert-case",
    sourceKey: "RiskAlert",
    targetKey: "RetentionCase",
    label: "转为运营处置",
    description: "风险告警进入运营流程后会生成 Case，承载状态、优先级和责任队列。",
  },
  {
    key: "case-task",
    sourceKey: "RetentionCase",
    targetKey: "Task",
    label: "拆解执行任务",
    description: "Case 会继续拆解为多个任务，供不同角色串联处理。",
  },
  {
    key: "case-action-def",
    sourceKey: "RetentionCase",
    targetKey: "ActionDefinition",
    label: "编排可执行动作",
    description: "Case 会根据状态和风险等级匹配可执行动作定义。",
  },
  {
    key: "task-action-def",
    sourceKey: "Task",
    targetKey: "ActionDefinition",
    label: "调用动作定义",
    description: "任务会引用动作定义，决定执行方式、角色约束和状态迁移。",
  },
] as const;

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

/** 按风险等级裁剪概览图谱。 */
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

function uniqueStrings(values: string[]) {
  return Array.from(new Set(values.filter((item) => item.trim().length > 0)));
}

function detailValue(value: string | number | boolean | null | undefined) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function riskScopeLabel(value: string) {
  if (value === "HIGH") {
    return "高风险";
  }
  if (value === "MEDIUM") {
    return "中风险";
  }
  if (value === "LOW") {
    return "低风险";
  }
  return value;
}

function buildOntologyGraph(summary: Summary | null): OntologyGraphPayload {
  const counts: Record<OntologyKind, number> = {
    entity: 0,
    property: 0,
    relation: 0,
    rule: 0,
    action: 0,
  };

  if (!summary) {
    return {
      graph: { nodes: [], edges: [] },
      nodes: [],
      counts,
    };
  }

  const nodes: OntologyGraphNode[] = [];
  const edges: GraphData["edges"] = [];
  const nodeById = new Map<string, OntologyGraphNode>();
  const entityNodeIdByKey = new Map<string, string>();
  const entityYByKey = new Map<string, number>();
  const edgeKeySet = new Set<string>();

  function addNode(node: OntologyGraphNode) {
    if (nodeById.has(node.id)) {
      return;
    }
    nodeById.set(node.id, node);
    nodes.push(node);
    counts[node.kind] += 1;
  }

  function addEdge(source: string, target: string, label: string) {
    const edgeKey = `${source}-${target}-${label}`;
    if (edgeKeySet.has(edgeKey)) {
      return;
    }
    edgeKeySet.add(edgeKey);
    edges.push({ source, target, label });
  }

  const entityX = 360;
  const entityStartY = 140;
  const entityGapY = 170;

  summary.ontologyObjects.forEach((item, index) => {
    const entityId = `ontology-entity:${item.key}`;
    const entityY = entityStartY + index * entityGapY;
    entityNodeIdByKey.set(item.key, entityId);
    entityYByKey.set(item.key, entityY);

    addNode({
      id: entityId,
      label: item.label,
      type: "OntologyEntity",
      x: entityX,
      y: entityY,
      kind: "entity",
      description: item.description,
      details: [
        { label: "对象键", value: item.key },
        { label: "本体类型", value: item.ontologyType },
        { label: "标识字段", value: item.identityField },
      ],
      collections: [
        {
          title: "属性清单",
          items: uniqueStrings([item.identityField, ...item.attributes]),
        },
      ],
    });

    const attributes = uniqueStrings([item.identityField, ...item.attributes]);
    const rows = Math.max(Math.ceil(attributes.length / 2), 1);
    attributes.forEach((attribute, attributeIndex) => {
      const column = Math.floor(attributeIndex / rows);
      const row = attributeIndex % rows;
      const propertyId = `ontology-property:${item.key}:${attribute}`;
      const propertyX = entityX - 220 - column * 128;
      const propertyY = entityY - ((rows - 1) * 18) + row * 36;

      addNode({
        id: propertyId,
        label: attribute,
        type: "OntologyProperty",
        x: propertyX,
        y: propertyY,
        kind: "property",
        description: `${item.label} 的${attribute === item.identityField ? "标识属性" : "业务属性"}，用于定义对象字段边界和展示语义。`,
        details: [
          { label: "归属实体", value: item.label },
          { label: "字段名", value: attribute },
          { label: "属性角色", value: attribute === item.identityField ? "身份标识" : "业务属性" },
        ],
      });
      addEdge(entityId, propertyId, "拥有属性");
    });
  });

  ONTOLOGY_RELATION_SPECS.forEach((relation, index) => {
    const sourceId = entityNodeIdByKey.get(relation.sourceKey);
    const targetId = entityNodeIdByKey.get(relation.targetKey);
    if (!sourceId || !targetId) {
      return;
    }

    const sourceLabel = summary.ontologyObjects.find((item) => item.key === relation.sourceKey)?.label ?? relation.sourceKey;
    const targetLabel = summary.ontologyObjects.find((item) => item.key === relation.targetKey)?.label ?? relation.targetKey;
    const sourceY = entityYByKey.get(relation.sourceKey) ?? entityStartY;
    const targetY = entityYByKey.get(relation.targetKey) ?? entityStartY;
    const relationId = `ontology-relation:${relation.key}`;

    addNode({
      id: relationId,
      label: relation.label,
      type: "OntologyRelation",
      x: 680,
      y: (sourceY + targetY) / 2 + (index % 2 === 0 ? -18 : 18),
      kind: "relation",
      description: relation.description,
      details: [
        { label: "源实体", value: sourceLabel },
        { label: "目标实体", value: targetLabel },
        { label: "关系语义", value: relation.label },
      ],
    });

    addEdge(sourceId, relationId, "关系起点");
    addEdge(relationId, targetId, "关系终点");
  });

  const userEntityId = entityNodeIdByKey.get("User") ?? nodes.find((item) => item.kind === "entity")?.id;
  const alertEntityId = entityNodeIdByKey.get("RiskAlert") ?? userEntityId;

  summary.ruleCards.forEach((rule, index) => {
    const ruleId = `ontology-rule:${rule.label}`;
    addNode({
      id: ruleId,
      label: rule.label,
      type: "OntologyRule",
      x: 980,
      y: 150 + index * 190,
      kind: "rule",
      description: rule.desc,
      details: [
        { label: "规则等级", value: toneLabel(rule.tone) },
        { label: "命中次数", value: detailValue(summary.topRules.find((item) => item.rule === rule.label)?.count ?? 0) },
      ],
      collections: [
        {
          title: "规则定位",
          items: [toneLabel(rule.tone), "面向运营风险判断"],
          tone: "rule",
        },
      ],
    });

    if (userEntityId) {
      addEdge(userEntityId, ruleId, "评估对象");
    }
    if (alertEntityId && alertEntityId !== ruleId) {
      addEdge(ruleId, alertEntityId, "产生告警");
    }
  });

  const actionAnchorId =
    entityNodeIdByKey.get("RetentionCase") ?? entityNodeIdByKey.get("RiskAlert") ?? entityNodeIdByKey.get("ActionDefinition");

  summary.actionCatalog.forEach((action, index) => {
    const column = Math.floor(index / 4);
    const row = index % 4;
    const actionId = `ontology-action:${action.id}`;
    addNode({
      id: actionId,
      label: action.label,
      type: "OntologyAction",
      x: 1220 + column * 180,
      y: 170 + row * 150,
      kind: "action",
      description: action.description || "动作定义用于驱动运营闭环中的状态迁移与执行审计。",
      details: [
        { label: "动作 ID", value: action.id },
        { label: "队列提示", value: detailValue(action.queue_hint) },
        { label: "副作用", value: detailValue(action.side_effect) },
      ],
      collections: [
        {
          title: "允许角色",
          items: action.allowed_roles.length ? action.allowed_roles : ["未限制"],
          tone: "action",
        },
        {
          title: "允许状态",
          items: action.allowed_states.length ? action.allowed_states : ["未限制"],
          tone: "action",
        },
        {
          title: "风险范围",
          items: action.allowed_risk_levels.length ? action.allowed_risk_levels.map(riskScopeLabel) : ["全部风险"],
          tone: "action",
        },
      ],
    });

    if (actionAnchorId) {
      addEdge(actionAnchorId, actionId, "可执行动作");
    }
  });

  return {
    graph: {
      nodes,
      edges,
    },
    nodes,
    counts,
  };
}

function toneLabel(value: string) {
  if (value === "high") {
    return "高优先级规则";
  }
  if (value === "medium") {
    return "中优先级规则";
  }
  if (value === "low") {
    return "低优先级规则";
  }
  return value;
}

/** 渲染内置 SVG 图标。 */
function SvgIcon({ name, size = 20, color = "currentColor" }: { name: IconName; size?: number; color?: string }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill={color} aria-hidden="true">
      <path d={ICON_PATHS[name]} />
    </svg>
  );
}

/** 页面区块头部。 */
function PageHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="page-header">
      <h1 className="page-title">{title}</h1>
      <p className="page-subtitle">{subtitle}</p>
    </div>
  );
}

/** 风险状态标签。 */
function RiskStatus({ level }: { level: RiskLevel }) {
  return <span className={`risk-status ${riskTone(level)}`}>{riskLabel(level)}</span>;
}

/** 首页统计卡片。 */
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

/** 空状态占位。 */
function EmptyState({ message }: { message: string }) {
  return (
    <div className="empty-state">
      <SvgIcon name="graph" size={48} />
      <p>{message}</p>
    </div>
  );
}

/** 应用主组件，负责页面状态、数据获取和主要交互。 */
export default function App() {
  const [page, setPage] = useState<PageKey>("ontologyStudio");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [ontologyWorkspace, setOntologyWorkspace] = useState<OntologyWorkspace | null>(null);
  const [platformSummary, setPlatformSummary] = useState<PlatformSummary | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [cases, setCases] = useState<OperationalCaseSummary[]>([]);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [appError, setAppError] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedOntologyNodeId, setSelectedOntologyNodeId] = useState<string | null>(null);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [simulationEntityId, setSimulationEntityId] = useState<string | null>(null);
  const [graphRiskFilter, setGraphRiskFilter] = useState<GraphRiskFilter>("ALL");
  const [subscriberDetails, setSubscriberDetails] = useState<Record<string, SubscriberDetail>>({});
  const [caseDetails, setCaseDetails] = useState<Record<string, OperationalCase>>({});
  const [detailLoadingId, setDetailLoadingId] = useState<string | null>(null);
  const [caseLoadingId, setCaseLoadingId] = useState<string | null>(null);
  const [detailError, setDetailError] = useState("");
  const [simulationDetailLoading, setSimulationDetailLoading] = useState(false);
  const [simulationDetailError, setSimulationDetailError] = useState("");
  const [questionInput, setQuestionInput] = useState("");
  const [askingQuestion, setAskingQuestion] = useState(false);
  const [runningInference, setRunningInference] = useState(false);
  const [switchingScenario, setSwitchingScenario] = useState(false);
  const [actionBusyKey, setActionBusyKey] = useState<string | null>(null);
  const [ontologyDraftBusy, setOntologyDraftBusy] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const appLoadRequestRef = useRef(0);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "我是运营智能问答助手。你可以直接询问风险对象、规则命中、交互事件、Case、任务或动作建议。",
    },
  ]);

  async function loadAppData() {
    const requestId = appLoadRequestRef.current + 1;
    appLoadRequestRef.current = requestId;
    setLoading(true);
    setAppError("");
    setSubscriberDetails({});
    setCaseDetails({});
    setDetailLoadingId(null);
    setCaseLoadingId(null);
    setDetailError("");
    const [summaryResult, workspaceResult, platformResult, alertsResult, casesResult, tasksResult] = await Promise.allSettled([
      getSummary(),
      getOntologyWorkspace(),
      getPlatformSummary(),
      getAlerts(),
      getCases(),
      getTasks(),
    ]);

    if (requestId !== appLoadRequestRef.current) {
      return;
    }

    if (summaryResult.status === "fulfilled") {
      setSummary(summaryResult.value);
    } else {
      setAppError(summaryResult.reason instanceof Error ? summaryResult.reason.message : "加载 summary 失败");
    }

    if (workspaceResult.status === "fulfilled") {
      setOntologyWorkspace(workspaceResult.value);
    } else {
      setAppError((current) => current || (workspaceResult.reason instanceof Error ? workspaceResult.reason.message : "加载 ontology workspace 失败"));
    }

    if (platformResult.status === "fulfilled") {
      setPlatformSummary(platformResult.value);
    } else {
      setAppError((current) => current || (platformResult.reason instanceof Error ? platformResult.reason.message : "加载 platform 失败"));
    }

    if (alertsResult.status === "fulfilled") {
      setAlerts(alertsResult.value);
    } else {
      setAppError((current) => current || (alertsResult.reason instanceof Error ? alertsResult.reason.message : "加载 alerts 失败"));
    }

    if (casesResult.status === "fulfilled") {
      setCases(casesResult.value);
    } else {
      setAppError((current) => current || (casesResult.reason instanceof Error ? casesResult.reason.message : "加载 cases 失败"));
    }

    if (tasksResult.status === "fulfilled") {
      setTasks(tasksResult.value);
    } else {
      setAppError((current) => current || (tasksResult.reason instanceof Error ? tasksResult.reason.message : "加载 tasks 失败"));
    }

    setLoading(false);
  }

  async function handleActivateScenario(scenarioKey: string) {
    setSwitchingScenario(true);
    setFeedback(null);
    try {
      const result = await activateScenario(scenarioKey);
      setPlatformSummary(result);
      await loadAppData();
      setFeedback({
        tone: "success",
        text: `当前已切换到场景包 ${result.activeScenarioName}。`,
      });
    } catch (error) {
      setFeedback({
        tone: "error",
        text: error instanceof Error ? error.message : "切换场景失败",
      });
    } finally {
      setSwitchingScenario(false);
    }
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

  const ontologyGraphPayload = buildOntologyGraph(summary);
  const ontologyGraph = ontologyGraphPayload.graph;
  const ontologyNodes = ontologyGraphPayload.nodes;

  useEffect(() => {
    if (!ontologyNodes.length) {
      if (selectedOntologyNodeId) {
        setSelectedOntologyNodeId(null);
      }
      return;
    }

    if (!selectedOntologyNodeId || !ontologyNodes.some((node) => node.id === selectedOntologyNodeId)) {
      const defaultEntityNode = ontologyNodes.find((node) => node.kind === "entity");
      setSelectedOntologyNodeId((defaultEntityNode ?? ontologyNodes[0]).id);
    }
  }, [ontologyNodes, selectedOntologyNodeId]);

  useEffect(() => {
    if (!cases.length) {
      if (selectedCaseId) {
        setSelectedCaseId(null);
      }
      return;
    }
    if (!selectedCaseId || !cases.some((item) => item.caseId === selectedCaseId)) {
      const actionable = cases.find((item) => item.availableActions?.length);
      setSelectedCaseId((actionable ?? cases[0]).caseId);
    }
  }, [cases, selectedCaseId]);

  useEffect(() => {
    if (!alerts.length) {
      if (simulationEntityId) {
        setSimulationEntityId(null);
      }
      return;
    }

    if (!simulationEntityId || !alerts.some((item) => item.entityId === simulationEntityId)) {
      const defaultEntity = alerts.find((item) => item.availableActions?.length) ?? alerts[0];
      setSimulationEntityId(defaultEntity.entityId);
    }
  }, [alerts, simulationEntityId]);

  async function handleRefresh() {
    setFeedback(null);
    await loadAppData();
    if (selectedCaseId) {
      await refreshCaseDetail(selectedCaseId);
    }

    const entityIds = Array.from(new Set([selectedEntityId, simulationEntityId].filter((item): item is string => Boolean(item))));
    if (entityIds.length) {
      await Promise.all(entityIds.map((entityId) => refreshSubscriberDetail(entityId)));
    }
  }

  async function handleRunInference() {
    setRunningInference(true);
    setFeedback(null);
    try {
      const result = await triggerInference();
      await loadAppData();
      if (selectedCaseId) {
        await refreshCaseDetail(selectedCaseId);
      }

      const entityIds = Array.from(new Set([selectedEntityId, simulationEntityId].filter((item): item is string => Boolean(item))));
      if (entityIds.length) {
        await Promise.all(entityIds.map((entityId) => refreshSubscriberDetail(entityId)));
      }
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

  async function handleSaveOntologyDraftChange(payload: {
    resourceType: string;
    resourceId: string;
    changes: Record<string, unknown>;
  }) {
    setOntologyDraftBusy(true);
    setFeedback(null);
    try {
      await saveOntologyDraftChange(payload);
      await loadAppData();
      setFeedback({
        tone: "success",
        text: "本体草稿已更新。",
      });
    } catch (error) {
      setFeedback({
        tone: "error",
        text: error instanceof Error ? error.message : "保存本体草稿失败",
      });
    } finally {
      setOntologyDraftBusy(false);
    }
  }

  async function handlePublishOntologyDraft() {
    setOntologyDraftBusy(true);
    setFeedback(null);
    try {
      await publishOntologyDraft();
      await loadAppData();
      setFeedback({
        tone: "success",
        text: "本体草稿已发布。",
      });
    } catch (error) {
      setFeedback({
        tone: "error",
        text: error instanceof Error ? error.message : "发布本体草稿失败",
      });
    } finally {
      setOntologyDraftBusy(false);
    }
  }

  async function handleRevertOntologyDraftChange(changeId: string) {
    setOntologyDraftBusy(true);
    setFeedback(null);
    try {
      await revertOntologyDraftChange(changeId);
      await loadAppData();
      setFeedback({
        tone: "success",
        text: "本体草稿变更已回退。",
      });
    } catch (error) {
      setFeedback({
        tone: "error",
        text: error instanceof Error ? error.message : "回退本体草稿失败",
      });
    } finally {
      setOntologyDraftBusy(false);
    }
  }

  async function handleDiscardOntologyDraft() {
    setOntologyDraftBusy(true);
    setFeedback(null);
    try {
      await discardOntologyDraft();
      await loadAppData();
      setFeedback({
        tone: "success",
        text: "本体草稿已丢弃。",
      });
    } catch (error) {
      setFeedback({
        tone: "error",
        text: error instanceof Error ? error.message : "丢弃本体草稿失败",
      });
    } finally {
      setOntologyDraftBusy(false);
    }
  }

  async function refreshCaseDetail(caseId: string) {
    const detail = await getCase(caseId);
    setCaseDetails((current) => ({ ...current, [caseId]: detail }));
    return detail;
  }

  async function refreshSubscriberDetail(entityId: string) {
    const detail = await getSubscriber(entityId);
    setSubscriberDetails((current) => ({ ...current, [entityId]: detail }));
    return detail;
  }

  async function handleExecuteRuntimeAction(actionId: string, caseId: string, entityId: string) {
    const busyKey = `${caseId}:${actionId}`;
    setActionBusyKey(busyKey);
    setFeedback(null);

    try {
      await executeAction({
        actionId,
        caseId,
        entityId,
      });
      await loadAppData();
      await Promise.all([refreshCaseDetail(caseId), refreshSubscriberDetail(entityId)]);
      setSelectedCaseId(caseId);
      setFeedback({
        tone: "success",
        text: `动作 ${actionId} 已执行，运营状态已刷新。`,
      });
    } catch (error) {
      setFeedback({
        tone: "error",
        text: error instanceof Error ? error.message : "动作执行失败",
      });
    } finally {
      setActionBusyKey(null);
    }
  }

  async function handleConfirmPendingAction(messageId: string, pendingAction: PendingAction) {
    const actionId = pendingAction.actionId.trim();
    if (!actionId) {
      return;
    }
    const busyKey = `${pendingAction.caseId}:${actionId}`;
    setActionBusyKey(busyKey);
    setFeedback(null);

    try {
      await executeAction({
        actionId,
        caseId: pendingAction.caseId || undefined,
        entityId: pendingAction.entityId || undefined,
        actorRole: pendingAction.actorRole || undefined,
        actorId: pendingAction.actorId || undefined,
        actorAreaId: pendingAction.actorAreaId || undefined,
      });
      await loadAppData();
      if (pendingAction.caseId) {
        await refreshCaseDetail(pendingAction.caseId);
        setSelectedCaseId(pendingAction.caseId);
      }
      if (pendingAction.entityId) {
        await refreshSubscriberDetail(pendingAction.entityId);
      }
      setMessages((current) =>
        current.map((message) =>
          message.id === messageId
            ? {
                ...message,
                content: `${message.content}\n\n已确认执行动作：${pendingAction.actionLabel || actionId}`,
                pendingAction: null,
                requiresConfirmation: false,
              }
            : message,
        ),
      );
      setFeedback({
        tone: "success",
        text: `动作 ${pendingAction.actionLabel || actionId} 已执行。`,
      });
    } catch (error) {
      setFeedback({
        tone: "error",
        text: error instanceof Error ? error.message : "动作执行失败",
      });
    } finally {
      setActionBusyKey(null);
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
      const result = await askAgent({ question });
      const toolSummary = result.toolRuns.length
        ? `工具链路：${result.toolRuns.map((item) => item.tool).join(" -> ")}`
        : undefined;
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId
            ? {
                ...message,
                content: result.answer,
                toolSummary,
                pendingAction: result.pendingAction,
                requiresConfirmation: result.requiresConfirmation,
              }
            : message,
        ),
      );
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

  function openEntityInGraph(entityId: string) {
    const target = alerts.find((item) => item.entityId === entityId);
    if (!target) {
      return;
    }
    openAlertInGraph(target);
  }

  function openCaseInWorkbench(caseId: string) {
    startTransition(() => {
      setPage("operations");
      setSelectedCaseId(caseId);
    });
  }

  function focusOntologyKind(kind: OntologyKind) {
    const targetNode = ontologyNodes.find((node) => node.kind === kind);
    if (!targetNode) {
      return;
    }
    setSelectedOntologyNodeId(targetNode.id);
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
  const caseLoading = selectedCaseId !== null && caseLoadingId === selectedCaseId;
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
  const selectedOntologyNode = ontologyNodes.find((node) => node.id === selectedOntologyNodeId) ?? null;
  const ontologyEdges = ontologyGraph.edges;
  const ontologyLegendTypes = Array.from(new Set(ontologyNodes.map((node) => node.type)));
  const ontologyNodeLinks = selectedOntologyNode
    ? ontologyEdges
        .flatMap((edge) => {
          if (edge.source !== selectedOntologyNode.id && edge.target !== selectedOntologyNode.id) {
            return [];
          }
          const relatedNodeId = edge.source === selectedOntologyNode.id ? edge.target : edge.source;
          const relatedNode = ontologyNodes.find((node) => node.id === relatedNodeId);
          if (!relatedNode) {
            return [];
          }
          return [
            {
              key: `${edge.source}-${edge.target}-${edge.label}`,
              label: edge.label,
              node: relatedNode,
            },
          ];
        })
        .sort((left, right) => {
          if (left.node.kind === right.node.kind) {
            return left.node.label.localeCompare(right.node.label, "zh-CN");
          }
          return ONTOLOGY_KIND_ORDER[left.node.kind] - ONTOLOGY_KIND_ORDER[right.node.kind];
        })
    : [];
  const visibleAlerts =
    graphRiskFilter === "ALL" ? alerts : alerts.filter((item) => item.riskLevel === graphRiskFilter);
  const selectedCaseSummary = selectedCaseId ? cases.find((item) => item.caseId === selectedCaseId) ?? null : null;
  const selectedCase = selectedCaseId ? caseDetails[selectedCaseId] ?? null : null;
  const selectedOperationsTasks = selectedCase ? selectedCase.tasks : tasks.filter((item) => item.status === "TODO");
  const selectedRuntimeCase =
    selectedSubscriber?.case ??
    (selectedEntityAlert?.caseId ? caseDetails[selectedEntityAlert.caseId] ?? cases.find((item) => item.caseId === selectedEntityAlert.caseId) ?? null : null);
  const selectedSimulationSubscriber = simulationEntityId ? subscriberDetails[simulationEntityId] ?? null : null;

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

  useEffect(() => {
    if (!selectedCaseId || caseDetails[selectedCaseId]) {
      return;
    }

    let cancelled = false;
    setCaseLoadingId(selectedCaseId);

    void getCase(selectedCaseId)
      .then((detail) => {
        if (cancelled) {
          return;
        }
        setCaseDetails((current) => ({ ...current, [selectedCaseId]: detail }));
      })
      .finally(() => {
        if (cancelled) {
          return;
        }
        setCaseLoadingId((current) => (current === selectedCaseId ? null : current));
      });

    return () => {
      cancelled = true;
    };
  }, [caseDetails, selectedCaseId]);

  useEffect(() => {
    if (!simulationEntityId || subscriberDetails[simulationEntityId]) {
      setSimulationDetailError("");
      setSimulationDetailLoading(false);
      return;
    }

    let cancelled = false;
    setSimulationDetailLoading(true);
    setSimulationDetailError("");

    void refreshSubscriberDetail(simulationEntityId)
      .catch((error) => {
        if (cancelled) {
          return;
        }
        setSimulationDetailError(error instanceof Error ? error.message : "加载模拟对象失败");
      })
      .finally(() => {
        if (cancelled) {
          return;
        }
        setSimulationDetailLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [simulationEntityId, subscriberDetails]);

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
          {feedback ? <div className={`global-notice ${feedback.tone}`}>{feedback.text}</div> : null}

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

                <div className="dashboard-card">
                  <div className="card-header">
                    <h3 className="card-title">运营控制面</h3>
                  </div>
                  <div className="card-body">
                    <div className="ops-dashboard-strip">
                      {(summary?.operationsWorkbench.priorityBands || []).map((item) => (
                        <div key={item.priority} className={`ops-priority-band compact ${item.priority.toLowerCase()}`}>
                          <strong>{item.priority}</strong>
                          <span>{item.caseCount} 个 Case</span>
                        </div>
                      ))}
                    </div>
                    <div className="ops-dashboard-list">
                      {(summary?.operationsWorkbench.focusCases || []).slice(0, 4).map((item) => (
                        <button
                          key={item.caseId}
                          type="button"
                          className="ops-dashboard-item"
                          onClick={() => openCaseInWorkbench(item.caseId)}
                        >
                          <div>
                            <div className="alert-name">{item.displayName || item.entityId}</div>
                            <div className="alert-meta">{item.recommendedAction || item.nextAction?.label || "等待动作"}</div>
                          </div>
                          <div className="ops-dashboard-item-right">
                            <span className={`risk-status ${riskTone((item.risk_level as RiskLevel) || "LOW")}`}>
                              {riskLabel((item.risk_level as RiskLevel) || "LOW")}
                            </span>
                            <span className="ops-dashboard-count">{item.openTaskCount} 待办</span>
                          </div>
                        </button>
                      ))}
                      {!summary?.operationsWorkbench.focusCases.length ? <EmptyState message="暂无运营对象" /> : null}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : null}

          {page === "ontologyStudio" ? (
            <div className="page active ontology-studio-shell">
              <OntologyWorkbench
                workspace={ontologyWorkspace}
                loading={loading}
                draftBusy={ontologyDraftBusy}
                onSaveDraftChange={(payload) => {
                  void handleSaveOntologyDraftChange(payload);
                }}
                onPublishDraft={() => {
                  void handlePublishOntologyDraft();
                }}
                onRevertDraftChange={(changeId) => {
                  void handleRevertOntologyDraftChange(changeId);
                }}
                onDiscardDraft={() => {
                  void handleDiscardOntologyDraft();
                }}
              />
            </div>
          ) : null}

          {page === "simulation" ? (
            <div className="page active">
              <OntologySimulationWorkbench
                entityLabel={summary?.primaryEntityLabel || "实体"}
                alerts={alerts}
                selectedEntityId={simulationEntityId}
                selectedSubscriber={selectedSimulationSubscriber}
                loading={loading}
                detailLoading={simulationDetailLoading}
                detailError={simulationDetailError}
                actionBusyKey={actionBusyKey}
                onSelectEntity={setSimulationEntityId}
                onExecuteAction={(actionId, caseId, entityId) => {
                  void handleExecuteRuntimeAction(actionId, caseId, entityId);
                }}
                onOpenGraph={openEntityInGraph}
                onOpenCase={openCaseInWorkbench}
              />
            </div>
          ) : null}

          {page === "operations" ? (
            <div className="page active ops-page-shell">
              <OperationsWorkbench
                summary={summary}
                cases={cases}
                tasks={selectedOperationsTasks}
                selectedCaseId={selectedCaseId}
                selectedCaseSummary={selectedCaseSummary}
                selectedCase={selectedCase}
                loading={loading}
                caseLoading={caseLoading}
                actionBusyKey={actionBusyKey}
                onSelectCase={setSelectedCaseId}
                onOpenGraph={openEntityInGraph}
                onExecuteAction={(actionId, caseId, entityId) => {
                  void handleExecuteRuntimeAction(actionId, caseId, entityId);
                }}
              />
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

          {page === "ontologyMap" ? (
            <div className="page active">
              <PageHeader title="本体图谱" subtitle="以对象模型为骨架，串联实体、属性、关系、规则和动作，便于从建模视角理解系统语义。" />

              <div className="ontology-map-strip">
                {(Object.keys(ONTOLOGY_KIND_LABELS) as OntologyKind[]).map((kind) => (
                  <button
                    key={kind}
                    type="button"
                    className="ontology-map-card"
                    onClick={() => focusOntologyKind(kind)}
                    disabled={ontologyGraphPayload.counts[kind] === 0}
                  >
                    <span className="ontology-map-card-label">{ONTOLOGY_KIND_LABELS[kind]}</span>
                    <strong className="ontology-map-card-value">{ontologyGraphPayload.counts[kind]}</strong>
                    <span className="ontology-map-card-note">{ONTOLOGY_KIND_NOTES[kind]}</span>
                  </button>
                ))}
              </div>

              <div className="graph-container ontology-map-container">
                <div className="graph-canvas ontology-map-canvas">
                  {ontologyNodes.length ? (
                    <>
                      <div className="ontology-map-banner">建议先从“实体”节点开始，再沿关系追踪到规则和动作，阅读路径更清晰。</div>
                      <div className="graph-stats ontology-map-stats">
                        <span>实体: {ontologyGraphPayload.counts.entity}</span>|
                        <span> 属性: {ontologyGraphPayload.counts.property}</span>|
                        <span> 关系: {ontologyGraphPayload.counts.relation}</span>|
                        <span> 规则: {ontologyGraphPayload.counts.rule}</span>|
                        <span> 动作: {ontologyGraphPayload.counts.action}</span>
                      </div>
                      <div className="graph-legend ontology-map-legend">
                        <h4>语义类型</h4>
                        <div className="legend-items">
                          {ontologyLegendTypes.map((type) => (
                            <div key={type} className="legend-item">
                              <span className="legend-color" style={{ background: NODE_TYPE_COLORS[type] || "#999999" }} />
                              <span>{NODE_TYPE_LABELS[type] || type}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      <GraphCanvas
                        graph={ontologyGraph}
                        selectedNodeId={selectedOntologyNodeId}
                        onSelectNode={(node) => {
                          setSelectedOntologyNodeId(node.id);
                        }}
                      />
                    </>
                  ) : (
                    <div className="graph-empty">
                      <SvgIcon name="relation" size={48} />
                      <p>{loading ? "正在整理本体图谱..." : "当前没有可展示的本体语义结构"}</p>
                    </div>
                  )}
                </div>

                <div className="node-detail-panel ontology-detail-panel">
                  {!selectedOntologyNode ? (
                    <EmptyState message="在本体图谱中选择一个节点，查看它的语义说明、关键字段与关联对象。" />
                  ) : (
                    <div className="node-detail-content">
                      <div className="detail-header">
                        <div className="detail-icon" style={{ background: NODE_TYPE_COLORS[selectedOntologyNode.type] || "#999999" }}>
                          <SvgIcon name="relation" size={28} color="#ffffff" />
                        </div>
                        <h3>{selectedOntologyNode.label}</h3>
                        <span className="node-type-tag">{ONTOLOGY_KIND_LABELS[selectedOntologyNode.kind]}</span>
                      </div>

                      <div className="detail-body">
                        <div className="ontology-hero">
                          <div className="ontology-hero-label">语义说明</div>
                          <div className="ontology-hero-summary">{selectedOntologyNode.description}</div>
                        </div>

                        <div className="detail-section">
                          <div className="detail-section-title">关键字段</div>
                          {selectedOntologyNode.details.map((item) => (
                            <div key={`${selectedOntologyNode.id}-${item.label}`} className="detail-property">
                              <span className="detail-property-key">{item.label}</span>
                              <span className="detail-property-value">{item.value}</span>
                            </div>
                          ))}
                        </div>

                        {(selectedOntologyNode.collections ?? []).map((collection) => (
                          <div key={`${selectedOntologyNode.id}-${collection.title}`} className="detail-section">
                            <div className="detail-section-title">{collection.title}</div>
                            <div className="token-list">
                              {collection.items.map((item) => (
                                <span key={`${collection.title}-${item}`} className={`token-chip ${collection.tone || "ontology"}`}>
                                  {item}
                                </span>
                              ))}
                            </div>
                          </div>
                        ))}

                        <div className="detail-section">
                          <div className="detail-section-title">关联对象</div>
                          {ontologyNodeLinks.length ? (
                            <div className="ontology-link-list">
                              {ontologyNodeLinks.map((item) => (
                                <button
                                  key={item.key}
                                  type="button"
                                  className="ontology-link-card"
                                  onClick={() => setSelectedOntologyNodeId(item.node.id)}
                                >
                                  <span className="ontology-link-label">{item.label}</span>
                                  <strong>{item.node.label}</strong>
                                  <span className="ontology-link-type">{ONTOLOGY_KIND_LABELS[item.node.kind]}</span>
                                </button>
                              ))}
                            </div>
                          ) : (
                            <div className="detail-muted">当前节点没有额外的邻接对象。</div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
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

                        {selectedRuntimeCase ? (
                          <div className="detail-section">
                            <div className="detail-section-title">运营处置</div>
                            <div className="ops-inline-card">
                              <div className="ops-inline-top">
                                <div>
                                  <div className="ops-inline-title">{selectedRuntimeCase.displayName || selectedRuntimeCase.entityId}</div>
                                  <div className="ops-inline-meta">
                                    {selectedRuntimeCase.caseId} · {selectedRuntimeCase.state} · {selectedRuntimeCase.queue_name}
                                  </div>
                                </div>
                                <button
                                  type="button"
                                  className="ops-jump-button"
                                  onClick={() => openCaseInWorkbench(selectedRuntimeCase.caseId)}
                                >
                                  打开工作台
                                </button>
                              </div>
                              <div className="token-list">
                                {(selectedRuntimeCase.availableActions || []).map((action) => {
                                  const busy = actionBusyKey === `${selectedRuntimeCase.caseId}:${action.id}`;
                                  return (
                                    <button
                                      key={action.id}
                                      type="button"
                                      className="token-chip rule action-token"
                                      disabled={busy}
                                      onClick={() => {
                                        void handleExecuteRuntimeAction(
                                          action.id,
                                          selectedRuntimeCase.caseId,
                                          selectedRuntimeCase.entityId,
                                        );
                                      }}
                                    >
                                      {busy ? "执行中..." : action.label}
                                    </button>
                                  );
                                })}
                              </div>
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
              <PageHeader title="智能问答" subtitle="基于本体对象与工具编排的运营问答助手" />

              <div className="qa-container">
                <div className="qa-capability-card">
                  <div className="capability-left">
                    <div className="capability-icon">
                      <SvgIcon name="bot" size={32} color="#ffffff" />
                    </div>
                    <div className="capability-text">
                      <h3>{summary?.agentProfile.name || "运营智能问答"}</h3>
                      <p>以 ontology objects 为上下文，以 query/get/semantic-query/execute-action 为工具，受控编排回答运营问题。</p>
                    </div>
                  </div>
                  <div className="capability-status">
                    <span className={`status-badge ${summary ? "success" : "error"}`}>
                      {summary ? `${summary.agentProfile.objectCount} Objects / ${summary.agentProfile.toolCount} Tools` : "等待后端连接"}
                    </span>
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
                        {message.toolSummary ? <div className="message-meta">{message.toolSummary}</div> : null}
                        {message.requiresConfirmation && message.pendingAction ? (
                          <div className="message-action-card">
                            <div className="message-action-title">待确认动作</div>
                            <div className="message-action-desc">
                              {message.pendingAction.actionLabel || message.pendingAction.actionId}
                            </div>
                            <button
                              type="button"
                              className="btn btn-secondary"
                              disabled={
                                !message.pendingAction.actionId ||
                                actionBusyKey === `${message.pendingAction.caseId}:${message.pendingAction.actionId}`
                              }
                              onClick={() => void handleConfirmPendingAction(message.id, message.pendingAction!)}
                            >
                              {actionBusyKey === `${message.pendingAction.caseId}:${message.pendingAction.actionId}` ? "执行中..." : "确认执行"}
                            </button>
                          </div>
                        ) : null}
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
                    <span className="setting-label">场景 Key</span>
                    <span className="setting-value">{summary?.scenarioKey || "加载中..."}</span>
                  </div>
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
                </div>

                <div className="settings-card">
                  <h3>平台场景包</h3>
                  <div className="setting-item">
                    <span className="setting-label">当前激活</span>
                    <span className="setting-value">{platformSummary?.activeScenarioName || "加载中..."}</span>
                  </div>
                  <div className="setting-item">
                    <span className="setting-label">场景数量</span>
                    <span className="setting-value">{platformSummary?.scenarioCount ?? "-"}</span>
                  </div>
                  <div className="setting-item multiline">
                    <span className="setting-label">平台状态文件</span>
                    <span className="setting-value setting-path">{platformSummary?.statePath || "-"}</span>
                  </div>
                  <div className="platform-scenario-list">
                    {(platformSummary?.scenarios || []).map((item) => (
                      <div key={item.key} className={`platform-scenario-item ${item.active ? "active" : ""}`}>
                        <div className="platform-scenario-head">
                          <strong>{item.name}</strong>
                          <span>{item.version}</span>
                        </div>
                        <div className="platform-scenario-meta">{item.key}</div>
                        <div className="platform-scenario-desc">{item.description || "未提供描述"}</div>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          disabled={switchingScenario || item.active}
                          onClick={() => void handleActivateScenario(item.key)}
                        >
                          {item.active ? "当前场景" : switchingScenario ? "切换中..." : "激活场景"}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </main>
      </div>
    </div>
  );
}
