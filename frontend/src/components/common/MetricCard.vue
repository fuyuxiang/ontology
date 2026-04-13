<template>
  <div class="metric-card" :class="{ 'metric-card--clickable': clickable }" @click="clickable && emit('click')">
    <div class="metric-card__value">{{ formattedValue }}</div>
    <div class="metric-card__label">{{ label }}</div>
    <div v-if="trend !== undefined" class="metric-card__trend" :class="trend >= 0 ? 'metric-card__trend--up' : 'metric-card__trend--down'">
      <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
        <path v-if="trend >= 0" d="M5 2l4 6H1l4-6z" fill="currentColor"/>
        <path v-else d="M5 8L1 2h8L5 8z" fill="currentColor"/>
      </svg>
      {{ Math.abs(trend) }}%
      <span v-if="trendLabel" class="metric-card__trend-label">{{ trendLabel }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  value: number | string
  label: string
  trend?: number          // 正数=上升，负数=下降，undefined=不显示
  trendLabel?: string     // 如"较上周"
  clickable?: boolean
}>(), {
  clickable: false,
})

const emit = defineEmits<{ click: [] }>()

const formattedValue = computed(() => {
  if (typeof props.value === 'number') {
    return props.value >= 10000
      ? (props.value / 10000).toFixed(1) + 'w'
      : props.value.toLocaleString()
  }
  return props.value
})
</script>

<style scoped>
.metric-card {
  background: var(--neutral-0);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-lg);
  padding: 16px 20px;
  text-align: center;
  transition: box-shadow var(--transition-fast), transform var(--transition-fast);
  min-width: 160px;
  box-shadow: var(--shadow-xs);
}
.metric-card--clickable { cursor: pointer; }
.metric-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.metric-card__value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
  color: var(--neutral-900);
}

.metric-card__label {
  font-size: 11px;
  font-weight: 400;
  color: var(--neutral-600);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  margin-top: 6px;
}

.metric-card__trend {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  font-weight: 500;
  margin-top: 4px;
}
.metric-card__trend--up   { color: var(--status-success); }
.metric-card__trend--down { color: var(--status-error); }

.metric-card__trend-label {
  font-size: 11px;
  font-weight: 400;
  color: var(--neutral-500);
  margin-left: 2px;
}
</style>
