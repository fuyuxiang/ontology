import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { workflowApi, type WorkflowBrief, type WorkflowFull } from '../api/harness'

export const useHarnessStore = defineStore('harness', () => {
  const workflows = ref<WorkflowBrief[]>([])
  const current = ref<WorkflowFull | null>(null)
  const loading = ref(false)
  const executing = ref(false)
  const executionLog = ref<Array<{ event: string; data: any; ts: number }>>([])
  const selectedNodeId = ref<string | null>(null)

  const isDirty = ref(false)

  const statusLabel = computed(() => {
    if (!current.value) return ''
    return { draft: '草稿', published: '已发布', disabled: '已停用' }[current.value.status] ?? current.value.status
  })

  async function loadList() {
    loading.value = true
    try {
      workflows.value = await workflowApi.list()
    } finally {
      loading.value = false
    }
  }

  async function loadWorkflow(id: string) {
    loading.value = true
    try {
      current.value = await workflowApi.get(id)
      isDirty.value = false
      selectedNodeId.value = null
    } finally {
      loading.value = false
    }
  }

  async function createWorkflow(name: string, description = '', namespace = '') {
    const w = await workflowApi.create({ name, description, namespace })
    workflows.value.unshift(w)
    current.value = w
    isDirty.value = false
    return w
  }

  async function saveCanvas(nodes: any[], edges: any[]) {
    if (!current.value) return
    const updated = await workflowApi.update(current.value.id, {
      nodes_json: nodes,
      edges_json: edges,
      name: current.value.name,
      description: current.value.description,
    })
    current.value = updated
    isDirty.value = false
    const idx = workflows.value.findIndex(w => w.id === updated.id)
    if (idx >= 0) workflows.value[idx] = { ...workflows.value[idx], node_count: nodes.length }
  }

  async function publishWorkflow() {
    if (!current.value) return
    await workflowApi.publish(current.value.id)
    current.value.status = 'published'
    const idx = workflows.value.findIndex(w => w.id === current.value!.id)
    if (idx >= 0) workflows.value[idx].status = 'published'
  }

  async function deleteWorkflow(id: string) {
    await workflowApi.delete(id)
    workflows.value = workflows.value.filter(w => w.id !== id)
    if (current.value?.id === id) current.value = null
  }

  function startExecution(wid: string) {
    executing.value = true
    executionLog.value = []
    const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'
    const es = new EventSource(`${baseUrl}/workflows/${wid}/execute`, )

    // EventSource doesn't support POST, use fetch SSE instead
    es.close()

    // Use fetch for SSE POST
    const ctrl = new AbortController()
    fetch(`${baseUrl}/workflows/${wid}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input_params: {} }),
      signal: ctrl.signal,
    }).then(async res => {
      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const lines = buf.split('\n')
        buf = lines.pop() ?? ''
        let event = ''
        for (const line of lines) {
          if (line.startsWith('event:')) event = line.slice(6).trim()
          else if (line.startsWith('data:')) {
            try {
              const data = JSON.parse(line.slice(5).trim())
              executionLog.value.push({ event, data, ts: Date.now() })
              if (event === 'workflow_done') executing.value = false
            } catch {}
          }
        }
      }
      executing.value = false
    }).catch(() => { executing.value = false })

    return ctrl
  }

  function markDirty() { isDirty.value = true }
  function selectNode(id: string | null) { selectedNodeId.value = id }

  return {
    workflows, current, loading, executing, executionLog,
    selectedNodeId, isDirty, statusLabel,
    loadList, loadWorkflow, createWorkflow, saveCanvas,
    publishWorkflow, deleteWorkflow, startExecution,
    markDirty, selectNode,
  }
})
