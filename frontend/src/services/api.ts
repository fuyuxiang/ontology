/** 前端 API 访问层，统一封装后端请求与错误处理。 */

import type {
  ActionExecutionResult,
  Alert,
  InferenceTriggerResult,
  OperationalCase,
  OperationalCaseSummary,
  SparqlResult,
  SubscriberDetail,
  SubscriberListItem,
  Summary,
  TaskItem,
} from "../types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "/api";

/** 解析后端错误响应，优先返回业务错误信息。 */
async function parseError(response: Response): Promise<string> {
  const text = await response.text();
  if (!text) {
    return `HTTP ${response.status}`;
  }
  try {
    const body = JSON.parse(text) as { detail?: string };
    return body.detail || text;
  } catch {
    return text;
  }
}

/** 统一发起 JSON 请求并处理非成功状态。 */
async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as T;
}

/** 获取首页汇总数据。 */
export function getSummary(signal?: AbortSignal): Promise<Summary> {
  return requestJson<Summary>("/summary", { signal });
}

/** 获取风险告警列表。 */
export function getAlerts(signal?: AbortSignal): Promise<Alert[]> {
  return requestJson<Alert[]>("/alerts", { signal });
}

/** 按关键字搜索实体。 */
export function searchSubscribers(query: string, signal?: AbortSignal): Promise<SubscriberListItem[]> {
  const params = new URLSearchParams({ q: query });
  return requestJson<SubscriberListItem[]>(`/subscribers?${params.toString()}`, { signal });
}

/** 获取单个实体详情。 */
export function getSubscriber(subscriberId: string, signal?: AbortSignal): Promise<SubscriberDetail> {
  return requestJson<SubscriberDetail>(`/subscribers/${subscriberId}`, { signal });
}

/** 执行 SPARQL 查询。 */
export function runSparql(query: string): Promise<SparqlResult> {
  return requestJson<SparqlResult>("/sparql", {
    method: "POST",
    body: JSON.stringify({ query }),
  });
}

/** 手动触发后端推理。 */
export function triggerInference(): Promise<InferenceTriggerResult> {
  return requestJson<InferenceTriggerResult>("/inference/trigger", {
    method: "POST",
  });
}

/** 获取运营 case 列表。 */
export function getCases(signal?: AbortSignal): Promise<OperationalCaseSummary[]> {
  return requestJson<OperationalCaseSummary[]>("/cases", { signal });
}

/** 获取单个运营 case。 */
export function getCase(caseId: string, signal?: AbortSignal): Promise<OperationalCase> {
  return requestJson<OperationalCase>(`/cases/${caseId}`, { signal });
}

/** 获取任务列表。 */
export function getTasks(params?: { status?: string; assignee_role?: string }, signal?: AbortSignal): Promise<TaskItem[]> {
  const search = new URLSearchParams();
  if (params?.status) {
    search.set("status", params.status);
  }
  if (params?.assignee_role) {
    search.set("assignee_role", params.assignee_role);
  }
  const suffix = search.size ? `?${search.toString()}` : "";
  return requestJson<TaskItem[]>(`/tasks${suffix}`, { signal });
}

/** 执行运营动作。 */
export function executeAction(payload: {
  actionId: string;
  caseId?: string;
  entityId?: string;
  actorRole?: string;
  actorId?: string;
  actorAreaId?: string;
  parameters?: Record<string, string | number | boolean | null>;
}): Promise<ActionExecutionResult> {
  return requestJson<ActionExecutionResult>("/actions/execute", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
