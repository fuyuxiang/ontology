import { get, post, put, del } from './client'
import type {
  AppBrief, AppCreate, AppUpdate, WorkflowApp,
  ToolSpec, ApprovalTask, PublishedApp,
} from '../types/workflow'

export const workflowApi = {
  // ── 设计态 CRUD ──
  createApp: (data: AppCreate) => post<AppBrief>('/workflow/apps', data),
  listApps: (params?: { status?: string; scene_code?: string }) =>
    get<AppBrief[]>('/workflow/apps', { params }),
  getApp: (id: string) => get<WorkflowApp>(`/workflow/apps/${id}`),
  updateApp: (id: string, data: AppUpdate) => put<AppBrief>(`/workflow/apps/${id}`, data),
  deleteApp: (id: string) => del<{ ok: boolean }>(`/workflow/apps/${id}`),

  // ── 发布 ──
  publish: (id: string) =>
    post<{ app_id: string; version: number; published_json: PublishedApp }>(
      `/workflow/apps/${id}/publish`
    ),
  getPublished: (sceneCode: string) => get<PublishedApp>(`/workflow/published/${sceneCode}`),

  // ── 工具注册 ──
  listTools: () => get<ToolSpec[]>('/workflow/tools'),

  // ── 审批 ──
  listApprovals: (params?: { status?: string; session_id?: string; app_id?: string }) =>
    get<ApprovalTask[]>('/workflow/approvals', { params }),
  approve: (taskId: string) => post<ApprovalTask>(`/workflow/approvals/${taskId}/approve`),
  reject: (taskId: string) => post<ApprovalTask>(`/workflow/approvals/${taskId}/reject`),
}
