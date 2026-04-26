<template>
  <section class="ontology-board">
    <div class="ontology-board__intro">
      <div>
        <p class="text-caption-upper">Hydrate · Activate · Wield</p>
        <h2 class="text-h2 ontology-board__title">3D 本体场景板</h2>
        <p class="ontology-board__subtitle">
          三层等距架构：底层数据基座 → 中层本体网络 → 顶层应用能力。点击任意节点查看上下游并跳转。
        </p>
      </div>

      <div class="ontology-board__metrics">
        <div class="stage-metric" v-for="metric in activeStageMetrics" :key="metric.label">
          <span class="stage-metric__value">{{ metric.value }}</span>
          <span class="stage-metric__label">{{ metric.label }}</span>
        </div>
      </div>
    </div>

    <div class="ontology-board__stage-strip">
      <button
        v-for="stage in stages"
        :key="stage.id"
        type="button"
        class="stage-pill"
        :class="[
          `stage-pill--${stage.tone}`,
          { 'stage-pill--active': activeStage === stage.id },
        ]"
        @click="activateStage(stage.id)"
      >
        <span class="stage-pill__label">{{ stage.label }}</span>
        <span class="stage-pill__title">{{ stage.title }}</span>
      </button>
    </div>

    <div class="ontology-board__body">
      <IsometricScene
        :entities="entities"
        :relations="relations"
        :activeStage="activeStage"
        :selectedKey="selectedKey"
        :topModules="topModules"
        :bottomModules="bottomModules"
        @selectTarget="selectTarget"
      />

      <BoardDetailPanel
        :meta="selectedMeta"
        @select="selectTarget"
        @route="openRoute"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import IsometricScene from './isometric/IsometricScene.vue'
import BoardDetailPanel from './isometric/BoardDetailPanel.vue'
import type { DetailMeta } from './isometric/BoardDetailPanel.vue'
import type { DashboardStats, EntityListItem } from '../../types'
import type { RelationData } from '../../api/relations'

type StageId = 'hydrate' | 'activate' | 'wield'
type Tone = 'semantic' | 'dynamic' | 'kinetic'

interface StageDefinition {
  id: StageId
  label: string
  title: string
  summary: string
  tone: Tone
}

interface ModuleCard {
  key: string
  title: string
  label: string
  metric: string
  metricLabel: string
  description: string
  route: string
  secondaryRoute: string
  primaryLabel: string
  secondaryLabel: string
  placement: 'top' | 'bottom'
  tone: Tone
  badge: string
  stageAffinity: StageId[]
  highlights: string[]
}

const props = defineProps<{
  stats: DashboardStats | null
  entities: EntityListItem[]
  relations: RelationData[]
}>()

const router = useRouter()

const stages: StageDefinition[] = [
  { id: 'hydrate', label: '01', title: 'Hydrate', summary: '先把数据、规则和对象吸收到同一张业务底座里。', tone: 'semantic' },
  { id: 'activate', label: '02', title: 'Activate', summary: '再把对象之间的关系点亮，让链路真正可追踪。', tone: 'dynamic' },
  { id: 'wield', label: '03', title: 'Wield', summary: '最后把分析、工作流和集成能力挂到本体之上。', tone: 'kinetic' },
]

const relationLabelMap: Record<string, string> = {
  user_queries_portability: '发起携转查询',
  user_bindto_contract: '绑定合约',
  user_bindto_billing: '同步月账单',
  user_bindto_arrears: '关联欠费状态',
  user_has_voice_calls: '连接通话详单',
  user_receives_retention: '产生维系记录',
  user_bindto_convergence: '绑定融合套餐',
  contract_restricts_portability: '限制携转资格',
  arrears_restricts_portability: '欠费拦截携转',
  complaint_influences_retention: '投诉驱动挽留',
  user_has_complaints: '触发投诉工单',
}

const statusLabelMap = { active: '在线', warning: '关注', error: '异常' } as const

