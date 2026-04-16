<template>
  <div class="mnp-page">
    <!-- 页面标题 -->
    <div class="mnp-page__header">
      <div class="mnp-page__title-row">
        <div class="mnp-page__icon">
          <svg width="20" height="20" viewBox="0 0 16 16" fill="none">
            <path d="M8 2l5 3v6l-5 3-5-3V5l5-3z" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/>
            <path d="M8 5v6" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>
            <circle cx="8" cy="13" r="0.8" fill="#fff"/>
          </svg>
        </div>
        <div>
          <h1 class="mnp-page__title">携号转网预警</h1>
          <p class="mnp-page__desc">基于本体实体间的流程驱动，展示携转预警从信号感知到任务分发的端到端编排</p>
        </div>
      </div>
    </div>

    <!-- KPI 指标栏 -->
    <div class="mnp-kpis">
      <div class="kpi-card"><div class="kpi-val">7</div><div class="kpi-lbl">流程阶段</div></div>
      <div class="kpi-card"><div class="kpi-val">{{ totalEntities }}</div><div class="kpi-lbl">参与实体</div></div>
      <div class="kpi-card"><div class="kpi-val">{{ totalRules }}</div><div class="kpi-lbl">关联规则</div></div>
      <div class="kpi-card"><div class="kpi-val">{{ totalActions }}</div><div class="kpi-lbl">驱动动作</div></div>
      <div class="kpi-card"><div class="kpi-val">100%</div><div class="kpi-lbl">实体覆盖率</div></div>
      <div class="kpi-card"><div class="kpi-val">100%</div><div class="kpi-lbl">规则覆盖率</div></div>
      <div class="kpi-card"><div class="kpi-val">&lt;3s</div><div class="kpi-lbl">端到端耗时</div></div>
      <div class="kpi-card"><div class="kpi-val">85%</div><div class="kpi-lbl">自动化率</div></div>
    </div>

    <!-- 流程层级带 -->
    <div class="mnp-layers">
      <div v-for="layer in layers" :key="layer.key" class="layer-band" :class="`layer-band--${layer.key}`">
        <div class="layer-band__head"><strong>{{ layer.label }}</strong></div>
        <div class="layer-band__stats">
          <span>{{ layer.entityCount }} 个实体</span>
          <span>{{ layer.attrCount }} 个属性</span>
          <span>{{ layer.relationCount }} 条关系</span>
          <span>{{ layer.ruleCount }} 条规则</span>
          <span>{{ layer.actionCount }} 个动作</span>
        </div>
      </div>
    </div>

    <!-- 案例用户选择 -->
    <div class="mnp-user-bar">
      <div class="user-bar__label">案例用户</div>
      <div class="user-bar__cards">
        <div v-for="(u, i) in userList" :key="u.id"
          class="user-mini-card"
          :class="{ 'user-mini-card--active': selectedUserIndex === i }"
          @click="selectedUserIndex = i">
          <div class="user-mini__avatar" :class="`avatar--${u.finalRiskLevel}`">{{ u.name[0] }}</div>
          <div class="user-mini__info">
            <div class="user-mini__name">{{ u.name }}</div>
            <div class="user-mini__phone">{{ u.phone }}</div>
          </div>
          <div class="user-mini__risk" :class="`risk--${u.finalRiskLevel}`">
            {{ u.finalRiskLevel === 'high' ? '高风险' : u.finalRiskLevel === 'medium' ? '中风险' : '低风险' }}
          </div>
          <div class="user-mini__score" v-if="u.riskScore">{{ u.riskScore }}分</div>
        </div>
      </div>
      <div v-if="dataLoading" class="user-bar__loading">加载中...</div>
      <div v-if="loadError" class="user-bar__error">{{ loadError }}</div>
    </div>

    <!-- 主工作区: 左右分栏 -->
    <div class="mnp-body">
      <!-- 左侧: 流程时间线 -->
      <div class="mnp-left">
        <ProcessOrchTimeline
          :steps="orchSteps"
          :active-step="activeStep"
          :step-states="stepStates"
          :step-durations="stepDurations"
          :running="execRunning"
          @step-click="onStepClick"
          @start-exec="startExecution"
        />
      </div>
      <!-- 右侧: 选中阶段详情 -->
      <div class="mnp-right">
        <!-- 阶段描述 -->
        <div class="stage-desc-card" v-if="currentStage">
          <div class="stage-desc__header">
            <span class="stage-desc__name">{{ currentStage.name }}</span>
            <span class="stage-desc__layer" :class="`layer-tag--${currentStage.layer}`">{{ layerLabel(currentStage.layer) }}</span>
          </div>
          <div class="stage-desc__text">{{ currentStage.description }}</div>
        </div>

        <!-- 阶段执行结果摘要 -->
        <div class="stage-result-card" v-if="stepStates[activeStep] === 'done'">
          <div class="stage-result__header">
            <span class="stage-result__icon">&#9679;</span>
            <span class="stage-result__title">{{ currentStage?.name }} — 执行结果</span>
          </div>
          <!-- 信号触发 -->
          <div v-if="activeStep === 0" class="stage-result__body">
            <div class="result-row"><span class="result-label">信号来源</span><span class="result-value">{{ selectedUser.entities.MnpEligibilityQuery?.query_channel }}</span></div>
            <div class="result-row"><span class="result-label">触发时间</span><span class="result-value">{{ selectedUser.entities.MnpEligibilityQuery?.query_time }}</span></div>
            <div class="result-row"><span class="result-label">携出状态</span><span class="result-value">{{ selectedUser.entities.MnpEligibilityQuery?.out_tag }}</span></div>
          </div>
          <!-- 本体数据拉取 -->
          <div v-else-if="activeStep === 1" class="stage-result__body">
            <div class="result-row"><span class="result-label">拉取实体</span><span class="result-value">7 个核心实体</span></div>
            <div class="result-row"><span class="result-label">用户</span><span class="result-value">{{ selectedUser.name }} ({{ selectedUser.phone }})</span></div>
            <div class="result-row"><span class="result-label">在网时长</span><span class="result-value">{{ selectedUser.entities.CbssSubscriber?.innet_months }}个月</span></div>
            <div class="result-row"><span class="result-label">合约到期</span><span class="result-value">{{ selectedUser.entities.SubscriberContract?.end_date }}</span></div>
          </div>
          <!-- 规则匹配校验 -->
          <div v-else-if="activeStep === 2" class="stage-result__body">
            <div class="result-row" v-for="r in selectedUser.ruleResults" :key="r.ruleName">
              <span class="result-label">{{ r.ruleName }}</span>
              <span class="result-value">
                <span class="result-match" :class="r.conditions.every(c => c.matched) ? 'match--yes' : 'match--partial'">
                  {{ r.conditions.filter(c => c.matched).length }}/{{ r.conditions.length }} 条件命中
                </span>
              </span>
            </div>
          </div>
          <!-- 风险等级定级 -->
          <div v-else-if="activeStep === 3" class="stage-result__body">
            <div class="result-row"><span class="result-label">风险等级</span><span class="result-value"><span class="risk-badge" :class="`risk--${selectedUser.finalRiskLevel}`">{{ selectedUser.entities.MnpRiskUser?.risk_level }}</span></span></div>
            <div class="result-row"><span class="result-label">风险评分</span><span class="result-value result-value--bold">{{ selectedUser.riskScore }}分</span></div>
          </div>
          <!-- 流失根因拆解 -->
          <div v-else-if="activeStep === 4" class="stage-result__body">
            <div class="result-row"><span class="result-label">TOP3 流失动因</span></div>
            <div class="result-tags">
              <span v-for="(reason, ri) in selectedUser.churnReasonTop3" :key="ri" class="reason-tag">{{ ri + 1 }}. {{ reason }}</span>
            </div>
          </div>
          <!-- 动作推荐生成 -->
          <div v-else-if="activeStep === 5" class="stage-result__body">
            <div class="result-row"><span class="result-label">推荐动作</span></div>
            <div class="result-tags">
              <span v-for="act in selectedUser.recommendedActions" :key="act" class="action-tag">{{ act }}</span>
            </div>
          </div>
          <!-- 任务自动分发 -->
          <div v-else-if="activeStep === 6" class="stage-result__body">
            <div class="result-row"><span class="result-label">分发渠道</span><span class="result-value result-value--bold">{{ selectedUser.assignedChannel }}</span></div>
            <div class="result-row"><span class="result-label">任务状态</span><span class="result-value"><span class="status-tag">{{ selectedUser.entities.MnpRiskUser?.task_status }}</span></span></div>
          </div>
        </div>

        <!-- 实体参与 -->
        <EntityParticipantPanel :stage="currentStage" />

        <!-- 实体-规则映射表 -->
        <EntityMappingTable
          :title="mappingTitle"
          :badge="mappingBadge"
          :badge-type="mappingBadgeType"
          :conditions="mappingConditions"
        />

        <!-- 动作驱动 -->
        <ActionDriverPanel :actions="actionDrivers" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import ProcessOrchTimeline from '../../components/mnp/ProcessOrchTimeline.vue'
