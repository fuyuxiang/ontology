import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useHarnessStore = defineStore('harness', () => {
  const workflows = ref<any[]>([])
  const current = ref<any | null>(null)
  const loading = ref(false)
  const executing = ref(false)
  const executionLog = ref<Array<{ event: string; data: any; ts: number }>>([])
  const selectedNodeId = ref<string | null>(null)
  const isDirty = ref(false)

  const statusLabel = computed(() => {
    if (!current.value) return ''
    return { draft: '草稿', published: '已发布', disabled: '已停用' }[current.value.status as string] ?? current.value.status
  })

  async function loadList() { workflows.value = [] }
  async function loadWorkflow(_id: string) { current.value = null }
  async function createWorkflow(name: string, description = '', _namespace = '') {
    const w = { id: crypto.randomUUID(), name, description, status: 'draft', nodes_json: [], edges_json: [] }
    workflows.value.unshift(w)
    current.value = w
    isDirty.value = false
    return w
  }
  async function saveCanvas(_nodes: any[], _edges: any[]) { isDirty.value = false }
  async function publishWorkflow() { if (current.value) current.value.status = 'published' }
  async function deleteWorkflow(id: string) {
    workflows.value = workflows.value.filter(w => w.id !== id)
    if (current.value?.id === id) current.value = null
  }
  function startExecution(_wid: string) { return new AbortController() }
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
