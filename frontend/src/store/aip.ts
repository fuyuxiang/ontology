import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  listScenes, getScene, createScene as apiCreateScene,
  updateScene as apiUpdateScene, deleteScene as apiDeleteScene,
  publishScene as apiPublishScene, validateScene as apiValidateScene,
  executeSceneStream, listExecutions, getExecution,
  listVersions as apiListVersions, rollbackScene as apiRollbackScene,
  testFireTrigger, getTrigger, upsertTrigger,
  type AipSceneBrief, type AipSceneFull, type AipTrigger,
  type AipExecutionBrief, type AipExecutionFull,
} from '../api/aip'

export interface AipNode {
  id: string
  type: string
  position: { x: number; y: number }
  data: Record<string, any>
}
export interface AipEdge {
  id: string
  source: string
  target: string
  sourceHandle?: string
  targetHandle?: string
  label?: string
  animated?: boolean
  type?: string
  style?: Record<string, any>
}

const STATUS_LABEL: Record<string, string> = {
  idle: '空闲', running: '运行中', success: '成功', error: '失败', waiting: '等待',
}

export const useAipStore = defineStore('aip', () => {
  // ── 数据 ───────────────────────────────────────────────
  const scenes = ref<AipSceneBrief[]>([])
  const sceneCache = ref<Record<string, AipSceneFull>>({})
  const currentSceneId = ref<string>('')
  const viewMode = ref<'workflow' | 'skills' | 'agents'>('workflow')
  const selectedNodeId = ref<string | null>(null)
  const nodeStatuses = ref<Record<string, 'idle' | 'running' | 'success' | 'error' | 'waiting'>>({})

  // ── 执行 ───────────────────────────────────────────────
  const executing = ref(false)
  const progress = ref(0)
  const currentExecutionId = ref<string>('')
  const logs = ref<Array<{ time: string; level: 'info' | 'warn' | 'error' | 'success'; message: string; nodeId?: string }>>([])
  const reasoning = ref<Array<{ nodeId: string; nodeName: string; status: string; durationMs: number; consumed: string[]; rules: string[]; models: string[]; writeback: string[]; output: string; raw?: any }>>([])
  const finalOutput = ref<Record<string, any>>({})
  let cancelStream: (() => void) | null = null

  // ── UI ─────────────────────────────────────────────────
  const bottomDrawerOpen = ref(false)
  const bottomDrawerHeight = ref(280)
  const bottomTab = ref<'logs' | 'reasoning' | 'history'>('logs')
  const ioTab = ref<'input' | 'output'>('output')
  const ioView = ref<'table' | 'json' | 'schema'>('json')
  const sceneDrawerOpen = ref(false)
  const sceneDrawerTab = ref<'basic' | 'trigger' | 'history'>('basic')

  const isDirty = ref(false)
  const dataLoaded = ref(false)
  let saveTimer: number | null = null

  // ── 触发器 ─────────────────────────────────────────────
  const trigger = ref<AipTrigger | null>(null)

  // ── 执行历史 ───────────────────────────────────────────
  const executions = ref<AipExecutionBrief[]>([])
  const currentExecution = ref<AipExecutionFull | null>(null)

  // ── computed ──────────────────────────────────────────
  const currentScene = computed(() => sceneCache.value[currentSceneId.value])
  const currentBrief = computed(() => scenes.value.find(s => s.id === currentSceneId.value))
  const currentNodes = computed(() => currentScene.value?.nodes_json ?? [])
  const currentEdges = computed(() => currentScene.value?.edges_json ?? [])
  const selectedNode = computed(() => currentNodes.value.find((n: any) => n.id === selectedNodeId.value))
  const totalNodes = computed(() => currentNodes.value.filter((n: any) => !['skillNode', 'memoryNode', 'toolNode'].includes(n.type)).length)
  const totalEdges = computed(() => currentEdges.value.filter((e: any) => !((e.id || '').includes('_es'))).length)

  // ── actions ───────────────────────────────────────────

  async function loadScenes(force = false) {
    if (dataLoaded.value && !force) return
    try {
      const list = await listScenes()
      scenes.value = list
      if (!currentSceneId.value && list.length) {
        await switchScene(list[0].id)
      }
      dataLoaded.value = true
    } catch (e) {
      pushLog('error', `加载场景列表失败: ${(e as Error).message}`)
    }
  }

  async function switchScene(id: string) {
    currentSceneId.value = id
    selectedNodeId.value = null
    nodeStatuses.value = {}
    progress.value = 0
    reasoning.value = []
    finalOutput.value = {}
    if (!sceneCache.value[id]) {
      try {
        sceneCache.value[id] = await getScene(id)
      } catch (e) {
        pushLog('error', `加载场景详情失败: ${(e as Error).message}`)
        return
      }
    }
    // 加载触发器
    try {
      trigger.value = await getTrigger(id)
    } catch {
      trigger.value = null
    }
  }

  function selectNode(id: string | null) { selectedNodeId.value = id }

  function _patchCacheNode(id: string, patch: Record<string, any>) {
    const sc = currentScene.value
    if (!sc) return
    const node = sc.nodes_json.find((n: any) => n.id === id)
    if (!node) return
    node.data = { ...node.data, ...patch }
  }
  function updateNodeData(id: string, patch: Record<string, any>) {
    _patchCacheNode(id, patch)
    markDirty()
  }
  function updateNodes(next: AipNode[]) {
    const sc = currentScene.value
    if (!sc) return
    sc.nodes_json = next as any
    markDirty()
  }
  function updateEdges(next: AipEdge[]) {
    const sc = currentScene.value
    if (!sc) return
    sc.edges_json = next as any
    markDirty()
  }
  function addNode(node: AipNode) {
    const sc = currentScene.value
    if (!sc) return
    sc.nodes_json = [...(sc.nodes_json || []), node] as any
    markDirty()
  }
  function deleteNode(id: string) {
    const sc = currentScene.value
    if (!sc) return
    sc.nodes_json = (sc.nodes_json || []).filter((n: any) => n.id !== id) as any
    sc.edges_json = (sc.edges_json || []).filter((e: any) => e.source !== id && e.target !== id) as any
    if (selectedNodeId.value === id) selectedNodeId.value = null
    markDirty()
  }
  function addEdge(edge: AipEdge) {
    const sc = currentScene.value
    if (!sc) return
    sc.edges_json = [...(sc.edges_json || []), edge] as any
    markDirty()
  }
  function removeEdge(id: string) {
    const sc = currentScene.value
    if (!sc) return
    sc.edges_json = (sc.edges_json || []).filter((e: any) => e.id !== id) as any
    markDirty()
  }

  function markDirty() {
    isDirty.value = true
    if (saveTimer) window.clearTimeout(saveTimer)
    saveTimer = window.setTimeout(() => { saveScene().catch(() => {}) }, 800)
  }

  async function createNewScene(name: string, group = '自定义') {
    const created = await apiCreateScene({ name, group_name: group, description: '' })
    sceneCache.value[created.id] = created
    scenes.value = [{
      id: created.id, name: created.name, description: created.description || '',
      group_name: created.group_name, status: created.status, version: created.version || 0,
      node_count: 0, edge_count: 0,
      ontology_bindings: created.ontology_bindings || [],
      datasource_bindings: created.datasource_bindings || [],
      stats: created.stats || {},
      trigger_config: created.trigger_config || {},
      created_at: created.created_at, updated_at: created.updated_at,
      created_by: created.created_by || '',
    }, ...scenes.value]
    await switchScene(created.id)
    return created
  }

  async function saveScene(): Promise<void> {
    const sc = currentScene.value
    if (!sc) return
    try {
      const saved = await apiUpdateScene(sc.id, {
        name: sc.name,
        description: sc.description,
        group_name: sc.group_name,
        nodes_json: sc.nodes_json,
        edges_json: sc.edges_json,
        ontology_bindings: sc.ontology_bindings,
        datasource_bindings: sc.datasource_bindings,
        input_schema: sc.input_schema,
        output_schema: sc.output_schema,
        stats_json: sc.stats,
      } as Partial<AipSceneFull> & { stats_json?: Record<string, any> })
      sceneCache.value[sc.id] = saved
      // 同步列表中的概要
      const idx = scenes.value.findIndex(s => s.id === sc.id)
      if (idx !== -1) {
        scenes.value[idx] = {
          ...scenes.value[idx],
          name: saved.name, description: saved.description, group_name: saved.group_name,
          node_count: (saved.nodes_json || []).length,
          edge_count: (saved.edges_json || []).length,
          updated_at: saved.updated_at, status: saved.status, version: saved.version,
        }
      }
      isDirty.value = false
    } catch (e) {
      pushLog('error', `保存失败: ${(e as Error).message}`)
    }
  }

  async function deleteCurrentScene() {
    const id = currentSceneId.value
    if (!id) return
    if (!window.confirm('确定删除当前场景？')) return
    try {
      await apiDeleteScene(id)
      delete sceneCache.value[id]
      scenes.value = scenes.value.filter(s => s.id !== id)
      currentSceneId.value = ''
      if (scenes.value.length) await switchScene(scenes.value[0].id)
    } catch (e) {
      pushLog('error', `删除失败: ${(e as Error).message}`)
    }
  }

  async function publishScene() {
    const id = currentSceneId.value
    if (!id) return
    try {
      const v = await apiValidateScene(id)
      if (!v.ok) {
        pushLog('error', `校验未通过：${v.errors.join('；')}`)
        return
      }
      const r = await apiPublishScene(id)
      if (currentScene.value) {
        currentScene.value.status = 'published' as any
        currentScene.value.version = r.version
        currentScene.value.published_version_id = r.version_id
      }
      const idx = scenes.value.findIndex(s => s.id === id)
      if (idx !== -1) {
        scenes.value[idx].status = 'published'
        scenes.value[idx].version = r.version
      }
      pushLog('success', `已发布 v${r.version}`)
    } catch (e) {
      pushLog('error', `发布失败: ${(e as Error).message}`)
    }
  }

  async function executeScene(inputParams: Record<string, any> = {}) {
    if (executing.value) return
    if (!currentSceneId.value) return
    if (isDirty.value) await saveScene()
    executing.value = true
    progress.value = 0
    nodeStatuses.value = {}
    reasoning.value = []
    finalOutput.value = {}
    bottomDrawerOpen.value = true
    bottomTab.value = 'logs'
    pushLog('info', `[执行] 场景 「${currentBrief.value?.name || ''}」 开始执行`)

    const totalMain = (currentScene.value?.nodes_json || [])
      .filter((n: any) => !['skillNode', 'memoryNode', 'toolNode'].includes(n.type)).length || 1
    let doneCount = 0

    cancelStream = executeSceneStream(currentSceneId.value, inputParams, (ev) => {
      switch (ev.type) {
        case 'execution_started':
          currentExecutionId.value = ev.execution_id
          pushLog('info', `Execution: ${ev.execution_id}`)
          break
        case 'scene_started':
          pushLog('info', `节点总数: ${ev.total_nodes}`)
          break
        case 'node_started':
          nodeStatuses.value[ev.node_id] = 'running'
          pushLog('info', `▶ ${ev.label} 开始执行`, ev.node_id)
          break
        case 'node_finished':
          nodeStatuses.value[ev.node_id] = 'success'
          doneCount += 1
          progress.value = Math.min(100, Math.round((doneCount / totalMain) * 100))
          pushLog('success', `✔ ${ev.label} (${ev.duration_ms}ms) — ${ev.summary || ''}`, ev.node_id)
          appendReasoning(ev.node_id, ev.label, 'success', ev.duration_ms, ev.output, ev.summary)
          break
        case 'node_failed':
          nodeStatuses.value[ev.node_id] = 'error'
          doneCount += 1
          progress.value = Math.min(100, Math.round((doneCount / totalMain) * 100))
          pushLog('error', `✘ ${ev.label} 失败：${ev.error}`, ev.node_id)
          appendReasoning(ev.node_id, ev.label, 'failed', ev.duration_ms || 0, { error: ev.error }, ev.error || '失败')
          break
        case 'scene_finished':
          finalOutput.value = ev.final_output || {}
          break
        case 'scene_failed':
          pushLog('error', `场景执行失败: ${ev.error}`)
          break
        case 'execution_finished':
          progress.value = 100
          pushLog(ev.status === 'success' ? 'success' : 'error',
            `[执行] 结束 (${ev.duration_ms}ms, status=${ev.status})`)
          break
        case 'sse_done':
          executing.value = false
          cancelStream = null
          break
      }
    })
  }

  function stopScene() {
    if (!executing.value) return
    if (cancelStream) cancelStream()
    cancelStream = null
    executing.value = false
    pushLog('warn', '[执行] 用户主动停止')
  }

  function appendReasoning(
    nodeId: string, name: string, status: string,
    durationMs: number, output: any, summary: string,
  ) {
    reasoning.value.push({
      nodeId, nodeName: name, status, durationMs,
      consumed: extractStrings(output, ['input', 'objectTypes', 'objectType', 'consumed']),
      rules: extractStrings(output, ['rules', 'rule_name']),
      models: extractStrings(output, ['model', 'mlModelRef']),
      writeback: extractStrings(output, ['target', 'targetObjectType']),
      output: summary || (typeof output === 'string' ? output : JSON.stringify(output).slice(0, 200)),
      raw: output,
    })
  }

  function extractStrings(obj: any, keys: string[]): string[] {
    if (!obj || typeof obj !== 'object') return []
    const out: string[] = []
    for (const k of keys) {
      const v = obj[k]
      if (typeof v === 'string') out.push(v)
      else if (Array.isArray(v)) v.forEach((x) => typeof x === 'string' && out.push(x))
    }
    return out.slice(0, 4)
  }

  function pushLog(level: 'info' | 'warn' | 'error' | 'success', message: string, nodeId?: string) {
    const time = new Date().toLocaleTimeString('zh-CN', { hour12: false })
    logs.value.push({ time, level, message, nodeId })
    if (logs.value.length > 500) logs.value.shift()
  }
  function clearLogs() { logs.value = []; reasoning.value = [] }

  async function loadHistory() {
    if (!currentSceneId.value) return
    try {
      executions.value = await listExecutions({ scene_id: currentSceneId.value, limit: 50 })
    } catch {
      executions.value = []
    }
  }

  async function viewExecution(eid: string) {
    try {
      currentExecution.value = await getExecution(eid)
    } catch {
      currentExecution.value = null
    }
  }

  async function saveTrigger(payload: Partial<AipTrigger>) {
    if (!currentSceneId.value) return
    const r = await upsertTrigger(currentSceneId.value, payload as any)
    trigger.value = { ...(trigger.value || ({} as AipTrigger)), ...r.trigger }
  }

  async function fireTriggerOnce() {
    if (!currentSceneId.value) return
    await testFireTrigger(currentSceneId.value)
    pushLog('success', '已下发触发请求（后台执行）')
  }

  async function listSceneVersions() { return apiListVersions(currentSceneId.value) }
  async function rollback(versionId: string) {
    const r = await apiRollbackScene(currentSceneId.value, versionId)
    sceneCache.value[r.id] = r
    return r
  }

  function statusOf(id: string) { return nodeStatuses.value[id] || 'idle' }
  function statusLabel(id: string) { return STATUS_LABEL[statusOf(id)] }

  return {
    // state
    scenes, sceneCache, currentSceneId, viewMode, selectedNodeId, nodeStatuses,
    executing, progress, currentExecutionId, logs, reasoning, finalOutput,
    bottomDrawerOpen, bottomDrawerHeight, bottomTab, ioTab, ioView,
    sceneDrawerOpen, sceneDrawerTab, isDirty, dataLoaded,
    trigger, executions, currentExecution,
    // computed
    currentScene, currentBrief, currentNodes, currentEdges, selectedNode, totalNodes, totalEdges,
    // actions
    loadScenes, switchScene, selectNode,
    updateNodeData, updateNodes, updateEdges, addNode, deleteNode, addEdge, removeEdge,
    markDirty, createNewScene, saveScene, deleteCurrentScene, publishScene,
    executeScene, stopScene,
    pushLog, clearLogs,
    loadHistory, viewExecution,
    saveTrigger, fireTriggerOnce, listSceneVersions, rollback,
    statusOf, statusLabel,
  }
})

export type { AipSceneBrief, AipSceneFull, AipTrigger, AipExecutionBrief, AipExecutionFull }