import type { OrchStep, StepState } from '../../components/mnp/ProcessOrchTimeline.vue'
import EntityParticipantPanel from '../../components/mnp/EntityParticipantPanel.vue'
import EntityMappingTable from '../../components/mnp/EntityMappingTable.vue'
import type { MappingCondition } from '../../components/mnp/EntityMappingTable.vue'
import ActionDriverPanel from '../../components/mnp/ActionDriverPanel.vue'
import type { ActionDriver } from '../../components/mnp/ActionDriverPanel.vue'
import { entityApi } from '../../api/ontology'
import { sceneApi } from '../../api/scene'
import type { MnpExecuteResult } from '../../api/scene'

/* -------- TYPES -------- */
export interface EntityRole {
  entityName: string
  entityNameCn: string
  role: string
  attributes: string[]
  values?: Record<string, string | number | boolean>
}

export interface ProcessStage {
  id: number
  name: string
  layer: 'signal' | 'aggregate' | 'decision'
  inputEntities: EntityRole[]
  outputEntities: EntityRole[]
  rules: string[]
  actions: string[]
  description: string
}

/* -------- USER INSTANCE TYPE -------- */
interface UserInstance {
  id: string; name: string; phone: string
  entities: Record<string, Record<string, string | number | boolean>>
  ruleResults: Array<{
    ruleName: string; riskLevel: 'high' | 'medium' | 'low'
    conditions: Array<{ condition: string; sourceEntity: string; sourceAttribute: string; operator: string; threshold: string; actual: string; matched: boolean }>
  }>
  finalRiskLevel: 'high' | 'medium' | 'low'
  riskScore: number
  churnReasonTop3: string[]
  recommendedActions: string[]
  assignedChannel: string
}

