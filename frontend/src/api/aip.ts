/**
 * AIP 场景平台 — 前端 API 客户端
 * 接 backend/app/api/v1/aip_*.py 的所有真实接口
 */
import { get, post, put, del } from './client'

export interface AipSceneBrief {
  id: string
  name: string
  description: string
  group_name: string
  status: 'draft' | 'reviewing' | 'published' | 'archived'
  version: number
  node_count: number
  edge_count: number
  ontology_bindings: string[]
  datasource_bindings: string[]
  stats: Record<string, any>
  trigger_config: Record<string, any>
  created_at: string
  updated_at: string
  created_by: string
  ontology_stale?: boolean
  ontology_stale_detail?: Record<string, any> | null
}

export interface AipSceneFull extends AipSceneBrief {
  nodes_json: any[]
  edges_json: any[]
  input_schema: Record<string, any>
  output_schema: Record<string, any>
  published_version_id: string
}

export interface AipNodeIO {
  node_id: string
  node_type: string
  label: string
  status: 'success' | 'failed'
  input: any
  output: any
  summary: string
  started_at: number
  finished_at: number
  duration_ms: number
}

export interface AipExecutionBrief {
  id: string
  scene_id: string
  scene_name: string
  scene_version: number
  status: 'running' | 'success' | 'failed' | 'cancelled'
  triggered_by: string
  started_at: string
  finished_at: string | null
  duration_ms: number
  error_message: string | null
  node_count: number
}

export interface AipExecutionFull extends AipExecutionBrief {
  input_params: Record<string, any>
  trigger_payload: Record<string, any>
  node_results: Record<string, AipNodeIO>
  final_output: Record<string, any>
  trace_id: string | null
}

export interface AipTrigger {
  id?: string
  scene_id: string
  type: 'schedule' | 'event' | 'webhook' | 'manual'
  enabled: boolean
  cron_expr?: string
  timezone?: string
  schedule_payload?: Record<string, any>
  event_entity?: string
  event_action?: string
  webhook_path?: string
  webhook_secret?: string
  last_fired_at?: string | null
  fire_count?: number
}

export interface AipSceneVersion {
  id: string
  scene_id: string
  version: number
  note: string
  status: string
  published_at: string
  published_by: string
}

// ── 场景 CRUD ──────────────────────────────────────────────

export const listScenes = (params?: { status?: string; group?: string; keyword?: string }) =>
  get<AipSceneBrief[]>('/aip/scenes', { params })

export const getScene = (id: string) => get<AipSceneFull>(`/aip/scenes/${id}`)

export const createScene = (body: Partial<AipSceneFull>) => post<AipSceneFull>('/aip/scenes', body)

export const updateScene = (id: string, body: Partial<AipSceneFull>) =>
  put<AipSceneFull>(`/aip/scenes/${id}`, body)

export const deleteScene = (id: string) => del<{ ok: boolean }>(`/aip/scenes/${id}`)

export const validateScene = (id: string) =>
  post<{ ok: boolean; errors: string[]; warnings: string[] }>(`/aip/scenes/${id}/validate`)

export const publishScene = (id: string) =>
  post<{ ok: boolean; status: string; version: number; version_id: string }>(`/aip/scenes/${id}/publish`)

export const rollbackScene = (id: string, versionId: string) =>
  post<AipSceneFull>(`/aip/scenes/${id}/rollback?version_id=${encodeURIComponent(versionId)}`)

export const listVersions = (id: string) => get<AipSceneVersion[]>(`/aip/scenes/${id}/versions`)

export const testNode = (sceneId: string, nodeId: string) =>
  post<{ ok: boolean; output?: any; error?: string; node_io?: AipNodeIO }>(
    `/aip/scenes/${sceneId}/test?node_id=${encodeURIComponent(nodeId)}`,
  )

// ── 触发器 ─────────────────────────────────────────────────

export const getTrigger = (sceneId: string) => get<AipTrigger>(`/aip/scenes/${sceneId}/trigger`)

export const upsertTrigger = (sceneId: string, body: Partial<AipTrigger>) =>
  put<{ ok: boolean; trigger: AipTrigger }>(`/aip/scenes/${sceneId}/trigger`, body)

export const testFireTrigger = (sceneId: string) =>
  post<{ ok: boolean; scheduled: boolean }>(`/aip/scenes/${sceneId}/trigger/test-fire`)

// ── 执行历史 ───────────────────────────────────────────────

export const listExecutions = (params?: {
  scene_id?: string
  status?: string
  triggered_by?: string
  limit?: number
}) => get<AipExecutionBrief[]>('/aip/executions', { params })

export const getExecution = (eid: string) => get<AipExecutionFull>(`/aip/executions/${eid}`)

export const getExecutionTrace = (eid: string) =>
  get<{ trace_id: string | null; events?: any[] }>(`/aip/executions/${eid}/trace`)

export const replayExecution = (eid: string) =>
  post<{ ok: boolean; scheduled: boolean; source_execution_id: string }>(
    `/aip/executions/${eid}/replay`,
  )

// ── SSE 执行 ───────────────────────────────────────────────

export type AipSseHandler = (event: { type: string;[k: string]: any }) => void

/** 场景 SSE 执行流。返回 abort 函数。 */
export function executeSceneStream(
  sceneId: string,
  inputParams: Record<string, any>,
  onEvent: AipSseHandler,
): () => void {
  const ctrl = new AbortController()
  const token = localStorage.getItem('token') || ''
  const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

  ;(async () => {
    try {
      const resp = await fetch(`${baseURL}/aip/scenes/${sceneId}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ input_params: inputParams || {} }),
        signal: ctrl.signal,
      })
      if (!resp.ok || !resp.body) {
        onEvent({ type: 'scene_failed', error: `HTTP ${resp.status}` })
        return
      }
      const reader = resp.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        let idx
        while ((idx = buffer.indexOf('\n\n')) !== -1) {
          const chunk = buffer.slice(0, idx)
          buffer = buffer.slice(idx + 2)
          const lines = chunk.split('\n')
          let data = ''
          for (const line of lines) {
            if (line.startsWith('data:')) data += line.slice(5).trim()
          }
          if (!data) continue
          if (data === '[DONE]') {
            onEvent({ type: 'sse_done' })
            return
          }
          try {
            onEvent(JSON.parse(data))
          } catch {
            /* ignore parse errors */
          }
        }
      }
    } catch (e: any) {
      if (e?.name === 'AbortError') return
      onEvent({ type: 'scene_failed', error: String(e?.message || e) })
    }
  })()

  return () => ctrl.abort()
}

// ── 资产下拉（PropertyPanel / ResourcePicker 用） ─────────

export const listAgentsAsResources = () => get<any[]>('/agents')
export const listSkillsAsResources = () => get<any[]>('/skills')
export const listRulesAsResources = () => get<any[]>('/rules')
export const listActionsAsResources = () => get<any[]>('/actions')
export const listFunctionsAsResources = () => get<any[]>('/functions')
export const listEntitiesAsResources = () => get<any[]>('/entities')
export const listModelsAsResources = () => get<any[]>('/models')
export const listDatasourcesAsResources = () => get<any[]>('/connections')

// ── 本体发布影响预览 & 陈旧确认 ────────────────────────────

export const ontologyPublishApi = {
  previewImpact: (versionId: string) =>
    get<any>(`/ontology-publish/versions/${versionId}/impact`),
}

export const sceneStaleApi = {
  acknowledgeStale: (sceneId: string) =>
    post<any>(`/aip-scenes/${sceneId}/acknowledge-stale`),
}
