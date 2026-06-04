<template>
  <div class="qd-page">
    <div class="qd-header">
      <div>
        <h1 class="qd-title">数据质量</h1>
        <p class="qd-subtitle">本体数据健康度总览</p>
      </div>
      <button class="qd-btn-primary" :disabled="evaluating" @click="runEvaluate">
        {{ evaluating ? '检测中...' : '立即检测' }}
      </button>
    </div>

    <div class="qd-body">
      <!-- Left column -->
      <div class="qd-left">
        <!-- Score ring -->
        <div class="qd-score-card">
          <div class="qd-ring">
            <svg viewBox="0 0 120 120" class="qd-ring__svg">
              <circle cx="60" cy="60" r="52" fill="none" stroke="#e5e7eb" stroke-width="10" />
              <circle
                cx="60" cy="60" r="52" fill="none"
                :stroke="scoreColor" stroke-width="10"
                stroke-linecap="round"
                :stroke-dasharray="ringDash"
                stroke-dashoffset="0"
                transform="rotate(-90 60 60)"
                class="qd-ring__progress"
              />
            </svg>
            <div class="qd-ring__value" :style="{ color: scoreColor }">
              {{ data?.overall_score ?? '--' }}
            </div>
          </div>
          <div class="qd-summary">
            <span class="qd-pill qd-pill--healthy">● 健康 {{ data?.summary['healthy'] ?? 0 }}</span>
            <span class="qd-pill qd-pill--warning">● 告警 {{ data?.summary['warning'] ?? 0 }}</span>
            <span class="qd-pill qd-pill--failure">● 失败 {{ data?.summary['failure'] ?? 0 }}</span>
            <span class="qd-pill qd-pill--unknown">● 未检 {{ data?.summary['unknown'] ?? 0 }}</span>
          </div>
        </div>

        <!-- Entity scorecards -->
        <div class="qd-scorecards">
          <h3 class="qd-section-title">实体健康度 ({{ data?.entities.length ?? 0 }})</h3>
          <div
            v-for="e in data?.entities"
            :key="e.entity_id"
            class="qd-entity-row"
          >
            <span class="qd-entity-name" :title="e.entity_name">{{ e.entity_name }}</span>
            <div class="qd-bar">
              <div
                class="qd-bar__fill"
                :style="{ width: e.score + '%', background: barColor(e.score) }"
              />
            </div>
            <span class="qd-entity-score" :style="{ color: barColor(e.score) }">{{ e.score }}</span>
            <div class="qd-dims">
              <span
                v-for="(status, dim) in e.dimensions"
                :key="String(dim)"
                class="qd-dot"
                :class="'qd-dot--' + status"
                :title="String(dim) + ': ' + status"
              />
            </div>
          </div>
          <div v-if="!data?.entities.length" class="qd-empty">暂无已绑定数据资产的实体</div>
        </div>
      </div>

      <!-- Right column -->
      <div class="qd-right">
        <!-- Trend chart -->
        <div class="qd-trend-card">
          <h3 class="qd-section-title">质量趋势</h3>
          <div v-if="data?.trend.length" class="qd-trend-chart">
            <div
              v-for="t in data.trend.slice(-14)"
              :key="t.date"
              class="qd-trend-bar"
            >
              <div
                class="qd-trend-bar__fill"
                :style="{ height: t.score + '%', background: barColor(t.score) }"
              />
              <span class="qd-trend-bar__label">{{ t.date.slice(5) }}</span>
            </div>
          </div>
          <div v-else class="qd-empty">暂无趋势数据</div>
        </div>

        <!-- Recent issues -->
        <div class="qd-issues-card">
          <h3 class="qd-section-title">最近异常</h3>
          <div v-if="data?.recent_issues.length" class="qd-timeline">
            <div
              v-for="(issue, idx) in data.recent_issues"
              :key="issue.occurred_at + '_' + idx"
              class="qd-issue"
            >
              <span
                class="qd-issue__icon"
                :class="'qd-issue__icon--' + issue.severity"
              >
                {{ issue.severity === 'failure' ? '✗' : '⚠' }}
              </span>
              <div class="qd-issue__body">
                <div class="qd-issue__head">
                  <span class="qd-issue__entity">{{ issue.entity_name }}</span>
                  <span class="qd-issue__time">{{ relativeTime(issue.occurred_at) }}</span>
                </div>
                <div class="qd-issue__msg">{{ issue.message }}</div>
              </div>
            </div>
          </div>
          <div v-else class="qd-empty qd-empty--ok">✓ 所有检查通过</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { qualityApi, type QualityDashboard } from '../../../api/quality'

const data = ref<QualityDashboard | null>(null)
const loading = ref(false)
const evaluating = ref(false)
let timer: ReturnType<typeof setInterval> | null = null

const scoreColor = computed(() => {
  const s = data.value?.overall_score ?? 0
  if (s >= 80) return '#10b981'
  if (s >= 60) return '#f59e0b'
  return '#ef4444'
})

const ringDash = computed(() => {
  const circumference = 2 * Math.PI * 52
  const score = data.value?.overall_score ?? 0
  const filled = (score / 100) * circumference
  return `${filled} ${circumference}`
})

function barColor(score: number) {
  if (score >= 80) return '#10b981'
  if (score >= 60) return '#f59e0b'
  return '#ef4444'
}

function relativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const min = Math.floor(diff / 60000)
  if (min < 1) return '刚刚'
  if (min < 60) return `${min}分钟前`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr}小时前`
  return `${Math.floor(hr / 24)}天前`
}

async function fetchData() {
  loading.value = true
  try {
    data.value = await qualityApi.dashboard() as QualityDashboard
  } catch (e) {
    console.error('Failed to load quality dashboard', e)
  } finally {
    loading.value = false
  }
}

async function runEvaluate() {
  evaluating.value = true
  try {
    await qualityApi.evaluateAll()
    await fetchData()
  } finally {
    evaluating.value = false
  }
}

onMounted(() => {
  fetchData()
  timer = setInterval(fetchData, 60000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
@import './quality-dashboard.css';
</style>
