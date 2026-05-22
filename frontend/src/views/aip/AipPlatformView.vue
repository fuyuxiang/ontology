<template>
  <div class="aip-page">
    <!-- 顶部 Header -->
    <div class="aip-header">
      <div class="aip-header__left">
        <span class="aip-header__logo">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 1l1.5 4.5H14l-3.7 2.7L11.8 13 8 10.3 4.2 13l1.5-4.8L2 5.5h4.5L8 1z" fill="#2E5BFF"/></svg>
        </span>
        <span class="aip-header__title">AIP 场景平台</span>
        <template v-if="store.currentBrief">
          <span class="aip-header__divider">|</span>
          <span class="aip-header__scene">{{ store.currentBrief.name }}</span>
          <span class="aip-header__status-tag" :class="`aip-header__status-tag--${store.currentBrief.status}`">
            {{ store.currentBrief.status === 'published' ? '已发布' : '草稿' }}
          </span>
          <span class="aip-header__version" v-if="store.currentBrief.version">v{{ store.currentBrief.version }}</span>
          <span v-if="store.isDirty" class="aip-header__dirty">●未保存</span>
          <span class="aip-header__trigger" @click="openSceneTrigger">
            <span v-html="triggerIcon(store.currentBrief)"></span>
            {{ triggerText(store.currentBrief) }}
          </span>
        </template>
      </div>

      <div class="aip-header__right">
        <button class="aip-btn aip-btn--ghost" @click="onCreateNew">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          新建场景
        </button>
        <button class="aip-btn aip-btn--ghost" @click="store.saveScene()" :disabled="!store.isDirty">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M3 2h8l3 3v9H3V2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M6 2v4h5V2M5 9h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          保存
        </button>
        <button class="aip-btn aip-btn--ghost" @click="store.publishScene()">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 2l6 4v4l-6 4-6-4V6l6-4z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
          发布
        </button>
        <button class="aip-btn aip-btn--primary" @click="onExecute">
          <svg v-if="!store.executing" width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M5 3l9 5-9 5V3z" fill="currentColor"/></svg>
          <svg v-else width="13" height="13" viewBox="0 0 16 16" fill="none"><rect x="4" y="4" width="8" height="8" fill="currentColor"/></svg>
          {{ store.executing ? '停止' : '执行' }}
        </button>
        <button class="aip-btn aip-btn--ghost aip-btn--icon" @click="store.bottomDrawerOpen = !store.bottomDrawerOpen" title="日志 / 推理 / 历史">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5"/><path d="M8 4v4l2.5 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          <span v-if="store.logs.length" class="aip-btn__dot"></span>
        </button>

        <span class="aip-header__divider">|</span>
        <span class="aip-header__count">{{ store.totalNodes }} 节点 · {{ store.totalEdges }} 连线</span>

        <div v-if="store.executing" class="aip-progress">
          <div class="aip-progress__bar"><div class="aip-progress__fill" :style="{ width: store.progress + '%' }"></div></div>
          <span class="aip-progress__text">{{ store.progress }}%</span>
        </div>
      </div>
    </div>

    <!-- 主体：画布 -->
    <div class="aip-body">
      <SceneSidebar @open-import="onCreateNew" />

      <div class="aip-canvas-wrap" ref="canvasWrapEl">
        <button class="aip-canvas-add" :class="{ active: showAddNode }" @click="showAddNode = !showAddNode" title="添加节点">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </button>

        <div v-if="!store.dataLoaded || !store.currentScene" class="aip-canvas-loading">
          {{ store.dataLoaded ? '请先选择或创建场景' : '正在加载场景数据...' }}
        </div>
        <VueFlow v-else
          v-model:nodes="flowNodes"
          v-model:edges="flowEdges"
          :node-types="nodeTypes"
          :default-edge-options="defaultEdgeOptions"
          :snap-to-grid="true"
          :snap-grid="[16, 16]"
          fit-view-on-init
          :default-viewport="{ x: 100, y: 100, zoom: 0.55 }"
          @node-click="onNodeClick"
          @pane-click="onPaneClick"
          @nodes-change="onNodesChange"
          @edges-change="onEdgesChange"
          @connect="onConnect"
          @dragover="onCanvasDragOver"
          @drop="onCanvasDrop"
          class="aip-flow">
          <Background variant="dots" pattern-color="#cbd5e1" :gap="16" :size="1" />
          <Controls />
          <MiniMap :node-color="miniMapColor" mask-color="rgba(15,23,42,0.5)" />
        </VueFlow>

        <AddNodeDrawer :open="showAddNode" @close="showAddNode = false" @pick="onAddNodePick" />
      </div>

      <transition name="aip-drawer">
        <div v-if="store.selectedNodeId" class="aip-right-drawer">
          <PropertyPanel />
        </div>
      </transition>

      <BottomDrawer v-if="store.bottomDrawerOpen" />
      <SceneConfigDrawer />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, markRaw } from 'vue'
