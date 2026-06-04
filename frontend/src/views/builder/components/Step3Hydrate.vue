<template>
  <div class="step3-root">
    <header class="step3-topbar">
      <button class="step3-back-btn" @click="$emit('prev')">← 返回</button>
      <div class="step3-topbar-title">水合演练 · 本体发布</div>
      <div class="step3-topbar-progress" v-if="drillStarted && !drillResult">
        <span class="step3-progress-label">演练进行中</span>
        <div class="step3-progress-track">
          <div class="step3-progress-bar" :style="{ width: drillProgress * 100 + '%' }"></div>
        </div>
        <span class="step3-progress-pct">{{ Math.round(drillProgress * 100) }}%</span>
      </div>
      <div class="step3-topbar-progress" v-else-if="drillResult">
        <span class="step3-progress-label step3-progress-label--done">演练完成</span>
      </div>
    </header>

    <!-- 发布成功大屏 -->
    <div v-if="success" class="step3-success">
      <div class="step3-success__hero">🎉</div>
      <div class="step3-success__title">发布成功</div>
      <div class="step3-success__sub">{{ session.ontologyName }} 已发布至本体工作室</div>
      <div class="step3-success__stats">
        <div class="step3-success-stat">
          <div class="num">{{ session.ontologyObjects.length }}</div>
          <div class="label">对象</div>
        </div>
        <div class="step3-success-stat">
          <div class="num">{{ session.ontologyRelations.length }}</div>
          <div class="label">关系</div>
        </div>
        <div class="step3-success-stat">
          <div class="num">{{ drillResult?.entityCount?.toLocaleString() || 0 }}</div>
          <div class="label">数据行数</div>
        </div>
        <div class="step3-success-stat">
          <div class="num">{{ drillResult?.attributionAccuracy || 'N/A' }}</div>
          <div class="label">映射准确率</div>
        </div>
      </div>
      <div class="step3-success__cta">
        <a-button type="primary" size="large" @click="$emit('goto-studio')">前往本体工作室查看</a-button>
        <a-button size="large" @click="success = false">留在构建器</a-button>
      </div>
    </div>

    <!-- 主体区域 -->
    <div v-else class="step3-body">
      <!-- 左侧主区域 -->
      <main class="step3-main">
        <!-- 演练前：数据源选择 -->
        <div v-if="!drillStarted" class="step3-panel">
          <div class="step3-panel__title">数据源选择</div>
          <div class="step3-panel__sub">选择参与水合演练的数据资产，验证本体属性与真实数据列的映射关系</div>

          <div v-if="assetLoading" class="step3-loading">加载资产信息中...</div>
          <div v-else-if="assetList.length > 0" class="step3-ds-list">
            <div class="step3-ds-actions">
              <button class="step3-ds-action" @click="selectAll">全选</button>
              <button class="step3-ds-action" @click="selectedSourceIds = []">清空</button>
              <span class="step3-ds-count">已选 {{ selectedSourceIds.length }} / {{ assetList.length }}</span>
            </div>
            <label
              v-for="ds in assetList"
              :key="ds.id"
              class="step3-ds-item"
              :class="{ 'step3-ds-item--selected': selectedSourceIds.includes(ds.id) }"
            >
              <input type="checkbox" :value="ds.id" v-model="selectedSourceIds" />
              <div class="step3-ds-info">
                <div class="step3-ds-name">{{ ds.displayName }}</div>
                <div class="step3-ds-meta">
                  <span class="step3-ds-kind">{{ ds.kind }}</span>
                  <span v-if="ds.columnCount">{{ ds.columnCount }} 列</span>
                  <span v-if="ds.objectName" class="step3-ds-obj">绑定: {{ ds.objectName }}</span>
                </div>
              </div>
            </label>
          </div>
          <div v-else class="step3-ds-empty">
            <div class="step3-ds-empty__text">未找到可用数据资产</div>
            <div class="step3-ds-empty__hint">本体对象未绑定数据资产，演练将仅验证结构完整性</div>
          </div>

          <button
            class="step3-drill-btn"
            :disabled="assetList.length > 0 && selectedSourceIds.length === 0"
            @click="startDrill"
          >
            开始演练
          </button>
        </div>

        <!-- 演练中/演练后：日志 + 结果 -->
        <div v-if="drillStarted" class="step3-panel step3-panel--drill">
          <div class="step3-drill-header">
            <span class="step3-drill-dot" :class="{ done: !!drillResult }"></span>
            <span>{{ !drillResult ? '演练进行中' : drillStatus === 'pass' ? '演练完成 · 全部通过' : drillStatus === 'warn' ? '演练完成 · 存在警告' : '演练失败' }}</span>
            <span class="step3-drill-elapsed">{{ drillElapsed }}s</span>
            <button v-if="drillResult" class="step3-retry-btn" @click="resetDrill">重新演练</button>
          </div>

          <!-- 4 阶段指示 -->
          <div class="step3-phases">
            <div
              v-for="(p, i) in HYDRATION_PHASES"
              :key="p.key"
              class="step3-phase-pill"
              :class="{ active: drillProgress >= (i + 1) / HYDRATION_PHASES.length }"
            >
              <span class="phase-idx" :style="{ background: drillProgress >= (i + 1) / HYDRATION_PHASES.length ? p.color : '#cbd5e1' }">{{ i + 1 }}</span>
              <span class="phase-label">{{ p.label }}</span>
            </div>
          </div>

          <!-- 日志终端 -->
          <div class="step3-log">
            <div class="step3-log__head">
              <span class="dot red"></span><span class="dot yellow"></span><span class="dot green"></span>
              <span class="step3-log__title">hydration.log</span>
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

        <!-- 演练结果卡片 -->
        <div v-if="drillResult" class="step3-panel">
          <div class="step3-result-banner" :class="`step3-result-banner--${drillStatus}`">
            <span class="step3-result-icon">{{ drillStatus === 'pass' ? '✅' : drillStatus === 'warn' ? '⚠️' : '❌' }}</span>
            <div>
              <div class="step3-result-title">
                {{ drillStatus === 'pass' ? '全部阶段通过' : drillStatus === 'warn' ? '存在警告，建议确认后发布' : '演练失败，请修复后重试' }}
              </div>
              <div class="step3-result-sub">
                映射 {{ drillResult.attributionAccuracy || 'N/A' }} · 数据 {{ drillResult.entityCount?.toLocaleString() || 0 }} 行 · 用时 {{ drillElapsed }}s
              </div>
            </div>
          </div>
          <div class="step3-phase-cards">
            <div v-for="p in drillResult.phases" :key="p.key" class="step3-phase-card">
              <div class="step3-phase-card__head">
                <span class="phase-card-dot" :style="{ background: phaseColor(p.key) }"></span>
                <span class="phase-card-name">{{ p.label }}</span>
                <span class="phase-card-status" :class="`phase-card-status--${p.status}`">
                  {{ p.status === 'pass' ? '通过' : p.status === 'warn' ? '警告' : '失败' }}
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
        </div>
      </main>

      <!-- 右侧面板 -->
      <aside class="step3-aside">
        <div class="step3-panel">
          <div class="step3-panel__title">本体概览</div>
          <div class="step3-summary-grid">
            <div class="step3-summary-item">
              <div class="step3-summary-val">{{ session.ontologyObjects.length }}</div>
              <div class="step3-summary-label">对象</div>
            </div>
            <div class="step3-summary-item">
              <div class="step3-summary-val">{{ session.ontologyRelations.length }}</div>
              <div class="step3-summary-label">关系</div>
            </div>
            <div class="step3-summary-item">
              <div class="step3-summary-val">{{ totalProps }}</div>
              <div class="step3-summary-label">属性</div>
            </div>
            <div class="step3-summary-item">
              <div class="step3-summary-val">{{ mappingCoverage }}</div>
              <div class="step3-summary-label">映射覆盖</div>
            </div>
          </div>
        </div>

        <div class="step3-panel">
          <div class="step3-panel__title">发布门禁</div>
          <div class="step3-gates">
            <div v-for="g in gates" :key="g.key" class="step3-gate">
              <span class="step3-gate__icon" :class="{ pass: g.pass }">{{ g.pass ? '✓' : '○' }}</span>
              <div>
                <div class="step3-gate__label">{{ g.label }}</div>
                <div class="step3-gate__desc">{{ g.desc }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="step3-panel">
          <div class="step3-panel__title">版本信息</div>
          <div class="step3-version-info">
            <div class="step3-version-row"><span>版本号</span><strong>{{ versionLabel }}</strong></div>
            <div class="step3-version-row"><span>构建方式</span><strong>{{ buildPathLabel }}</strong></div>
            <div class="step3-version-row"><span>对象数</span><strong>{{ session.ontologyObjects.length }}</strong></div>
            <div class="step3-version-row"><span>关系数</span><strong>{{ session.ontologyRelations.length }}</strong></div>
          </div>
        </div>

        <button
          class="step3-publish-btn"
          :disabled="!canPublish"
          @click="publishModalOpen = true"
        >
          发布至本体工作室
        </button>
      </aside>
    </div>

    <!-- 发布弹窗 -->
    <a-modal v-model:open="publishModalOpen" :footer="null" :width="480" class="step3-publish-modal">
      <div class="step3-modal-content">
        <div class="step3-modal-title">确认发布 · {{ versionLabel }}</div>
        <div class="step3-modal-text">
          将发布 <strong>{{ session.ontologyName }}</strong>，包含
          <strong>{{ session.ontologyObjects.length }}</strong> 个对象、
          <strong>{{ session.ontologyRelations.length }}</strong> 条关系
        </div>
        <div class="step3-modal-stats" v-if="drillResult">
          <div><span>字段映射：</span><strong>{{ drillResult.attributionAccuracy || 'N/A' }}</strong></div>
          <div><span>数据行数：</span><strong>{{ drillResult.entityCount?.toLocaleString() || 0 }}</strong></div>
          <div><span>关系实例：</span><strong>{{ drillResult.relationCount?.toLocaleString() || 0 }}</strong></div>
        </div>
        <div class="step3-modal-actions">
          <a-button @click="publishModalOpen = false">取消</a-button>
          <a-button type="primary" :loading="publishing" @click="confirmPublish">确认发布</a-button>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useBuilderStore } from '../../../store/builder'