const activeStage = ref<StageId>('activate')
const selectedKey = ref('')

function displayEntityName(entity: Pick<EntityListItem, 'name' | 'name_cn'>) {
  return entity.name_cn || entity.name
}

function formatRelationLabel(name: string) {
  return relationLabelMap[name] ?? name.replaceAll('_', ' ')
}

const entityDegree = computed(() => {
  const map = new Map<string, number>()
  for (const r of props.relations) {
    map.set(r.from_entity_id, (map.get(r.from_entity_id) ?? 0) + 1)
    map.set(r.to_entity_id, (map.get(r.to_entity_id) ?? 0) + 1)
  }
  return map
})

const boardNodes = computed(() => {
  return [...props.entities]
    .sort((a, b) => {
      const dd = (entityDegree.value.get(b.id) ?? 0) - (entityDegree.value.get(a.id) ?? 0)
      if (dd !== 0) return dd
      if (b.relation_count !== a.relation_count) return b.relation_count - a.relation_count
      return b.rule_count - a.rule_count
    })
    .slice(0, 9)
})

const centerNode = computed(() => boardNodes.value[0] ?? null)
const activeEntityCount = computed(() => props.entities.filter(e => e.status === 'active').length)
const recentActivityCount = computed(() => props.stats?.recent_activities.length ?? 0)

const renderedRelations = computed(() => {
  const nodeIds = new Set(boardNodes.value.map(n => n.id))
  return props.relations.filter(r => nodeIds.has(r.from_entity_id) && nodeIds.has(r.to_entity_id))
})

const moduleCards = computed<ModuleCard[]>(() => {
  const entityCount = props.stats?.entity_count ?? props.entities.length
  const relationCount = props.stats?.relation_count ?? props.relations.length
  const ruleCount = props.stats?.rule_count ?? props.entities.reduce((s, e) => s + e.rule_count, 0)
  const activeRuleCount = props.stats?.active_rule_count ?? 0

  return [
    {
      key: 'module:analytics', title: 'ANALYTICS', label: '分析视角',
      metric: String(activeEntityCount.value), metricLabel: '活跃节点',
      description: '围绕对象状态、链路密度和异常信号做实时分析。',
      route: '/browser/graph', secondaryRoute: '/dashboard',
      primaryLabel: '打开关系画布', secondaryLabel: '回到看板总览',
      placement: 'top', tone: 'semantic', badge: '上层能力',
      stageAffinity: ['wield'],
      highlights: ['对象不是散点，而是分析入口。', '从单个节点可以回溯整个风险传播路径。', '适合承接图谱分析和健康度观察。'],
    },
    {
      key: 'module:workflows', title: 'WORKFLOWS', label: '流程编排',
      metric: String(ruleCount), metricLabel: '自动策略',
      description: '把规则命中、任务分发和处置动作挂到对象网络上执行。',
      route: '/scene/mnp', secondaryRoute: '/browser/rules',
      primaryLabel: '打开携转场景', secondaryLabel: '查看规则工坊',
      placement: 'top', tone: 'dynamic', badge: '上层能力',
      stageAffinity: ['wield'],
      highlights: ['对象变化可以直接触发流程。', '规则、动作和场景页面能串成一条执行链。', '适合承接预警、维系和派单。'],
    },
    {
      key: 'module:integrations', title: 'INTEGRATIONS', label: '集成出口',
      metric: String(recentActivityCount.value), metricLabel: '实时事件',
      description: '把场景结果推送到工单、外呼、短信或外部接口。',
      route: '/copilot', secondaryRoute: '/datasource',
      primaryLabel: '打开智能对话', secondaryLabel: '查看数据工坊',
      placement: 'top', tone: 'kinetic', badge: '上层能力',
      stageAffinity: ['wield'],
      highlights: ['把对象变化翻译成对外动作。', '让结果不仅可看见，也可下发。', '适合接入 AI 助理与外部系统。'],
    },
    {
      key: 'module:data', title: 'DATA', label: '数据基座',
      metric: String(entityCount), metricLabel: '对象',
      description: '承接用户、账单、投诉、合约等原始业务数据。',
      route: '/datasource', secondaryRoute: '/browser',
      primaryLabel: '打开数据工坊', secondaryLabel: '查看本体浏览器',
      placement: 'bottom', tone: 'semantic', badge: '底层输入',
      stageAffinity: ['hydrate'],
      highlights: ['先把数据接进来，后面的关系和动作才有依托。', '这里对应视频里底部的 DATA 平台。', '适合承接宽表、明细和主题数据。'],
    },
    {
      key: 'module:models', title: 'MODELS', label: '规则模型',
      metric: String(activeRuleCount), metricLabel: '启用规则',
      description: '把评分、规则和条件表达式挂到对象上。',
      route: '/browser/rules', secondaryRoute: '/scene/mnp',
      primaryLabel: '打开规则工坊', secondaryLabel: '查看携转场景',
      placement: 'bottom', tone: 'kinetic', badge: '底层输入',
      stageAffinity: ['hydrate'],
      highlights: ['模型不是额外的一层文档，而是对象的行为定义。', '这里对应视频里底部的 MODELS 平台。', '适合承接规则、评分卡和策略模型。'],
    },
    {
      key: 'module:ontology', title: 'ONTOLOGY', label: '对象网络',
      metric: String(relationCount), metricLabel: '关系',
      description: '把数据和规则组织成可追踪的业务对象网络。',
      route: '/browser/graph', secondaryRoute: '/browser',
      primaryLabel: '打开关系画布', secondaryLabel: '查看本体浏览器',
      placement: 'bottom', tone: 'dynamic', badge: '核心层',
      stageAffinity: ['hydrate', 'activate', 'wield'],
      highlights: ['这里是整块场景板的中心。', '点击任意对象，都能看到它的上游和下游。', '视频里所有能力面板都围绕它展开。'],
    },
  ]
})