import { VueFlow, MarkerType, applyNodeChanges, applyEdgeChanges, addEdge as flowAddEdge } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

import { useAipStore } from '../../store/aip'
import { NODE_TYPES } from './aipData'
import type { AipSceneBrief } from '../../api/aip'
import AipNode from './nodes/AipNode.vue'
import SceneSidebar from './panels/SceneSidebar.vue'
import PropertyPanel from './panels/PropertyPanel.vue'
import BottomDrawer from './panels/BottomDrawer.vue'
import SceneConfigDrawer from './panels/SceneConfigDrawer.vue'
import AddNodeDrawer from './panels/AddNodeDrawer.vue'

const store = useAipStore()
const showAddNode = ref(false)
const canvasWrapEl = ref<HTMLElement | null>(null)

const nodeTypes = NODE_TYPES.reduce((acc, t) => { acc[t.type] = markRaw(AipNode); return acc }, {} as Record<string, any>)

const defaultEdgeOptions = {
  type: 'smoothstep',
  markerEnd: MarkerType.ArrowClosed,
  style: { stroke: '#4a90d9', strokeWidth: 1.5 },
}

const flowNodes = ref<any[]>([])
const flowEdges = ref<any[]>([])

let suppressSync = false

function syncFromStore() {
  suppressSync = true
  flowNodes.value = (store.currentNodes as any[]).map(n => ({
    id: n.id,
    type: n.type,
    position: n.position,
    data: { ...n.data, status: store.statusOf(n.id) },
  }))
  flowEdges.value = (store.currentEdges as any[]).map(e => {
    const isSubEdge = (e.id || '').includes('_es') || (e.sourceHandle && e.sourceHandle.startsWith('sub-'))
    const subColor = e.sourceHandle === 'sub-skill' ? '#10b981'
      : e.sourceHandle === 'sub-memory' ? '#7c3aed'
      : e.sourceHandle === 'sub-tool' ? '#0ea5e9'
      : e.sourceHandle === 'sub-llm' ? '#f59e0b'
      : '#4a90d9'
    return {
      id: e.id,
      source: e.source,
      target: e.target,
      sourceHandle: e.sourceHandle,
      targetHandle: e.targetHandle,
      label: e.label,
      animated: !!e.animated,
      type: 'smoothstep',
      style: {
        stroke: e.style?.stroke || subColor,
        strokeWidth: 1.5,
        ...(isSubEdge ? { strokeDasharray: '4 2' } : {}),
      },
    }
  })
  setTimeout(() => { suppressSync = false }, 0)
}

watch(() => [store.currentSceneId, store.dataLoaded], syncFromStore)
watch(() => store.nodeStatuses, syncFromStore, { deep: true })
watch(() => store.currentScene, () => syncFromStore(), { deep: false })

onMounted(async () => {
  await store.loadScenes()
  syncFromStore()
})

function onNodeClick({ node }: any) { store.selectNode(node.id) }
function onPaneClick() { store.selectNode(null) }