import { HYDRATION_PHASES, DEFAULT_PUBLISH_GATES } from '../../../data/builderPresets'
import type { BuilderSession, DrillLogLine, DrillPhase, DrillResult, PublishGate } from '../../../types/builder'

const props = defineProps<{ session: BuilderSession }>()
defineEmits<{ (e: 'prev'): void; (e: 'goto-studio'): void }>()
const store = useBuilderStore()

// ── 状态 ──
const drillStarted = ref(!!props.session.drillResult)
const drillProgress = ref(props.session.drillResult ? 1 : 0)
const drillStatus = ref<'pass' | 'warn' | 'error' | undefined>(props.session.drillStatus)
const drillLogs = ref<DrillLogLine[]>([])
const drillElapsed = ref(0)
const drillResult = ref<DrillResult | null>(props.session.drillResult || null)
const selectedSourceIds = ref<string[]>([])
const publishModalOpen = ref(false)
const publishing = ref(false)
const success = ref(props.session.status === 'published')
const logBodyRef = ref<HTMLElement | null>(null)
const assetLoading = ref(false)
const assetList = ref<AssetDisplayItem[]>([])

let drillTimer: number | null = null

interface AssetDisplayItem {
  id: string
  displayName: string
  kind: string
  columnCount: number
  objectName: string
}

