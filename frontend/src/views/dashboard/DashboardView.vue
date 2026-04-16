<template>
  <div class="pd">
    <!-- 顶栏 -->
    <header class="pd-header">
      <div class="pd-header__left">
        <div class="pd-header__logo">
          <svg width="18" height="18" viewBox="0 0 16 16" fill="none">
            <path d="M8 1l6 3.5v7L8 15l-6-3.5v-7L8 1z" stroke="#3b82f6" stroke-width="1.5" stroke-linejoin="round"/>
            <path d="M8 5v6M5 6.5l3-1.5 3 1.5" stroke="#3b82f6" stroke-width="1.2" stroke-linecap="round"/>
          </svg>
        </div>
        <span class="pd-header__title">本体智能体平台</span>
        <span class="pd-header__sep">/</span>
        <span class="pd-header__sub">运营看板</span>
      </div>
      <div class="pd-header__right">
        <span class="pd-status-dot"></span>
        <span class="pd-header__ts">{{ currentTime }}</span>
        <button class="pd-refresh-btn" @click="loadData" :class="{ 'pd-refresh-btn--spin': loading }">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M12 7A5 5 0 1 1 7 2a5 5 0 0 1 3.5 1.5L12 2v4H8l1.5-1.5A3 3 0 1 0 10 7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
        </button>
      </div>
    </header>

    <div class="pd-body">
      <!-- KPI 行 -->
      <div class="pd-kpi-row">
        <div v-for="kpi in kpis" :key="kpi.key"
          class="pd-kpi"
          :class="{ 'pd-kpi--active': activeModule === kpi.key }"
          @click="openModule(kpi.key)">
          <div class="pd-kpi__icon" :style="{ background: kpi.color + '22', color: kpi.color }">
            <span v-html="kpi.icon"></span>
          </div>
          <div class="pd-kpi__body">
            <div class="pd-kpi__val">{{ stats ? stats[kpi.field] ?? '—' : '—' }}</div>
            <div class="pd-kpi__lbl">{{ kpi.label }}</div>
          </div>
          <div class="pd-kpi__trend" v-if="kpi.trend">
            <span class="pd-kpi__trend-val" :class="kpi.trend > 0 ? 'up' : 'down'">
              {{ kpi.trend > 0 ? '+' : '' }}{{ kpi.trend }}%
            </span>
          </div>
        </div>
      </div>

      <!-- 主网格 -->
      <div class="pd-grid">
        <!-- 左列 -->
        <div class="pd-col pd-col--left">
          <!-- Tier 分布 -->
          <div class="pd-panel" @click="openModule('tier')">
            <div class="pd-panel__hd">
              <span class="pd-panel__title">对象层级分布</span>
              <span class="pd-panel__badge">Tier</span>
            </div>
            <div class="pd-tier-list" v-if="stats">
              <div v-for="t in stats.tier_distribution" :key="t.tier" class="pd-tier-row">
                <span class="pd-tier-label">{{ t.name }}</span>
                <div class="pd-tier-bar-wrap">
                  <div class="pd-tier-bar" :style="{ width: t.pct + '%', background: tierColor(t.tier) }"></div>
                </div>
                <span class="pd-tier-cnt">{{ t.count }}</span>
                <span class="pd-tier-pct">{{ t.pct }}%</span>
              </div>
            </div>
            <div v-else class="pd-skeleton-rows"></div>
          </div>

          <!-- 命名空间分布 -->
          <div class="pd-panel" @click="openModule('ns')">
            <div class="pd-panel__hd">
              <span class="pd-panel__title">场景命名空间</span>
              <span class="pd-panel__badge">NS</span>
            </div>
            <div class="pd-ns-grid" v-if="stats">
              <div v-for="n in stats.ns_distribution" :key="n.ns" class="pd-ns-card">
                <div class="pd-ns-card__name">{{ n.ns }}</div>
                <div class="pd-ns-card__cnt">{{ n.count }}</div>
              </div>
            </div>
          </div>

          <!-- 规则优先级 -->
          <div class="pd-panel" @click="openModule('rules')">
            <div class="pd-panel__hd">
              <span class="pd-panel__title">规则优先级分布</span>
              <span class="pd-panel__badge">Rules</span>
            </div>
            <div class="pd-rule-priority" v-if="stats">
              <div v-for="p in stats.rule_priority" :key="p.priority" class="pd-rp-row">
                <span class="pd-rp-dot" :class="`rp--${p.priority}`"></span>
                <span class="pd-rp-lbl">{{ { high: '高优先级', medium: '中优先级', low: '低优先级' }[p.priority] }}</span>
                <span class="pd-rp-cnt">{{ p.count }}</span>
                <div class="pd-rp-bar-wrap">
                  <div class="pd-rp-bar" :class="`rp--${p.priority}`"
                    :style="{ width: maxRulePriority ? (p.count / maxRulePriority * 100) + '%' : '0%' }"></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 中列 -->
        <div class="pd-col pd-col--mid">
          <!-- 健康状态矩阵 -->
          <div class="pd-panel pd-panel--tall" @click="openModule('health')">
            <div class="pd-panel__hd">
              <span class="pd-panel__title">对象健康矩阵</span>
              <div class="pd-health-legend">
                <span class="pd-hl-dot hl--active"></span><span>活跃</span>
                <span class="pd-hl-dot hl--inactive"></span><span>停用</span>
                <span class="pd-hl-dot hl--draft"></span><span>草稿</span>
              </div>
            </div>
            <div class="pd-health-grid" v-if="stats">
              <div v-for="e in stats.health_status" :key="e.id"
                class="pd-health-cell"
                :class="`hc--${e.status}`"
                :title="`${e.name_cn || e.name} (Tier ${e.tier})`"
                @click.stop="openEntityDetail(e.id)">
                <span class="pd-health-cell__tier">T{{ e.tier }}</span>
              </div>
            </div>
            <div v-else class="pd-skeleton-grid"></div>
          </div>

          <!-- TOP 规则触发 -->
          <div class="pd-panel" @click="openModule('top-rules')">
            <div class="pd-panel__hd">
              <span class="pd-panel__title">规则触发 TOP 5</span>
              <span class="pd-panel__badge pd-panel__badge--green">实时</span>
            </div>
            <div class="pd-top-rules" v-if="stats">
              <div v-for="(r, i) in stats.top_rules" :key="r.id" class="pd-tr-row">
                <span class="pd-tr-rank" :class="`rank--${i < 3 ? i + 1 : 'rest'}`">{{ i + 1 }}</span>
                <span class="pd-tr-name">{{ r.name }}</span>
                <div class="pd-tr-bar-wrap">
                  <div class="pd-tr-bar" :style="{ width: maxTrigger ? (r.trigger_count / maxTrigger * 100) + '%' : '0%' }"></div>
                </div>
                <span class="pd-tr-cnt">{{ r.trigger_count }}</span>
              </div>
              <div v-if="!stats.top_rules.length" class="pd-empty">暂无触发记录</div>
            </div>
          </div>
        </div>

        <!-- 右列 -->
        <div class="pd-col pd-col--right">
          <!-- 数据源状态 -->
          <div class="pd-panel" @click="openModule('datasource')">
            <div class="pd-panel__hd">
              <span class="pd-panel__title">数据源</span>
              <span class="pd-panel__badge">{{ stats?.datasource_count ?? 0 }} 个</span>
            </div>
            <div class="pd-ds-list" v-if="stats">
              <div v-for="d in stats.datasources" :key="d.id" class="pd-ds-row">
                <span class="pd-ds-type" :class="`ds--${d.type}`">{{ d.type.toUpperCase() }}</span>
                <span class="pd-ds-name">{{ d.name }}</span>
                <span class="pd-ds-status" :class="`dss--${d.status}`">{{ d.status === 'active' ? '在线' : '离线' }}</span>
              </div>
              <div v-if="!stats.datasources.length" class="pd-empty">暂无数据源</div>
            </div>
          </div>

          <!-- 近期活动流 -->
          <div class="pd-panel pd-panel--activity">
            <div class="pd-panel__hd">
              <span class="pd-panel__title">操作日志</span>
              <span class="pd-panel__badge pd-panel__badge--blue">最近 15 条</span>
            </div>
            <div class="pd-activity" v-if="stats">
              <div v-for="a in stats.recent_activities" :key="a.id" class="pd-act-row">
                <span class="pd-act-dot" :class="`act--${a.type}`"></span>
                <div class="pd-act-body">
                  <span class="pd-act-name">{{ a.target_name || '—' }}</span>
                  <span class="pd-act-type">{{ actionLabel(a.type) }} · {{ a.target_type }}</span>
                </div>
                <span class="pd-act-time">{{ a.time }}</span>
              </div>
              <div v-if="!stats.recent_activities.length" class="pd-empty">暂无操作记录</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 详情侧边栏 -->
    <transition name="slide">
      <div class="pd-drawer" v-if="activeModule" @click.self="activeModule = null">
        <div class="pd-drawer__panel">
          <div class="pd-drawer__hd">
            <span class="pd-drawer__title">{{ drawerTitle }}</span>
            <button class="pd-drawer__close" @click="activeModule = null">✕</button>
          </div>
          <div class="pd-drawer__body">
            <!-- Tier 详情 -->
            <template v-if="activeModule === 'tier' && stats">
              <div v-for="t in stats.tier_distribution" :key="t.tier" class="pd-detail-block">
                <div class="pd-detail-block__hd" :style="{ borderColor: tierColor(t.tier) }">
                  <span class="pd-detail-block__name">Tier {{ t.tier }} — {{ t.name }}</span>
                  <span class="pd-detail-block__cnt">{{ t.count }} 个对象</span>
                </div>
                <div class="pd-detail-entities">
                  <span v-for="e in stats.health_status.filter(h => h.tier === t.tier)" :key="e.id"
                    class="pd-detail-entity-chip" :class="`hc--${e.status}`"
                    @click="openEntityDetail(e.id)">
                    {{ e.name_cn || e.name }}
                  </span>
                </div>
              </div>
            </template>

            <!-- 命名空间详情 -->
            <template v-else-if="activeModule === 'ns' && stats">
              <div v-for="n in stats.ns_distribution" :key="n.ns" class="pd-detail-block">
                <div class="pd-detail-block__hd">
                  <span class="pd-detail-block__name">{{ n.ns }}</span>
                  <span class="pd-detail-block__cnt">{{ n.count }} 个实体</span>
                </div>
                <div class="pd-detail-entities">
                  <span v-for="e in stats.health_status.filter(h => h.name.startsWith(n.ns + '.'))" :key="e.id"
                    class="pd-detail-entity-chip" :class="`hc--${e.status}`"
                    @click="openEntityDetail(e.id)">
                    {{ e.name_cn || e.name }}
                  </span>
                </div>
              </div>
            </template>

            <!-- 规则详情 -->
            <template v-else-if="(activeModule === 'rules' || activeModule === 'top-rules') && stats">
              <div v-for="r in stats.top_rules" :key="r.id" class="pd-detail-rule">
                <div class="pd-detail-rule__hd">
                  <span class="pd-rp-dot" :class="`rp--${r.priority}`"></span>
                  <span class="pd-detail-rule__name">{{ r.name }}</span>
                </div>
                <div class="pd-detail-rule__meta">
                  <span class="pd-meta-chip">触发 {{ r.trigger_count }} 次</span>
                  <span class="pd-meta-chip" :class="r.status === 'active' ? 'chip--green' : 'chip--gray'">{{ r.status }}</span>
                </div>
              </div>
            </template>

            <!-- 健康矩阵详情 -->
            <template v-else-if="activeModule === 'health' && stats">
              <div class="pd-health-summary">
                <div class="pd-hs-card" v-for="s in healthSummary" :key="s.status">
                  <div class="pd-hs-card__val" :class="`hc--${s.status}`">{{ s.count }}</div>
                  <div class="pd-hs-card__lbl">{{ s.label }}</div>
                </div>
              </div>
              <div class="pd-detail-entities" style="margin-top:12px">
                <span v-for="e in stats.health_status" :key="e.id"
                  class="pd-detail-entity-chip" :class="`hc--${e.status}`"
                  @click="openEntityDetail(e.id)">
                  {{ e.name_cn || e.name }}
                </span>
              </div>
            </template>

            <!-- 数据源详情 -->
            <template v-else-if="activeModule === 'datasource' && stats">
              <div v-for="d in stats.datasources" :key="d.id" class="pd-detail-rule">
                <div class="pd-detail-rule__hd">
                  <span class="pd-ds-type" :class="`ds--${d.type}`">{{ d.type.toUpperCase() }}</span>
                  <span class="pd-detail-rule__name">{{ d.name }}</span>
                </div>
                <div class="pd-detail-rule__meta">
                  <span class="pd-meta-chip" :class="d.status === 'active' ? 'chip--green' : 'chip--gray'">
                    {{ d.status === 'active' ? '在线' : '离线' }}
                  </span>
                </div>
              </div>
            </template>

            <!-- KPI 模块 -->
            <template v-else-if="['entity_count','relation_count','rule_count','active_rule_count','action_count','attr_count'].includes(activeModule) && stats">
              <div class="pd-kpi-detail">
                <div class="pd-kpi-detail__val">{{ stats[activeModule as keyof typeof stats] }}</div>
                <div class="pd-kpi-detail__lbl">{{ kpis.find(k => k.key === activeModule)?.label }}</div>
              </div>
              <div class="pd-detail-entities" style="margin-top:16px" v-if="activeModule === 'entity_count'">
                <span v-for="e in stats.health_status" :key="e.id"
                  class="pd-detail-entity-chip" :class="`hc--${e.status}`"
                  @click="openEntityDetail(e.id)">
                  {{ e.name_cn || e.name }}
                </span>
              </div>
            </template>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { dashboardApi } from '../../api/dashboard'

