import { defineStore } from 'pinia'
import { ref } from 'vue'
import { workflowApi } from '../api/workflow'
import type { WorkflowApp, AppBrief, ToolSpec, ApprovalTask } from '../types/workflow'

export const useWorkflowStore = defineStore('workflow', () => {
  const apps = ref<AppBrief[]>([])
  const currentApp = ref<WorkflowApp | null>(null)
  const tools = ref<ToolSpec[]>([])
  const approvals = ref<ApprovalTask[]>([])
  const saving = ref(false)
  const publishing = ref(false)

  async function loadApps() {
    apps.value = await workflowApi.listApps()
  }

  async function loadApp(id: string) {
    currentApp.value = await workflowApi.getApp(id)
  }

  async function saveCanvas(id: string, canvas: Record<string, any>) {
    saving.value = true
    try {
      await workflowApi.updateApp(id, { canvas_json: canvas })
      if (currentApp.value && currentApp.value.id === id) {
        currentApp.value.canvas_json = canvas as any
      }
    } finally {
      saving.value = false
    }
  }

  async function publishApp(id: string) {
    publishing.value = true
    try {
      const result = await workflowApi.publish(id)
      if (currentApp.value && currentApp.value.id === id) {
        currentApp.value.published_json = result.published_json
        currentApp.value.published_version = result.version
        currentApp.value.status = 'published'
      }
      return result
    } finally {
      publishing.value = false
    }
  }

  async function loadTools() {
    tools.value = await workflowApi.listTools()
  }

  async function loadApprovals(params?: { status?: string; session_id?: string }) {
    approvals.value = await workflowApi.listApprovals(params)
  }

  async function approveTask(taskId: string) {
    const result = await workflowApi.approve(taskId)
    const idx = approvals.value.findIndex(a => a.id === taskId)
    if (idx >= 0) approvals.value[idx] = result
    return result
  }

  async function rejectTask(taskId: string) {
    const result = await workflowApi.reject(taskId)
    const idx = approvals.value.findIndex(a => a.id === taskId)
    if (idx >= 0) approvals.value[idx] = result
    return result
  }

  return {
    apps, currentApp, tools, approvals, saving, publishing,
    loadApps, loadApp, saveCanvas, publishApp,
    loadTools, loadApprovals, approveTask, rejectTask,
  }
})