// ── 计算属性 ──
const versionLabel = computed(() => props.session.publishedVersion || 'v0.1')
const buildPathLabel = computed(() => {
  const m = props.session.buildMethod
  if (m === 'chat') return '对话生成'
  if (m === 'import') return '文件导入'
  if (m === 'extract') return '文档抽取'
  return '手工建模'
})

const totalProps = computed(() =>
  props.session.ontologyObjects.reduce((sum, o) => sum + (o.properties?.length || 0), 0)
)

const mappingCoverage = computed(() => {
  let mapped = 0
  let total = 0
  for (const obj of props.session.ontologyObjects) {
    for (const p of (obj.properties || [])) {
      total++
      if (p.source_column) mapped++
    }
  }
  return total > 0 ? `${Math.round(mapped / total * 100)}%` : 'N/A'
})

// PLACEHOLDER_SCRIPT_REST

const gates = computed<PublishGate[]>(() => {
  const list: PublishGate[] = JSON.parse(JSON.stringify(DEFAULT_PUBLISH_GATES))
  const objCount = props.session.ontologyObjects.length
  list[0] = { ...list[0], desc: `${objCount} 个对象`, pass: objCount > 0 }
  list[1] = {
    ...list[1],
    desc: drillResult.value
      ? (drillStatus.value === 'error' ? '演练失败' : '演练通过')
      : '未演练',
    pass: !!drillResult.value && drillStatus.value !== 'error',
  }
  list[2] = { ...list[2], desc: versionLabel.value, pass: true }
  return list
})

