import type {
  ActionDefinition,
  OperationalCase,
  OperationalCaseSummary,
  Summary,
  TaskItem,
} from "../types";

function formatTime(value?: string) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function queueLabel(value: string) {
  return value.replace(/-/g, " ");
}

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
  return "未知";
}

function stateLabel(value?: string) {
  const labels: Record<string, string> = {
    OPEN: "待分诊",
    ACKED: "已确认",
    ASSIGNED: "已分派",
    CONTACTED: "已联系",
    OFFERED: "已出方案",
    WON: "已挽回",
    LOST: "已流失",
    RESOLVED: "已解决",
    MONITORING: "监控中",
    CLOSED: "已关闭",
    TODO: "待执行",
    DONE: "已完成",
    CANCELED: "已取消",
  };
  return labels[value || ""] || value || "-";
}

function MetricCard({ label, value, hint }: { label: string; value: string | number; hint: string }) {
  return (
    <div className="ops-metric-card">
      <div className="ops-metric-label">{label}</div>
      <div className="ops-metric-value">{value}</div>
      <div className="ops-metric-hint">{hint}</div>
    </div>
  );
}

function ActionBar({
  actions,
  caseId,
  entityId,
  actionBusyKey,
  onExecuteAction,
}: {
  actions: ActionDefinition[];
  caseId: string;
  entityId: string;
  actionBusyKey: string | null;
  onExecuteAction: (actionId: string, caseId: string, entityId: string) => void;
}) {
  if (!actions.length) {
    return <div className="ops-empty-inline">当前状态下没有可执行动作。</div>;
  }

  return (
    <div className="ops-action-grid">
      {actions.map((action) => {
        const busy = actionBusyKey === `${caseId}:${action.id}`;
        return (
          <button
            key={action.id}
            type="button"
            className="ops-action-button"
            onClick={() => onExecuteAction(action.id, caseId, entityId)}
            disabled={busy}
          >
            <span className="ops-action-title">{busy ? "执行中..." : action.label}</span>
            <span className="ops-action-desc">{action.description}</span>
          </button>
        );
      })}
    </div>
  );
}

interface OperationsWorkbenchProps {
  summary: Summary | null;
  cases: OperationalCaseSummary[];
  tasks: TaskItem[];
  selectedCaseId: string | null;
  selectedCaseSummary: OperationalCaseSummary | null;
  selectedCase: OperationalCase | null;
  loading: boolean;
  caseLoading: boolean;
  actionBusyKey: string | null;
  onSelectCase: (caseId: string) => void;
  onOpenGraph: (entityId: string) => void;
  onExecuteAction: (actionId: string, caseId: string, entityId: string) => void;
}

