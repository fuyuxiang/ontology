import { useEffect, useState, type CSSProperties } from "react";

import { searchSubscribers } from "../services/api";
import type { SubscriberDetail, SubscriberListItem } from "../types";
import { GraphCanvas, NODE_TYPE_LABELS } from "./GraphCanvas";

type SimulationStepKey = "entity" | "relations" | "rules" | "result" | "actions";

interface SimulationAssociation {
  key: string;
  nodeId: string;
  label: string;
  relation: string;
  typeLabel: string;
}

const SIMULATION_STEPS: Array<{
  key: SimulationStepKey;
  title: string;
  description: string;
}> = [
  {
    key: "entity",
    title: "锁定对象",
    description: "读取输入实体的主档信息，确定本次推理演示的起点。",
  },
  {
    key: "relations",
    title: "展开关联",
    description: "沿对象关系拉出相关交互、账务、业务和处置上下文。",
  },
  {
    key: "rules",
    title: "命中规则",
    description: "展示触发推理的规则与风险因子，说明结论不是黑箱给出的。",
  },
  {
    key: "result",
    title: "生成结论",
    description: "汇总规则命中、事件规模与风险等级，形成最终推理结果。",
  },
  {
    key: "actions",
    title: "执行动作",
    description: "给出处置建议与当前可执行动作，并直接联动运营闭环。",
  },
];

const NON_ASSOCIATION_TYPES = new Set(["RiskResult", "Action", "Inference", "Case", "Task", "Event", "ActionDefinition"]);

function riskLabel(level?: string) {
  if (level === "HIGH") {
    return "高风险";
  }
  if (level === "MEDIUM") {
    return "中风险";
  }
  if (level === "LOW") {
    return "低风险";
  }
  return "待判定";
}

function riskTone(level?: string) {
  if (level === "HIGH") {
    return "high";
  }
  if (level === "MEDIUM") {
    return "medium";
  }
  if (level === "LOW") {
    return "low";
  }
  return "neutral";
}

function compactFieldText(fields: Array<{ label: string; value: string | number | boolean | null }>, maxItems = 2) {
  return fields
    .filter((field) => field.value !== "" && field.value !== null && field.value !== undefined)
    .slice(0, maxItems)
    .map((field) => `${field.label}: ${field.value}`)
    .join(" / ");
}

function buildAssociationItems(detail: SubscriberDetail | null): SimulationAssociation[] {
  const primaryNodeId = detail?.graph.nodes[0]?.id;
  if (!detail || !primaryNodeId) {
    return [];
  }

  const nodeById = new Map(detail.graph.nodes.map((node) => [node.id, node]));
  const seen = new Set<string>();
  const items: SimulationAssociation[] = [];

  for (const edge of detail.graph.edges) {
    if (edge.source !== primaryNodeId && edge.target !== primaryNodeId) {
      continue;
    }

    const relatedNodeId = edge.source === primaryNodeId ? edge.target : edge.source;
    const relatedNode = nodeById.get(relatedNodeId);
    if (!relatedNode || NON_ASSOCIATION_TYPES.has(relatedNode.type)) {
      continue;
    }

    const key = `${edge.label}:${relatedNode.id}`;
    if (seen.has(key)) {
      continue;
    }

    seen.add(key);
    items.push({
      key,
      nodeId: relatedNode.id,
      label: relatedNode.label,
      relation: edge.label,
      typeLabel: NODE_TYPE_LABELS[relatedNode.type] || relatedNode.type,
    });
  }

  return items;
}

function findFocusNodeId(detail: SubscriberDetail | null, activeStepIndex: number, associations: SimulationAssociation[]) {
  if (!detail) {
    return null;
  }

  const primaryNodeId = detail.graph.nodes[0]?.id ?? null;
  const firstRuleNode = detail.graph.nodes.find((node) => node.id.startsWith("rule:"))?.id;
  const firstInferenceNode = detail.graph.nodes.find((node) => node.type === "Inference")?.id;
  const resultNodeId = detail.graph.nodes.find((node) => node.type === "RiskResult")?.id;
  const actionNodeId =
    detail.graph.nodes.find((node) => node.type === "ActionDefinition")?.id ||
    detail.graph.nodes.find((node) => node.type === "Action")?.id;

  if (activeStepIndex === 1) {
    return associations[0]?.nodeId || primaryNodeId;
  }
  if (activeStepIndex === 2) {
    return firstRuleNode || firstInferenceNode || primaryNodeId;
  }
  if (activeStepIndex === 3) {
    return resultNodeId || primaryNodeId;
  }
  if (activeStepIndex >= 4) {
    return actionNodeId || primaryNodeId;
  }
  return primaryNodeId;
}

function EmptySimulation({ message }: { message: string }) {
  return <div className="simulation-empty-inline">{message}</div>;
}