/* -------- STATE -------- */
const activeStep = ref(0)
const execRunning = ref(false)
const stepStates = ref<StepState[]>(Array(7).fill('pending'))
const stepDurations = ref<(string | null)[]>(Array(7).fill(null))
const selectedUserIndex = ref(0)

/* -------- DATA -------- */
const users = ref<UserInstance[]>([])
const userDataMap = ref<Record<string, MnpExecuteResult>>({})
const dataLoading = ref(false)
const loadError = ref('')

const userList = computed(() => users.value)
const selectedUser = computed<UserInstance>(() => {
  const user = users.value[selectedUserIndex.value]
  if (!user) return { id: '', name: '', phone: '', entities: {}, ruleResults: [], finalRiskLevel: 'low', riskScore: 0, churnReasonTop3: [], recommendedActions: [], assignedChannel: '' } as UserInstance
  const live = userDataMap.value[user.id]
  if (live) {
    return {
      ...user,
      entities: live.entities as any,
      ruleResults: live.ruleResults.map(r => ({
        ...r,
        riskLevel: r.riskLevel as 'high' | 'medium' | 'low',
      })),
      finalRiskLevel: live.finalRiskLevel as 'high' | 'medium' | 'low',
      riskScore: live.riskScore,
      churnReasonTop3: live.churnReasonTop3,
      recommendedActions: live.recommendedActions,
      assignedChannel: live.assignedChannel,
    }
  }
  return user
})