const canPublish = computed(() => gates.value.every(g => g.pass))

// ── 资产加载 ──
async function loadAssetDetails() {
  const allIds = new Set<string>()
  for (const obj of props.session.ontologyObjects) {
    for (const aid of (obj.backing_asset_ids || [])) {
      allIds.add(aid)
    }
  }
  if (allIds.size === 0 && props.session.selectedAssetIds?.length) {
    for (const aid of props.session.selectedAssetIds) {
      allIds.add(aid)
    }
  }

  // Fallback: query active table/sql_view assets from backend
  if (allIds.size === 0) {
    try {
      const { get } = await import('../../../api/client')
      const assets = await get('/assets?kinds=table%2Csql_view&status=active') as any[]
      if (assets && assets.length) {
        for (const a of assets) {
          allIds.add(a.id)
        }
      }
    } catch { /* ignore */ }
  }

  if (allIds.size === 0) {
    assetList.value = []
    return
  }

  assetLoading.value = true
  try {
    const { get } = await import('../../../api/client')
    const items: AssetDisplayItem[] = []
    for (const aid of allIds) {
      try {
        const res = await get(`/assets/${aid}`)
        const a = res as any
        const objName = props.session.ontologyObjects.find(
          o => (o.backing_asset_ids || []).includes(aid)
        )?.displayName || ''
        items.push({
          id: aid,
          displayName: a.alias || a.name || (a.locator?.table) || aid.slice(0, 12),
          kind: a.kind || 'table',
          columnCount: (a.schema_snapshot || []).length,
          objectName: objName,
        })
      } catch {
        items.push({
          id: aid,
          displayName: aid.slice(0, 12),
          kind: 'table',
          columnCount: 0,
          objectName: '',
        })
      }
    }
    assetList.value = items
    selectedSourceIds.value = items.map(i => i.id)
  } catch {
    assetList.value = []
  } finally {
    assetLoading.value = false
  }
}

function selectAll() {
  selectedSourceIds.value = assetList.value.map(i => i.id)
}

// ── 演练 ──
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

function resetDrill() {
  drillStarted.value = false
  drillResult.value = null
  drillStatus.value = undefined
  drillProgress.value = 0
  drillLogs.value = []
  drillElapsed.value = 0
}

// PLACEHOLDER_DRILL_FN

