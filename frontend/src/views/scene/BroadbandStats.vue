<template>
  <div class="bs-page">
    <div class="bs-header">
      <RouterLink to="/scene/broadband" class="bs-back">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M10 12L6 8l4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        返回列表
      </RouterLink>
      <h1 class="bs-header__title">退单稽核统计分析</h1>
    </div>

    <PageState :loading="loading" :empty="!loading && !stats">
    <template v-if="stats && overview">

    <!-- KPI -->
    <div class="bs-kpis">
      <div class="bs-kpi" v-for="kpi in kpis" :key="kpi.label">
        <div class="bs-kpi__val" :style="{ color: kpi.color }">{{ kpi.value }}</div>
        <div class="bs-kpi__lbl">{{ kpi.label }}</div>
      </div>
    </div>

    <div class="bs-grid">
      <!-- 根因分布 -->
      <div class="bs-card">
        <div class="bs-card__head">根因分布</div>
        <div class="bs-pie-wrap">
          <div class="bs-pie">
            <svg viewBox="0 0 120 120">
              <circle v-for="(seg, i) in pieSegments" :key="i"
                cx="60" cy="60" r="50"
                fill="none" :stroke="seg.color" stroke-width="20"
                :stroke-dasharray="seg.dash" :stroke-dashoffset="seg.offset"
                :style="{ transition: 'stroke-dasharray 0.5s, stroke-dashoffset 0.5s' }" />
            </svg>
          </div>
          <div class="bs-pie-legend">
            <div v-for="(item, i) in stats.cause_distribution" :key="i" class="bs-pie-legend__item">
              <span class="bs-pie-legend__dot" :style="{ background: causeColors[item.name] || '#adb5bd' }"></span>
              <span class="bs-pie-legend__name">{{ item.name }}</span>
              <span class="bs-pie-legend__val">{{ item.value }}</span>
              <span class="bs-pie-legend__pct">{{ causePct(item.value) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 稽核状态分布 -->
      <div class="bs-card">
        <div class="bs-card__head">稽核状态分布</div>
        <div class="bs-hbar-list">
          <div v-for="item in stats.audit_status_distribution" :key="item.name" class="bs-hbar">
            <span class="bs-hbar__lbl">{{ item.name }}</span>
            <div class="bs-hbar__track">
              <div class="bs-hbar__fill" :style="{ width: statusPct(item.value), background: statusColor(item.name) }"></div>
            </div>
            <span class="bs-hbar__val">{{ item.value }}</span>
          </div>
        </div>
      </div>

      <!-- 17小类退单原因分布 -->
      <div class="bs-card bs-card--wide">
        <div class="bs-card__head">退单原因17小类分布</div>
        <div class="bs-sub-dist">
          <div v-for="item in stats.subcategory_distribution" :key="item.name" class="bs-hbar">
            <span class="bs-hbar__lbl">{{ item.name }}</span>
            <div class="bs-hbar__track">
              <div class="bs-hbar__fill" :style="{ width: subPct(item.value), background: causeColors[item.category] || '#adb5bd' }"></div>
            </div>
            <span class="bs-hbar__val">{{ item.value }}</span>
          </div>
        </div>
      </div>

      <!-- 退单趋势 -->
      <div class="bs-card bs-card--wide">
        <div class="bs-card__head">退单趋势 (近30天)</div>
        <div class="bs-trend">
          <div class="bs-trend__bars">
            <div v-for="d in trendData" :key="d.date" class="bs-trend__col" :title="`${d.date}: ${d.count}单`">
              <div class="bs-trend__bar" :style="{ height: trendHeight(d.count) }"></div>
              <span class="bs-trend__date">{{ d.date.slice(5) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 工程师退单排名 -->
      <div class="bs-card">
        <div class="bs-card__head">工程师退单排名 TOP15</div>
        <div class="bs-rank-table-wrap">
          <table class="bs-rank-table">
            <thead><tr><th>#</th><th>姓名</th><th>班组</th><th>级别</th><th>退单数</th><th>虚报数</th><th>90日退单率</th></tr></thead>
            <tbody>
              <tr v-for="(e, i) in stats.engineer_ranking" :key="e.engineer_id">
                <td><span class="bs-rank-num" :class="i < 3 ? 'bs-rank-num--top' : ''">{{ i + 1 }}</span></td>
                <td>{{ e.engineer_name }}</td>
                <td>{{ e.team_name }}</td>
                <td>{{ e.tech_level }}</td>
                <td class="bs-rank-table__val">{{ e.churn_count }}</td>
                <td class="bs-rank-table__val" :style="e.false_report_count > 0 ? 'color:var(--status-error)' : ''">{{ e.false_report_count }}</td>
                <td>
                  <div class="bs-mini-bar">
                    <div class="bs-mini-bar__fill" :style="{ width: (e.churn_rate_90d * 100) + '%' }" :class="e.churn_rate_90d > 0.15 ? 'bs-mini-bar__fill--danger' : ''"></div>
                    <span>{{ (e.churn_rate_90d * 100).toFixed(1) }}%</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 渠道退单统计 -->
      <div class="bs-card">
        <div class="bs-card__head">渠道退单统计</div>
        <div class="bs-rank-table-wrap">
          <table class="bs-rank-table">
            <thead><tr><th>渠道</th><th>类型</th><th>退单数</th><th>退单率</th></tr></thead>
            <tbody>
              <tr v-for="ch in stats.channel_stats" :key="ch.channel_id">
                <td>{{ ch.channel_name }}</td>
                <td><span class="bs-tag">{{ ch.channel_type }}</span></td>
                <td class="bs-rank-table__val">{{ ch.churn_count }}</td>
                <td>
                  <div class="bs-mini-bar">
                    <div class="bs-mini-bar__fill" :style="{ width: (ch.hist_churn_rate * 100) + '%' }"></div>
                    <span>{{ (ch.hist_churn_rate * 100).toFixed(1) }}%</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 地址热点 -->
      <div class="bs-card bs-card--wide">
        <div class="bs-card__head">退单热点区域 TOP15</div>
        <div class="bs-rank-table-wrap">
          <table class="bs-rank-table">
            <thead><tr><th>社区名称</th><th>资源状态</th><th>无条件受理</th><th>退单数</th><th>历史退单率</th></tr></thead>
            <tbody>
              <tr v-for="a in stats.address_hotspots" :key="a.community_name">
                <td>{{ a.community_name }}</td>
                <td><span class="bs-tag" :class="resClass(a.resource_status)">{{ a.resource_status }}</span></td>
                <td>{{ a.is_unconditional_accept ? '是' : '否' }}</td>
                <td class="bs-rank-table__val">{{ a.churn_count }}</td>
                <td>
                  <div class="bs-mini-bar">
                    <div class="bs-mini-bar__fill" :style="{ width: (a.hist_churn_rate * 100 * 3) + '%' }" :class="a.hist_churn_rate > 0.15 ? 'bs-mini-bar__fill--danger' : ''"></div>
                    <span>{{ (a.hist_churn_rate * 100).toFixed(1) }}%</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    </template>
    </PageState>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import PageState from '../../components/common/PageState.vue'
import { broadbandApi } from '../../api/broadband'
import type { BroadbandOverview, BroadbandStats } from '../../api/broadband'

const loading = ref(true)
const overview = ref<BroadbandOverview | null>(null)
const stats = ref<BroadbandStats | null>(null)

const causeColors: Record<string, string> = {
  '用户原因': '#339af0', '施工原因': '#f59f00', '资源原因': '#fa5252', '业务原因': '#20c997',
}
const statusColors: Record<string, string> = {
  '待稽核': '#f59f00', '推理中': '#339af0', '待补全回访': '#e67700', '强制回访待核实': '#e67700', '待人工审核': '#fa5252', '已归档': '#12b886',
}

const kpis = computed(() => {
  const o = overview.value
  if (!o) return []
  return [
    { label: '总退单数', value: o.total, color: 'var(--neutral-900)' },
    { label: '待稽核', value: o.pending, color: '#f59f00' },
    { label: '待人工审核', value: o.manual_review, color: '#fa5252' },
    { label: '已归档', value: o.archived, color: '#12b886' },
    { label: '平均置信度', value: (o.avg_confidence * 100).toFixed(1) + '%', color: 'var(--semantic-600)' },
    { label: '稽核准确率', value: (o.accuracy_rate * 100).toFixed(1) + '%', color: 'var(--semantic-600)' },
  ]
})

const causeTotal = computed(() => stats.value?.cause_distribution.reduce((s, i) => s + i.value, 0) || 1)
function causePct(v: number) { return ((v / causeTotal.value) * 100).toFixed(1) + '%' }

const pieSegments = computed(() => {
  const items = stats.value?.cause_distribution || []
  const total = causeTotal.value
  const circ = 2 * Math.PI * 50
  let offset = 0
  return items.map(item => {
    const pct = item.value / total
    const dash = `${pct * circ} ${circ}`
    const seg = { color: causeColors[item.name] || '#adb5bd', dash, offset: -offset + circ * 0.25 }
    offset += pct * circ
    return seg
  })
})

const trendData = computed(() => {
  const d = stats.value?.trend_daily || []
  return [...d].reverse().slice(-30)
})
const trendMax = computed(() => Math.max(...trendData.value.map(d => d.count), 1))
function trendHeight(v: number) { return Math.max(4, (v / trendMax.value) * 120) + 'px' }

function statusPct(v: number) {
  const max = Math.max(...(stats.value?.audit_status_distribution || []).map(i => i.value), 1)
  return (v / max * 100) + '%'
}
function statusColor(s: string) { return statusColors[s] || '#adb5bd' }

const subMax = computed(() => Math.max(...(stats.value?.subcategory_distribution || []).map(i => i.value), 1))
function subPct(v: number) { return (v / subMax.value * 100) + '%' }

function resClass(s: string) {
  if (s === '资源充足') return 'bs-tag--success'
  if (s === '资源紧张' || s === '建设中') return 'bs-tag--warning'
  if (s === '资源不足' || s === '未覆盖') return 'bs-tag--danger'
  return ''
}

onMounted(async () => {
  loading.value = true
  try {
    const [ov, st] = await Promise.all([broadbandApi.overview(), broadbandApi.stats()])
    overview.value = ov
    stats.value = st
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.bs-page { padding: 24px; }
.bs-header { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }
.bs-back { display: flex; align-items: center; gap: 4px; color: var(--semantic-500); text-decoration: none; font-size: 13px; }
.bs-back:hover { text-decoration: underline; }
.bs-header__title { font-size: 20px; font-weight: 700; color: var(--neutral-900); margin: 0; }

.bs-kpis { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin-bottom: 20px; }
.bs-kpi { padding: 16px; background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); text-align: center; }
.bs-kpi__val { font-size: 26px; font-weight: 700; }
.bs-kpi__lbl { font-size: 11px; color: var(--neutral-500); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.3px; }

.bs-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.bs-card { background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); overflow: hidden; }
.bs-card--wide { grid-column: 1 / -1; }
.bs-card__head { padding: 12px 16px; font-size: 14px; font-weight: 600; color: var(--neutral-800); background: var(--neutral-50); border-bottom: 1px solid var(--neutral-200); }

.bs-pie-wrap { display: flex; align-items: center; gap: 24px; padding: 20px; }
.bs-pie { width: 140px; height: 140px; flex-shrink: 0; }
.bs-pie svg { width: 100%; height: 100%; transform: rotate(-90deg); }
.bs-pie-legend { flex: 1; }
.bs-pie-legend__item { display: flex; align-items: center; gap: 8px; padding: 4px 0; font-size: 13px; }
.bs-pie-legend__dot { width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; }
.bs-pie-legend__name { flex: 1; color: var(--neutral-700); }
.bs-pie-legend__val { font-weight: 600; color: var(--neutral-800); min-width: 30px; text-align: right; }
.bs-pie-legend__pct { font-size: 11px; color: var(--neutral-500); min-width: 40px; text-align: right; }

.bs-hbar-list { padding: 16px; }
.bs-sub-dist { padding: 16px; }
.bs-hbar { display: flex; align-items: center; gap: 8px; padding: 6px 0; }
.bs-hbar__lbl { font-size: 12px; color: var(--neutral-600); min-width: 90px; }
.bs-hbar__track { flex: 1; height: 8px; background: var(--neutral-100); border-radius: 4px; overflow: hidden; }
.bs-hbar__fill { height: 100%; border-radius: 4px; transition: width 0.4s; }
.bs-hbar__val { font-size: 12px; font-weight: 600; color: var(--neutral-700); min-width: 30px; text-align: right; }

.bs-trend { padding: 16px; overflow-x: auto; }
.bs-trend__bars { display: flex; align-items: flex-end; gap: 4px; height: 150px; }
.bs-trend__col { display: flex; flex-direction: column; align-items: center; flex: 1; min-width: 18px; }
.bs-trend__bar { width: 100%; max-width: 24px; background: var(--semantic-400); border-radius: 3px 3px 0 0; transition: height 0.3s; }
.bs-trend__bar:hover { background: var(--semantic-600); }
.bs-trend__date { font-size: 9px; color: var(--neutral-400); margin-top: 4px; white-space: nowrap; }

.bs-rank-table-wrap { max-height: 400px; overflow-y: auto; }
.bs-rank-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.bs-rank-table th { text-align: left; padding: 8px 12px; font-size: 11px; font-weight: 600; color: var(--neutral-500); border-bottom: 1px solid var(--neutral-200); position: sticky; top: 0; background: var(--neutral-0); }
.bs-rank-table td { padding: 8px 12px; border-bottom: 1px solid var(--neutral-50); color: var(--neutral-700); }
.bs-rank-table tr:hover td { background: var(--semantic-50); }
.bs-rank-table__val { font-weight: 600; color: var(--neutral-800); }

.bs-rank-num { display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: var(--radius-full); font-size: 11px; font-weight: 600; background: var(--neutral-100); color: var(--neutral-600); }
.bs-rank-num--top { background: var(--kinetic-500); color: #fff; }

.bs-mini-bar { display: flex; align-items: center; gap: 6px; }
.bs-mini-bar__fill { height: 6px; border-radius: 3px; background: var(--semantic-400); max-width: 80px; }
.bs-mini-bar__fill--danger { background: var(--status-error); }
.bs-mini-bar span { font-size: 11px; color: var(--neutral-600); }

.bs-tag { display: inline-block; padding: 1px 6px; border-radius: var(--radius-sm); font-size: 11px; background: var(--neutral-100); color: var(--neutral-600); }
.bs-tag--success { background: var(--status-success-bg); color: var(--status-success); }
.bs-tag--warning { background: var(--status-warning-bg); color: #e67700; }
.bs-tag--danger { background: var(--status-error-bg); color: var(--status-error); }
</style>