const topModules = computed(() => moduleCards.value.filter(m => m.placement === 'top'))
const bottomModules = computed(() => moduleCards.value.filter(m => m.placement === 'bottom'))

function stageDefaultSelection(stage: StageId) {
  if (stage === 'hydrate') return 'module:ontology'
  if (stage === 'wield') return 'module:workflows'
  return centerNode.value ? `entity:${centerNode.value.id}` : 'module:ontology'
}

watch(
  () => [moduleCards.value.length, boardNodes.value.length, centerNode.value?.id].join(':'),
  () => {
    const validKeys = new Set([
      ...moduleCards.value.map(m => m.key),
      ...boardNodes.value.map(n => `entity:${n.id}`),
    ])
    if (!selectedKey.value || !validKeys.has(selectedKey.value)) {
      selectedKey.value = stageDefaultSelection(activeStage.value)
    }
  },
  { immediate: true },
)

function activateStage(stage: StageId) {
  activeStage.value = stage
  selectedKey.value = stageDefaultSelection(stage)
}

function selectTarget(key: string) {
  selectedKey.value = key
  if (key.startsWith('entity:')) {
    activeStage.value = 'activate'
    return
  }
  const mod = moduleCards.value.find(m => m.key === key)
  if (mod && !mod.stageAffinity.includes(activeStage.value)) {
    activeStage.value = mod.stageAffinity[0]
  }
}

function openRoute(path: string) {
  router.push(path)
}

const activeStageMetrics = computed(() => {
  if (activeStage.value === 'hydrate') {
    return [
      { value: props.stats?.entity_count ?? props.entities.length, label: '已吸收对象' },
      { value: props.stats?.relation_count ?? props.relations.length, label: '已建立关系' },
      { value: props.stats?.active_rule_count ?? 0, label: '已挂载规则' },
    ]
  }
  if (activeStage.value === 'wield') {
    return [
      { value: props.stats?.rule_count ?? 0, label: '编排策略' },
      { value: recentActivityCount.value, label: '实时事件' },
      { value: topModules.value.length, label: '能力出口' },
    ]
  }
  return [
    { value: activeEntityCount.value, label: '活跃节点' },
    { value: renderedRelations.value.length, label: '可追踪链路' },
    { value: centerNode.value ? displayEntityName(centerNode.value) : '-', label: '核心对象' },
  ]
})

