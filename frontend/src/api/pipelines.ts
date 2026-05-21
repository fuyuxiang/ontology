import { get, post, put, del } from './client'

export interface PipelineRun {
  id: string
  pipeline_id: string
  status: 'running' | 'success' | 'error' | 'stopped' | 'pending' | 'idle'
  step_index: number
  step_label: string
  records: number
  duration_ms: number
  progress: number
  started_at: string
}

export interface Pipeline {
  id: string
  name: string
  description: string
  source: string
  target: string
  datasource_id: string | null
  steps: string[]
  tags: string[]
  schedule: string
  step_duration_ms: number
  status: 'idle' | 'running' | 'success' | 'error' | 'stopped'
  last_run_at: string | null
  last_records: number | null
  last_objects: number | null
  last_duration_ms: number | null
  recent_runs: PipelineRun[]
}

export interface PipelineSummary {
  total: number
  running: number
  success: number
  stopped: number
  error: number
  idle: number
  total_records_last_run: number
}

export interface PipelinePayload {
  name: string
  description: string
  source: string
  target: string
  datasource_id: string | null
  steps: string[]
  tags: string[]
  schedule: string
  step_duration_ms: number
}

export function listPipelines(params?: { keyword?: string; status?: string }) {
  return get<{ items: Pipeline[]; summary: PipelineSummary }>('/pipelines', { params })
}

export function listActiveRuns() {
  return get<{ items: PipelineRun[] }>('/pipelines/runs/active')
}

export function getPipeline(id: string) {
  return get<Pipeline>(`/pipelines/${id}`)
}

export function createPipeline(body: PipelinePayload) {
  return post<Pipeline>('/pipelines', body)
}

export function updatePipeline(id: string, body: PipelinePayload) {
  return put<Pipeline>(`/pipelines/${id}`, body)
}

export function deletePipeline(id: string) {
  return del<void>(`/pipelines/${id}`)
}

export function runPipeline(id: string) {
  return post<PipelineRun>(`/pipelines/${id}/run`)
}

export function stopPipeline(id: string) {
  return post<PipelineRun>(`/pipelines/${id}/stop`)
}