/* -------- STAGES (for EntityParticipantPanel) -------- */
const stagesData: ProcessStage[] = [
  {
    id: 1, name: '信号触发', layer: 'signal',
    description: '用户通过手厅APP、10086热线或营业厅发起携转资格查询，系统实时捕获该信号作为预警起点。MnpEligibilityQuery 实体记录查询时间、渠道、受限原因等关键字段，与 CbssSubscriber 实体通过 user_id 关联，形成完整触发语义。',
    inputEntities: [
      { entityName: 'MnpEligibilityQuery', entityNameCn: '携转资格查询', role: '触发源', attributes: ['query_time', 'query_channel', 'out_tag', 'limit_remark'] },
      { entityName: 'CbssSubscriber', entityNameCn: 'CBSS移网用户', role: '数据源', attributes: ['user_id', 'device_number', 'user_status'] },
    ],
    outputEntities: [{ entityName: 'MnpRiskUser', entityNameCn: '携转风险用户', role: '产出', attributes: ['signal_source', 'signal_time'] }],
    rules: ['101号携转意向信号识别规则'], actions: [],
  },
  {
    id: 2, name: '本体数据拉取', layer: 'aggregate',
    description: '系统秒级拉取该用户全量本体数据，覆盖7大核心实体的全属性。通过实体间的语义关联关系（user_id、device_number），将分散在不同数据源的信息聚合为统一的本体视图。',
    inputEntities: [
      { entityName: 'CbssSubscriber', entityNameCn: 'CBSS移网用户', role: '数据源', attributes: ['innet_months', 'is_5g', 'pay_mode'] },
      { entityName: 'SubscriberContract', entityNameCn: '用户合约', role: '数据源', attributes: ['activity_type', 'end_date', 'protocal_month'] },
      { entityName: 'CustomerComplaint', entityNameCn: '客户投诉', role: '数据源', attributes: ['complaint_type', 'complaint_count_3m'] },
      { entityName: 'NetworkQuality', entityNameCn: '网络质量', role: '数据源', attributes: ['avg_download_speed', 'coverage_score', 'fault_count_3m'] },
      { entityName: 'CompetitorActivity', entityNameCn: '竞品活动', role: '数据源', attributes: ['competitor_name', 'offer_type', 'price_advantage'] },
      { entityName: 'FamilyGroup', entityNameCn: '家庭群组', role: '数据源', attributes: ['member_count', 'ported_member_count', 'family_arpu'] },
    ],
    outputEntities: [], rules: [], actions: [],
  },
  {
    id: 3, name: '规则匹配校验', layer: 'decision',
    description: '系统自动匹配高/中/低风险预警规则，逐条校验。每条规则由多个条件项组成，每个条件项锚定到具体的本体实体和属性。',
    inputEntities: [
      { entityName: 'CbssSubscriber', entityNameCn: 'CBSS移网用户', role: '数据源', attributes: ['innet_months'] },
      { entityName: 'SubscriberContract', entityNameCn: '用户合约', role: '数据源', attributes: ['end_date'] },
      { entityName: 'CustomerComplaint', entityNameCn: '客户投诉', role: '数据源', attributes: ['complaint_count_3m'] },
      { entityName: 'CompetitorActivity', entityNameCn: '竞品活动', role: '数据源', attributes: ['query_count'] },
      { entityName: 'FamilyGroup', entityNameCn: '家庭群组', role: '数据源', attributes: ['ported_member_count'] },
    ],
    outputEntities: [{ entityName: 'MnpRiskUser', entityNameCn: '携转风险用户', role: '产出', attributes: ['matched_rule_id', 'condition_pass_count'] }],
    rules: ['NP-RULE-H01 高风险规则', 'NP-RULE-M01 中风险规则', 'NP-RULE-L01 低风险规则'], actions: [],
  },
  {
    id: 4, name: '风险等级定级', layer: 'decision',
    description: '完成全规则校验后，根据匹配结果对用户进行风险等级定级。定级结果写入 MnpRiskUser 实体的 risk_level 属性，同时生成风险预警事件。',
    inputEntities: [{ entityName: 'MnpRiskUser', entityNameCn: '携转风险用户', role: '数据源', attributes: ['matched_rule_id', 'condition_pass_count'] }],
    outputEntities: [{ entityName: 'MnpRiskUser', entityNameCn: '携转风险用户', role: '产出', attributes: ['risk_level', 'risk_score', 'risk_time'] }],
    rules: [], actions: [],
  },
  {
    id: 5, name: '流失根因拆解', layer: 'decision',
    description: '基于全本体关联分析，交叉分析合约状态、投诉历史、网络体验、竞品活动和家庭关系，输出TOP3流失动因。',
    inputEntities: [
      { entityName: 'SubscriberContract', entityNameCn: '用户合约', role: '数据源', attributes: ['end_date', 'activity_type'] },
      { entityName: 'CustomerComplaint', entityNameCn: '客户投诉', role: '数据源', attributes: ['complaint_type', 'complaint_count_3m'] },
      { entityName: 'NetworkQuality', entityNameCn: '网络质量', role: '数据源', attributes: ['avg_download_speed', 'fault_count_3m'] },
      { entityName: 'CompetitorActivity', entityNameCn: '竞品活动', role: '数据源', attributes: ['offer_type', 'price_advantage'] },
      { entityName: 'FamilyGroup', entityNameCn: '家庭群组', role: '数据源', attributes: ['ported_member_count'] },
    ],
    outputEntities: [{ entityName: 'MnpRiskUser', entityNameCn: '携转风险用户', role: '产出', attributes: ['churn_reason_top3'] }],
    rules: [], actions: [],
  },
  {
    id: 6, name: '动作推荐生成', layer: 'decision',
    description: '基于流失根因和用户本体属性，从预定义的维系动作库中匹配最优个性化方案，包括专属优惠、套餐升级、网络优化、回访关怀等。',
    inputEntities: [
      { entityName: 'MnpRiskUser', entityNameCn: '携转风险用户', role: '数据源', attributes: ['risk_level', 'churn_reason_top3'] },
      { entityName: 'CbssSubscriber', entityNameCn: 'CBSS移网用户', role: '数据源', attributes: ['pay_mode', 'is_5g'] },
      { entityName: 'SubscriberContract', entityNameCn: '用户合约', role: '数据源', attributes: ['activity_type'] },
    ],
    outputEntities: [{ entityName: 'MnpRiskUser', entityNameCn: '携转风险用户', role: '产出', attributes: ['recommended_actions'] }],
    rules: [], actions: ['发送专属优惠', '套餐升级推荐', '网络质量优化', '一键外呼关怀', '一键发送挽留短信', '一键下发产品'],
  },
  {
    id: 7, name: '任务自动分发', layer: 'decision',
    description: '根据风险等级和维系方案，自动生成维系任务并分发至对应的维系坐席或自动化通道。',
    inputEntities: [{ entityName: 'MnpRiskUser', entityNameCn: '携转风险用户', role: '数据源', attributes: ['risk_level', 'recommended_actions'] }],
    outputEntities: [{ entityName: 'MnpRiskUser', entityNameCn: '携转风险用户', role: '产出', attributes: ['task_status', 'assigned_channel'] }],
    rules: [], actions: ['高风险→专属坐席', '中风险→自动外呼', '低风险→短信触达'],
  },
]

const currentStage = computed<ProcessStage | null>(() => {
  const stage = stagesData[activeStep.value]
  if (!stage) return null
  const user = selectedUser.value
  const injectValues = (entities: EntityRole[]): EntityRole[] =>
    entities.map(e => ({ ...e, values: user.entities[e.entityName] }))
  return { ...stage, inputEntities: injectValues(stage.inputEntities), outputEntities: injectValues(stage.outputEntities) }
})

/* -------- ORCH STEPS (for timeline) -------- */
const orchSteps: OrchStep[] = stagesData.map(s => ({
  tag: s.name,
  desc: s.description,
  inputEntities: s.inputEntities.map(e => e.entityName),
  outputEntities: s.outputEntities.map(e => e.entityName),
  rules: s.rules,
  actions: s.actions,
  color: s.layer === 'signal' ? 'blue' : s.layer === 'aggregate' ? 'orange' : s.id === 4 ? 'red' : s.id === 5 ? 'purple' : 'green',
} as OrchStep))