const selectedModule = computed(() => moduleCards.value.find(m => m.key === selectedKey.value) ?? null)
const selectedNode = computed(() => {
  if (!selectedKey.value.startsWith('entity:')) return null
  const id = selectedKey.value.slice(7)
  return props.entities.find(e => e.id === id) ?? null
})

function moduleConnections(moduleKey: string) {
  const top3 = boardNodes.value.slice(0, 3)
  const workflowNode = boardNodes.value.find(n => n.rule_count > 0)

  if (moduleKey === 'module:data') {
    return top3.map(n => ({ key: `entity:${n.id}`, label: `对象 · ${displayEntityName(n)}` }))
  }
  if (moduleKey === 'module:models') {
    return (workflowNode ? [workflowNode] : boardNodes.value.slice(0, 1))
      .map(n => ({ key: `entity:${n.id}`, label: `规则挂接 · ${displayEntityName(n)}` }))
  }
  if (moduleKey === 'module:ontology') {
    return boardNodes.value.slice(0, 4).map(n => ({ key: `entity:${n.id}`, label: `链路节点 · ${displayEntityName(n)}` }))
  }
  if (moduleKey === 'module:analytics') {
    return [
      { key: 'module:ontology', label: '回到对象网络' },
      ...boardNodes.value.slice(0, 2).map(n => ({ key: `entity:${n.id}`, label: `分析对象 · ${displayEntityName(n)}` })),
    ]
  }
  if (moduleKey === 'module:integrations') {
    return [
      { key: 'module:workflows', label: '联动流程编排' },
      ...boardNodes.value.slice(0, 2).map(n => ({ key: `entity:${n.id}`, label: `输出对象 · ${displayEntityName(n)}` })),
    ]
  }
  return [
    { key: 'module:ontology', label: '回到对象网络' },
    ...boardNodes.value.slice(0, 2).map(n => ({ key: `entity:${n.id}`, label: `任务焦点 · ${displayEntityName(n)}` })),
  ]
}

const selectedMeta = computed<DetailMeta>(() => {
  if (selectedNode.value) {
    const entity = selectedNode.value
    const connections = props.relations
      .filter(r => r.from_entity_id === entity.id || r.to_entity_id === entity.id)
      .map(r => {
        const targetId = r.from_entity_id === entity.id ? r.to_entity_id : r.from_entity_id
        const target = props.entities.find(e => e.id === targetId)
        return {
          key: `entity:${targetId}`,
          label: `${formatRelationLabel(r.name)} · ${target ? displayEntityName(target) : targetId}`,
        }
      })
      .slice(0, 6)

    const tone: Tone = entity.status === 'active' ? 'dynamic' : entity.status === 'warning' ? 'kinetic' : 'semantic'

    return {
      eyebrow: '对象节点',
      title: displayEntityName(entity),
      badge: statusLabelMap[entity.status] ?? entity.status,
      badgeTone: tone,
      summary: `${displayEntityName(entity)} 已经从视频中的示意对象变成真实可点选节点。你可以继续追踪它关联的账单、合约、投诉、维系或携转记录。`,
      facts: [
        { label: '对象层级', value: `Tier ${entity.tier}` },
        { label: '属性数', value: entity.attr_count },
        { label: '关系数', value: entity.relation_count },
        { label: '规则数', value: entity.rule_count },
      ],
      connections,
      notes: [
        `${displayEntityName(entity)} 当前状态为"${statusLabelMap[entity.status] ?? entity.status}"。`,
        '点击上面的关联链路，可以沿着对象网络继续钻取。',
        '如需查看属性、规则和血缘视图，可直接进入实体详情页。',
      ],
      primaryLabel: '打开实体详情',
      primaryRoute: `/ontology/${entity.id}`,
      secondaryLabel: '查看全局关系',
      secondaryRoute: '/browser/graph',
    }
  }

  const mod = selectedModule.value ?? moduleCards.value.find(m => m.key === 'module:ontology')!
  const stage = stages.find(s => s.id === activeStage.value)

  return {
    eyebrow: stage ? `${stage.title} Stage` : 'Stage',
    title: mod.label,
    badge: mod.badge,
    badgeTone: mod.tone,
    summary: `${mod.description} ${stage?.summary ?? ''}`,
    facts: [
      { label: '焦点阶段', value: stage?.title ?? '-' },
      { label: '当前指标', value: `${mod.metric} ${mod.metricLabel}` },
      { label: '可视对象', value: boardNodes.value.length },
      { label: '链路总数', value: renderedRelations.value.length },
    ],
    connections: moduleConnections(mod.key),
    notes: mod.highlights,
    primaryLabel: mod.primaryLabel,
    primaryRoute: mod.route,
    secondaryLabel: mod.secondaryLabel,
    secondaryRoute: mod.secondaryRoute,
  }
})
</script>