export function OperationsWorkbench({
  summary,
  cases,
  tasks,
  selectedCaseId,
  selectedCaseSummary,
  selectedCase,
  loading,
  caseLoading,
  actionBusyKey,
  onSelectCase,
  onOpenGraph,
  onExecuteAction,
}: OperationsWorkbenchProps) {
  const workbench = summary?.operationsWorkbench;
  const visibleTasks = selectedCase ? selectedCase.tasks : tasks.slice(0, 8);
  const visibleActions = selectedCase?.availableActions || selectedCaseSummary?.availableActions || [];
  const currentCaseId = selectedCase?.caseId || selectedCaseSummary?.caseId || "";
  const currentEntityId = selectedCase?.entityId || selectedCaseSummary?.entityId || "";

  return (
    <div className="ops-page">
      <div className="ops-topline">
        <div>
          <h2 className="ops-title">运营工作台</h2>
          <p className="ops-subtitle">围绕对象、证据、动作和审计轨迹组织处置流程。</p>
        </div>
        <div className="ops-metrics">
          <MetricCard
            label="Open Cases"
            value={summary?.operationalMetrics.openCaseCount ?? "-"}
            hint="当前需跟进的对象"
          />
          <MetricCard
            label="Todo Tasks"
            value={summary?.operationalMetrics.todoTaskCount ?? "-"}
            hint="待办任务总量"
          />
          <MetricCard
            label="Actions"
            value={summary?.operationalMetrics.actionRunCount ?? "-"}
            hint="已执行动作次数"
          />
          <MetricCard
            label="Events"
            value={summary?.operationalMetrics.eventCount ?? "-"}
            hint="审计事件沉淀"
          />
        </div>
      </div>

      <div className="ops-strip-grid">
        <div className="ops-strip-card">
          <div className="ops-strip-title">优先级带</div>
          <div className="ops-priority-grid">
            {(workbench?.priorityBands || []).map((band) => (
              <div key={band.priority} className={`ops-priority-band ${band.priority.toLowerCase()}`}>
                <div className="ops-priority-head">
                  <strong>{band.priority}</strong>
                  <span>{band.label}</span>
                </div>
                <div className="ops-priority-stats">
                  <span>{band.caseCount} 个 Case</span>
                  <span>{band.openTaskCount} 个任务</span>
                  <span>{band.actionableCount} 个可执行</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="ops-strip-card">
          <div className="ops-strip-title">队列视图</div>
          <div className="ops-lane-grid">
            {(workbench?.queueLanes || []).map((lane) => (
              <div key={lane.queueName} className="ops-lane-card">
                <div className="ops-lane-name">{lane.label}</div>
                <div className="ops-lane-meta">
                  <span>{lane.caseCount} 个 Case</span>
                  <span>{lane.taskCount} 个任务</span>
                  <span>{lane.highRiskCount} 个高风险</span>
                </div>
                <div className="ops-lane-owners">{lane.owners.join(" / ") || "未分派"}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="ops-focus-card">
        <div className="ops-strip-title">重点对象</div>
        <div className="ops-focus-grid">
          {(workbench?.focusCases || []).map((item) => (
            <button key={item.caseId} type="button" className="ops-focus-item" onClick={() => onSelectCase(item.caseId)}>
              <div className="ops-focus-top">
                <span className={`ops-risk-pill ${(item.risk_level || "").toLowerCase()}`}>{riskLabel(item.risk_level)}</span>
                <span className="ops-state-pill">{stateLabel(item.state)}</span>
              </div>
              <div className="ops-focus-name">{item.displayName || item.entityId}</div>
              <div className="ops-focus-meta">{item.summaryFields?.map((field) => `${field.label}: ${field.value}`).join(" | ") || item.recommendedAction}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="ops-layout">
        <section className="ops-column ops-column-list">
          <div className="ops-panel-header">
            <h3>对象队列</h3>
            <span>{cases.length} 个对象</span>
          </div>
          <div className="ops-case-list">
            {loading ? <div className="ops-empty-inline">正在加载工作台数据...</div> : null}
            {!loading && cases.length === 0 ? <div className="ops-empty-inline">当前没有可处置对象。</div> : null}
            {!loading &&
              cases.map((item) => (
                <button
                  key={item.caseId}
                  type="button"
                  className={`ops-case-card ${selectedCaseId === item.caseId ? "active" : ""}`}
                  onClick={() => onSelectCase(item.caseId)}
                >
                  <div className="ops-case-row">
                    <span className="ops-case-name">{item.displayName || item.entityId}</span>
                    <span className={`ops-risk-pill ${(item.risk_level || "").toLowerCase()}`}>{riskLabel(item.risk_level)}</span>
                  </div>
                  <div className="ops-case-row dense">
                    <span>{item.priority}</span>
                    <span>{stateLabel(item.state)}</span>
                    <span>{queueLabel(item.queue_name)}</span>
                  </div>
                  <div className="ops-case-summary">{item.recommendedAction || "等待下一步处置建议"}</div>
                  <div className="ops-case-row dense">
                    <span>{item.openTaskCount} 个待办</span>
                    <span>{item.nextAction?.label || "无可执行动作"}</span>
                  </div>
                </button>
              ))}
          </div>
        </section>

        <section className="ops-column ops-column-feed">
          <div className="ops-panel-header">
            <h3>{selectedCase ? "当前 Case 任务" : "任务积压"}</h3>
            <span>{visibleTasks.length} 条</span>
          </div>
          <div className="ops-task-list">
            {visibleTasks.length === 0 ? <div className="ops-empty-inline">暂无任务。</div> : null}
            {visibleTasks.map((task) => (
              <div key={task.id} className="ops-task-card">
                <div className="ops-case-row">
                  <strong>{task.title}</strong>
                  <span className="ops-state-pill">{stateLabel(task.status)}</span>
                </div>
                <div className="ops-task-meta">{task.displayName || task.entity_id}</div>
                <div className="ops-case-row dense">
                  <span>{task.priority || "-"}</span>
                  <span>{task.assignee_role}</span>
                  <span>SLA {task.due_sla_hours}h</span>
                </div>
              </div>
            ))}
          </div>

          <div className="ops-panel-header secondary">
            <h3>最近动作</h3>
            <span>{workbench?.recentActions.length ?? 0} 条</span>
          </div>
          <div className="ops-activity-list">
            {(workbench?.recentActions || []).length === 0 ? <div className="ops-empty-inline">暂无动作执行记录。</div> : null}
            {(workbench?.recentActions || []).map((item) => (
              <div key={item.id} className="ops-activity-item">
                <div className="ops-case-row">
                  <strong>{item.label}</strong>
                  <span className="ops-state-pill">{item.status}</span>
                </div>
                <div className="ops-task-meta">
                  {item.displayName} · {item.actorRole}
                </div>
                <div className="ops-activity-time">{formatTime(item.time)}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="ops-column ops-column-detail">
          <div className="ops-panel-header">
            <h3>对象指挥面板</h3>
            <span>{selectedCaseSummary?.caseId || "-"}</span>
          </div>

          {!selectedCaseSummary ? (
            <div className="ops-empty-inline">从左侧选择一个对象查看证据、动作和时间线。</div>
          ) : (
            <div className="ops-detail-stack">
              <div className="ops-detail-hero">
                <div className="ops-detail-top">
                  <div>
                    <div className="ops-detail-name">{selectedCaseSummary.displayName || selectedCaseSummary.entityId}</div>
                    <div className="ops-detail-meta">
                      {selectedCaseSummary.summaryFields?.map((field) => `${field.label}: ${field.value}`).join(" | ") ||
                        selectedCaseSummary.entityId}
                    </div>
                  </div>
                  <div className="ops-detail-tags">
                    <span className={`ops-risk-pill ${(selectedCaseSummary.risk_level || "").toLowerCase()}`}>
                      {riskLabel(selectedCaseSummary.risk_level)}
                    </span>
                    <span className="ops-state-pill">{stateLabel(selectedCaseSummary.state)}</span>
                  </div>
                </div>
                <div className="ops-detail-kpis">
                  <div>
                    <span>Priority</span>
                    <strong>{selectedCaseSummary.priority}</strong>
                  </div>
                  <div>
                    <span>Queue</span>
                    <strong>{queueLabel(selectedCaseSummary.queue_name)}</strong>
                  </div>
                  <div>
                    <span>Open Tasks</span>
                    <strong>{selectedCaseSummary.openTaskCount}</strong>
                  </div>
                </div>
                <div className="ops-detail-guidance">
                  <span className="ops-guidance-label">Next Best Action</span>
                  <strong>{selectedCaseSummary.nextAction?.label || selectedCaseSummary.recommendedAction || "暂无建议"}</strong>
                </div>
                <div className="ops-detail-actions">
                  <button type="button" className="ops-jump-button" onClick={() => onOpenGraph(selectedCaseSummary.entityId)}>
                    打开图谱证据
                  </button>
                </div>
              </div>

              <div className="ops-detail-section">
                <div className="ops-section-title">动作执行</div>
                {currentCaseId && currentEntityId ? (
                  <ActionBar
                    actions={visibleActions}
                    caseId={currentCaseId}
                    entityId={currentEntityId}
                    actionBusyKey={actionBusyKey}
                    onExecuteAction={onExecuteAction}
                  />
                ) : (
                  <div className="ops-empty-inline">当前对象没有可执行动作。</div>
                )}
              </div>

              <div className="ops-detail-section">
                <div className="ops-section-title">对象上下文</div>
                <div className="ops-field-grid">
                  {(selectedCaseSummary.detailFields || []).map((field) => (
                    <div key={field.label} className="ops-field-card">
                      <span>{field.label}</span>
                      <strong>{String(field.value ?? "-")}</strong>
                    </div>
                  ))}
                </div>
              </div>

              <div className="ops-detail-section">
                <div className="ops-section-title">审计时间线</div>
                {caseLoading ? <div className="ops-empty-inline">正在加载 Case 明细...</div> : null}
                {!caseLoading && !selectedCase?.timeline.length ? <div className="ops-empty-inline">暂无时间线记录。</div> : null}
                <div className="ops-timeline">
                  {(selectedCase?.timeline || []).map((item) => (
                    <div key={`${item.kind}-${item.time}-${item.title}`} className="ops-timeline-item">
                      <div className="ops-timeline-time">{formatTime(item.time)}</div>
                      <div className="ops-timeline-content">
                        <strong>{item.title}</strong>
                        <span>{item.reason || item.eventType || item.subjectType || item.kind}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="ops-detail-section">
                <div className="ops-section-title">动作回放</div>
                {!selectedCase?.actionRuns.length ? <div className="ops-empty-inline">暂无动作记录。</div> : null}
                <div className="ops-activity-list">
                  {(selectedCase?.actionRuns || []).map((item) => (
                    <div key={item.id} className="ops-activity-item">
                      <div className="ops-case-row">
                        <strong>{item.action_id}</strong>
                        <span className="ops-state-pill">{item.status}</span>
                      </div>
                      <div className="ops-task-meta">
                        {item.actor_role} · {formatTime(item.updated_at)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
