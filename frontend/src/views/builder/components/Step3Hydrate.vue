<template>
  <div class="step3">
    <header class="step3-topbar">
      <button class="ob-back-btn" @click="$emit('prev')">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M9 11L5 7l4-4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        返回
      </button>
      <div class="step3-topbar__title">水合演练 · 本体发布</div>
      <div class="step3-topbar__sub">数据接入 · C05 端到端验证 · 版本冻结</div>
    </header>

    <!-- 演练成功大屏 -->
    <div v-if="success" class="step3-success">
      <div class="step3-success__hero">🎉</div>
      <div class="step3-success__title">{{ session.buildMethod === 'upload' ? '导入成功' : '发布成功' }}</div>
      <div class="step3-success__sub">{{ session.ontologyName }} 已发布至本体工作室</div>

      <div class="step3-success__stats">
        <div class="step3-success-stat">
          <div class="num">{{ session.ontologyClasses.length }}</div>
          <div class="label">本体</div>
        </div>
        <div class="step3-success-stat">
          <div class="num">{{ session.ontologyRelations.length }}</div>
          <div class="label">关系</div>
        </div>
        <div class="step3-success-stat">
          <div class="num">{{ session.ontologyClasses.length }}</div>
          <div class="label">走测节点</div>
        </div>
        <div class="step3-success-stat">
          <div class="num">{{ drillResult?.entityCount?.toLocaleString() || 0 }}</div>
          <div class="label">演练成功数</div>
        </div>
      </div>

      <div class="step3-success__cta">
        <a-button type="primary" size="large" @click="$emit('goto-studio')">→ 前往本体工作室查看</a-button>
        <a-button size="large" @click="success = false">留在构建器</a-button>
      </div>
      <div class="step3-success__count">{{ countdown }} 秒后自动跳转...</div>
    </div>

    <div v-else class="step3-body">
      <!-- 中央演练区 -->
      <div class="step3-center">
        <div class="step3-panel step3-panel--phases" v-if="drillStarted">
          <div class="step3-drilling__header">
            <span class="dot"></span>
            <span>{{ drillStatus === 'pass' ? '✅ 演练完成' : drillStatus === 'warn' ? '⚠️ 演练完成 · 存在警告' : drillStatus === 'error' ? '❌ 演练失败' : '⏳ 演练进行中' }}</span>
            <span class="step3-drill-elapsed">{{ drillElapsed }}s</span>
          </div>
          <div class="step3-phases">
            <div
              v-for="(p, i) in HYDRATION_PHASES"
              :key="p.key"
              class="step3-phase-pill"
              :class="{ active: drillProgress >= (i + 1) / HYDRATION_PHASES.length, done: drillProgress >= (i + 1) / HYDRATION_PHASES.length }"
              :style="{ borderColor: p.color }"
            >
              <span class="phase-idx" :style="{ background: p.color }">{{ i + 1 }}</span>
              <span class="phase-label">{{ p.label }}</span>
            </div>
          </div>
          <div class="step3-progress-bar">
            <div class="step3-progress-fill" :style="{ width: drillProgress * 100 + '%' }"></div>
          </div>

          <div class="step3-log">
            <div class="step3-log__head">
              <span class="dot red"></span><span class="dot yellow"></span><span class="dot green"></span>
              <span class="step3-log__title">hydration.log · 演练耗时 {{ drillElapsed }}s</span>
            </div>
            <div class="step3-log__body" ref="logBodyRef">
              <div v-for="(l, i) in drillLogs" :key="i" class="step3-log__line">
                <span class="log-ts">[{{ l.ts }}]</span>
                <span class="log-lvl" :class="`log-lvl--${l.level.toLowerCase()}`">{{ l.level }}</span>
                <span class="log-msg">{{ l.msg }}</span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="drillResult" class="step3-drill-result">
          <div class="step3-result-banner" :class="`step3-result-banner--${drillStatus}`">
            <span class="step3-result-banner__icon">
              {{ drillStatus === 'pass' ? '✅' : drillStatus === 'warn' ? '⚠️' : '❌' }}
            </span>
            <div>
              <div class="step3-result-banner__title">
                {{ drillStatus === 'pass' ? '演练完成 · 全部通过 · 用时 ' + drillElapsed + ' 秒' : drillStatus === 'warn' ? '演练完成 · 存在警告 · 建议人工确认后发布' : '演练失败 · 请修复错误后重新演练' }}
              </div>
              <div class="step3-result-banner__sub">
                字段映射 100% · 关系映射 {{ relationAccuracy }}% · 数据总条数 {{ drillResult.entityCount.toLocaleString() }}
              </div>
            </div>
          </div>

          <div class="step3-phase-cards">
            <div v-for="p in drillResult.phases" :key="p.key" class="step3-phase-card">
              <div class="step3-phase-card__head">
                <span class="phase-card-idx" :style="{ background: phaseColor(p.key) }"></span>
                <span class="phase-card-name">{{ p.label }}</span>
                <span class="phase-card-status" :class="`phase-card-status--${p.status}`">
                  {{ p.status === 'pass' ? '已通过' : p.status === 'warn' ? '存在警告' : p.status === 'error' ? '失败' : '进行中' }}
                </span>
              </div>
              <div class="step3-phase-card__metrics">
                <div v-for="m in p.metrics" :key="m.label" class="phase-metric">
                  <div class="phase-metric__val" :class="m.tone ? `phase-metric__val--${m.tone}` : ''">{{ m.value }}</div>
                  <div class="phase-metric__label">{{ m.label }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="step3-drill-hint">
            ✅ 完成水合，下一步：本体发布
          </div>
        </div>

        <div v-else-if="!drillStarted" class="step3-pre-drill">
          <div class="step3-panel">
            <div class="step3-panel__title">📦 数据源选择</div>
            <div class="step3-data-source-card">
              <div class="step3-data-source-list">
                <label
                  v-for="ds in SAMPLE_DATA_SOURCES"
                  :key="ds.id"
                  class="step3-data-source-item"
                  :class="{ 'step3-data-source-item--selected': selectedSourceIds.includes(ds.id) }"
                >
                  <input
                    type="checkbox"
                    :value="ds.id"
                    v-model="selectedSourceIds"
                  />
                  <div class="ds-main">
                    <div class="ds-name">{{ ds.fileName }}</div>
                    <div class="ds-meta">{{ ds.rows }} 行 × {{ ds.columns }} 列 · {{ ds.system }}<span v-if="ds.targetClass"> · 映射 {{ ds.targetClass }}</span></div>
                  </div>
                </label>
              </div>
              <div class="step3-data-source-tip" v-if="!selectedSourceIds.length">请至少选择 1 张样例表后再开始演练。</div>
              <button
                class="step3-drill-btn"
                :disabled="selectedSourceIds.length === 0"
                @click="startDrill"
              >
                🚀 开始演练
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：发布面板 -->
      <aside class="step3-right">
        <div class="step3-panel">
          <div class="step3-panel__title">✅ 准备状态核查</div>
          <div class="step3-gates">
            <div v-for="g in gates" :key="g.key" class="step3-gate">
              <span class="step3-gate__icon" :class="{ pass: g.pass }">
                {{ g.pass ? '✓' : '○' }}
              </span>
              <div>
                <div class="step3-gate__label">{{ g.label }}</div>
                <div class="step3-gate__desc">{{ g.desc }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="step3-panel">
          <div class="step3-panel__title">📊 版本快照预览</div>
          <a-descriptions size="small" :column="1" bordered>
            <a-descriptions-item label="版本号">{{ versionLabel }}</a-descriptions-item>
            <a-descriptions-item label="冻结时间">{{ frozenAt }}</a-descriptions-item>
            <a-descriptions-item label="对象总数">{{ session.ontologyClasses.length }}</a-descriptions-item>
            <a-descriptions-item label="关系总数">{{ session.ontologyRelations.length }}</a-descriptions-item>
            <a-descriptions-item label="构建路径">{{ session.buildMethod === 'ai' ? '路径A 场景对话驱动' : '路径B 已有本体导入' }}</a-descriptions-item>
            <a-descriptions-item label="水合状态">{{ drillStatus ? '已演练' : '未演练' }}</a-descriptions-item>
          </a-descriptions>
        </div>

        <div class="step3-panel">
          <div class="step3-panel__title">🤝 消费方对接</div>
          <a-table
            :columns="consumerColumns"
            :data-source="CONSUMER_TARGETS"
            :pagination="false"
            size="small"
            row-key="name"
          />
        </div>

        <div class="step3-panel">
          <div class="step3-panel__title">🚀 发布后监控指标（基线）</div>
          <div class="step3-baseline-grid">
            <div v-for="b in baselines" :key="b.label" class="step3-baseline-card" :class="`step3-baseline-card--${b.level}`">
              <div class="bv">{{ b.value }}</div>
              <div class="bl">{{ b.label }}</div>
              <div class="bt">{{ b.target }}</div>
            </div>
          </div>
        </div>

        <div class="step3-panel">
          <div class="step3-panel__title">↩️ 回滚方案</div>
          <div class="step3-rollback">
            <div class="rollback-target">回滚目标：v0.0</div>
            <div class="rollback-text">{{ rollbackText }}</div>
            <div class="rollback-rules">
              <div v-for="(r, i) in rollbackRules" :key="i" class="rollback-rule">{{ r }}</div>
            </div>
          </div>
        </div>

        <button
          class="step3-publish-btn"
          :disabled="!canPublish"
          @click="publishModalOpen = true"
        >
          🚀 发布至本体工作室
        </button>
      </aside>
    </div>

    <!-- 发布弹窗 -->
    <a-modal v-model:open="publishModalOpen" :footer="null" :width="560" class="step3-publish-modal">
      <div class="step3-modal-content">
        <div class="step3-modal-title">确认发布 · {{ versionLabel }} {{ session.scenarioName }}</div>
        <div class="step3-modal-text">
          首次发布：{{ versionLabel }} {{ session.scenarioName }}，包含
          <strong>{{ session.ontologyClasses.length }}</strong> 个本体、
          <strong>{{ session.ontologyRelations.length }}</strong> 条关系，
          <strong>{{ session.ontologyClasses.length }}</strong> 个走测节点全部通过
        </div>
        <div class="step3-modal-stats">
          <div><span>归因准确率：</span><strong>{{ baselines[0]?.value || '94.6%' }}</strong></div>
          <div><span>水合实体：</span><strong>{{ drillResult?.entityCount?.toLocaleString() || 0 }}</strong></div>
          <div><span>关系实例：</span><strong>{{ drillResult?.relationCount?.toLocaleString() || 0 }}</strong></div>
        </div>
        <div v-if="drillStatus === 'warn'" class="step3-warn-radio">
          <a-radio-group v-model:value="warnAction">
            <a-radio value="ignore">忽略警告，继续发布</a-radio>
            <a-radio value="rollback">退回重新演练</a-radio>
          </a-radio-group>
        </div>
        <div class="step3-modal-actions">
          <a-button @click="publishModalOpen = false">取消</a-button>
          <a-button type="primary" :loading="publishing" @click="confirmPublish">🚀 确认发布</a-button>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useBuilderStore } from '../../../store/builder'
import {
  HYDRATION_PHASES,
  SAMPLE_DATA_SOURCES,
  CONSUMER_TARGETS,
  MONITORING_BASELINES,
  DEFAULT_PUBLISH_GATES,
} from '../../../data/builderPresets'
import type { BuilderSession, DrillLogLine, DrillPhase, DrillResult, PublishGate } from '../../../types/builder'

const props = defineProps<{ session: BuilderSession }>()
defineEmits<{ (e: 'prev'): void; (e: 'goto-studio'): void }>()
const store = useBuilderStore()

const drillStarted = ref(!!props.session.drillResult)
const drillProgress = ref(props.session.drillResult ? 1 : 0)
const drillStatus = ref<'pass' | 'warn' | 'error' | undefined>(props.session.drillStatus)
const drillLogs = ref<DrillLogLine[]>([])
const drillElapsed = ref(0)
const drillResult = ref<DrillResult | null>(props.session.drillResult || null)
const selectedSourceIds = ref<string[]>(props.session.selectedSampleSourceIds.length ? props.session.selectedSampleSourceIds : SAMPLE_DATA_SOURCES.slice(0, 4).map(d => d.id))
const publishModalOpen = ref(false)
const publishing = ref(false)
const warnAction = ref<'ignore' | 'rollback'>('ignore')
const success = ref(props.session.status === 'published')
const countdown = ref(8)
const logBodyRef = ref<HTMLElement | null>(null)
let countdownTimer: number | null = null
let drillTimer: number | null = null

const versionLabel = computed(() => props.session.publishedVersion || 'v0.1')
const frozenAt = computed(() => {
  const d = new Date(props.session.publishedAt || new Date().toISOString())
  return d.toLocaleString('zh-CN')
})

const baselines = computed(() => MONITORING_BASELINES[props.session.scenarioId] || MONITORING_BASELINES['refund-root-cause'])
const relationAccuracy = computed(() => drillStatus.value === 'pass' ? '98.2' : drillStatus.value === 'warn' ? '92.4' : '0')

const consumerColumns = [
  { title: '消费方', dataIndex: 'name' },
  { title: '使用方式', dataIndex: 'usage' },
  { title: '状态', dataIndex: 'status' },
]

const rollbackText = computed(() =>
  props.session.scenarioId === 'fttr-renewal'
    ? '首发版本，回滚到 schema-only 模式'
    : '首发版本，无历史快照（默认回退到本体水合前草稿）',
)
const rollbackRules = computed(() => {
  const id = props.session.scenarioId
  if (id === 'enterprise-qa') return [
    '· 问数命中率跌破 90% → 产品经理 + 架构师决策，2 小时内回滚',
    '· 推理成功率 < 90% → 数据工程师决策，1 小时内回滚',
    '· 本体查询持续 > 1s → 技术开发决策，30 分钟内回滚',
  ]
  if (id === 'fttr-renewal') return [
    '· 转化率跌破 0.5% → 产品经理 + 架构师决策，2 小时内回滚',
    '· 触达成功率跌破 75% → 运营负责人决策，2 小时内回滚',
    '· 回访覆盖率跌破 80% → 运营负责人决策，1 小时内回滚',
  ]
  return [
    '· 归因准确率跌破 85% → 产品经理 + 架构师决策，2 小时内回滚',
    '· 根因解释覆盖率跌破 85% → 业务负责人决策，1 小时内回滚',
    '· 回访覆盖率跌破 80% → 运营负责人决策，1 小时内回滚',
  ]
})

const gates = computed<PublishGate[]>(() => {
  const list: PublishGate[] = JSON.parse(JSON.stringify(DEFAULT_PUBLISH_GATES))
  const classCount = props.session.ontologyClasses.length
  const approvedCount = props.session.ontologyClasses.filter(c => c.approved).length
  list[0] = { ...list[0], desc: `本体 ${classCount} 个`, pass: classCount > 0 }
  list[1] = { ...list[1], desc: `通过节点 ${approvedCount} / ${classCount}`, pass: classCount > 0 && approvedCount === classCount }
  list[2] = { ...list[2], desc: `实体 ${drillResult.value?.entityCount?.toLocaleString() || 0} · 关系 ${drillResult.value?.relationCount?.toLocaleString() || 0}`, pass: !!drillResult.value && drillStatus.value !== 'error' }
  list[3] = { ...list[3], pass: !!drillResult.value }
  list[4] = { ...list[4], pass: props.session.reviewLog.length > 0 }
  list[5] = { ...list[5], pass: classCount > 0 }
  list[6] = { ...list[6], pass: true }
  return list
})

const canPublish = computed(() => gates.value.every(g => g.pass))

function phaseColor(key: string) {
  return HYDRATION_PHASES.find(p => p.key === key)?.color || '#6366f1'
}

function nowStamp() {
  const d = new Date()
  return [d.getHours(), d.getMinutes(), d.getSeconds()].map(n => String(n).padStart(2, '0')).join(':')
}
function pushLog(level: 'OK' | 'RUN' | 'ERR', msg: string) {
  drillLogs.value.push({ ts: nowStamp(), level, msg })
  nextTick(() => {
    if (logBodyRef.value) logBodyRef.value.scrollTop = logBodyRef.value.scrollHeight
  })
}

async function startDrill() {
  if (selectedSourceIds.value.length === 0) {
    message.warning('请至少选择 1 张样例表后再开始演练。')
    return
  }
  drillStarted.value = true
  drillProgress.value = 0
  drillLogs.value = []
  drillElapsed.value = 0
  drillStatus.value = undefined
  drillResult.value = null
  store.setStatus('hydrating')
  if (drillTimer) clearInterval(drillTimer)
  drillTimer = window.setInterval(() => drillElapsed.value++, 1000)

  const sources = SAMPLE_DATA_SOURCES.filter(d => selectedSourceIds.value.includes(d.id))
  const totalRows = sources.reduce((s, d) => s + d.rows, 0)
  const totalCols = sources.reduce((s, d) => s + d.columns, 0)

  // 阶段 1：数据接入
  pushLog('RUN', `准备装载 ${sources.length} 张样例表...`)
  for (const ds of sources) {
    await sleep(280)
    pushLog('OK', `装载 ${ds.fileName.split(' / ').pop()}：${ds.rows} 条样例 / ${ds.columns} 列`)
  }
  drillProgress.value = 0.25

  // 阶段 2：实例化
  pushLog('RUN', `字段映射检查：${totalCols}/${totalCols} 字段全部命中`)
  for (const c of props.session.ontologyClasses.slice(0, 4)) {
    await sleep(280)
    pushLog('OK', `创建 ${c.displayName} 实例 × ${Math.round(totalRows / 4).toLocaleString()}...`)
  }
  drillProgress.value = 0.5

  // 阶段 3：关系映射
  pushLog('RUN', `关系映射：${props.session.ontologyRelations.length} 种关系类型实例化`)
  await sleep(600)
  pushLog('OK', `关系映射验证完成：${props.session.ontologyRelations.length} 关系全部命中`)
  drillProgress.value = 0.75

  // 阶段 4：策略输出
  for (const c of props.session.ontologyClasses.slice(0, 2)) {
    await sleep(260)
    pushLog('RUN', `执行规则：${c.name}_validation（结构验证）...`)
    await sleep(220)
    pushLog('OK', `${c.displayName} 规则通过率 98.2%`)
  }
  await sleep(300)
  pushLog('OK', '生成样例归因结果：高置信 184 条，人工复核 23 条')
  drillProgress.value = 1

  if (drillTimer) clearInterval(drillTimer)
  drillStatus.value = 'pass'

  const phases: DrillPhase[] = [
    {
      key: 'ingest', label: '数据接入', status: 'pass',
      metrics: [
        { label: '装载行数', value: totalRows.toLocaleString() },
        { label: '装载列数', value: totalCols.toLocaleString() },
        { label: '装载耗时', value: drillElapsed.value + 's' },
      ],
    },
    {
      key: 'instantiate', label: '本体实例化', status: 'pass',
      metrics: [
        { label: '实体实例数', value: totalRows.toLocaleString(), tone: 'pass' },
        { label: '字段映射准确率', value: '100%', tone: 'pass' },
        { label: '映射耗时', value: '4.2s' },
      ],
    },
    {
      key: 'match', label: '关系映射验证', status: 'pass',
      metrics: [
        { label: '关系实例数', value: (props.session.ontologyRelations.length * Math.round(totalRows * 1.5)).toLocaleString() },
        { label: '关系映射准确率', value: '98.2%', tone: 'pass' },
        { label: '匹配覆盖率', value: '94.6%', tone: 'pass' },
      ],
    },
    {
      key: 'strategy', label: '策略输出', status: 'pass',
      metrics: [
        { label: '规则执行成功率', value: '100%', tone: 'pass' },
        { label: '高置信归因', value: '184 条', tone: 'pass' },
        { label: '人工复核', value: '23 条', tone: 'warn' },
      ],
    },
  ]
  drillResult.value = {
    phases,
    logs: drillLogs.value,
    selectedRows: totalRows,
    selectedColumns: totalCols,
    selectedSources: sources.length,
    entityCount: totalRows,
    relationCount: props.session.ontologyRelations.length * Math.round(totalRows * 1.5),
    attributionAccuracy: '94.6%',
    highConfidenceAttribution: 184,
    manualReview: 23,
  }
  store.patchActive({
    drillStatus: 'pass',
    drillResult: drillResult.value,
    selectedSampleSourceIds: selectedSourceIds.value,
    status: 'pending_publish',
  })
  message.success('水合演练完成')
}

function sleep(ms: number) {
  return new Promise(r => setTimeout(r, ms))
}

async function confirmPublish() {
  if (warnAction.value === 'rollback') {
    publishModalOpen.value = false
    drillStarted.value = false
    drillResult.value = null
    return
  }
  publishing.value = true
  store.setStatus('publishing')
  await sleep(1200)
  const version = props.session.publishedVersion || 'v0.1'
  store.patchActive({
    status: 'published',
    publishedVersion: version,
    publishedAt: new Date().toISOString(),
  })
  publishing.value = false
  publishModalOpen.value = false
  success.value = true
  startCountdown()
}

function startCountdown() {
  countdown.value = 8
  if (countdownTimer) clearInterval(countdownTimer)
  countdownTimer = window.setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      if (countdownTimer) clearInterval(countdownTimer)
    }
  }, 1000)
}

