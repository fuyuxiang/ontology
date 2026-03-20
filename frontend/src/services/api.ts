import type {
  Alert,
  InferenceTriggerResult,
  SparqlResult,
  SubscriberDetail,
  SubscriberListItem,
  Summary,
} from "../types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "/api";

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

export function getSummary(signal?: AbortSignal): Promise<Summary> {
  return requestJson<Summary>("/summary", { signal });
}

export function getAlerts(signal?: AbortSignal): Promise<Alert[]> {
  return requestJson<Alert[]>("/alerts", { signal });
}

export function searchSubscribers(query: string, signal?: AbortSignal): Promise<SubscriberListItem[]> {
  const params = new URLSearchParams({ q: query });
  return requestJson<SubscriberListItem[]>(`/subscribers?${params.toString()}`, { signal });
}

export function getSubscriber(subscriberId: string, signal?: AbortSignal): Promise<SubscriberDetail> {
  return requestJson<SubscriberDetail>(`/subscribers/${subscriberId}`, { signal });
}

export function runSparql(query: string): Promise<SparqlResult> {
  return requestJson<SparqlResult>("/sparql", {
    method: "POST",
    body: JSON.stringify({ query }),
  });
}

export function triggerInference(): Promise<InferenceTriggerResult> {
  return requestJson<InferenceTriggerResult>("/inference/trigger", {
    method: "POST",
  });
}
