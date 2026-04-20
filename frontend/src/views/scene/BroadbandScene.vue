<template>
  <div class="bb-scene">
    <!-- Header -->
    <div class="bb-header">
      <div class="bb-header__left">
        <div class="bb-header__icon">
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
            <path d="M9 11l2 2 4-4" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="11" cy="11" r="9" stroke="#fff" stroke-width="2"/>
          </svg>
        </div>
        <div>
          <h1 class="bb-header__title">宽带装机退单原因稽核</h1>
          <p class="bb-header__desc">基于订单、派单、录音、地址库等多源数据，通过本体规则自动判断退单原因合理性</p>
        </div>
      </div>
      <div class="bb-header__badges">
        <span class="bb-badge bb-badge--blue">本体驱动</span>
        <span class="bb-badge bb-badge--green">实时稽核</span>
      </div>
    </div>

    <!-- Stats -->
    <div class="bb-stats" v-if="stats">
      <div class="bb-stat-card">
        <div class="bb-stat-card__value">{{ stats.total_orders }}</div>
        <div class="bb-stat-card__label">总工单数</div>
      </div>
      <div class="bb-stat-card">
        <div class="bb-stat-card__value bb-stat-card__value--warn">{{ stats.total_churns }}</div>
        <div class="bb-stat-card__label">退单总数</div>
        <div class="bb-stat-card__sub">占比 {{ churnRate }}%</div>
      </div>
      <div class="bb-stat-card">
        <div class="bb-stat-card__value bb-stat-card__value--success">{{ stats.archived }}</div>
        <div class="bb-stat-card__label">已归档</div>
        <div class="bb-stat-card__sub">自动稽核通过</div>
      </div>
      <div class="bb-stat-card">
        <div class="bb-stat-card__value bb-stat-card__value--orange">{{ stats.manual_review }}</div>
        <div class="bb-stat-card__label">人工审核中</div>
      </div>
      <div class="bb-stat-card">
        <div class="bb-stat-card__value bb-stat-card__value--gray">{{ stats.pending_callback }}</div>
        <div class="bb-stat-card__label">待补全回访</div>
      </div>
      <div class="bb-stat-card">
        <div class="bb-stat-card__value bb-stat-card__value--blue">{{ (stats.avg_confidence * 100).toFixed(1) }}%</div>
        <div class="bb-stat-card__label">平均置信度</div>
      </div>
    </div>

    <!-- Cause Distribution + Filter -->
    <div class="bb-toolbar">
      <div class="bb-cause-pills">
        <button class="bb-pill" :class="{ 'bb-pill--active': filterCause === '' }" @click="filterCause = ''; loadList()">全部</button>
        <button
          v-for="(cnt, cause) in stats?.cause_distribution"
          :key="cause"
          class="bb-pill"
          :class="['bb-pill--' + causeColor(String(cause)), { 'bb-pill--active': filterCause === String(cause) }]"
          @click="filterCause = String(cause); loadList()"
        >{{ cause }} <span class="bb-pill__cnt">{{ cnt }}</span></button>
      </div>
      <div class="bb-status-filter">
        <select v-model="filterStatus" @change="loadList()" class="bb-select">
          <option value="">全部状态</option>
          <option value="已归档">已归档</option>
          <option value="人工审核中">人工审核中</option>
          <option value="待补全回访">待补全回访</option>
        </select>
      </div>
    </div>

    <!-- Main content: list + detail -->
    <div class="bb-main">
      <!-- List -->
      <div class="bb-list">
        <div v-if="listLoading" class="bb-loading">加载中...</div>
        <div
          v-for="item in list"
          :key="item.churn_id"
          class="bb-list-item"
          :class="{ 'bb-list-item--active': selectedId === item.churn_id }"
          @click="selectChurn(item.churn_id)"
        >
          <div class="bb-list-item__top">
            <span class="bb-list-item__id">{{ item.churn_id }}</span>
            <span class="bb-status-tag" :class="statusClass(item.audit_status)">{{ item.audit_status }}</span>
          </div>
          <div class="bb-list-item__order">工单 {{ item.related_order_no }}</div>
          <div class="bb-list-item__meta">
            <span class="bb-cause-tag" :class="'bb-cause-tag--' + causeColor(item.root_cause_level_one)">{{ item.root_cause_level_one }}</span>
            <span class="bb-list-item__l2">{{ item.root_cause_level_two }}</span>
          </div>
          <div class="bb-list-item__bottom">
            <span class="bb-conf-bar-wrap">
              <span class="bb-conf-bar" :style="{ width: confPct(item.root_cause_confidence) + '%', background: confColor(item.root_cause_confidence) }"></span>
            </span>
            <span class="bb-conf-val">{{ confPct(item.root_cause_confidence) }}%</span>
            <span class="bb-list-item__time">{{ fmtDate(item.churn_time) }}</span>
          </div>
        </div>
        <!-- Pagination -->
        <div class="bb-pagination">
          <button class="bb-page-btn" :disabled="page <= 1" @click="page--; loadList()">‹</button>
          <span class="bb-page-info">{{ page }} / {{ totalPages }}</span>
          <button class="bb-page-btn" :disabled="page >= totalPages" @click="page++; loadList()">›</button>
        </div>
      </div>

      <!-- Detail -->
      <div class="bb-detail" v-if="detail">
        <div class="bb-detail__header">
          <div>
            <div class="bb-detail__id">{{ detail.churn.churn_id }}</div>
            <div class="bb-detail__order">工单号：{{ detail.churn.related_order_no }}</div>
          </div>
          <span class="bb-status-tag bb-status-tag--lg" :class="statusClass(detail.churn.audit_status)">{{ detail.churn.audit_status }}</span>
        </div>

        <!-- Tabs -->
        <div class="bb-detail__tabs">
          <button v-for="t in detailTabs" :key="t" class="bb-detail__tab" :class="{ 'bb-detail__tab--active': detailTab === t }" @click="detailTab = t">{{ t }}</button>
        </div>

        <!-- Tab: 稽核结论 -->
        <div v-if="detailTab === '稽核结论'" class="bb-detail__body">
          <div class="bb-conclusion">
            <div class="bb-conclusion__cause">
              <div class="bb-conclusion__label">根因判定</div>
              <div class="bb-conclusion__l1" :class="'bb-cause-tag--' + causeColor(detail.churn.root_cause_level_one)">{{ detail.churn.root_cause_level_one }}</div>
              <div class="bb-conclusion__arrow">›</div>
              <div class="bb-conclusion__l2">{{ detail.churn.root_cause_level_two }}</div>
            </div>
            <div class="bb-conf-meter">
              <div class="bb-conf-meter__label">置信度</div>
              <div class="bb-conf-meter__bar-wrap">
                <div class="bb-conf-meter__bar" :style="{ width: confPct(detail.churn.root_cause_confidence) + '%', background: confColor(detail.churn.root_cause_confidence) }"></div>
              </div>
              <div class="bb-conf-meter__val">{{ confPct(detail.churn.root_cause_confidence) }}%</div>
            </div>
            <div class="bb-info-grid">
              <div class="bb-info-row"><span class="bb-info-key">退单阶段</span><span class="bb-info-val">{{ detail.churn.churn_phase }}</span></div>
              <div class="bb-info-row"><span class="bb-info-key">退单时间</span><span class="bb-info-val">{{ fmtDate(detail.churn.churn_time) }}</span></div>
              <div class="bb-info-row"><span class="bb-info-key">产品</span><span class="bb-info-val">{{ detail.churn.product_name }}</span></div>
              <div class="bb-info-row"><span class="bb-info-key">业务类型</span><span class="bb-info-val">{{ detail.churn.biz_type }}</span></div>
              <div class="bb-info-row"><span class="bb-info-key">渠道</span><span class="bb-info-val">{{ detail.churn.channel_id }}</span></div>
              <div class="bb-info-row"><span class="bb-info-key">安装地址</span><span class="bb-info-val bb-info-val--addr">{{ detail.churn.install_address }}</span></div>
              <div class="bb-info-row" v-if="detail.churn.triggered_action_type"><span class="bb-info-key">触发动作</span><span class="bb-info-val bb-info-val--action">{{ detail.churn.triggered_action_type }}</span></div>
            </div>
            <div class="bb-evidence-summary" v-if="detail.churn.evidence_chain_summary">
              <div class="bb-evidence-summary__label">证据链摘要</div>
              <div class="bb-evidence-summary__text">{{ detail.churn.evidence_chain_summary }}</div>
            </div>
          </div>
        </div>

        <!-- Tab: 证据链 -->
        <div v-else-if="detailTab === '证据链'" class="bb-detail__body">
          <div class="bb-evidence-list">
            <div v-for="ev in detail.evidences" :key="ev.evidence_id" class="bb-ev-item" :class="{ 'bb-ev-item--hit': ev.hit }">
              <div class="bb-ev-item__left">
                <span class="bb-ev-hit" :class="ev.hit ? 'bb-ev-hit--yes' : 'bb-ev-hit--no'">{{ ev.hit ? '命中' : '未中' }}</span>
                <span class="bb-ev-code">{{ ev.evidence_code }}</span>
                <span class="bb-ev-type">{{ ev.evidence_type }}</span>
              </div>
              <div class="bb-ev-item__content">{{ ev.content }}</div>
              <div class="bb-ev-item__right">
                <span class="bb-ev-conf" :style="{ color: confColor(ev.confidence) }">{{ confPct(ev.confidence) }}%</span>
                <span class="bb-ev-src">{{ ev.source_type }}</span>
              </div>
            </div>
            <div v-if="!detail.evidences.length" class="bb-empty">暂无证据记录</div>
          </div>
        </div>

        <!-- Tab: 派单信息 -->
        <div v-else-if="detailTab === '派单信息'" class="bb-detail__body">
          <div v-if="detail.dispatch.length" class="bb-dispatch">
            <div v-for="d in detail.dispatch" :key="d.dispatch_id" class="bb-dispatch-card">
              <div class="bb-dispatch-card__eng">
                <span class="bb-eng-name">{{ d.engineer_name }}</span>
                <span class="bb-eng-level">{{ d.engineer_level }}</span>
                <span class="bb-eng-type">{{ d.employment_type }}</span>
              </div>
              <div class="bb-info-grid">
                <div class="bb-info-row"><span class="bb-info-key">预约时间</span><span class="bb-info-val">{{ fmtDate(d.appointed_time) }}</span></div>
                <div class="bb-info-row"><span class="bb-info-key">实际到达</span><span class="bb-info-val">{{ fmtDate(d.actual_arrival_time) }}</span></div>
                <div class="bb-info-row"><span class="bb-info-key">迟到分钟</span><span class="bb-info-val" :class="d.late_minutes > 30 ? 'bb-info-val--warn' : ''">{{ d.late_minutes }} 分钟</span></div>
                <div class="bb-info-row"><span class="bb-info-key">改约次数</span><span class="bb-info-val">{{ d.reschedule_count }}</span></div>
                <div class="bb-info-row" v-if="d.exception_type"><span class="bb-info-key">异常类型</span><span class="bb-info-val bb-info-val--warn">{{ d.exception_type }}</span></div>
              </div>
            </div>
          </div>
          <div v-else class="bb-empty">暂无派单记录</div>
        </div>

        <!-- Tab: 审计轨迹 -->
        <div v-else-if="detailTab === '审计轨迹'" class="bb-detail__body">
          <div class="bb-trail">
            <div v-for="(t, i) in detail.trails" :key="i" class="bb-trail-item">
              <div class="bb-trail-item__dot"></div>
              <div class="bb-trail-item__body">
                <div class="bb-trail-item__action">{{ t.action_type }}</div>
                <div class="bb-trail-item__meta">{{ t.operator_name }} · {{ fmtDate(t.action_time) }}</div>
                <div class="bb-trail-item__status">{{ t.from_status }} → {{ t.to_status }}</div>
                <div class="bb-trail-item__remark" v-if="t.remark">{{ t.remark }}</div>
              </div>
            </div>
            <div v-if="!detail.trails.length" class="bb-empty">暂无轨迹记录</div>
          </div>
        </div>
      </div>

      <!-- Empty detail -->
      <div class="bb-detail bb-detail--empty" v-else>
        <div class="bb-detail__placeholder">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none" opacity="0.3">
            <path d="M12 8h24l6 6v26H6V8h6z" stroke="currentColor" stroke-width="2"/>
            <path d="M16 20h16M16 26h12M16 32h8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
          <p>选择左侧退单记录查看详情</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const stats = ref<any>(null)