/* -------- LAYERS (从后端动态获取) -------- */
interface LayerStats {
  key: string; label: string
  entityCount: number; attrCount: number; relationCount: number
  ruleCount: number; actionCount: number
}
const layers = ref<LayerStats[]>([
  { key: 'signal', label: '语义层', entityCount: 0, attrCount: 0, relationCount: 0, ruleCount: 0, actionCount: 0 },
  { key: 'aggregate', label: '动力层', entityCount: 0, attrCount: 0, relationCount: 0, ruleCount: 0, actionCount: 0 },
  { key: 'decision', label: '动态层', entityCount: 0, attrCount: 0, relationCount: 0, ruleCount: 0, actionCount: 0 },
])

onMounted(async () => {
  try {
    layers.value = await entityApi.sceneLayerStats('s5')
  } catch (e) {
    console.warn('Failed to load layer stats', e)
  }
  // 从后端加载案例用户列表
  dataLoading.value = true
  try {
    const caseUsers = await sceneApi.mnpCaseUsers()
    users.value = caseUsers.map(u => ({
      id: u.user_id,
      name: u.name || u.user_id,
      phone: u.phone || '',
      entities: {},
      ruleResults: [],
      finalRiskLevel: (u.finalRiskLevel || 'low') as 'high' | 'medium' | 'low',
      riskScore: u.riskScore || 0,
      churnReasonTop3: [],
      recommendedActions: [],
      assignedChannel: '',
    }))
    if (caseUsers.length) {
      await loadUserData(caseUsers[0].user_id)
    }
  } catch (e: any) {
    loadError.value = '加载案例用户失败: ' + (e?.message || e)
    console.error('加载案例用户失败', e)
  } finally {
    dataLoading.value = false
  }
})

async function loadUserData(userId: string) {
  if (userDataMap.value[userId]) return
  dataLoading.value = true
  try {
    const result = await sceneApi.mnpExecute(userId)
    userDataMap.value = { ...userDataMap.value, [userId]: result }
    const idx = users.value.findIndex(u => u.id === userId)
    if (idx >= 0) {
      users.value[idx] = {
        ...users.value[idx],
        finalRiskLevel: result.finalRiskLevel as 'high' | 'medium' | 'low',
        riskScore: result.riskScore,
      }
      users.value = [...users.value]
    }
  } catch (e: any) {
    loadError.value = `加载用户 ${userId} 数据失败: ` + (e?.message || e)
    console.error(`加载用户 ${userId} 数据失败`, e)
  } finally {
    dataLoading.value = false
  }
}

// 切换用户时自动加载数据
watch(selectedUserIndex, (idx) => {
  const user = users.value[idx]
  if (user) {
    loadUserData(user.id)
  }
})

const totalEntities = computed(() => layers.value.reduce((s, l) => s + l.entityCount, 0))
const totalRules = computed(() => layers.value.reduce((s, l) => s + l.ruleCount, 0))
const totalActions = computed(() => layers.value.reduce((s, l) => s + l.actionCount, 0))

function layerLabel(layer: string) {
  const m: Record<string, string> = { signal: '语义层', aggregate: '动力层', decision: '动态层' }
  return m[layer] || layer
}

/* -------- EXECUTION LOGIC -------- */
const stageDurations = [0.3, 0.8, 1.2, 0.5, 0.9, 0.7, 0.4]

function onStepClick(i: number) {
  if (!execRunning.value) activeStep.value = i
}

function startExecution() {
  execRunning.value = true
  stepStates.value = Array(7).fill('pending')
  stepDurations.value = Array(7).fill(null)
  activeStep.value = 0
  runStep(0)
}

function runStep(i: number) {
  if (i >= stagesData.length) { execRunning.value = false; return }
  stepStates.value[i] = 'running'
  stepStates.value = [...stepStates.value]
  activeStep.value = i
  const duration = stageDurations[i]
  setTimeout(() => {
    stepStates.value[i] = 'done'
    stepDurations.value[i] = String(duration)
    stepStates.value = [...stepStates.value]
    stepDurations.value = [...stepDurations.value]
    setTimeout(() => runStep(i + 1), 200)
  }, duration * 1000)
}