async function startDrill() {
  if (assetList.value.length > 0 && selectedSourceIds.value.length === 0) {
    message.warning('请至少选择 1 个数据资产后再开始演练。')
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

  pushLog('RUN', '启动水合演练...')

  try {
    const payload = {
      session_id: props.session.sessionId || '',
      objects: (props.session.ontologyObjects || []).map(o => ({
        name: o.name,
        displayName: o.displayName,
        tier: o.tier,
        primaryKey: o.primaryKey,
        properties: (o.properties || []).map(p => ({
          name: p.name,
          displayName: p.displayName,
          type: p.type,
          required: !!p.required,
          source_asset_id: p.source_asset_id ?? null,
          source_column: p.source_column ?? null,
          source_field: (p as any).source_field ?? null,
          source_table: (p as any).source_table ?? null,
        })),
        backing_asset_ids: o.backing_asset_ids || [],
      })),
      relations: (props.session.ontologyRelations || []).map(r => {
        const srcObj = (props.session.ontologyObjects || []).find(o => o.id === r.source)
        const tgtObj = (props.session.ontologyObjects || []).find(o => o.id === r.target)
        return {
          name: r.name,
          displayName: r.displayName,
          source: srcObj?.name || r.source,
          target: tgtObj?.name || r.target,
          cardinality: r.cardinality || '1:N',
        }
      }),
      asset_ids: selectedSourceIds.value,
    }

    const resp = await fetch('/api/v1/builder/hydrate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!resp.ok || !resp.body) {
      throw new Error(`HTTP ${resp.status}`)
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buf = ''
    const phaseData: Record<string, DrillPhase> = {}

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      let idx
      while ((idx = buf.indexOf('\n\n')) >= 0) {
        const chunk = buf.slice(0, idx).trim()
        buf = buf.slice(idx + 2)
        if (!chunk.startsWith('data:')) continue
        const raw = chunk.slice(5).trim()
        if (raw === '[DONE]') continue
        try {
          const ev = JSON.parse(raw)
          handleHydrationEvent(ev, phaseData)
        } catch { /* ignore parse errors */ }
      }
    }
  } catch (e: any) {
    pushLog('ERR', `演练异常: ${e.message || e}`)
    drillStatus.value = 'error'
  } finally {
    if (drillTimer) clearInterval(drillTimer)
  }
}

// PLACEHOLDER_EVENT_HANDLER

function handleHydrationEvent(ev: any, phaseData: Record<string, DrillPhase>) {
  switch (ev.type) {
    case 'phase_log':
      pushLog(ev.level || 'OK', ev.msg || '')
      break
    case 'phase_progress':
      if (typeof ev.progress === 'number') {
        drillProgress.value = ev.progress
      }
      break
    case 'phase_complete': {
      const phase = ev.phase as string
      const phaseLabel = HYDRATION_PHASES.find(p => p.key === phase)?.label || phase
      phaseData[phase] = {
        key: phase as any,
        label: phaseLabel,
        status: ev.status || 'pass',
        metrics: ev.metrics || [],
      }
      break
    }
    case 'drill_complete': {
      const phases = (ev.result?.phases || []).map((p: any) => ({
        key: p.key,
        label: p.label || HYDRATION_PHASES.find(h => h.key === p.key)?.label || p.key,
        status: p.status || 'pass',
        metrics: p.metrics || [],
      }))
      drillResult.value = {
        phases,
        logs: drillLogs.value,
        selectedRows: ev.result?.selectedRows || 0,
        selectedColumns: ev.result?.selectedColumns || 0,
        selectedSources: ev.result?.selectedSources || 0,
        entityCount: ev.result?.entityCount || 0,
        relationCount: ev.result?.relationCount || 0,
        attributionAccuracy: ev.result?.attributionAccuracy,
        highConfidenceAttribution: ev.result?.highConfidenceAttribution,
        manualReview: ev.result?.manualReview,
      }
      drillStatus.value = ev.status || 'pass'
      drillProgress.value = 1
      if (drillTimer) clearInterval(drillTimer)
      store.patchActive({
        drillStatus: drillStatus.value,
        drillResult: drillResult.value,
        selectedSampleSourceIds: selectedSourceIds.value,
        status: 'pending_publish',
      })
      message.success('水合演练完成')
      break
    }
    case 'error':
      pushLog('ERR', ev.content || '未知错误')
      drillStatus.value = 'error'
      break
  }
}

async function confirmPublish() {
  publishing.value = true
  store.setStatus('publishing')
  try {
    const objects = (props.session.ontologyObjects || []).map((o: any) => ({
      name: o.name,
      displayName: o.displayName,
      tier: o.tier,
      namespace: o.namespace,
      description: o.description,
      primaryKey: o.primaryKey,
      properties: (o.properties || []).map((p: any) => ({
        name: p.name,
        displayName: p.displayName,
        type: p.type,
        required: !!p.required,
        description: p.description,
        source_asset_id: p.source_asset_id ?? null,
        source_column: p.source_column ?? null,
      })),
      backing_asset_ids: o.backing_asset_ids || [],
    }))
    const relations = (props.session.ontologyRelations || []).map((r: any) => {
      const srcObj = (props.session.ontologyObjects || []).find((o: any) => o.id === r.source)
      const tgtObj = (props.session.ontologyObjects || []).find((o: any) => o.id === r.target)
      return {
        name: r.name,
        displayName: r.displayName,
        source: srcObj?.name || r.source,
        target: tgtObj?.name || r.target,
        cardinality: r.cardinality || '1:N',
        relationType: r.relationType || 'ObjectProperty',
        description: r.description || r.displayName || r.name,
      }
    })
    if (objects.length > 0) {
      const { post } = await import('../../../api/client')
      await post('/builder/finalize', { objects, relations })
    }
  } catch (e) {
    console.error('finalize failed', e)
  }
  const version = props.session.publishedVersion || 'v0.1'
  store.patchActive({
    status: 'published',
    publishedVersion: version,
    publishedAt: new Date().toISOString(),
  })
  publishing.value = false
  publishModalOpen.value = false
  success.value = true
}

// ── 生命周期 ──
onMounted(() => {
  loadAssetDetails()
})

watch(() => props.session.sessionId, () => {
  drillStarted.value = !!props.session.drillResult
  drillResult.value = props.session.drillResult || null
  drillStatus.value = props.session.drillStatus
  drillProgress.value = props.session.drillResult ? 1 : 0
  success.value = props.session.status === 'published'
  loadAssetDetails()
})

onUnmounted(() => {
  if (drillTimer) clearInterval(drillTimer)
})
</script>

<style scoped>
.step3-root { display: flex; flex-direction: column; height: 100%; background: #f8fafc; }

.step3-topbar {
  display: flex; align-items: center; gap: 16px;
  padding: 10px 20px; background: #fff; border-bottom: 1px solid #e2e8f0;
}
.step3-back-btn {
  background: transparent; border: 0; padding: 4px 10px;
  border-radius: 6px; color: #475569; font-size: 12px; cursor: pointer;
}
.step3-back-btn:hover { background: #f1f5f9; color: #0f172a; }
.step3-topbar-title { font-size: 14px; font-weight: 600; color: #0f172a; }
.step3-topbar-progress { display: flex; align-items: center; gap: 8px; margin-left: auto; }
.step3-progress-label { font-size: 11px; color: #64748b; }
.step3-progress-label--done { color: #059669; font-weight: 500; }
.step3-progress-track { width: 80px; height: 4px; background: #e2e8f0; border-radius: 2px; overflow: hidden; }
.step3-progress-bar { height: 100%; background: #4f46e5; border-radius: 2px; transition: width 200ms ease; }
.step3-progress-pct { font-size: 11px; color: #475569; font-weight: 500; }

.step3-body {
  flex: 1; overflow: auto;
  display: grid; grid-template-columns: 1fr 320px;
  gap: 16px; padding: 16px;
}
.step3-main { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.step3-aside { display: flex; flex-direction: column; gap: 12px; }

.step3-panel {
  background: #fff; border: 1px solid #e2e8f0;
  border-radius: 12px; padding: 14px 16px;
}
.step3-panel__title { font-size: 13px; font-weight: 600; color: #0f172a; margin-bottom: 6px; }
.step3-panel__sub { font-size: 11px; color: #94a3b8; margin-bottom: 12px; }

/* 数据源选择 */
.step3-loading { font-size: 12px; color: #94a3b8; padding: 20px 0; text-align: center; }
.step3-ds-actions { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.step3-ds-action {
  padding: 2px 10px; border-radius: 6px; font-size: 11px; cursor: pointer;
  background: #f1f5f9; border: 1px solid #e2e8f0; color: #475569;
}
.step3-ds-action:hover { background: #e2e8f0; }
.step3-ds-count { font-size: 11px; color: #94a3b8; margin-left: auto; }

.step3-ds-list { max-height: 320px; overflow-y: auto; }
.step3-ds-item {
  display: flex; gap: 10px; align-items: flex-start;
  padding: 8px 10px; border-radius: 8px;
  border: 1px solid transparent; cursor: pointer; margin-bottom: 4px;
}
.step3-ds-item:hover { background: #f8fafc; }
.step3-ds-item--selected { background: rgba(79, 70, 229, 0.04); border-color: #c7d2fe; }
.step3-ds-item input { margin-top: 3px; flex-shrink: 0; }
.step3-ds-info { flex: 1; min-width: 0; }
.step3-ds-name { font-size: 12px; font-weight: 500; color: #0f172a; }
.step3-ds-meta { display: flex; gap: 8px; font-size: 11px; color: #94a3b8; margin-top: 2px; }
.step3-ds-kind {
  padding: 0 6px; border-radius: 4px;
  background: #f1f5f9; color: #64748b; font-size: 10px;
}
.step3-ds-obj { color: #6366f1; }

.step3-ds-empty { padding: 32px 16px; text-align: center; }
.step3-ds-empty__text { font-size: 13px; font-weight: 600; color: #475569; }
.step3-ds-empty__hint { font-size: 11px; color: #94a3b8; margin-top: 4px; }

/* PLACEHOLDER_STYLE_2 */

.step3-drill-btn {
  margin-top: 12px; width: 100%; padding: 10px;
  border: 0; border-radius: 10px;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  color: #fff; font-size: 13px; font-weight: 600; cursor: pointer;
}
.step3-drill-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.step3-drill-btn:hover:not(:disabled) { box-shadow: 0 4px 12px -2px rgba(79, 70, 229, 0.4); }

/* 演练中 */
.step3-drill-header {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; font-weight: 600; color: #0f172a; margin-bottom: 10px;
}
.step3-drill-dot {
  width: 8px; height: 8px; border-radius: 50%; background: #4f46e5;
  animation: pulseDot 1.2s ease-in-out infinite;
}
.step3-drill-dot.done { background: #10b981; animation: none; }
@keyframes pulseDot { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
.step3-drill-elapsed { margin-left: auto; color: #94a3b8; font-weight: 500; font-size: 12px; }
.step3-retry-btn {
  padding: 3px 10px; border-radius: 6px; font-size: 11px; cursor: pointer;
  background: #f1f5f9; border: 1px solid #e2e8f0; color: #475569;
}
.step3-retry-btn:hover { background: #e2e8f0; }

.step3-phases {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 10px;
}
.step3-phase-pill {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 10px; border-radius: 8px; background: #f8fafc; font-size: 11px;
}
.step3-phase-pill.active { background: rgba(16, 185, 129, 0.06); }
.phase-idx {
  width: 20px; height: 20px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 10px; font-weight: 700;
}
.phase-label { color: #0f172a; font-weight: 500; }

/* 日志终端 */
.step3-log { background: #0f172a; border-radius: 8px; overflow: hidden; }
.step3-log__head {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 12px; border-bottom: 1px solid #1e293b;
}
.step3-log__head .dot { width: 10px; height: 10px; border-radius: 50%; }
.step3-log__head .dot.red { background: #ef4444; }
.step3-log__head .dot.yellow { background: #f59e0b; }
.step3-log__head .dot.green { background: #10b981; }
.step3-log__title { color: #94a3b8; font-size: 11px; margin-left: 8px; font-family: 'JetBrains Mono', monospace; }
.step3-log__body {
  padding: 8px 12px; max-height: 240px; overflow-y: auto;
  font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #cbd5e1;
}
.step3-log__line { display: flex; gap: 8px; line-height: 1.7; white-space: nowrap; }
.log-ts { color: #64748b; }
.log-lvl { font-weight: 600; min-width: 28px; }
.log-lvl--ok { color: #10b981; }
.log-lvl--run { color: #6366f1; }
.log-lvl--err { color: #ef4444; }
.log-msg { color: #e2e8f0; white-space: pre-wrap; word-break: break-all; }

/* 结果 */
.step3-result-banner {
  display: flex; gap: 12px; align-items: center;
  padding: 12px 16px; border-radius: 10px; margin-bottom: 12px;
}
.step3-result-banner--pass { background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.3); }
.step3-result-banner--warn { background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.3); }
.step3-result-banner--error { background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.3); }
.step3-result-icon { font-size: 22px; }
.step3-result-title { font-size: 13px; font-weight: 600; color: #0f172a; }
.step3-result-sub { font-size: 11px; color: #64748b; margin-top: 2px; }

.step3-phase-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.step3-phase-card {
  padding: 10px 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px;
}
.step3-phase-card__head { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
.phase-card-dot { width: 6px; height: 20px; border-radius: 3px; }
.phase-card-name { font-size: 11px; font-weight: 600; color: #0f172a; flex: 1; }
.phase-card-status { padding: 2px 8px; border-radius: 999px; font-size: 10px; font-weight: 500; }
.phase-card-status--pass { background: rgba(16, 185, 129, 0.12); color: #059669; }
.phase-card-status--warn { background: rgba(245, 158, 11, 0.12); color: #b45309; }
.phase-card-status--error { background: rgba(239, 68, 68, 0.12); color: #dc2626; }
.step3-phase-card__metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(80px, 1fr)); gap: 6px; }
.phase-metric { background: #fff; border-radius: 6px; padding: 6px 8px; }
.phase-metric__val { font-size: 13px; font-weight: 700; color: #0f172a; }
.phase-metric__val--pass { color: #059669; }
.phase-metric__val--warn { color: #b45309; }
.phase-metric__label { font-size: 10px; color: #94a3b8; margin-top: 1px; }

/* 右侧面板 */
.step3-summary-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.step3-summary-item { background: #f8fafc; border-radius: 8px; padding: 10px; text-align: center; }
.step3-summary-val { font-size: 18px; font-weight: 700; color: #0f172a; }
.step3-summary-label { font-size: 10px; color: #94a3b8; margin-top: 2px; }

.step3-gates { display: flex; flex-direction: column; gap: 6px; }
.step3-gate { display: flex; gap: 8px; align-items: flex-start; }
.step3-gate__icon {
  width: 18px; height: 18px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 10px; font-weight: 700; color: #94a3b8;
  border: 1.5px solid #cbd5e1; flex-shrink: 0; margin-top: 1px;
}
.step3-gate__icon.pass { background: #10b981; color: #fff; border-color: #10b981; }
.step3-gate__label { font-size: 12px; font-weight: 500; color: #0f172a; }
.step3-gate__desc { font-size: 11px; color: #94a3b8; }

.step3-version-info { display: flex; flex-direction: column; gap: 6px; }
.step3-version-row {
  display: flex; justify-content: space-between; font-size: 12px; color: #475569;
}
.step3-version-row strong { color: #0f172a; }

.step3-publish-btn {
  width: 100%; padding: 10px; border: 0; border-radius: 10px;
  background: linear-gradient(135deg, #10b981, #059669);
  color: #fff; font-size: 13px; font-weight: 600; cursor: pointer;
}
.step3-publish-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.step3-publish-btn:hover:not(:disabled) { box-shadow: 0 4px 12px -2px rgba(16, 185, 129, 0.4); }

/* 成功大屏 */
.step3-success { display: flex; flex-direction: column; align-items: center; justify-content: center; flex: 1; padding: 40px; }
.step3-success__hero { font-size: 56px; margin-bottom: 12px; }
.step3-success__title { font-size: 20px; font-weight: 700; color: #0f172a; }
.step3-success__sub { font-size: 13px; color: #64748b; margin-top: 4px; }
.step3-success__stats { display: flex; gap: 24px; margin-top: 24px; }
.step3-success-stat { text-align: center; }
.step3-success-stat .num { font-size: 22px; font-weight: 700; color: #0f172a; }
.step3-success-stat .label { font-size: 11px; color: #94a3b8; margin-top: 2px; }
.step3-success__cta { display: flex; gap: 12px; margin-top: 28px; }

/* 发布弹窗 */
.step3-modal-content { padding: 8px 0; }
.step3-modal-title { font-size: 16px; font-weight: 600; color: #0f172a; margin-bottom: 12px; }
.step3-modal-text { font-size: 13px; color: #475569; line-height: 1.6; }
.step3-modal-stats { display: flex; gap: 16px; margin-top: 12px; font-size: 12px; color: #475569; }
.step3-modal-stats strong { color: #0f172a; }
.step3-modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; }
</style>