const list = ref<any[]>([])
const listLoading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 20
const filterStatus = ref('')
const filterCause = ref('')
const selectedId = ref<string | null>(null)
const detail = ref<any>(null)
const detailTab = ref('稽核结论')
const detailTabs = ['稽核结论', '证据链', '派单信息', '审计轨迹']

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const churnRate = computed(() => stats.value ? ((stats.value.total_churns / stats.value.total_orders) * 100).toFixed(1) : '0')

const api = axios.create({ baseURL: '/api/v1' })

async function loadStats() {
  const r = await api.get('/scenes/broadband/stats')
  stats.value = r.data
}

async function loadList() {
  listLoading.value = true
  selectedId.value = null
  detail.value = null
  try {
    const r = await api.get('/scenes/broadband/churns', {
      params: { status: filterStatus.value, cause_l1: filterCause.value, page: page.value, page_size: pageSize }
    })
    list.value = r.data.items
    total.value = r.data.total
  } finally {
    listLoading.value = false
  }
}

async function selectChurn(id: string) {
  selectedId.value = id
  detailTab.value = '稽核结论'
  const r = await api.get(`/scenes/broadband/churns/${id}`)
  detail.value = r.data
}

function causeColor(cause: string) {
  const map: Record<string, string> = { '施工原因': 'red', '用户原因': 'blue', '资源原因': 'orange', '业务原因': 'purple' }
  return map[cause] || 'gray'
}