/* -------- ENTITY-RULE MAPPINGS -------- */
const allMappings: Record<number, { title: string; badge: string; badgeType: 'high' | 'medium' | 'low'; conditions: MappingCondition[] }> = {
  0: { title: '信号触发 — 实体属性映射', badge: '信号层', badgeType: 'low', conditions: [
    { condition: '携转资格查询发生', sourceEntity: 'MnpEligibilityQuery', sourceAttribute: 'query_time', operator: 'IS NOT NULL', threshold: '-' },
    { condition: '用户状态为在网', sourceEntity: 'CbssSubscriber', sourceAttribute: 'user_status', operator: '=', threshold: '在网' },
  ]},
  1: { title: '本体数据拉取 — 实体属性映射', badge: '聚合层', badgeType: 'medium', conditions: [
    { condition: '用户基础信息', sourceEntity: 'CbssSubscriber', sourceAttribute: 'innet_months, is_5g, pay_mode', operator: '全量拉取', threshold: '-' },
    { condition: '合约信息', sourceEntity: 'SubscriberContract', sourceAttribute: 'end_date, protocal_month', operator: '全量拉取', threshold: '-' },
    { condition: '投诉记录', sourceEntity: 'CustomerComplaint', sourceAttribute: 'complaint_type, complaint_count_3m', operator: '全量拉取', threshold: '-' },
    { condition: '网络质量', sourceEntity: 'NetworkQuality', sourceAttribute: 'avg_download_speed, coverage_score', operator: '全量拉取', threshold: '-' },
    { condition: '竞品活动', sourceEntity: 'CompetitorActivity', sourceAttribute: 'offer_type, price_advantage', operator: '全量拉取', threshold: '-' },
    { condition: '家庭关系', sourceEntity: 'FamilyGroup', sourceAttribute: 'member_count, ported_member_count', operator: '全量拉取', threshold: '-' },
  ]},
  2: { title: '规则匹配校验 — 实体属性映射', badge: '高风险规则', badgeType: 'high', conditions: [
    { condition: '在网时长 ≤ 24月', sourceEntity: 'CbssSubscriber', sourceAttribute: 'innet_months', operator: '≤', threshold: '24' },
    { condition: '合约到期 ≤ 3月', sourceEntity: 'SubscriberContract', sourceAttribute: 'end_date', operator: '≤ 当前+3月', threshold: '90天' },
    { condition: '近3月投诉 ≥ 2次', sourceEntity: 'CustomerComplaint', sourceAttribute: 'complaint_count_3m', operator: '≥', threshold: '2' },
    { condition: '竞品查询 ≥ 3次', sourceEntity: 'CompetitorActivity', sourceAttribute: 'query_count', operator: '≥', threshold: '3' },
    { condition: '家庭已携转成员 ≥ 1', sourceEntity: 'FamilyGroup', sourceAttribute: 'ported_member_count', operator: '≥', threshold: '1' },
  ]},
  3: { title: '风险等级定级 — 实体属性映射', badge: '定级', badgeType: 'high', conditions: [
    { condition: '规则匹配结果', sourceEntity: 'MnpRiskUser', sourceAttribute: 'matched_rule_id', operator: '匹配', threshold: 'H01/M01/L01' },
    { condition: '条件通过数', sourceEntity: 'MnpRiskUser', sourceAttribute: 'condition_pass_count', operator: '≥ 阈值', threshold: '按规则定义' },
  ]},
  4: { title: '流失根因拆解 — 实体属性映射', badge: '根因', badgeType: 'medium', conditions: [
    { condition: '合约即将到期', sourceEntity: 'SubscriberContract', sourceAttribute: 'end_date', operator: '≤ 当前+3月', threshold: '90天' },
    { condition: '投诉未解决', sourceEntity: 'CustomerComplaint', sourceAttribute: 'complaint_type', operator: '包含', threshold: '网络/资费/服务' },
    { condition: '网络体验差', sourceEntity: 'NetworkQuality', sourceAttribute: 'avg_download_speed', operator: '<', threshold: '50Mbps' },
    { condition: '竞品价格优势', sourceEntity: 'CompetitorActivity', sourceAttribute: 'price_advantage', operator: '>', threshold: '20%' },
    { condition: '家庭成员已携转', sourceEntity: 'FamilyGroup', sourceAttribute: 'ported_member_count', operator: '≥', threshold: '1' },
  ]},
  5: { title: '动作推荐生成 — 实体属性映射', badge: '推荐', badgeType: 'low', conditions: [
    { condition: '风险等级', sourceEntity: 'MnpRiskUser', sourceAttribute: 'risk_level', operator: '=', threshold: 'HIGH/MEDIUM/LOW' },
    { condition: '流失根因', sourceEntity: 'MnpRiskUser', sourceAttribute: 'churn_reason_top3', operator: '匹配动作库', threshold: '-' },
    { condition: '付费模式', sourceEntity: 'CbssSubscriber', sourceAttribute: 'pay_mode', operator: '决定优惠类型', threshold: '-' },
    { condition: '合约类型', sourceEntity: 'SubscriberContract', sourceAttribute: 'activity_type', operator: '决定升级方案', threshold: '-' },
  ]},
  6: { title: '任务自动分发 — 实体属性映射', badge: '分发', badgeType: 'low', conditions: [
    { condition: '风险等级决定通道', sourceEntity: 'MnpRiskUser', sourceAttribute: 'risk_level', operator: '映射', threshold: '高→坐席/中→外呼/低→短信' },
    { condition: '推荐动作列表', sourceEntity: 'MnpRiskUser', sourceAttribute: 'recommended_actions', operator: '生成任务', threshold: '-' },
  ]},
}
const mappingTitle = computed(() => (allMappings[activeStep.value] || allMappings[0]).title)
const mappingBadge = computed(() => (allMappings[activeStep.value] || allMappings[0]).badge)
const mappingBadgeType = computed(() => (allMappings[activeStep.value] || allMappings[0]).badgeType)
const mappingConditions = computed<MappingCondition[]>(() => {
  const base = (allMappings[activeStep.value] || allMappings[0]).conditions
  const user = selectedUser.value
  // For stage 2 (规则匹配校验), inject from ruleResults
  if (activeStep.value === 2) {
    const highRule = user.ruleResults.find(r => r.riskLevel === 'high')
    if (highRule) return highRule.conditions.map(c => ({ ...c }))
  }
  // For other stages, try to resolve actual values from entity data
  return base.map(c => {
    const entityData = user.entities[c.sourceEntity]
    if (!entityData) return c
    const attrs = c.sourceAttribute.split(',').map(a => a.trim())
    if (attrs.length === 1) {
      const val = entityData[attrs[0]]
      if (val !== undefined) return { ...c, actualValue: String(val), matched: c.operator === '全量拉取' ? undefined : undefined }
    } else {
      const vals = attrs.map(a => entityData[a]).filter(v => v !== undefined)
      if (vals.length) return { ...c, actualValue: vals.join(', ') }
    }
    return c
  })
})