interface OntologySimulationWorkbenchProps {
  entityLabel: string;
  alerts: SubscriberListItem[];
  selectedEntityId: string | null;
  selectedSubscriber: SubscriberDetail | null;
  loading: boolean;
  detailLoading: boolean;
  detailError: string;
  actionBusyKey: string | null;
  onSelectEntity: (entityId: string) => void;
  onExecuteAction: (actionId: string, caseId: string, entityId: string) => void;
  onOpenGraph: (entityId: string) => void;
  onOpenCase: (caseId: string) => void;
}

export function OntologySimulationWorkbench({
  entityLabel,
  alerts,
  selectedEntityId,
  selectedSubscriber,
  loading,
  detailLoading,
  detailError,
  actionBusyKey,
  onSelectEntity,
  onExecuteAction,
  onOpenGraph,
  onOpenCase,
}: OntologySimulationWorkbenchProps) {
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SubscriberListItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [activeStepIndex, setActiveStepIndex] = useState(-1);
  const [playVersion, setPlayVersion] = useState(0);

  useEffect(() => {
    const keyword = query.trim();
    if (!keyword) {
      setSearchResults([]);
      setSearching(false);
      setSearchError("");
      return;
    }

    let cancelled = false;
    const controller = new AbortController();
    const timerId = window.setTimeout(() => {
      setSearching(true);
      setSearchError("");

      void searchSubscribers(keyword, controller.signal)
        .then((results) => {
          if (cancelled) {
            return;
          }
          setSearchResults(results);
        })
        .catch((error) => {
          if (cancelled || error?.name === "AbortError") {
            return;
          }
          setSearchError(error instanceof Error ? error.message : "搜索实体失败");
        })
        .finally(() => {
          if (cancelled) {
            return;
          }
          setSearching(false);
        });
    }, 260);

    return () => {
      cancelled = true;
      controller.abort();
      window.clearTimeout(timerId);
    };
  }, [query]);

  useEffect(() => {
    if (!selectedSubscriber) {
      setActiveStepIndex(-1);
      return;
    }

    setActiveStepIndex(-1);
    const timerIds = SIMULATION_STEPS.map((_, index) =>
      window.setTimeout(() => {
        setActiveStepIndex(index);
      }, 220 + index * 520),
    );

    return () => {
      timerIds.forEach((timerId) => window.clearTimeout(timerId));
    };
  }, [playVersion, selectedSubscriber?.entityId]);

  const quickPicks = alerts.slice(0, 6);
  const listItems = query.trim() ? searchResults : quickPicks;
  const associations = buildAssociationItems(selectedSubscriber);
  const focusNodeId = findFocusNodeId(selectedSubscriber, activeStepIndex, associations);
  const availableActions = selectedSubscriber?.availableActions || [];
  const caseId = selectedSubscriber?.case?.caseId || "";
  const recentTimeline = (selectedSubscriber?.timeline || []).slice(-3).reverse();

  function handlePickEntity(entityId: string) {
    onSelectEntity(entityId);
    setPlayVersion((current) => current + 1);
  }

  function stepStyle(index: number): CSSProperties {
    return {
      animationDelay: `${index * 120}ms`,
    };
  }

  return (
    <div className="simulation-page">
      <div className="simulation-topbar">
        <div>
          <h2 className="simulation-title">本体模拟</h2>
          <p className="simulation-subtitle">输入一个实体，按关联对象、规则命中、推理结果和处置动作的顺序回放本体链路。</p>
        </div>
        <div className="simulation-top-actions">
          <button
            type="button"
            className="simulation-action-btn"
            disabled={!selectedEntityId}
            onClick={() => {
              if (selectedEntityId) {
                onOpenGraph(selectedEntityId);
              }
            }}
          >
            打开图谱
          </button>
          <button
            type="button"
            className="simulation-action-btn primary"
            disabled={!selectedSubscriber}
            onClick={() => setPlayVersion((current) => current + 1)}
          >
            重新播放
          </button>
        </div>
      </div>

      <div className="simulation-shell">
        <aside className="simulation-sidebar">
          <div className="simulation-search-card">
            <div className="simulation-card-title">输入实体</div>
            <div className="simulation-search-input">
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={`输入${entityLabel} ID、名称或关键字`}
              />
            </div>
            <div className="simulation-search-meta">
              <span>{query.trim() ? "搜索结果" : "快捷对象"}</span>
              <span>{searching ? "检索中..." : `${listItems.length} 个候选`}</span>
            </div>
            {searchError ? <div className="simulation-inline-error">{searchError}</div> : null}
            <div className="simulation-entity-list">
              {loading ? <EmptySimulation message="正在加载对象列表..." /> : null}
              {!loading && !searching && !listItems.length ? <EmptySimulation message="没有找到匹配对象。" /> : null}
              {!loading &&
                listItems.map((item) => (
                  <button
                    key={item.entityId}
                    type="button"
                    className={`simulation-entity-card ${selectedEntityId === item.entityId ? "active" : ""}`}
                    onClick={() => handlePickEntity(item.entityId)}
                  >
                    <div className="simulation-entity-head">
                      <strong>{item.displayName || item.entityId}</strong>
                      <span className={`simulation-risk-pill ${riskTone(item.riskLevel)}`}>{riskLabel(item.riskLevel)}</span>
                    </div>
                    <div className="simulation-entity-id">{item.entityId}</div>
                    <div className="simulation-entity-summary">
                      {compactFieldText(item.summaryFields) || item.recommendedAction || "等待推理说明"}
                    </div>
                  </button>
                ))}
            </div>
          </div>

          <div className="simulation-search-card compact">
            <div className="simulation-card-title">当前对象摘要</div>
            {!selectedSubscriber ? (
              <EmptySimulation message="选择左侧对象后开始回放。" />
            ) : (
              <div className="simulation-overview-stack">
                <div className="simulation-overview-head">
                  <strong>{selectedSubscriber.displayName}</strong>
                  <span className={`simulation-risk-pill ${riskTone(selectedSubscriber.riskLevel)}`}>
                    {riskLabel(selectedSubscriber.riskLevel)}
                  </span>
                </div>
                <div className="simulation-overview-id">{selectedSubscriber.entityId}</div>
                <div className="simulation-kpi-grid">
                  <div>
                    <span>关联节点</span>
                    <strong>{associations.length}</strong>
                  </div>
                  <div>
                    <span>命中规则</span>
                    <strong>{selectedSubscriber.rules.length}</strong>
                  </div>
                  <div>
                    <span>时间线</span>
                    <strong>{selectedSubscriber.timeline?.length || 0}</strong>
                  </div>
                  <div>
                    <span>动作数</span>
                    <strong>{availableActions.length}</strong>
                  </div>
                </div>
                <div className="simulation-overview-summary">
                  {selectedSubscriber.inference.summary || selectedSubscriber.recommendedAction}
                </div>
                {caseId ? (
                  <button type="button" className="simulation-action-btn" onClick={() => onOpenCase(caseId)}>
                    打开当前 Case
                  </button>
                ) : null}
              </div>
            )}
          </div>
        </aside>

        <section className="simulation-main">
          {detailLoading ? <EmptySimulation message="正在构建实体推理链路..." /> : null}
          {detailError ? <div className="simulation-inline-error standalone">{detailError}</div> : null}

          {!detailLoading && !selectedSubscriber ? (
            <EmptySimulation message="当前没有可回放的实体，请先从左侧选择一个对象。" />
          ) : null}

          {!detailLoading && selectedSubscriber ? (
            <>
              <div className="simulation-hero-card">
                <div className="simulation-hero-copy">
                  <span className="simulation-hero-label">推理结论</span>
                  <h3>{selectedSubscriber.inference.headline}</h3>
                  <p>{selectedSubscriber.inference.summary}</p>
                </div>
                <div className="simulation-hero-metrics">
                  <div>
                    <span>风险等级</span>
                    <strong>{riskLabel(selectedSubscriber.inference.riskLevel)}</strong>
                  </div>
                  <div>
                    <span>命中规则</span>
                    <strong>{selectedSubscriber.inference.ruleCount}</strong>
                  </div>
                  <div>
                    <span>关联事件</span>
                    <strong>{selectedSubscriber.inference.eventCount}</strong>
                  </div>
                  <div>
                    <span>建议动作</span>
                    <strong>{selectedSubscriber.inference.recommendedAction}</strong>
                  </div>
                </div>
              </div>

              <div className="simulation-workspace">
                <div className="simulation-graph-card">
                  <div className="simulation-card-title">推理链路图</div>
                  <div className="simulation-graph-frame">
                    <GraphCanvas
                      graph={selectedSubscriber.graph}
                      selectedNodeId={focusNodeId}
                      showEdgeLabels
                      showControls={false}
                    />
                  </div>
                </div>

                <div className="simulation-flow-card">
                  {SIMULATION_STEPS.map((step, index) => {
                    const unlocked = activeStepIndex >= index;
                    const current = activeStepIndex === index;
                    return (
                      <section
                        key={`${selectedSubscriber.entityId}-${playVersion}-${step.key}`}
                        className={`simulation-step ${unlocked ? "active" : ""} ${current ? "current" : ""}`}
                        style={stepStyle(index)}
                      >
                        <div className="simulation-step-index">{index + 1}</div>
                        <div className="simulation-step-body">
                          <div className="simulation-step-head">
                            <div>
                              <h3>{step.title}</h3>
                              <p>{step.description}</p>
                            </div>
                            <span className={`simulation-step-status ${unlocked ? "done" : "pending"}`}>
                              {unlocked ? "已展开" : "等待中"}
                            </span>
                          </div>

                          {step.key === "entity" ? (
                            <div className="simulation-detail-grid">
                              {selectedSubscriber.summaryFields.slice(0, 6).map((field) => (
                                <div key={field.label} className="simulation-detail-card">
                                  <span>{field.label}</span>
                                  <strong>{String(field.value ?? "-")}</strong>
                                </div>
                              ))}
                            </div>
                          ) : null}

                          {step.key === "relations" ? (
                            associations.length ? (
                              <div className="simulation-chip-grid">
                                {associations.map((item, relationIndex) => (
                                  <div
                                    key={item.key}
                                    className="simulation-link-card"
                                    style={{ animationDelay: `${160 + relationIndex * 90}ms` }}
                                  >
                                    <span className="simulation-link-label">{item.relation}</span>
                                    <strong>{item.label}</strong>
                                    <span className="simulation-link-type">{item.typeLabel}</span>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <EmptySimulation message="当前对象没有额外的关联实体说明。" />
                            )
                          ) : null}

                          {step.key === "rules" ? (
                            <div className="simulation-rule-stage">
                              <div className="simulation-token-strip">
                                {selectedSubscriber.rules.length ? (
                                  selectedSubscriber.rules.map((rule) => (
                                    <span key={rule} className="simulation-token rule">
                                      {rule}
                                    </span>
                                  ))
                                ) : (
                                  <EmptySimulation message="当前没有显式命中的规则。" />
                                )}
                              </div>
                              <div className="simulation-token-strip">
                                {selectedSubscriber.factors.length ? (
                                  selectedSubscriber.factors.map((factor) => (
                                    <span key={factor} className="simulation-token factor">
                                      {factor}
                                    </span>
                                  ))
                                ) : null}
                              </div>
                            </div>
                          ) : null}

                          {step.key === "result" ? (
                            <div className={`simulation-result-card ${riskTone(selectedSubscriber.inference.riskLevel)}`}>
                              <div className="simulation-result-top">
                                <span className="simulation-risk-pill solid">{riskLabel(selectedSubscriber.inference.riskLevel)}</span>
                                <strong>{selectedSubscriber.inference.recommendedAction}</strong>
                              </div>
                              <p>{selectedSubscriber.inference.summary}</p>
                              <div className="simulation-detail-grid compact">
                                <div className="simulation-detail-card">
                                  <span>因子数</span>
                                  <strong>{selectedSubscriber.inference.factorCount}</strong>
                                </div>
                                <div className="simulation-detail-card">
                                  <span>规则数</span>
                                  <strong>{selectedSubscriber.inference.ruleCount}</strong>
                                </div>
                                <div className="simulation-detail-card">
                                  <span>事件数</span>
                                  <strong>{selectedSubscriber.inference.eventCount}</strong>
                                </div>
                              </div>
                            </div>
                          ) : null}

                          {step.key === "actions" ? (
                            <div className="simulation-action-stage">
                              <div className="simulation-action-head">
                                <div>
                                  <strong>当前建议</strong>
                                  <p>{selectedSubscriber.recommendedAction}</p>
                                </div>
                                {selectedSubscriber.case ? (
                                  <div className="simulation-case-meta">
                                    <span>{selectedSubscriber.case.caseId}</span>
                                    <span>{selectedSubscriber.case.state}</span>
                                  </div>
                                ) : null}
                              </div>

                              {availableActions.length && caseId ? (
                                <div className="simulation-action-grid">
                                  {availableActions.map((action) => {
                                    const busy = actionBusyKey === `${caseId}:${action.id}`;
                                    return (
                                      <button
                                        key={action.id}
                                        type="button"
                                        className="simulation-run-button"
                                        disabled={busy}
                                        onClick={() => onExecuteAction(action.id, caseId, selectedSubscriber.entityId)}
                                      >
                                        <span>{busy ? "执行中..." : action.label}</span>
                                        <strong>{action.description}</strong>
                                      </button>
                                    );
                                  })}
                                </div>
                              ) : (
                                <EmptySimulation message="当前对象没有可直接执行的动作。" />
                              )}

                              {recentTimeline.length ? (
                                <div className="simulation-timeline-list">
                                  {recentTimeline.map((item) => (
                                    <div key={`${item.time}-${item.title}`} className="simulation-timeline-item">
                                      <span>{item.time}</span>
                                      <strong>{item.title}</strong>
                                    </div>
                                  ))}
                                </div>
                              ) : null}
                            </div>
                          ) : null}
                        </div>
                      </section>
                    );
                  })}
                </div>
              </div>
            </>
          ) : null}
        </section>
      </div>
    </div>
  );
}