function statusClass(s: string) {
  if (s === '已归档') return 'bb-status-tag--green'
  if (s === '人工审核中') return 'bb-status-tag--orange'
  if (s === '待补全回访') return 'bb-status-tag--gray'
  return ''
}

function confPct(v: any) {
  return v ? Math.round(Number(v) * 100) : 0
}

function confColor(v: any) {
  const p = confPct(v)
  if (p >= 85) return '#10b981'
  if (p >= 60) return '#f59e0b'
  return '#ef4444'
}

function fmtDate(s: string) {
  if (!s) return '-'
  return s.replace('T', ' ').slice(0, 16)
}

onMounted(async () => {
  await Promise.all([loadStats(), loadList()])
})
</script>

<style scoped>
.bb-scene { display: flex; flex-direction: column; height: 100%; padding: 20px; gap: 16px; overflow: hidden; }

/* Header */
.bb-header { display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; }
.bb-header__left { display: flex; align-items: center; gap: 14px; }
.bb-header__icon { width: 44px; height: 44px; border-radius: 10px; background: var(--kinetic-600); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.bb-header__title { font-size: 18px; font-weight: 700; color: var(--neutral-900); margin: 0; }
.bb-header__desc { font-size: 12px; color: var(--neutral-500); margin: 3px 0 0; }
.bb-header__badges { display: flex; gap: 8px; }
.bb-badge { font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 20px; }
.bb-badge--blue { background: var(--semantic-100); color: var(--semantic-700); }
.bb-badge--green { background: var(--dynamic-100); color: var(--dynamic-700); }

/* Stats */
.bb-stats { display: flex; gap: 10px; flex-shrink: 0; }
.bb-stat-card { flex: 1; padding: 14px 16px; background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); }
.bb-stat-card__value { font-size: 26px; font-weight: 700; color: var(--neutral-900); line-height: 1; }
.bb-stat-card__value--warn { color: var(--kinetic-600); }
.bb-stat-card__value--success { color: var(--dynamic-600); }
.bb-stat-card__value--orange { color: #f59e0b; }
.bb-stat-card__value--gray { color: var(--neutral-500); }
.bb-stat-card__value--blue { color: var(--semantic-600); }
.bb-stat-card__label { font-size: 12px; color: var(--neutral-500); margin-top: 4px; }
.bb-stat-card__sub { font-size: 11px; color: var(--neutral-400); margin-top: 2px; }

/* Toolbar */
.bb-toolbar { display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; }
.bb-cause-pills { display: flex; gap: 6px; flex-wrap: wrap; }
.bb-pill { padding: 4px 12px; border-radius: 20px; border: 1px solid var(--neutral-200); background: var(--neutral-0); font-size: 12px; font-weight: 500; cursor: pointer; color: var(--neutral-700); transition: all 0.15s; }
.bb-pill:hover { border-color: var(--neutral-400); }
.bb-pill--active { background: var(--neutral-900); color: #fff; border-color: var(--neutral-900); }
.bb-pill__cnt { font-size: 11px; opacity: 0.7; margin-left: 3px; }
.bb-pill--red { border-color: #fca5a5; color: #dc2626; }
.bb-pill--red.bb-pill--active { background: #dc2626; color: #fff; border-color: #dc2626; }
.bb-pill--blue { border-color: #93c5fd; color: #2563eb; }
.bb-pill--blue.bb-pill--active { background: #2563eb; color: #fff; border-color: #2563eb; }
.bb-pill--orange { border-color: #fcd34d; color: #d97706; }
.bb-pill--orange.bb-pill--active { background: #d97706; color: #fff; border-color: #d97706; }
.bb-pill--purple { border-color: #c4b5fd; color: #7c3aed; }
.bb-pill--purple.bb-pill--active { background: #7c3aed; color: #fff; border-color: #7c3aed; }
.bb-select { padding: 5px 10px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); font-size: 12px; background: var(--neutral-0); color: var(--neutral-700); cursor: pointer; }

/* Main layout */
.bb-main { display: flex; gap: 12px; flex: 1; min-height: 0; }

/* List */
.bb-list { width: 320px; flex-shrink: 0; display: flex; flex-direction: column; gap: 0; overflow-y: auto; border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); background: var(--neutral-0); }
.bb-loading { padding: 40px; text-align: center; color: var(--neutral-400); font-size: 13px; }
.bb-list-item { padding: 12px 14px; border-bottom: 1px solid var(--neutral-100); cursor: pointer; transition: background 0.1s; }
.bb-list-item:hover { background: var(--neutral-50); }
.bb-list-item--active { background: var(--semantic-50); border-left: 3px solid var(--semantic-500); }
.bb-list-item__top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.bb-list-item__id { font-size: 12px; font-weight: 600; color: var(--neutral-800); font-family: var(--font-mono); }
.bb-list-item__order { font-size: 11px; color: var(--neutral-500); margin-bottom: 5px; }
.bb-list-item__meta { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.bb-list-item__l2 { font-size: 11px; color: var(--neutral-600); }
.bb-list-item__bottom { display: flex; align-items: center; gap: 6px; }
.bb-conf-bar-wrap { flex: 1; height: 4px; background: var(--neutral-100); border-radius: 2px; overflow: hidden; }
.bb-conf-bar { height: 100%; border-radius: 2px; transition: width 0.3s; }
.bb-conf-val { font-size: 11px; color: var(--neutral-500); width: 32px; text-align: right; }
.bb-list-item__time { font-size: 10px; color: var(--neutral-400); }
.bb-pagination { display: flex; align-items: center; justify-content: center; gap: 12px; padding: 10px; border-top: 1px solid var(--neutral-100); }
.bb-page-btn { padding: 3px 10px; border: 1px solid var(--neutral-200); border-radius: var(--radius-sm); background: var(--neutral-0); cursor: pointer; font-size: 14px; color: var(--neutral-700); }
.bb-page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.bb-page-info { font-size: 12px; color: var(--neutral-500); }

/* Status tags */
.bb-status-tag { font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 10px; }
.bb-status-tag--lg { font-size: 12px; padding: 4px 12px; }
.bb-status-tag--green { background: var(--dynamic-100); color: var(--dynamic-700); }
.bb-status-tag--orange { background: #fef3c7; color: #d97706; }
.bb-status-tag--gray { background: var(--neutral-100); color: var(--neutral-600); }

/* Cause tags */
.bb-cause-tag { font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 10px; }
.bb-cause-tag--red { background: #fee2e2; color: #dc2626; }
.bb-cause-tag--blue { background: #dbeafe; color: #2563eb; }
.bb-cause-tag--orange { background: #fef3c7; color: #d97706; }
.bb-cause-tag--purple { background: #ede9fe; color: #7c3aed; }
.bb-cause-tag--gray { background: var(--neutral-100); color: var(--neutral-600); }

/* Detail panel */
.bb-detail { flex: 1; min-width: 0; border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); background: var(--neutral-0); display: flex; flex-direction: column; overflow: hidden; }
.bb-detail--empty { align-items: center; justify-content: center; }
.bb-detail__placeholder { text-align: center; color: var(--neutral-400); }
.bb-detail__placeholder p { margin-top: 12px; font-size: 13px; }
.bb-detail__header { display: flex; align-items: flex-start; justify-content: space-between; padding: 16px 20px 12px; border-bottom: 1px solid var(--neutral-100); flex-shrink: 0; }
.bb-detail__id { font-size: 15px; font-weight: 700; color: var(--neutral-900); font-family: var(--font-mono); }
.bb-detail__order { font-size: 12px; color: var(--neutral-500); margin-top: 3px; }
.bb-detail__tabs { display: flex; gap: 0; border-bottom: 1px solid var(--neutral-100); flex-shrink: 0; }
.bb-detail__tab { padding: 9px 18px; font-size: 13px; font-weight: 500; color: var(--neutral-500); background: none; border: none; border-bottom: 2px solid transparent; cursor: pointer; transition: all 0.15s; }
.bb-detail__tab:hover { color: var(--neutral-800); }
.bb-detail__tab--active { color: var(--semantic-600); border-bottom-color: var(--semantic-500); }
.bb-detail__body { flex: 1; overflow-y: auto; padding: 16px 20px; }

/* Conclusion */
.bb-conclusion__cause { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; padding: 14px; background: var(--neutral-50); border-radius: var(--radius-lg); }
.bb-conclusion__label { font-size: 11px; color: var(--neutral-500); font-weight: 600; }
.bb-conclusion__l1 { font-size: 14px; font-weight: 700; padding: 4px 12px; border-radius: 20px; }
.bb-conclusion__arrow { font-size: 18px; color: var(--neutral-400); }
.bb-conclusion__l2 { font-size: 13px; color: var(--neutral-700); font-weight: 500; }
.bb-conf-meter { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.bb-conf-meter__label { font-size: 12px; color: var(--neutral-500); width: 48px; flex-shrink: 0; }
.bb-conf-meter__bar-wrap { flex: 1; height: 8px; background: var(--neutral-100); border-radius: 4px; overflow: hidden; }
.bb-conf-meter__bar { height: 100%; border-radius: 4px; transition: width 0.4s; }
.bb-conf-meter__val { font-size: 14px; font-weight: 700; width: 44px; text-align: right; }
.bb-info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 14px; }
.bb-info-row { display: flex; flex-direction: column; gap: 2px; padding: 8px 10px; background: var(--neutral-50); border-radius: var(--radius-md); }
.bb-info-key { font-size: 10px; color: var(--neutral-400); font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }
.bb-info-val { font-size: 13px; color: var(--neutral-800); font-weight: 500; }
.bb-info-val--addr { font-size: 11px; }
.bb-info-val--warn { color: #d97706; }
.bb-info-val--action { color: var(--dynamic-600); font-weight: 600; }
.bb-evidence-summary { padding: 12px; background: var(--semantic-50); border-radius: var(--radius-md); border-left: 3px solid var(--semantic-400); }
.bb-evidence-summary__label { font-size: 11px; font-weight: 600; color: var(--semantic-600); margin-bottom: 6px; }
.bb-evidence-summary__text { font-size: 12px; color: var(--neutral-700); line-height: 1.6; }

/* Evidence list */
.bb-evidence-list { display: flex; flex-direction: column; gap: 6px; }
.bb-ev-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border: 1px solid var(--neutral-100); border-radius: var(--radius-md); background: var(--neutral-50); }
.bb-ev-item--hit { background: var(--dynamic-50); border-color: var(--dynamic-200); }
.bb-ev-item__left { display: flex; align-items: center; gap: 6px; flex-shrink: 0; width: 140px; }
.bb-ev-hit { font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 8px; }
.bb-ev-hit--yes { background: var(--dynamic-100); color: var(--dynamic-700); }
.bb-ev-hit--no { background: var(--neutral-100); color: var(--neutral-500); }
.bb-ev-code { font-size: 11px; font-family: var(--font-mono); color: var(--neutral-600); }
.bb-ev-type { font-size: 10px; color: var(--neutral-400); }
.bb-ev-item__content { flex: 1; font-size: 12px; color: var(--neutral-700); }
.bb-ev-item__right { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; flex-shrink: 0; }
.bb-ev-conf { font-size: 13px; font-weight: 700; }
.bb-ev-src { font-size: 10px; color: var(--neutral-400); }

/* Dispatch */
.bb-dispatch-card { padding: 14px; border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); margin-bottom: 10px; }
.bb-dispatch-card__eng { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.bb-eng-name { font-size: 14px; font-weight: 700; color: var(--neutral-900); }
.bb-eng-level { font-size: 11px; padding: 2px 8px; background: var(--semantic-100); color: var(--semantic-700); border-radius: 10px; }
.bb-eng-type { font-size: 11px; color: var(--neutral-500); }

/* Trail */
.bb-trail { display: flex; flex-direction: column; gap: 0; position: relative; padding-left: 20px; }
.bb-trail::before { content: ''; position: absolute; left: 6px; top: 8px; bottom: 8px; width: 2px; background: var(--neutral-200); }
.bb-trail-item { position: relative; padding: 0 0 16px 16px; }
.bb-trail-item__dot { position: absolute; left: -14px; top: 4px; width: 10px; height: 10px; border-radius: 50%; background: var(--semantic-400); border: 2px solid var(--neutral-0); }
.bb-trail-item__action { font-size: 13px; font-weight: 600; color: var(--neutral-900); }
.bb-trail-item__meta { font-size: 11px; color: var(--neutral-400); margin-top: 2px; }
.bb-trail-item__status { font-size: 11px; color: var(--neutral-600); margin-top: 3px; }
.bb-trail-item__remark { font-size: 11px; color: var(--neutral-500); margin-top: 4px; padding: 6px 8px; background: var(--neutral-50); border-radius: var(--radius-sm); }

.bb-empty { padding: 40px; text-align: center; color: var(--neutral-400); font-size: 13px; }
</style>