/* -------- ACTION DRIVERS -------- */
const actionDrivers = computed<ActionDriver[]>(() => {
  const user = selectedUser.value
  const isRecommended = (name: string) => user.recommendedActions.includes(name)

  if (activeStep.value === 5) return [
    { actionName: '发送专属优惠', basis: '用户ARPU水平 + 合约到期时间', recommended: isRecommended('发送专属优惠'), drivenBy: [
      { entity: 'CbssSubscriber', attribute: 'pay_mode', reason: '决定优惠券面额' },
      { entity: 'SubscriberContract', attribute: 'end_date', reason: '合约即将到期时优先推送' },
    ]},
    { actionName: '套餐升级推荐', basis: '当前套餐 + 5G终端状态', recommended: isRecommended('套餐升级推荐'), drivenBy: [
      { entity: 'CbssSubscriber', attribute: 'is_5g', reason: '5G用户推荐5G套餐' },
      { entity: 'SubscriberContract', attribute: 'activity_type', reason: '匹配升级路径' },
    ]},
    { actionName: '网络质量优化', basis: '网络体验指标 + 投诉类型', recommended: isRecommended('网络质量优化'), drivenBy: [
      { entity: 'NetworkQuality', attribute: 'avg_download_speed', reason: '速率低于阈值触发优化' },
      { entity: 'CustomerComplaint', attribute: 'complaint_type', reason: '网络类投诉优先处理' },
    ]},
    { actionName: '一键外呼关怀', basis: '风险等级 + 家庭关系', recommended: isRecommended('一键外呼关怀'), drivenBy: [
      { entity: 'MnpRiskUser', attribute: 'risk_level', reason: '高风险用户优先外呼' },
      { entity: 'FamilyGroup', attribute: 'ported_member_count', reason: '家庭传导风险需重点关怀' },
    ]},
    { actionName: '一键发送挽留短信', basis: '风险等级 + 用户偏好', recommended: isRecommended('一键发送挽留短信'), drivenBy: [
      { entity: 'MnpRiskUser', attribute: 'risk_level', reason: '所有风险等级均可触达' },
    ]},
    { actionName: '一键下发产品', basis: '用户套餐 + 竞品分析', recommended: isRecommended('一键下发产品'), drivenBy: [
      { entity: 'CompetitorActivity', attribute: 'offer_type', reason: '针对竞品优惠匹配产品' },
    ]},
  ]
  if (activeStep.value === 6) {
    const channelMap: Record<string, string> = { '专属坐席': '高风险→专属坐席', '自动外呼': '中风险→自动外呼', '短信触达': '低风险→短信触达' }
    return [
      { actionName: '高风险→专属坐席', basis: '风险等级为HIGH', recommended: user.assignedChannel === '专属坐席', drivenBy: [{ entity: 'MnpRiskUser', attribute: 'risk_level', reason: '高风险需人工专属跟进' }] },
      { actionName: '中风险→自动外呼', basis: '风险等级为MEDIUM', recommended: user.assignedChannel === '自动外呼', drivenBy: [{ entity: 'MnpRiskUser', attribute: 'risk_level', reason: '中风险通过IVR自动外呼' }] },
      { actionName: '低风险→短信触达', basis: '风险等级为LOW', recommended: user.assignedChannel === '短信触达', drivenBy: [{ entity: 'MnpRiskUser', attribute: 'risk_level', reason: '低风险通过短信批量触达' }] },
    ]
  }
  return [
    { actionName: '信号识别', basis: '携转资格查询实体触发', drivenBy: [{ entity: 'MnpEligibilityQuery', attribute: 'query_time', reason: '查询发生即触发信号' }] },
    { actionName: '规则校验', basis: '多实体属性交叉校验', drivenBy: [
      { entity: 'CbssSubscriber', attribute: 'innet_months', reason: '在网时长条件' },
      { entity: 'CustomerComplaint', attribute: 'complaint_count_3m', reason: '投诉频次条件' },
    ]},
    { actionName: '维系执行', basis: '根因驱动个性化方案', drivenBy: [{ entity: 'MnpRiskUser', attribute: 'churn_reason_top3', reason: '根因决定维系策略' }] },
  ]
})
</script>