function miniMapColor(node: any) {
  return NODE_TYPES.find(t => t.type === node.type)?.color || '#94a3b8'
}

function onNodesChange(changes: any[]) {
  if (suppressSync) return
  // 应用 VueFlow 内部变更并写回 store
  flowNodes.value = applyNodeChanges(changes, flowNodes.value)
  let needSave = false
  for (const c of changes) {
    if (c.type === 'position' && !c.dragging) needSave = true
    if (c.type === 'remove') {
      store.deleteNode(c.id)
      needSave = false
    }
  }
  if (needSave) {
    // 把最终位置写回 store
    const map: Record<string, { x: number; y: number }> = {}
    for (const n of flowNodes.value) map[n.id] = n.position
    const sc = store.currentScene
    if (sc) {
      const next = sc.nodes_json.map((n: any) =>
        map[n.id] ? { ...n, position: map[n.id] } : n,
      )
      store.updateNodes(next)
    }
  }
}

function onEdgesChange(changes: any[]) {
  if (suppressSync) return
  flowEdges.value = applyEdgeChanges(changes, flowEdges.value)
  for (const c of changes) {
    if (c.type === 'remove') store.removeEdge(c.id)
  }
}

function onConnect(conn: any) {
  if (suppressSync) return
  const newEdges = flowAddEdge(conn, flowEdges.value)
  // 找到新增的那条
  const before = new Set(flowEdges.value.map((e: any) => e.id))
  flowEdges.value = newEdges
  for (const e of newEdges) {
    if (!before.has(e.id)) {
      store.addEdge({
        id: e.id,
        source: e.source,
        target: e.target,
        sourceHandle: e.sourceHandle,
        targetHandle: e.targetHandle,
      } as any)
    }
  }
}

function onAddNodePick() { syncFromStore() }

function onCanvasDragOver(e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
}

function onCanvasDrop(e: DragEvent) {
  e.preventDefault()
  const type = e.dataTransfer?.getData('application/aip-node')
  const label = e.dataTransfer?.getData('application/aip-label')
  if (!type) return
  const meta = NODE_TYPES.find(t => t.type === type)
  const wrap = canvasWrapEl.value
  if (!wrap) return
  const rect = wrap.getBoundingClientRect()
  const position = { x: e.clientX - rect.left - 100, y: e.clientY - rect.top - 30 }
  const id = `${type}_${Date.now()}`
  store.addNode({
    id, type, position,
    data: { label: label || meta?.label || type, status: 'idle' },
  })
  showAddNode.value = false
  syncFromStore()
}

async function onCreateNew() {
  const name = window.prompt('新场景名称：', '新建场景')
  if (!name) return
  await store.createNewScene(name, '自定义')
}

function onExecute() {
  if (store.executing) store.stopScene()
  else store.executeScene()
}

function openSceneTrigger() {
  store.sceneDrawerOpen = true
  store.sceneDrawerTab = 'trigger'
}

function triggerText(s: AipSceneBrief | undefined) {
  if (!s) return ''
  const t: any = s.trigger_config || {}
  if (!t.enabled) return '触发已暂停'
  if (t.type === 'schedule' && t.schedule) return `定时 · ${pad(t.schedule.hour || 0)}:${pad(t.schedule.minute || 0)}`
  if (t.type === 'event') return '事件触发'
  if (t.type === 'webhook') return 'Webhook'
  if (t.type === 'manual') return '手动触发'
  return '未配置触发'
}
function triggerIcon(s: AipSceneBrief | undefined) {
  const t: any = (s && s.trigger_config) || {}
  if (t.type === 'schedule') return '<svg width="12" height="12" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.3"/><path d="M8 4v4l3 2" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>'
  return '<svg width="12" height="12"></svg>'
}
function pad(n: number) { return String(n).padStart(2, '0') }
</script>