<style scoped>
.ontology-board {
  position: relative;
  border: 1px solid rgba(18, 184, 134, 0.14);
  border-radius: 28px;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(18, 184, 134, 0.08), transparent 34%),
    radial-gradient(circle at top right, rgba(76, 110, 245, 0.08), transparent 32%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 249, 250, 0.92));
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.ontology-board__intro {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 18px;
}

.ontology-board__title { margin-top: 6px; }

.ontology-board__subtitle {
  max-width: 720px;
  margin-top: 8px;
  font-size: var(--text-body-size);
  line-height: 1.7;
  color: var(--neutral-600);
}

.ontology-board__metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  min-width: 330px;
}

.stage-metric {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(15, 17, 23, 0.05);
  box-shadow: 0 12px 24px rgba(15, 17, 23, 0.04);
}

.stage-metric__value {
  font-size: var(--text-h1-size);
  font-weight: 700;
  line-height: 1;
  color: var(--neutral-900);
}

.stage-metric__label {
  font-size: var(--text-caption-size);
  color: var(--neutral-500);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.ontology-board__stage-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.stage-pill {
  border: 1px solid var(--neutral-200);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.84);
  padding: 14px 16px;
  text-align: left;
  cursor: pointer;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast),
    border-color var(--transition-fast), opacity var(--transition-fast);
}

.stage-pill:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.stage-pill__label {
  display: block;
  font-size: var(--text-caption-size);
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--neutral-500);
}

.stage-pill__title {
  display: block;
  margin-top: 6px;
  font-size: var(--text-h3-size);
  font-weight: 600;
  color: var(--neutral-800);
}

.stage-pill--active.stage-pill--semantic {
  border-color: rgba(76, 110, 245, 0.28);
  box-shadow: 0 12px 30px rgba(76, 110, 245, 0.14);
}

.stage-pill--active.stage-pill--dynamic {
  border-color: rgba(18, 184, 134, 0.28);
  box-shadow: 0 12px 30px rgba(18, 184, 134, 0.16);
}

.stage-pill--active.stage-pill--kinetic {
  border-color: rgba(240, 140, 0, 0.28);
  box-shadow: 0 12px 30px rgba(240, 140, 0, 0.16);
}

.ontology-board__body {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) 330px;
  gap: 18px;
}

@media (max-width: 1280px) {
  .ontology-board__intro,
  .ontology-board__body {
    grid-template-columns: 1fr;
  }
  .ontology-board__metrics { min-width: 0; }
}

@media (max-width: 980px) {
  .ontology-board { padding: 18px; }
  .ontology-board__stage-strip { grid-template-columns: 1fr; }
}

@media (max-width: 720px) {
  .ontology-board__metrics { grid-template-columns: 1fr; }
}
</style>
