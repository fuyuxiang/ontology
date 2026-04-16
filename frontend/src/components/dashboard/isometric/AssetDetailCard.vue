<template>
  <div class="asset-card" :class="{ 'asset-card--visible': visible }">
    <div class="asset-card__header">
      <span class="asset-card__tag">ASSET #{{ entity?.id?.slice(-3) ?? '---' }}</span>
      <span class="asset-card__status" :class="`asset-card__status--${entity?.status ?? 'active'}`">
        {{ statusLabel }}
      </span>
    </div>

    <div class="asset-card__body">
      <div class="asset-card__row">
        <span class="asset-card__label">名称</span>
        <span class="asset-card__value">{{ displayName }}</span>
      </div>
      <div class="asset-card__row">
        <span class="asset-card__label">层级</span>
        <span class="asset-card__value">Tier {{ entity?.tier ?? '-' }}</span>
      </div>
      <div class="asset-card__row">
        <span class="asset-card__label">关系</span>
        <span class="asset-card__value">{{ entity?.relation_count ?? 0 }}</span>
      </div>
      <div class="asset-card__row">
        <span class="asset-card__label">规则</span>
        <span class="asset-card__value">{{ entity?.rule_count ?? 0 }}</span>
      </div>
    </div>

    <div class="asset-card__health">
      <span class="asset-card__health-label">Health Score</span>
      <span class="asset-card__health-value" :style="{ color: healthColor }">{{ animatedScore }}</span>
      <div class="asset-card__health-bar">
        <div class="asset-card__health-fill" :style="{ width: `${animatedScore}%`, background: healthColor }"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onUnmounted } from 'vue'
import type { EntityListItem } from '../../../types'

const props = defineProps<{
  entity: EntityListItem | null
  visible: boolean
}>()

const statusMap = { active: '在线', warning: '关注', error: '异常' } as const

const displayName = computed(() => {
  if (!props.entity) return '-'
  return props.entity.name_cn || props.entity.name
})

const statusLabel = computed(() => {
  if (!props.entity) return '-'
  return statusMap[props.entity.status] ?? props.entity.status
})

// Animated health score
const targetScore = ref(88)
const animatedScore = ref(88)
let rafId = 0
let driftTimer = 0

const healthColor = computed(() => {
  if (animatedScore.value >= 80) return 'var(--dynamic-600)'
  if (animatedScore.value >= 60) return 'var(--kinetic-600)'
  return 'var(--status-error)'
})

function animateTo(target: number) {
  const start = animatedScore.value
  const diff = target - start
  const duration = 600
  const startTime = performance.now()

  function tick(now: number) {
    const elapsed = now - startTime
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    animatedScore.value = Math.round(start + diff * eased)
    if (progress < 1) rafId = requestAnimationFrame(tick)
  }

  cancelAnimationFrame(rafId)
  rafId = requestAnimationFrame(tick)
}

function startDrift() {
  clearInterval(driftTimer)
  driftTimer = window.setInterval(() => {
    const drift = Math.floor(Math.random() * 7) - 3
    targetScore.value = Math.max(60, Math.min(95, targetScore.value + drift))
    animateTo(targetScore.value)
  }, 2000)
}

watch(() => props.entity?.id, () => {
  targetScore.value = 75 + Math.floor(Math.random() * 20)
  animateTo(targetScore.value)
  startDrift()
}, { immediate: true })

onUnmounted(() => {
  cancelAnimationFrame(rafId)
  clearInterval(driftTimer)
})
</script>

<style scoped>
.asset-card {
  position: absolute;
  left: 4%;
  top: 12%;
  width: 180px;
  padding: 14px;
  border-radius: 16px;
  border: 1px solid rgba(18, 184, 134, 0.22);
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(12px);
  box-shadow: 0 16px 40px rgba(18, 184, 134, 0.12);
  opacity: 0;
  transform: translateY(10px);
  transition: opacity 400ms ease, transform 400ms ease;
  pointer-events: none;
  z-index: 5;
}

.asset-card--visible {
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
}

.asset-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.asset-card__tag {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--neutral-500);
  font-family: var(--font-code);
}

.asset-card__status {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
}

.asset-card__status--active { background: var(--dynamic-50); color: var(--dynamic-700); }
.asset-card__status--warning { background: var(--kinetic-50); color: var(--kinetic-700); }
.asset-card__status--error { background: var(--status-error-bg); color: var(--status-error); }

.asset-card__body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}

.asset-card__row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.asset-card__label {
  font-size: 11px;
  color: var(--neutral-500);
}

.asset-card__value {
  font-size: 12px;
  font-weight: 600;
  color: var(--neutral-800);
}

.asset-card__health {
  padding-top: 10px;
  border-top: 1px solid rgba(15, 17, 23, 0.06);
}

.asset-card__health-label {
  display: block;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--neutral-500);
  text-transform: uppercase;
  margin-bottom: 4px;
}

.asset-card__health-value {
  display: block;
  font-size: 24px;
  font-weight: 700;
  line-height: 1;
  margin-bottom: 6px;
  font-family: var(--font-code);
}

.asset-card__health-bar {
  height: 4px;
  border-radius: 999px;
  background: var(--neutral-100);
  overflow: hidden;
}

.asset-card__health-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 600ms ease;
}
</style>