<style scoped>
.mnp-page { display: flex; flex-direction: column; height: 100%; background: var(--neutral-50, #f8f9fa); }
.mnp-page__header { padding: 20px 24px 0; }
.mnp-page__title-row { display: flex; align-items: center; gap: 16px; }
.mnp-page__icon { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; background: #fa5252; }
.mnp-page__title { font-size: 20px; font-weight: 700; color: #212529; margin: 0; }
.mnp-page__desc { font-size: 12px; color: #868e96; margin: 4px 0 0; }

.mnp-kpis { display: flex; gap: 10px; padding: 16px 24px 0; }
.kpi-card { flex: 1; padding: 12px 14px; border-radius: 10px; background: #fff; border: 1px solid #e9ecef; }
.kpi-val { font-size: 24px; font-weight: 700; line-height: 1; color: #4c6ef5; }
.kpi-lbl { font-size: 11px; color: #868e96; margin-top: 3px; }

.mnp-layers { display: flex; gap: 10px; padding: 12px 24px; }
.layer-band { flex: 1; padding: 10px 12px; border-radius: 10px; border: 1px solid #e9ecef; }
.layer-band--signal { background: linear-gradient(135deg, #e7f5ff 0%, #fff 100%); border-left: 3px solid #339af0; }
.layer-band--aggregate { background: linear-gradient(135deg, #fff8e1 0%, #fff 100%); border-left: 3px solid #f59f00; }
.layer-band--decision { background: linear-gradient(135deg, #f3f0ff 0%, #fff 100%); border-left: 3px solid #7950f2; }
.layer-band__head { font-size: 13px; color: #343a40; margin-bottom: 2px; }
.layer-band__stats { display: flex; gap: 10px; font-size: 11px; color: #868e96; }

.mnp-body { display: flex; flex: 1; overflow: hidden; padding: 0 24px 24px; gap: 14px; }
.mnp-left { width: 380px; flex-shrink: 0; overflow-y: auto; }
.mnp-right { flex: 1; display: flex; flex-direction: column; gap: 12px; overflow-y: auto; }

.stage-desc-card { background: #fff; border-radius: 10px; border: 1px solid #e9ecef; padding: 14px 16px; }
.stage-desc__header { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.stage-desc__name { font-size: 16px; font-weight: 700; color: #212529; }
.stage-desc__layer { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; }
.layer-tag--signal { background: #e7f5ff; color: #1c7ed6; }
.layer-tag--aggregate { background: #fff8e1; color: #e67700; }
.layer-tag--decision { background: #f3f0ff; color: #7048e8; }
.stage-desc__text { font-size: 13px; color: #495057; line-height: 1.6; }

/* 案例用户选择条 */
.mnp-user-bar { display: flex; align-items: center; gap: 12px; padding: 0 24px 4px; }
.user-bar__label { font-size: 12px; font-weight: 600; color: #868e96; white-space: nowrap; }
.user-bar__cards { display: flex; gap: 10px; flex: 1; }
.user-mini-card { display: flex; align-items: center; gap: 10px; padding: 8px 14px; border-radius: 10px; background: #fff; border: 2px solid #e9ecef; cursor: pointer; transition: all 0.2s; flex: 1; }
.user-mini-card:hover { border-color: #a5d8ff; }
.user-mini-card--active { border-color: #4c6ef5; background: #f8f9ff; }
.user-mini__avatar { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 700; color: #fff; flex-shrink: 0; }
.avatar--high { background: #fa5252; }
.avatar--medium { background: #f59f00; }
.avatar--low { background: #339af0; }
.user-mini__info { flex: 1; min-width: 0; }
.user-mini__name { font-size: 13px; font-weight: 600; color: #212529; }
.user-mini__phone { font-size: 11px; color: #868e96; font-family: monospace; }
.user-mini__risk { font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 4px; white-space: nowrap; }
.risk--high { background: #fff5f5; color: #fa5252; }
.risk--medium { background: #fff8e1; color: #f59f00; }
.risk--low { background: #e7f5ff; color: #339af0; }
.user-mini__score { font-size: 12px; font-weight: 700; color: #495057; white-space: nowrap; }
.user-bar__loading { font-size: 11px; color: #4c6ef5; white-space: nowrap; animation: fadeInOut 1.2s ease-in-out infinite; }
.user-bar__error { font-size: 11px; color: #fa5252; white-space: nowrap; }
@keyframes fadeInOut { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

/* 阶段执行结果摘要 */
.stage-result-card { background: #fff; border-radius: 10px; border: 1px solid #e9ecef; border-left: 3px solid #12b886; padding: 14px 16px; }
.stage-result__header { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.stage-result__icon { color: #12b886; font-size: 10px; }
.stage-result__title { font-size: 13px; font-weight: 600; color: #343a40; }
.stage-result__body { display: flex; flex-direction: column; gap: 6px; }
.result-row { display: flex; align-items: center; justify-content: space-between; font-size: 12px; padding: 4px 0; }
.result-label { color: #868e96; }
.result-value { color: #212529; font-weight: 500; }
.result-value--bold { font-size: 18px; font-weight: 700; color: #4c6ef5; }
.result-match { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; }
.match--yes { background: #e6fcf5; color: #0ca678; }
.match--partial { background: #fff8e1; color: #e67700; }
.risk-badge { font-size: 12px; font-weight: 700; padding: 2px 10px; border-radius: 4px; }
.result-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }
.reason-tag { font-size: 12px; padding: 4px 10px; border-radius: 6px; background: #fff8e1; color: #e67700; font-weight: 500; }
.action-tag { font-size: 12px; padding: 4px 10px; border-radius: 6px; background: #e6fcf5; color: #0ca678; font-weight: 500; }
.status-tag { font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 4px; background: #e6fcf5; color: #0ca678; }
</style>
