<template>
  <div class="profile">
    <div class="profile__header">
      <div class="profile__avatar" :class="`profile__avatar--${user.riskLevel}`">{{ user.name.charAt(0) }}</div>
      <div class="profile__info">
        <div class="profile__name">{{ user.name }} <span class="profile__level" :class="`level--${user.riskLevel}`">{{ levelLabel }} ({{ user.riskScore }}分)</span></div>
        <div class="profile__meta">{{ user.phone }} · 在网{{ user.tenure }}月 · {{ user.mnpStatus }}</div>
      </div>
    </div>
    <div class="profile__metrics">
      <div class="profile__metric">
        <span class="profile__metric-value" :class="{ 'text--danger': user.arpuTrend === 'declining' }">¥{{ user.arpu }}</span>
        <span class="profile__metric-label">月均ARPU {{ trendIcon }}</span>
      </div>
      <div class="profile__metric">
        <span class="profile__metric-value" :class="{ 'text--danger': user.complaints >= 3 }">{{ user.complaints }}</span>
        <span class="profile__metric-label">近3月投诉</span>
      </div>
      <div class="profile__metric">
        <span class="profile__metric-value" :class="{ 'text--danger': user.competitorQueries >= 3 }">{{ user.competitorQueries }}</span>
        <span class="profile__metric-label">竞品查询</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RiskUser } from '../../views/scene/MnpWorkbench.vue'

const props = defineProps<{ user: RiskUser }>()
const levelLabels: Record<string, string> = { high: '高风险', medium: '中风险', low: '低风险', safe: '安全' }
const levelLabel = computed(() => levelLabels[props.user.riskLevel])
const trendIcon = computed(() => ({ rising: '↑', stable: '→', declining: '↓' }[props.user.arpuTrend]))
</script>

<style scoped>
.profile { background: #fff; border-radius: 10px; border: 1px solid #e9ecef; padding: 16px; }
.profile__header { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.profile__avatar { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 700; color: #fff; }
.profile__avatar--high { background: #fa5252; }
.profile__avatar--medium { background: #f59f00; }
.profile__avatar--low { background: #339af0; }
.profile__avatar--safe { background: #12b886; }
.profile__name { font-size: 15px; font-weight: 600; color: #343a40; }
.profile__level { font-size: 12px; font-weight: 500; padding: 2px 8px; border-radius: 4px; margin-left: 6px; }
.level--high { background: #fff5f5; color: #fa5252; }
.level--medium { background: #fff8e1; color: #f59f00; }
.level--low { background: #e7f5ff; color: #339af0; }
.level--safe { background: #e6fcf5; color: #12b886; }
.profile__meta { font-size: 12px; color: #868e96; margin-top: 2px; }
.profile__metrics { display: flex; gap: 16px; }
.profile__metric { flex: 1; text-align: center; padding: 10px; background: #f8f9fa; border-radius: 8px; }
.profile__metric-value { display: block; font-size: 20px; font-weight: 700; color: #343a40; }
.profile__metric-label { font-size: 11px; color: #868e96; }
.text--danger { color: #fa5252; }
</style>