const router = useRouter()
const loading = ref(false)
const stats = ref<any>(null)
const activeModule = ref<string | null>(null)
const currentTime = ref('')

let timer: ReturnType<typeof setInterval> | null = null

function updateTime() {
  const now = new Date()
  currentTime.value = now.toLocaleString('zh-CN', { hour12: false })
}

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)
  loadData()
})
onUnmounted(() => { if (timer) clearInterval(timer) })

async function loadData() {
  loading.value = true
  try {
    stats.value = await dashboardApi.stats()
  } finally {
    loading.value = false
  }
}

const kpis = [
  { key: 'entity_count', field: 'entity_count', label: '本体对象', color: '#3b82f6', trend: null,
    icon: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="2" y="2" width="5" height="5" rx="1.5" fill="currentColor"/><rect x="9" y="2" width="5" height="5" rx="1.5" fill="currentColor" opacity=".6"/><rect x="2" y="9" width="5" height="5" rx="1.5" fill="currentColor" opacity=".6"/><rect x="9" y="9" width="5" height="5" rx="1.5" fill="currentColor" opacity=".3"/></svg>' },
  { key: 'relation_count', field: 'relation_count', label: '实体关系', color: '#8b5cf6', trend: null,
    icon: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="3" cy="8" r="2" fill="currentColor"/><circle cx="13" cy="8" r="2" fill="currentColor"/><path d="M5 8h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>' },
  { key: 'rule_count', field: 'rule_count', label: '业务规则', color: '#f59e0b', trend: null,
    icon: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 4h10M3 8h7M3 12h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>' },
  { key: 'active_rule_count', field: 'active_rule_count', label: '活跃规则', color: '#10b981', trend: null,
    icon: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 8l3 3 7-7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>' },
  { key: 'action_count', field: 'action_count', label: '驱动动作', color: '#ef4444', trend: null,
    icon: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 2l9 6-9 6V2z" fill="currentColor"/></svg>' },
  { key: 'attr_count', field: 'attr_count', label: '属性总数', color: '#06b6d4', trend: null,
    icon: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="5.5" stroke="currentColor" stroke-width="1.5"/><path d="M8 5v3l2 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>' },
]

const maxRulePriority = computed(() => {
  if (!stats.value?.rule_priority) return 1
  return Math.max(...stats.value.rule_priority.map((p: any) => p.count), 1)
})

const maxTrigger = computed(() => {
  if (!stats.value?.top_rules?.length) return 1
  return Math.max(...stats.value.top_rules.map((r: any) => r.trigger_count), 1)
})

const healthSummary = computed(() => {
  if (!stats.value?.health_status) return []
  const map: Record<string, number> = {}
  for (const e of stats.value.health_status) {
    map[e.status] = (map[e.status] || 0) + 1
  }
  return [
    { status: 'active', label: '活跃', count: map['active'] || 0 },
    { status: 'inactive', label: '停用', count: map['inactive'] || 0 },
    { status: 'draft', label: '草稿', count: map['draft'] || 0 },
  ]
})

const drawerTitle = computed(() => {
  const map: Record<string, string> = {
    tier: '对象层级详情', ns: '命名空间详情', rules: '规则详情',
    'top-rules': '规则触发详情', health: '健康矩阵详情', datasource: '数据源详情',
    entity_count: '本体对象', relation_count: '实体关系', rule_count: '业务规则',
    active_rule_count: '活跃规则', action_count: '驱动动作', attr_count: '属性总数',
  }
  return map[activeModule.value || ''] || '详情'
})

function tierColor(tier: number) {
  return ['#3b82f6', '#8b5cf6', '#10b981'][tier - 1] || '#6b7280'
}

function actionLabel(type: string) {
  const m: Record<string, string> = { create: '新建', update: '更新', delete: '删除', execute: '执行' }
  return m[type] || type
}

function openModule(key: string) {
  activeModule.value = activeModule.value === key ? null : key
}

function openEntityDetail(id: string) {
  router.push(`/ontology/${id}`)
}
</script>

<style scoped>
/* ── Root ── */
.pd { display: flex; flex-direction: column; height: 100vh; background: #0a0e1a; color: #f1f5f9; font-family: 'Inter', system-ui, sans-serif; overflow: hidden; }

/* ── Header ── */
.pd-header { display: flex; align-items: center; justify-content: space-between; padding: 0 20px; height: 48px; background: #0d1117; border-bottom: 1px solid #1e2535; flex-shrink: 0; }
.pd-header__left { display: flex; align-items: center; gap: 8px; }
.pd-header__logo { width: 28px; height: 28px; background: #0f172a; border: 1px solid #1e3a5f; border-radius: 6px; display: flex; align-items: center; justify-content: center; }
.pd-header__title { font-size: 13px; font-weight: 600; color: #e2e8f0; }
.pd-header__sep { color: #334155; font-size: 13px; }
.pd-header__sub { font-size: 12px; color: #64748b; }
.pd-header__right { display: flex; align-items: center; gap: 10px; }
.pd-status-dot { width: 7px; height: 7px; border-radius: 50%; background: #10b981; box-shadow: 0 0 6px #10b981; animation: glow 2s ease-in-out infinite; }
@keyframes glow { 0%,100%{box-shadow:0 0 4px #10b981} 50%{box-shadow:0 0 10px #10b981} }
.pd-header__ts { font-size: 11px; color: #475569; font-variant-numeric: tabular-nums; }
.pd-refresh-btn { background: none; border: 1px solid #1e2535; border-radius: 6px; color: #64748b; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all .2s; }
.pd-refresh-btn:hover { color: #3b82f6; border-color: #3b82f6; }
.pd-refresh-btn--spin svg { animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Body ── */
.pd-body { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 14px; }

/* ── KPI Row ── */
.pd-kpi-row { display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; }
.pd-kpi { background: #111827; border: 1px solid #1e2535; border-radius: 10px; padding: 14px; display: flex; align-items: center; gap: 12px; cursor: pointer; transition: all .2s; }
.pd-kpi:hover { border-color: #334155; background: #141d2e; transform: translateY(-1px); }
.pd-kpi--active { border-color: #3b82f6 !important; background: #0f1f3d !important; }
.pd-kpi__icon { width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.pd-kpi__body { flex: 1; min-width: 0; }
.pd-kpi__val { font-size: 22px; font-weight: 700; color: #f1f5f9; line-height: 1; }
.pd-kpi__lbl { font-size: 11px; color: #64748b; margin-top: 3px; }
.pd-kpi__trend-val { font-size: 11px; font-weight: 600; }
.pd-kpi__trend-val.up { color: #10b981; }
.pd-kpi__trend-val.down { color: #ef4444; }

/* ── Grid ── */
.pd-grid { display: grid; grid-template-columns: 260px 1fr 280px; gap: 14px; flex: 1; min-height: 0; }
.pd-col { display: flex; flex-direction: column; gap: 14px; min-height: 0; }

/* ── Panel ── */
.pd-panel { background: #111827; border: 1px solid #1e2535; border-radius: 10px; padding: 14px; cursor: pointer; transition: border-color .2s; }
.pd-panel:hover { border-color: #334155; }
.pd-panel--tall { flex: 1; min-height: 0; overflow: hidden; display: flex; flex-direction: column; }
.pd-panel--activity { flex: 1; min-height: 0; overflow: hidden; display: flex; flex-direction: column; }
.pd-panel__hd { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.pd-panel__title { font-size: 12px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: .06em; }
.pd-panel__badge { font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 4px; background: #1e2535; color: #64748b; }
.pd-panel__badge--green { background: #052e16; color: #10b981; }
.pd-panel__badge--blue { background: #0f1f3d; color: #3b82f6; }

/* ── Tier ── */
.pd-tier-list { display: flex; flex-direction: column; gap: 8px; }
.pd-tier-row { display: grid; grid-template-columns: 64px 1fr 28px 36px; align-items: center; gap: 8px; }
.pd-tier-label { font-size: 11px; color: #94a3b8; }
.pd-tier-bar-wrap { height: 6px; background: #1e2535; border-radius: 3px; overflow: hidden; }
.pd-tier-bar { height: 100%; border-radius: 3px; transition: width .6s ease; }
.pd-tier-cnt { font-size: 12px; font-weight: 600; color: #e2e8f0; text-align: right; }
.pd-tier-pct { font-size: 10px; color: #475569; text-align: right; }

/* ── NS ── */
.pd-ns-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; }
.pd-ns-card { background: #0d1117; border: 1px solid #1e2535; border-radius: 6px; padding: 8px 10px; }
.pd-ns-card__name { font-size: 11px; color: #64748b; margin-bottom: 2px; }
.pd-ns-card__cnt { font-size: 18px; font-weight: 700; color: #e2e8f0; }

/* ── Rule Priority ── */
.pd-rule-priority { display: flex; flex-direction: column; gap: 8px; }
.pd-rp-row { display: grid; grid-template-columns: 10px 64px 24px 1fr; align-items: center; gap: 8px; }
.pd-rp-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.rp--high { background: #ef4444; }
.rp--medium { background: #f59e0b; }
.rp--low { background: #10b981; }
.pd-rp-lbl { font-size: 11px; color: #94a3b8; }
.pd-rp-cnt { font-size: 12px; font-weight: 600; color: #e2e8f0; text-align: right; }
.pd-rp-bar-wrap { height: 5px; background: #1e2535; border-radius: 3px; overflow: hidden; }
.pd-rp-bar { height: 100%; border-radius: 3px; transition: width .6s ease; }
.pd-rp-bar.rp--high { background: #ef4444; }
.pd-rp-bar.rp--medium { background: #f59e0b; }
.pd-rp-bar.rp--low { background: #10b981; }

/* ── Health Matrix ── */
.pd-health-legend { display: flex; align-items: center; gap: 8px; font-size: 10px; color: #475569; }
.pd-hl-dot { width: 7px; height: 7px; border-radius: 2px; }
.hl--active { background: #10b981; }
.hl--inactive { background: #475569; }
.hl--draft { background: #f59e0b; }
.pd-health-grid { display: flex; flex-wrap: wrap; gap: 4px; overflow-y: auto; flex: 1; align-content: flex-start; padding-top: 2px; }
.pd-health-cell { width: 28px; height: 28px; border-radius: 5px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: transform .15s; }
.pd-health-cell:hover { transform: scale(1.15); }
.pd-health-cell__tier { font-size: 9px; font-weight: 700; color: rgba(255,255,255,.7); }
.hc--active { background: #052e16; border: 1px solid #10b981; color: #10b981; }
.hc--inactive { background: #1e2535; border: 1px solid #334155; color: #475569; }
.hc--draft { background: #2d1f00; border: 1px solid #f59e0b; color: #f59e0b; }

/* ── Top Rules ── */
.pd-top-rules { display: flex; flex-direction: column; gap: 8px; }
.pd-tr-row { display: grid; grid-template-columns: 20px 1fr 80px 32px; align-items: center; gap: 8px; }
.pd-tr-rank { width: 20px; height: 20px; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; }
.rank--1 { background: #7c2d12; color: #fb923c; }
.rank--2 { background: #1e1b4b; color: #818cf8; }
.rank--3 { background: #052e16; color: #4ade80; }
.rank--rest { background: #1e2535; color: #475569; }
.pd-tr-name { font-size: 11px; color: #94a3b8; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pd-tr-bar-wrap { height: 5px; background: #1e2535; border-radius: 3px; overflow: hidden; }
.pd-tr-bar { height: 100%; background: linear-gradient(90deg, #3b82f6, #8b5cf6); border-radius: 3px; transition: width .6s ease; }
.pd-tr-cnt { font-size: 11px; font-weight: 600; color: #e2e8f0; text-align: right; }

/* ── Datasource ── */
.pd-ds-list { display: flex; flex-direction: column; gap: 6px; }
.pd-ds-row { display: flex; align-items: center; gap: 8px; padding: 6px 8px; background: #0d1117; border-radius: 6px; }
.pd-ds-type { font-size: 9px; font-weight: 700; padding: 2px 5px; border-radius: 3px; flex-shrink: 0; }
.ds--mysql { background: #1a2744; color: #60a5fa; }
.ds--postgresql { background: #1a2744; color: #818cf8; }
.ds--oracle { background: #2d1f00; color: #fb923c; }
.ds--sqlserver { background: #1e1b4b; color: #a78bfa; }
.pd-ds-name { flex: 1; font-size: 12px; color: #94a3b8; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pd-ds-status { font-size: 10px; font-weight: 600; flex-shrink: 0; }
.dss--active { color: #10b981; }
.dss--inactive { color: #475569; }

/* ── Activity ── */
.pd-activity { display: flex; flex-direction: column; gap: 6px; overflow-y: auto; flex: 1; }
.pd-act-row { display: flex; align-items: flex-start; gap: 8px; padding: 6px 0; border-bottom: 1px solid #1e2535; }
.pd-act-row:last-child { border-bottom: none; }
.pd-act-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; margin-top: 4px; }
.act--create { background: #10b981; }
.act--update { background: #3b82f6; }
.act--delete { background: #ef4444; }
.act--execute { background: #f59e0b; }
.pd-act-body { flex: 1; min-width: 0; }
.pd-act-name { display: block; font-size: 12px; color: #e2e8f0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pd-act-type { font-size: 10px; color: #475569; }
.pd-act-time { font-size: 10px; color: #334155; flex-shrink: 0; white-space: nowrap; }

/* ── Empty ── */
.pd-empty { font-size: 12px; color: #334155; text-align: center; padding: 16px 0; }

/* ── Skeleton ── */
.pd-skeleton-rows { height: 80px; background: linear-gradient(90deg, #1e2535 25%, #253047 50%, #1e2535 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: 6px; }
.pd-skeleton-grid { flex: 1; background: linear-gradient(90deg, #1e2535 25%, #253047 50%, #1e2535 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: 6px; }
@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }

/* ── Drawer ── */
.pd-drawer { position: fixed; inset: 0; z-index: 100; display: flex; justify-content: flex-end; }
.pd-drawer__panel { width: 380px; height: 100%; background: #0d1117; border-left: 1px solid #1e2535; display: flex; flex-direction: column; box-shadow: -20px 0 60px rgba(0,0,0,.5); }
.pd-drawer__hd { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid #1e2535; flex-shrink: 0; }
.pd-drawer__title { font-size: 14px; font-weight: 600; color: #e2e8f0; }
.pd-drawer__close { background: none; border: 1px solid #1e2535; border-radius: 6px; color: #64748b; width: 28px; height: 28px; cursor: pointer; font-size: 12px; display: flex; align-items: center; justify-content: center; transition: all .2s; }
.pd-drawer__close:hover { color: #e2e8f0; border-color: #334155; }
.pd-drawer__body { flex: 1; overflow-y: auto; padding: 16px 20px; display: flex; flex-direction: column; gap: 12px; }

/* Drawer content */
.pd-detail-block { background: #111827; border: 1px solid #1e2535; border-radius: 8px; padding: 12px; }
.pd-detail-block__hd { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; padding-left: 8px; border-left: 3px solid #334155; }
.pd-detail-block__name { font-size: 12px; font-weight: 600; color: #e2e8f0; }
.pd-detail-block__cnt { font-size: 11px; color: #64748b; }
.pd-detail-entities { display: flex; flex-wrap: wrap; gap: 6px; }
.pd-detail-entity-chip { font-size: 11px; padding: 3px 8px; border-radius: 5px; cursor: pointer; transition: transform .15s; }
.pd-detail-entity-chip:hover { transform: scale(1.05); }
.pd-detail-entity-chip.hc--active { background: #052e16; border: 1px solid #10b981; color: #4ade80; }
.pd-detail-entity-chip.hc--inactive { background: #1e2535; border: 1px solid #334155; color: #64748b; }
.pd-detail-entity-chip.hc--draft { background: #2d1f00; border: 1px solid #f59e0b; color: #fbbf24; }
.pd-detail-rule { background: #111827; border: 1px solid #1e2535; border-radius: 8px; padding: 10px 12px; }
.pd-detail-rule__hd { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.pd-detail-rule__name { font-size: 12px; color: #e2e8f0; }
.pd-detail-rule__meta { display: flex; gap: 6px; flex-wrap: wrap; }
.pd-meta-chip { font-size: 10px; padding: 2px 7px; border-radius: 4px; background: #1e2535; color: #64748b; }
.chip--green { background: #052e16; color: #10b981; }
.chip--gray { background: #1e2535; color: #475569; }
.pd-health-summary { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.pd-hs-card { background: #111827; border: 1px solid #1e2535; border-radius: 8px; padding: 12px; text-align: center; }
.pd-hs-card__val { font-size: 24px; font-weight: 700; }
.pd-hs-card__lbl { font-size: 11px; color: #64748b; margin-top: 4px; }
.pd-kpi-detail { text-align: center; padding: 24px 0; }
.pd-kpi-detail__val { font-size: 56px; font-weight: 700; color: #3b82f6; }
.pd-kpi-detail__lbl { font-size: 14px; color: #64748b; margin-top: 8px; }

/* ── Slide transition ── */
.slide-enter-active, .slide-leave-active { transition: transform .25s ease; }
.slide-enter-from, .slide-leave-to { transform: translateX(100%); }
.slide-enter-to, .slide-leave-from { transform: translateX(0); }
</style>
