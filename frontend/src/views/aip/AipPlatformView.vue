<template>
  <div class="aip-page">
    <!-- 顶部 Header -->
    <div class="aip-header">
      <div class="aip-header__left">
        <span class="aip-header__logo">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 1l1.5 4.5H14l-3.7 2.7L11.8 13 8 10.3 4.2 13l1.5-4.8L2 5.5h4.5L8 1z" fill="#2E5BFF"/></svg>
        </span>
        <span class="aip-header__title">AIP 场景平台</span>
        <template v-if="store.currentScene">
          <span class="aip-header__divider">|</span>
          <span class="aip-header__scene">{{ store.currentScene.name }}</span>
          <span class="aip-header__status-tag" :class="`aip-header__status-tag--${store.currentScene.status}`">
            {{ store.currentScene.status === 'published' ? '已发布' : '草稿' }}
          </span>
          <span v-if="store.isDirty" class="aip-header__dirty">●未保存</span>
          <span class="aip-header__trigger" @click="openSceneTrigger">
            <span v-html="triggerIcon(store.currentScene)"></span>
            {{ triggerText(store.currentScene) }}
          </span>
        </template>
      </div>

      <div class="aip-header__right">
        <button class="aip-btn aip-btn--ghost" @click="showImport = true">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 2v8M5 7l3 3 3-3M2 13h12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          导入场景
        </button>
        <button class="aip-btn aip-btn--ghost" @click="store.saveScene()" :disabled="!store.isDirty">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M3 2h8l3 3v9H3V2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M6 2v4h5V2M5 9h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          保存
        </button>
        <button class="aip-btn aip-btn--ghost" @click="store.publishScene()">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 2l6 4v4l-6 4-6-4V6l6-4z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
          发布
        </button>
        <button class="aip-btn aip-btn--primary" @click="store.executing ? store.stopScene() : store.executeScene()">
          <svg v-if="!store.executing" width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M5 3l9 5-9 5V3z" fill="currentColor"/></svg>
          <svg v-else width="13" height="13" viewBox="0 0 16 16" fill="none"><rect x="4" y="4" width="8" height="8" fill="currentColor"/></svg>
          {{ store.executing ? '停止' : '执行' }}
        </button>
        <button class="aip-btn aip-btn--ghost aip-btn--icon" @click="store.bottomDrawerOpen = !store.bottomDrawerOpen" title="日志 / 推理">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5"/><path d="M8 4v4l2.5 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          <span v-if="store.logs.length" class="aip-btn__dot"></span>
        </button>

        <span class="aip-header__divider">|</span>

        <!-- 视图切换 Segmented -->
        <div class="aip-segmented">
          <button class="aip-seg" :class="{ active: store.viewMode === 'workflow' }" @click="store.viewMode = 'workflow'">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><circle cx="3" cy="8" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="13" cy="3" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="13" cy="13" r="2" stroke="currentColor" stroke-width="1.5"/><path d="M5 8l6-4M5 8l6 4" stroke="currentColor" stroke-width="1.3"/></svg>
            工作流
          </button>
          <button class="aip-seg" :class="{ active: store.viewMode === 'skills' }" @click="store.viewMode = 'skills'">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M9 1L3 9h4l-1 6 6-8H8l1-6z" fill="currentColor"/></svg>
            Skill 注册
          </button>
          <button class="aip-seg" :class="{ active: store.viewMode === 'agents' }" @click="store.viewMode = 'agents'">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="5" r="2.5" stroke="currentColor" stroke-width="1.5"/><path d="M3 14c0-2.76 2.24-5 5-5s5 2.24 5 5" stroke="currentColor" stroke-width="1.5"/></svg>
            Agent Studio
          </button>
        </div>

        <span class="aip-header__divider">|</span>
        <span class="aip-header__count">{{ store.totalNodes }} 节点 · {{ store.totalEdges }} 连线</span>

        <div v-if="store.executing" class="aip-progress">
          <div class="aip-progress__bar"><div class="aip-progress__fill" :style="{ width: store.progress + '%' }"></div></div>
          <span class="aip-progress__text">{{ store.progress }}%</span>
        </div>
      </div>
    </div>

    <!-- 主体 -->
    <div class="aip-body" v-if="store.viewMode === 'workflow'">
      <SceneSidebar @open-import="showImport = true" />

      <div class="aip-canvas-wrap">
        <button class="aip-canvas-add" @click="addNodeFromToolbox" title="添加节点">+</button>

        <div v-if="!store.dataLoaded" class="aip-canvas-loading">正在加载场景数据...</div>
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
          class="aip-flow">
          <Background variant="dots" pattern-color="#cbd5e1" :gap="16" :size="1" />
          <Controls />
          <MiniMap :node-color="miniMapColor" mask-color="rgba(15,23,42,0.5)" />
        </VueFlow>
      </div>

      <transition name="aip-drawer">
        <div v-if="store.selectedNodeId" class="aip-right-drawer">
          <PropertyPanel />
        </div>
      </transition>

      <BottomDrawer v-if="store.bottomDrawerOpen" />
      <SceneConfigDrawer />
    </div>

    <!-- Skill 注册视图 -->
    <div v-else-if="store.viewMode === 'skills'" class="aip-secondary">
      <div class="aip-secondary__head">
        <h2 class="aip-secondary__title">Skill 注册中心</h2>
        <p class="aip-secondary__sub">登记可被 Agent 节点调用的能力包；从场景画布的 Skill 子节点引用</p>
      </div>
      <div class="aip-skill-grid">
        <div v-for="s in SKILLS" :key="s.id" class="aip-skill-card">
          <div class="aip-skill-card__icon" :style="{ background: s.color }"><span v-html="s.iconSvg"></span></div>
          <div class="aip-skill-card__head">
            <span class="aip-skill-card__name">{{ s.name }}</span>
            <span class="aip-skill-card__tag">{{ s.tag }}</span>
          </div>
          <p class="aip-skill-card__desc">{{ s.description }}</p>
          <div class="aip-skill-card__meta">
            <span v-for="m in s.meta" :key="m" class="aip-tag aip-tag--blue">{{ m }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Agent Studio 视图 -->
    <div v-else class="aip-secondary">
      <div class="aip-secondary__head">
        <h2 class="aip-secondary__title">Agent Studio</h2>
        <p class="aip-secondary__sub">5 类 Agent 角色 · 主 Skill / 共享 Skill / Memory / Tools 配置</p>
      </div>
      <div class="aip-agent-grid">
        <div v-for="a in AGENTS" :key="a.id" class="aip-agent-card">
          <div class="aip-agent-card__head">
            <span class="aip-agent-card__icon" :style="{ background: a.color }">{{ a.idx }}</span>
            <div class="aip-agent-card__title-wrap">
              <span class="aip-agent-card__name">{{ a.name }}</span>
              <span class="aip-agent-card__role">{{ a.role }}</span>
            </div>
            <span class="aip-agent-card__primary" v-if="a.primary">⭐ 主 Skill</span>
          </div>
          <p class="aip-agent-card__desc">{{ a.description }}</p>
          <div class="aip-agent-card__cap">
            <div class="aip-agent-card__cap-row">
              <span class="aip-agent-card__cap-label">Skill</span>
              <span v-for="s in a.skills" :key="s" class="aip-tag aip-tag--green">{{ s }}</span>
            </div>
            <div class="aip-agent-card__cap-row">
              <span class="aip-agent-card__cap-label">Tool</span>
              <span v-for="t in a.tools" :key="t" class="aip-tag aip-tag--cyan">{{ t }}</span>
            </div>
            <div class="aip-agent-card__cap-row">
              <span class="aip-agent-card__cap-label">Memory</span>
              <span v-for="m in a.memories" :key="m" class="aip-tag aip-tag--purple">{{ m }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 导入场景对话框 -->
    <a-modal v-model:open="showImport" title="导入场景" @ok="onImport">
      <div class="aip-import">
        <div class="aip-import__hint">从 JSON 文件加载场景定义（节点 / 连线 / 触发配置）</div>
        <textarea class="aip-input aip-input--ta" v-model="importText" rows="12" placeholder="粘贴场景 JSON..."></textarea>
      </div>
    </a-modal>

    <!-- 添加节点对话框 -->
    <a-modal v-model:open="showAddNode" title="添加节点" @ok="confirmAddNode">
      <div class="aip-add-node">
        <div v-for="g in NODE_GROUPS" :key="g" class="aip-add-node__group">
          <div class="aip-add-node__group-label">{{ g }}</div>
          <div class="aip-add-node__items">
            <button v-for="t in NODE_TYPES.filter(t => t.group === g)" :key="t.type"
              class="aip-add-node__item" :class="{ active: addType === t.type }"
              :style="{ borderColor: addType === t.type ? t.color : '#e2e8f0', color: addType === t.type ? t.color : '#475569' }"
              @click="addType = t.type">
              {{ t.label }}
            </button>
          </div>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, markRaw, nextTick } from 'vue'
import { VueFlow, MarkerType, Position } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

import { useAipStore } from '../../store/aip'
import { NODE_TYPES, NODE_GROUPS, SCENE_LIST, type SceneMeta } from './aipData'
import AipNode from './nodes/AipNode.vue'
import SceneSidebar from './panels/SceneSidebar.vue'
import PropertyPanel from './panels/PropertyPanel.vue'
import BottomDrawer from './panels/BottomDrawer.vue'
import SceneConfigDrawer from './panels/SceneConfigDrawer.vue'

const store = useAipStore()
const showImport = ref(false)
const importText = ref('')
const showAddNode = ref(false)
const addType = ref<string>('ontologyQuery')

const nodeTypes = NODE_TYPES.reduce((acc, t) => { acc[t.type] = markRaw(AipNode); return acc }, {} as Record<string, any>)

const defaultEdgeOptions = {
  type: 'smoothstep',
  markerEnd: MarkerType.ArrowClosed,
  style: { stroke: '#4a90d9', strokeWidth: 1.5 },
}

const flowNodes = ref<any[]>([])
const flowEdges = ref<any[]>([])

function syncFromStore() {
  flowNodes.value = store.currentNodes.map(n => ({
    id: n.id,
    type: n.type,
    position: n.position,
    data: { ...n.data, status: store.statusOf(n.id) },
  }))
  flowEdges.value = store.currentEdges.map(e => {
    const isSubEdge = e.id.includes('_es') || (e.sourceHandle && e.sourceHandle.startsWith('sub-'))
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
}

watch(() => [store.currentSceneId, store.dataLoaded, store.nodeStatuses], syncFromStore, { deep: true })

onMounted(async () => {
  await store.loadScenes()
  syncFromStore()
})

function onNodeClick({ node }: any) { store.selectNode(node.id) }
function onPaneClick() { store.selectNode(null) }

function miniMapColor(node: any) {
  return NODE_TYPES.find(t => t.type === node.type)?.color || '#94a3b8'
}

function addNodeFromToolbox() {
  showAddNode.value = true
}
function confirmAddNode() {
  const meta = NODE_TYPES.find(t => t.type === addType.value)
  if (!meta) return
  const id = `${addType.value}_${Date.now()}`
  store.addNode({
    id, type: addType.value,
    position: { x: 100 + Math.random() * 400, y: 100 + Math.random() * 200 },
    data: { label: meta.label },
  })
  showAddNode.value = false
  syncFromStore()
}

function onImport() {
  try {
    const obj = JSON.parse(importText.value)
    if (obj.id && obj.name) {
      const meta: SceneMeta = {
        id: obj.id, name: obj.name, group: obj.group || '自定义',
        status: obj.status || 'draft', description: obj.description || '',
        ontologyBindings: obj.ontologyBindings || [],
        stats: obj.stats || {},
        triggerConfig: obj.triggerConfig || { type: 'manual', enabled: false },
        createdAt: new Date().toISOString().slice(0, 10),
        updatedAt: new Date().toISOString().slice(0, 10),
      }
      if (!store.scenes.find(s => s.id === meta.id)) store.scenes.unshift(meta)
      store.sceneData[meta.id] = { nodes: obj.nodes || [], edges: obj.edges || [] }
      store.switchScene(meta.id)
      showImport.value = false
      importText.value = ''
    } else {
      alert('JSON 缺少必要字段：id / name')
    }
  } catch (e) {
    alert('JSON 解析失败：' + (e as Error).message)
  }
}

function openSceneTrigger() {
  store.sceneDrawerOpen = true
  store.sceneDrawerTab = 'trigger'
}

function triggerText(s: SceneMeta) {
  const t = s.triggerConfig
  if (!t.enabled) return '触发已暂停'
  if (t.type === 'schedule' && t.schedule) return `定时 · ${pad(t.schedule.hour)}:${pad(t.schedule.minute)}`
  if (t.type === 'event') return '事件触发'
  if (t.type === 'webhook') return 'Webhook'
  if (t.type === 'manual') return '手动触发'
  return '未配置触发'
}
function triggerIcon(s: SceneMeta) {
  const t = s.triggerConfig
  if (t.type === 'schedule') return '<svg width="12" height="12" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.3"/><path d="M8 4v4l3 2" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>'
  return '<svg width="12" height="12"></svg>'
}
function pad(n: number) { return String(n).padStart(2, '0') }

const SKILLS = [
  { id: 'fttr_planning', name: 'FTTR 续约策划', tag: '主 Skill', color: '#10B981', description: '⭐ ① ② ④ 共享。LLM 调用 DeepSeek-V3，输入本体客户对象 + 25 标签摘要，输出推荐策略 / 产品 / 渠道', meta: ['LLM', '共享', '客群洞察 + 产品推荐 + 话术'], iconSvg: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none"><path d="M9 1L3 9h4l-1 6 6-8H8l1-6z" fill="#fff"/></svg>' },
  { id: 'v5_ranking', name: 'V5 ML 排序', tag: 'ML', color: '#0EA5E9', description: '调 ml-models 完成 ML 排序：churn_model AUC 0.821，product_model AUC 0.791', meta: ['ML', '排序'], iconSvg: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none"><path d="M2 12L6 7l3 3 2-4 3 4" stroke="#fff" stroke-width="1.5"/></svg>' },
  { id: 'eight_segment_script', name: '八段式话术生成', tag: 'LLM', color: '#7C3AED', description: '④ 主 Skill。DeepSeek-V3 (t=0.5) 生成 8 段对话剧本：开场 / 价值唤醒 / 产品推荐 / 异议处理 / 促成 / 二轮异议 / 工单确认 / 结束语', meta: ['LLM', '8 段式'], iconSvg: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none"><path d="M3 3h10v8H10l-3 3v-3H3V3z" stroke="#fff" stroke-width="1.5"/></svg>' },
  { id: 'objection_match', name: '异议匹配', tag: '双轨', color: '#F59E0B', description: '④ 共用 Skill。关键词快速通道 + LLM 语义识别深度通道，识别 10 类异议 OB01~OB10', meta: ['关键词', 'LLM 语义'], iconSvg: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none"><path d="M8 1l1.5 4.5H14l-3.7 2.7L11.8 13 8 10.3 4.2 13l1.5-4.8L2 5.5h4.5L8 1z" stroke="#fff" stroke-width="1.3"/></svg>' },
  { id: 'nlp_evidence', name: '通话录音证据批量提取', tag: 'LLM 批量', color: '#2E5BFF', description: '一次 LLM 调用批量抽取 26 条 NLP 证据 (E1~E25 + E37)，相比独立调用节省 95% token、降低 20× 延迟', meta: ['批量 NLP', '退单归因'], iconSvg: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none"><rect x="3" y="3" width="10" height="10" rx="1" stroke="#fff" stroke-width="1.5"/><path d="M5 6h6M5 8h4M5 10h6" stroke="#fff" stroke-width="1.3"/></svg>' },
  { id: 'rule_evidence', name: '规则类证据批量计算', tag: 'TS Function', color: '#FF8900', description: '纯规则计算，11 条 Rule 类证据 (E26~E36) 并行执行，与 NLP 证据并行后合并为 37 条证据集', meta: ['Function', '11 条'], iconSvg: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none"><path d="M3 3h10M3 8h7M3 13h10" stroke="#fff" stroke-width="1.5"/></svg>' },
  { id: 'hierarchical_attribution', name: '分层归因推理', tag: 'LLM 微调', color: '#059669', description: '23 项二级根因 → 4 项一级根因，分层归因带置信度评分。冲突触发 LLM 微调', meta: ['分层归因', '退单'], iconSvg: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none"><path d="M8 2v12M3 6h10M5 10h6" stroke="#fff" stroke-width="1.5"/></svg>' },
  { id: 'nl2sql', name: 'NL2SQL 语义化查询', tag: '政企', color: '#0EA5E9', description: '自然语言 + 本体 Schema → SQL，支持多表关联 / 时间窗口 / 地域层级聚合 / 指标血缘追溯', meta: ['NL2SQL', '政企'], iconSvg: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none"><path d="M3 5h10M3 8h10M3 11h7" stroke="#fff" stroke-width="1.5"/></svg>' },
  { id: 'kpi_anomaly', name: '指标异动检测', tag: 'ML+统计', color: '#7C3AED', description: '3-Sigma / IQR / 同比环比 / Isolation Forest 多算法融合，输出异动等级 + 方向 + 影响范围', meta: ['统计', 'ML'], iconSvg: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none"><path d="M2 11l4-5 3 3 5-7" stroke="#fff" stroke-width="1.5"/></svg>' },
  { id: 'multi_dim_attribution', name: '多维归因融合', tag: '混合编排', color: '#10B981', description: '地域 / 产品 / 客户 / 时间四维度归因结果融合，按贡献度加权汇聚为统一根因列表', meta: ['多维', '加权'], iconSvg: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none"><path d="M8 2v12M2 8h12" stroke="#fff" stroke-width="1.5"/></svg>' },
  { id: 'cross_attribution', name: '交叉归因分析', tag: '交互效应', color: '#F59E0B', description: '识别多维交叉影响（如"浙江 × 政企客户 × 5 月"组合异动），输出交叉项贡献度', meta: ['交叉', '交互'], iconSvg: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none"><path d="M4 4l8 8M12 4l-8 8" stroke="#fff" stroke-width="1.5"/></svg>' },
  { id: 'confidence', name: '根因置信度评估', tag: '路由决策', color: '#EF4444', description: '4 维加权：数据完整性 25% + 收敛度 30% + 外部证据 20% + 趋势一致性 25%。输出 0-1 置信度', meta: ['置信', '4 维'], iconSvg: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="#fff" stroke-width="1.5"/><path d="M5 8l2 2 4-5" stroke="#fff" stroke-width="1.5"/></svg>' },
]

const AGENTS = [
  { id: 'demand_insight', idx: '①', name: '需求洞察师', role: 'reasoning', color: '#10B981', primary: true,
    description: '分析客户画像和需求特征，识别 FTTR 续约意愿信号，输出客群分层与流失风险标签',
    skills: ['FTTRRenewalPlanningSkill', 'V5RankingSkill'],
    tools: ['OntologyEngineTool', 'MLModelTool', 'MiniMaxLLMTool'],
    memories: ['Working', 'Episodic', 'Semantic'] },
  { id: 'product_recommend', idx: '②', name: '产品推荐师', role: 'reasoning', color: '#0EA5E9', primary: true,
    description: '匹配产品方案，生成差异化续约策略，依托 18 条产品匹配规则推荐最优组合',
    skills: ['FTTRRenewalPlanningSkill'],
    tools: ['OntologyEngineTool', 'RuleEngineTool'],
    memories: ['Semantic', 'Procedural'] },
  { id: 'channel_alloc', idx: '③', name: '触点分配师', role: 'orchestration', color: '#FF8900', primary: false,
    description: '规则版触点选择 Function。基于客户偏好 + 渠道触点效果模型分配最佳触达渠道',
    skills: ['ChannelAllocationFunction'],
    tools: ['RuleEngineTool', 'TouchpointEffectModel'],
    memories: ['Working'] },
  { id: 'script_gen', idx: '④', name: '话术生成师', role: 'generation', color: '#7C3AED', primary: true,
    description: '基于客户画像和触点渠道，通过 LLM 多轮推理生成千人千面营销话术，含合规校验',
    skills: ['EightSegmentScriptSkill', 'ObjectionMatchSkill'],
    tools: ['DeepSeekLLMTool', 'ScriptComplianceTool'],
    memories: ['Episodic', 'Semantic', 'Procedural'] },
  { id: 'evidence_extract', idx: 'B1', name: '证据提取 Agent', role: 'reasoning', color: '#2E5BFF', primary: true,
    description: '一次 LLM 调用批量抽取 26 条 NLP 证据（E1~E25+E37），并行 11 条规则证据，合并为 37 条证据集',
    skills: ['NLPEvidenceExtractSkill', 'RuleEvidenceCalcSkill'],
    tools: ['DeepSeekLLMTool', 'TypeScriptFunctionTool'],
    memories: ['Working', 'Semantic'] },
  { id: 'attribution', idx: 'B2', name: '根因归因 Agent', role: 'reasoning', color: '#059669', primary: true,
    description: '23 项二级根因 → 4 项一级根因，分层归因带置信度评分。冲突触发 LLM 微调',
    skills: ['HierarchicalAttributionSkill'],
    tools: ['DeepSeekLLMTool', 'OntologyEngineTool'],
    memories: ['Episodic', 'Semantic'] },
]
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

.aip-segmented {
  display: inline-flex; background: #f1f5f9; border-radius: 4px; padding: 2px;
}
.aip-seg {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 10px;
  border: none; background: transparent;
  font-size: 12px; color: #64748b; cursor: pointer; border-radius: 3px;
}
.aip-seg.active { background: #fff; color: #2E5BFF; box-shadow: 0 1px 2px rgba(0,0,0,.06); font-weight: 600; }

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
  position: absolute; top: 16px; right: 16px; z-index: 5;
  width: 36px; height: 36px; border-radius: 50%;
  border: none; background: #2E5BFF; color: #fff;
  font-size: 20px; line-height: 1; cursor: pointer;
  box-shadow: 0 2px 8px rgba(46,91,255,.3);
}
.aip-canvas-add:hover { background: #1d4ed8; transform: scale(1.05); }
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

/* ====== Skills / Agents view ====== */
.aip-secondary { flex: 1; padding: 24px 32px; overflow: auto; }
.aip-secondary__head { margin-bottom: 24px; }
.aip-secondary__title { font-size: 20px; font-weight: 700; color: #1e293b; margin: 0; }
.aip-secondary__sub { font-size: 13px; color: #64748b; margin: 4px 0 0; }

.aip-skill-grid, .aip-agent-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}
.aip-skill-card, .aip-agent-card {
  background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px;
  display: flex; flex-direction: column; gap: 10px;
}
.aip-skill-card { position: relative; }
.aip-skill-card__icon {
  width: 36px; height: 36px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.aip-skill-card__head { display: flex; align-items: center; gap: 8px; }
.aip-skill-card__name { font-size: 14px; font-weight: 600; color: #1e293b; flex: 1; }
.aip-skill-card__tag { font-size: 10px; padding: 1px 6px; border-radius: 4px; background: #eff6ff; color: #2563eb; }
.aip-skill-card__desc { font-size: 12px; color: #475569; line-height: 1.5; margin: 0; }
.aip-skill-card__meta { display: flex; flex-wrap: wrap; gap: 4px; }

.aip-agent-card__head { display: flex; align-items: center; gap: 10px; }
.aip-agent-card__icon {
  width: 32px; height: 32px; border-radius: 6px;
  color: #fff; font-weight: 700; font-size: 14px;
  display: flex; align-items: center; justify-content: center;
}
.aip-agent-card__title-wrap { flex: 1; }
.aip-agent-card__name { display: block; font-size: 14px; font-weight: 600; color: #1e293b; }
.aip-agent-card__role { font-size: 10px; color: #94a3b8; }
.aip-agent-card__primary { font-size: 10px; padding: 1px 6px; background: #fef3c7; color: #b45309; border-radius: 4px; }
.aip-agent-card__desc { font-size: 12px; color: #475569; margin: 0; line-height: 1.5; }
.aip-agent-card__cap { display: flex; flex-direction: column; gap: 6px; padding-top: 8px; border-top: 1px dashed #f0f0f0; }
.aip-agent-card__cap-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.aip-agent-card__cap-label { font-size: 10px; color: #94a3b8; min-width: 48px; font-weight: 600; letter-spacing: 0.4px; }

.aip-tag { font-size: 10px; padding: 1px 6px; border-radius: 3px; }
.aip-tag--blue { background: #eff6ff; color: #2563eb; }
.aip-tag--green { background: #ecfdf5; color: #059669; }
.aip-tag--cyan { background: #ecfeff; color: #0891b2; }
.aip-tag--purple { background: #f5f3ff; color: #7c3aed; }

/* ====== Modal forms ====== */
.aip-import { padding: 8px 0; }
.aip-import__hint { font-size: 12px; color: #64748b; margin-bottom: 10px; }
.aip-input { width: 100%; padding: 6px 10px; border: 1px solid #e2e8f0; border-radius: 4px; font-size: 12px; outline: none; }
.aip-input--ta { resize: vertical; font-family: ui-monospace, monospace; }

.aip-add-node { display: flex; flex-direction: column; gap: 12px; }
.aip-add-node__group-label { font-size: 11px; color: #94a3b8; font-weight: 600; margin-bottom: 6px; letter-spacing: 0.4px; }
.aip-add-node__items { display: flex; flex-wrap: wrap; gap: 6px; }
.aip-add-node__item {
  padding: 6px 12px; background: #fff; border: 1.5px solid #e2e8f0;
  border-radius: 4px; font-size: 12px; color: #475569; cursor: pointer;
}
.aip-add-node__item:hover { border-color: #2E5BFF; color: #2E5BFF; }
.aip-add-node__item.active { background: rgba(46,91,255,.05); }
</style>