<style scoped>
.aip-page { display: flex; flex-direction: column; height: 100%; background: var(--ao-bg-primary, #f5f7fb); overflow: hidden; }

/* ====== Header ====== */
.aip-header {
  height: 48px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 16px;
  flex-shrink: 0;
  gap: 12px;
}
.aip-header__left, .aip-header__right { display: flex; align-items: center; gap: 8px; min-width: 0; }
.aip-header__right { gap: 6px; flex-shrink: 0; }
.aip-header__logo { display: flex; }
.aip-header__title { font-weight: 700; font-size: 14px; color: #1e293b; }
.aip-header__divider { color: #cbd5e1; }
.aip-header__scene { font-weight: 600; color: #1e293b; max-width: 280px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.aip-header__status-tag { font-size: 10px; padding: 1px 8px; border-radius: 999px; flex-shrink: 0; }
.aip-header__status-tag--published { background: #ecfdf5; color: #059669; }
.aip-header__status-tag--draft { background: #fffbeb; color: #b45309; }
.aip-header__version { font-size: 10px; color: #64748b; padding: 1px 6px; background: #f1f5f9; border-radius: 4px; }
.aip-header__dirty { font-size: 11px; color: #f59e0b; }
.aip-header__trigger {
  font-size: 11px; color: #64748b;
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 8px; border-radius: 4px; cursor: pointer;
}
.aip-header__trigger:hover { background: #f1f5f9; color: #2E5BFF; }
.aip-header__count { font-size: 11px; color: #64748b; }

.aip-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 10px;
  border: 1px solid transparent; border-radius: 4px;
  font-size: 12px; font-weight: 500; cursor: pointer;
  background: #fff; color: #475569;
  position: relative;
  transition: all .15s;
}
.aip-btn--ghost { border-color: #e2e8f0; }
.aip-btn--ghost:hover:not(:disabled) { border-color: #2E5BFF; color: #2E5BFF; background: rgba(46,91,255,.04); }
.aip-btn--primary { background: #2E5BFF; color: #fff; border-color: #2E5BFF; }
.aip-btn--primary:hover { background: #1d4ed8; border-color: #1d4ed8; }
.aip-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.aip-btn--icon { padding: 4px 8px; }
.aip-btn__dot { position: absolute; top: 2px; right: 2px; width: 6px; height: 6px; border-radius: 50%; background: #ef4444; }

.aip-progress { display: flex; align-items: center; gap: 6px; }
.aip-progress__bar { width: 80px; height: 4px; background: #e2e8f0; border-radius: 2px; overflow: hidden; }
.aip-progress__fill { height: 100%; background: linear-gradient(90deg, #2E5BFF, #7C3AED); transition: width .3s; }
.aip-progress__text { font-size: 10px; color: #64748b; min-width: 28px; }

/* ====== Body ====== */
.aip-body { flex: 1; display: flex; min-height: 0; position: relative; }
.aip-canvas-wrap {
  flex: 1; position: relative; min-width: 0;
  background: radial-gradient(rgba(59,108,255,.04) 0%, rgba(59,108,255,.02) 30%, #f5f7fb 70% 100%);
}
.aip-canvas-add {
  position: absolute; top: 12px; right: 12px; z-index: 10;
  width: 40px; height: 40px; border-radius: 50%;
  border: none; background: #2E5BFF; color: #fff;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 12px rgba(46,91,255,.35);
  transition: transform .15s, background .15s;
}
.aip-canvas-add:hover { background: #1d4ed8; transform: scale(1.06); }
.aip-canvas-add.active { background: #1d4ed8; transform: rotate(45deg); }
.aip-flow { width: 100%; height: 100%; }
.aip-canvas-loading { padding: 80px; text-align: center; color: #94a3b8; font-size: 13px; }

.aip-right-drawer {
  width: 480px; flex-shrink: 0;
  background: #fff; border-left: 1px solid #e5e7eb;
  display: flex; flex-direction: column;
  overflow: hidden;
}

.aip-drawer-enter-active, .aip-drawer-leave-active { transition: width .2s, opacity .2s; }
.aip-drawer-enter-from, .aip-drawer-leave-to { width: 0; opacity: 0; }
</style>
