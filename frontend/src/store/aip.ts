import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { SCENE_LIST, EXEC_HISTORY, type SceneMeta, type TriggerConfig, type ExecHistory } from '../views/aip/aipData'

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
type ScenePayload = { nodes: AipNode[]; edges: AipEdge[] }

const STATUS_LABEL: Record<string, string> = { idle: '空闲', running: '运行中', success: '成功', error: '失败', waiting: '等待' }

export const useAipStore = defineStore('aip', () => {
  const scenes = ref<SceneMeta[]>([...SCENE_LIST])
  const sceneData = ref<Record<string, ScenePayload>>({})
  const currentSceneId = ref<string>('refund_attribution')
  const viewMode = ref<'workflow' | 'skills' | 'agents'>('workflow')
  const selectedNodeId = ref<string | null>(null)
  const nodeStatuses = ref<Record<string, 'idle' | 'running' | 'success' | 'error' | 'waiting'>>({})
  const executing = ref(false)
  const progress = ref(0)
  const logs = ref<Array<{ time: string; level: 'info' | 'warn' | 'error' | 'success'; message: string; nodeId?: string }>>([])
  const reasoning = ref<Array<{ nodeId: string; nodeName: string; consumed: string[]; rules: string[]; models: string[]; writeback: string[]; output: string }>>([])
  const bottomDrawerOpen = ref(false)
  const bottomDrawerHeight = ref(280)
  const bottomTab = ref<'logs' | 'reasoning'>('logs')
  const ioTab = ref<'input' | 'output'>('output')
  const ioView = ref<'table' | 'json' | 'schema'>('table')
  const sceneDrawerOpen = ref(false)
  const sceneDrawerTab = ref<'basic' | 'trigger' | 'history'>('basic')
  const isDirty = ref(false)
  const dataLoaded = ref(false)

  const currentScene = computed(() => scenes.value.find(s => s.id === currentSceneId.value))
  const currentNodes = computed(() => sceneData.value[currentSceneId.value]?.nodes ?? [])
  const currentEdges = computed(() => sceneData.value[currentSceneId.value]?.edges ?? [])
  const selectedNode = computed(() => currentNodes.value.find(n => n.id === selectedNodeId.value))
  const currentHistory = computed(() => EXEC_HISTORY[currentSceneId.value] ?? [])
  const totalNodes = computed(() => currentNodes.value.filter(n => !['skillNode', 'memoryNode', 'toolNode', 'llmAgent'].includes(n.type)).length)
  const totalEdges = computed(() => currentEdges.value.filter(e => !e.id.includes('_es')).length)

  async function loadScenes() {
    if (dataLoaded.value) return
    try {
      const res = await fetch('/aip_scenes.json')
      const json = await res.json() as Record<string, ScenePayload>
      sceneData.value = json
      dataLoaded.value = true
    } catch (e) {
      console.warn('[aip] 加载场景数据失败', e)
    }
  }

  function switchScene(id: string) {
    currentSceneId.value = id
    selectedNodeId.value = null
    nodeStatuses.value = {}
    progress.value = 0
  }

  function selectNode(id: string | null) { selectedNodeId.value = id }
  function updateNodeData(id: string, patch: Record<string, any>) {
    const node = sceneData.value[currentSceneId.value]?.nodes.find(n => n.id === id)
    if (!node) return
    node.data = { ...node.data, ...patch }
    isDirty.value = true
  }
  function updateNodes(next: AipNode[]) { if (sceneData.value[currentSceneId.value]) sceneData.value[currentSceneId.value].nodes = next }
  function updateEdges(next: AipEdge[]) { if (sceneData.value[currentSceneId.value]) sceneData.value[currentSceneId.value].edges = next }
  function addNode(node: AipNode) {
    sceneData.value[currentSceneId.value]?.nodes.push(node)
    isDirty.value = true
  }
  function deleteNode(id: string) {
    const data = sceneData.value[currentSceneId.value]
    if (!data) return
    data.nodes = data.nodes.filter(n => n.id !== id)
    data.edges = data.edges.filter(e => e.source !== id && e.target !== id)
    if (selectedNodeId.value === id) selectedNodeId.value = null
    isDirty.value = true
  }

  function pushLog(level: 'info' | 'warn' | 'error' | 'success', message: string, nodeId?: string) {
    const time = new Date().toLocaleTimeString('zh-CN', { hour12: false })
    logs.value.push({ time, level, message, nodeId })
    if (logs.value.length > 500) logs.value.shift()
  }

  function clearLogs() { logs.value = []; reasoning.value = [] }

  async function executeScene() {
    if (executing.value) return
    if (!currentScene.value) return
    executing.value = true
    progress.value = 0
    nodeStatuses.value = {}
    bottomDrawerOpen.value = true
    bottomTab.value = 'logs'
    pushLog('info', `[执行] 场景 「${currentScene.value.name}」 开始执行`)

    const main = currentNodes.value.filter(n => !['skillNode', 'memoryNode', 'toolNode', 'llmAgent'].includes(n.type))
    const total = main.length || 1

    for (let i = 0; i < main.length; i++) {
      const n = main[i]
      nodeStatuses.value[n.id] = 'running'
      pushLog('info', `▶ ${n.data.label || n.id} 开始执行`, n.id)
      await new Promise(r => setTimeout(r, 600 + Math.random() * 400))

      const ok = Math.random() > 0.05
      nodeStatuses.value[n.id] = ok ? 'success' : 'error'
      pushLog(ok ? 'success' : 'error', `${ok ? '✔' : '✘'} ${n.data.label || n.id} ${ok ? '执行成功' : '执行失败'}`, n.id)
      reasoning.value.push({
        nodeId: n.id,
        nodeName: n.data.label || n.id,
        consumed: (n.data.objectTypes || (n.data.objectType ? [n.data.objectType] : [])).slice(0, 4),
        rules: (n.data.rules || []).slice(0, 3),
        models: [n.data.model, n.data.mlModelRef].filter(Boolean),
        writeback: n.data.targetObjectType ? [n.data.targetObjectType] : [],
        output: ok ? `${n.data.label || n.id} 输出 ${Math.floor(80 + Math.random() * 200)} 条记录` : '执行失败 · 已记录到日志',
      })
      progress.value = Math.round(((i + 1) / total) * 100)
      if (!ok) break
    }

    executing.value = false
    pushLog('success', `[执行] 场景执行结束（${progress.value}%）`)
  }

  function stopScene() {
    if (!executing.value) return
    executing.value = false
    pushLog('warn', '[执行] 用户主动停止')
  }

  function saveScene() { isDirty.value = false; pushLog('success', '[保存] 当前场景已保存') }
  function publishScene() { if (currentScene.value) currentScene.value.status = 'published'; pushLog('success', '[发布] 场景已发布') }

  function setTrigger(t: TriggerConfig) {
    if (!currentScene.value) return
    currentScene.value.triggerConfig = t
    isDirty.value = true
  }

  function statusOf(id: string) { return nodeStatuses.value[id] || 'idle' }
  function statusLabel(id: string) { return STATUS_LABEL[statusOf(id)] }

  return {
    scenes, sceneData, currentSceneId, viewMode, selectedNodeId, nodeStatuses,
    executing, progress, logs, reasoning,
    bottomDrawerOpen, bottomDrawerHeight, bottomTab, ioTab, ioView,
    sceneDrawerOpen, sceneDrawerTab, isDirty, dataLoaded,
    currentScene, currentNodes, currentEdges, selectedNode, currentHistory, totalNodes, totalEdges,
    loadScenes, switchScene, selectNode, updateNodeData, updateNodes, updateEdges, addNode, deleteNode,
    pushLog, clearLogs, executeScene, stopScene, saveScene, publishScene, setTrigger,
    statusOf, statusLabel,
  }
})

export type { ExecHistory, SceneMeta, TriggerConfig }