watch(() => props.session.sessionId, () => {
  drillStarted.value = !!props.session.drillResult
  drillResult.value = props.session.drillResult || null
  drillStatus.value = props.session.drillStatus
  drillProgress.value = props.session.drillResult ? 1 : 0
  selectedSourceIds.value = props.session.selectedSampleSourceIds.length ? [...props.session.selectedSampleSourceIds] : SAMPLE_DATA_SOURCES.slice(0, 4).map(d => d.id)
  success.value = props.session.status === 'published'
})

onUnmounted(() => {
  if (drillTimer) clearInterval(drillTimer)
  if (countdownTimer) clearInterval(countdownTimer)
})
</script>

<style scoped>
.step3 { display: flex; flex-direction: column; height: calc(100vh - 64px - 56px - 76px); background: #f1f5f9; }
.step3-topbar {
  display: flex; align-items: center; gap: 16px;
  padding: 12px 20px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
}
.ob-back-btn {
  display: inline-flex; align-items: center; gap: 6px;
  background: transparent; border: 0; padding: 4px 10px;
  border-radius: 6px; color: #475569; font-size: 12px; cursor: pointer;
}
.ob-back-btn:hover { background: #f1f5f9; color: #0f172a; }
.step3-topbar__title { font-size: 14px; font-weight: 600; color: #0f172a; }
.step3-topbar__sub { font-size: 11px; color: #94a3b8; flex: 1; }

.step3-body {
  flex: 1; overflow: auto;
  display: grid; grid-template-columns: 1fr 380px;
  gap: 16px; padding: 16px;
}
.step3-center { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.step3-right { display: flex; flex-direction: column; gap: 12px; }

.step3-panel {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px 16px;
}
.step3-panel__title {
  font-size: 13px; font-weight: 600; color: #0f172a;
  margin-bottom: 10px;
}

/* 演练前数据源选择 */
.step3-data-source-list { max-height: 380px; overflow-y: auto; }
.step3-data-source-item {
  display: flex; gap: 10px; align-items: flex-start;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid transparent;
  cursor: pointer;
  margin-bottom: 4px;
  transition: all 150ms ease;
}
.step3-data-source-item:hover { background: #f8fafc; }
.step3-data-source-item--selected { background: rgba(79, 70, 229, 0.04); border-color: #4f46e5; }
.step3-data-source-item input { margin-top: 4px; flex-shrink: 0; }
.ds-main { flex: 1; min-width: 0; }
.ds-name { font-size: 12px; font-weight: 500; color: #0f172a; word-break: break-all; }
.ds-meta { font-size: 11px; color: #94a3b8; margin-top: 2px; }
.step3-data-source-tip { padding: 8px; font-size: 11px; color: #b45309; background: rgba(245, 158, 11, 0.1); border-radius: 6px; margin-top: 8px; }

.step3-drill-btn {
  margin-top: 12px;
  width: 100%; padding: 10px;
  border: 0; border-radius: 10px;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  color: #fff; font-size: 14px; font-weight: 600;
  cursor: pointer;
}
.step3-drill-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.step3-drill-btn:hover:not(:disabled) { box-shadow: 0 6px 16px -4px rgba(79, 70, 229, 0.4); }

/* 演练中 */
.step3-panel--phases .step3-drilling__header {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; font-weight: 600; color: #0f172a; margin-bottom: 10px;
}
.step3-drilling__header .dot {
  width: 8px; height: 8px; border-radius: 50%; background: #4f46e5;
  animation: pulseDot 1.2s ease-in-out infinite;
}
@keyframes pulseDot { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
.step3-drill-elapsed { margin-left: auto; color: #94a3b8; font-weight: 500; }

.step3-phases {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;
  margin-bottom: 10px;
}
.step3-phase-pill {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; border-radius: 8px;
  background: #f8fafc;
  border: 1.5px solid transparent;
  font-size: 12px;
  transition: all 150ms ease;
}
.step3-phase-pill.done { background: rgba(16, 185, 129, 0.06); border-color: rgba(16, 185, 129, 0.3); }
.phase-idx {
  width: 22px; height: 22px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 11px; font-weight: 700;
}
.phase-label { color: #0f172a; font-weight: 500; }

.step3-progress-bar {
  height: 6px; border-radius: 999px;
  background: #f1f5f9; overflow: hidden;
  margin-bottom: 12px;
}
.step3-progress-fill {
  height: 100%; border-radius: 999px;
  background: linear-gradient(90deg, #6366f1, #10b981);
  transition: width 200ms ease;
}

.step3-log {
  background: #0f172a; border-radius: 8px; overflow: hidden;
}
.step3-log__head {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 12px; border-bottom: 1px solid #1e293b;
}
.step3-log__head .dot { width: 10px; height: 10px; border-radius: 50%; }
.step3-log__head .dot.red { background: #ef4444; }
.step3-log__head .dot.yellow { background: #f59e0b; }
.step3-log__head .dot.green { background: #10b981; }
.step3-log__title { color: #94a3b8; font-size: 11px; margin-left: 8px; font-family: 'JetBrains Mono', 'SF Mono', monospace; }
.step3-log__body {
  padding: 10px 14px; max-height: 220px; overflow-y: auto;
  font-family: 'JetBrains Mono', 'SF Mono', monospace; font-size: 11px;
  color: #cbd5e1; line-height: 1.7;
}
.step3-log__line { display: flex; gap: 8px; }
.log-ts { color: #475569; flex-shrink: 0; }
.log-lvl {
  flex-shrink: 0; padding: 0 6px; border-radius: 3px;
  font-size: 10px; font-weight: 700;
}
.log-lvl--ok { background: rgba(16, 185, 129, 0.2); color: #34d399; }
.log-lvl--run { background: rgba(99, 102, 241, 0.2); color: #818cf8; }
.log-lvl--err { background: rgba(239, 68, 68, 0.2); color: #f87171; }

/* 演练结果 */
.step3-result-banner {
  display: flex; gap: 12px; align-items: center;
  padding: 14px 18px;
  border-radius: 12px;
  margin-bottom: 12px;
}
.step3-result-banner--pass { background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.3); }
.step3-result-banner--warn { background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.3); }
.step3-result-banner--error { background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.3); }
.step3-result-banner__icon { font-size: 24px; }
.step3-result-banner__title { font-size: 14px; font-weight: 600; color: #0f172a; }
.step3-result-banner__sub { font-size: 11px; color: #64748b; margin-top: 4px; }

.step3-phase-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.step3-phase-card {
  padding: 12px 14px;
  background: #fff; border: 1px solid #e2e8f0; border-radius: 10px;
}
.step3-phase-card__head { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.phase-card-idx { width: 8px; height: 24px; border-radius: 4px; }
.phase-card-name { font-size: 12px; font-weight: 600; color: #0f172a; flex: 1; }
.phase-card-status {
  padding: 2px 8px; border-radius: 999px;
  font-size: 10px; font-weight: 500;
}
.phase-card-status--pass { background: rgba(16, 185, 129, 0.12); color: #059669; }
.phase-card-status--warn { background: rgba(245, 158, 11, 0.12); color: #b45309; }
.phase-card-status--error { background: rgba(239, 68, 68, 0.12); color: #dc2626; }

.step3-phase-card__metrics {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;
}
.phase-metric {
  background: #f8fafc; border-radius: 6px; padding: 8px;
}
.phase-metric__val { font-size: 14px; font-weight: 700; color: #0f172a; line-height: 1.2; }
.phase-metric__val--pass { color: #059669; }
.phase-metric__val--warn { color: #b45309; }
.phase-metric__label { font-size: 10px; color: #94a3b8; margin-top: 2px; }

.step3-drill-hint {
  margin-top: 12px; padding: 10px 14px;
  background: rgba(16, 185, 129, 0.06); border-radius: 8px;
  font-size: 12px; color: #059669; font-weight: 500;
}

/* 右侧 */
.step3-gates { display: grid; gap: 8px; }
.step3-gate { display: flex; gap: 10px; align-items: flex-start; }
.step3-gate__icon {
  width: 22px; height: 22px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: #f1f5f9; color: #94a3b8;
  font-size: 11px; flex-shrink: 0;
}
.step3-gate__icon.pass { background: #10b981; color: #fff; }
.step3-gate__label { font-size: 12px; font-weight: 500; color: #0f172a; }
.step3-gate__desc { font-size: 11px; color: #94a3b8; margin-top: 2px; }

.step3-baseline-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.step3-baseline-card {
  padding: 12px;
  border-radius: 10px;
  background: #f8fafc;
  border-left: 3px solid #cbd5e1;
}
.step3-baseline-card--success { border-color: #10b981; }
.step3-baseline-card--warning { border-color: #f59e0b; }
.step3-baseline-card--info { border-color: #06b6d4; }
.bv { font-size: 18px; font-weight: 700; color: #0f172a; }
.bl { font-size: 11px; color: #475569; margin-top: 2px; font-weight: 500; }
.bt { font-size: 10px; color: #94a3b8; margin-top: 4px; }

.step3-rollback { font-size: 11px; line-height: 1.7; }
.rollback-target { font-weight: 600; color: #0f172a; margin-bottom: 6px; }
.rollback-text { color: #64748b; margin-bottom: 6px; }
.rollback-rule { color: #475569; padding: 2px 0; }

.step3-publish-btn {
  width: 100%; padding: 12px;
  border: 0; border-radius: 12px;
  background: linear-gradient(135deg, #10b981, #059669);
  color: #fff; font-size: 14px; font-weight: 600;
  cursor: pointer;
}
.step3-publish-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.step3-publish-btn:hover:not(:disabled) { box-shadow: 0 8px 18px -6px rgba(16, 185, 129, 0.5); transform: translateY(-1px); }

/* 发布弹窗 */
.step3-publish-modal :deep(.ant-modal-content) { border-radius: 14px; }
.step3-modal-content { padding: 8px 8px 0; }
.step3-modal-title { font-size: 16px; font-weight: 700; color: #0f172a; margin-bottom: 12px; }
.step3-modal-text { font-size: 13px; color: #475569; line-height: 1.7; margin-bottom: 14px; }
.step3-modal-stats {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;
  margin-bottom: 14px;
}
.step3-modal-stats > div {
  background: #f8fafc; border-radius: 8px; padding: 10px;
  font-size: 11px; color: #94a3b8;
}
.step3-modal-stats strong { display: block; color: #0f172a; font-size: 16px; margin-top: 2px; }
.step3-warn-radio { padding: 10px; background: rgba(245, 158, 11, 0.08); border-radius: 8px; margin-bottom: 14px; }
.step3-modal-actions { display: flex; gap: 8px; justify-content: flex-end; padding-top: 12px; border-top: 1px solid #f1f5f9; }

/* 成功页 */
.step3-success {
  flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 16px; padding: 56px 32px;
  text-align: center;
}
.step3-success__hero { font-size: 64px; }
.step3-success__title {
  font-size: 32px; font-weight: 700;
  background: linear-gradient(135deg, #10b981, #059669);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.step3-success__sub { font-size: 14px; color: #64748b; }
.step3-success__stats {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;
  margin: 20px 0;
}
.step3-success-stat {
  padding: 18px 28px; border-radius: 12px;
  background: #fff; border: 1px solid #e2e8f0;
  min-width: 120px;
}
.step3-success-stat .num { font-size: 28px; font-weight: 700; color: #0f172a; }
.step3-success-stat .label { font-size: 11px; color: #94a3b8; margin-top: 4px; }
.step3-success__cta { display: flex; gap: 10px; }
.step3-success__count { font-size: 11px; color: #94a3b8; margin-top: 8px; }
</style>
