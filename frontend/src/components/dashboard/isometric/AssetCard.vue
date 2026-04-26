<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const healthScore = ref(88)
let timer = 0

onMounted(() => {
  timer = window.setInterval(() => {
    const drift = Math.floor(Math.random() * 7) - 3
    healthScore.value = Math.max(60, Math.min(95, healthScore.value + drift))
  }, 2000)
})

onUnmounted(() => clearInterval(timer))
</script>

<template>
  <div class="asset-card">
    <div class="asset-card__header">
      <span class="asset-card__tag">ASSET #731</span>
      <span class="asset-card__dot"></span>
    </div>
    <div class="asset-card__rows">
      <div class="asset-card__row">
        <span class="asset-card__label">Engineer</span>
        <span class="asset-card__value">Zhang Wei</span>
      </div>
      <div class="asset-card__row">
        <span class="asset-card__label">Region</span>
        <span class="asset-card__value">East China</span>
      </div>
      <div class="asset-card__row">
        <span class="asset-card__label">Location</span>
        <span class="asset-card__value">31.23°N, 121.47°E</span>
      </div>
    </div>
    <div class="asset-card__health">
      <span class="asset-card__health-label">Health Score</span>
      <span class="asset-card__health-value" :class="{ 'asset-card__health-value--warn': healthScore < 75 }">
        {{ healthScore }}
      </span>
      <div class="asset-card__bar">
        <div class="asset-card__bar-fill" :style="{ width: `${healthScore}%` }"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.asset-card {
  width: 200px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid var(--neutral-200);
  border-left: 3px solid #4ade80;
  border-radius: 8px;
  font-family: var(--font-sans);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  pointer-events: auto;
}

.asset-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.asset-card__tag {
  font-size: var(--text-caption-upper-size);
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--neutral-900);
  font-family: var(--font-mono);
}

.asset-card__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--dynamic-300);
  animation: pulse-dot 2s ease infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.3); }
}

.asset-card__rows {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}

.asset-card__row {
  display: flex;
  justify-content: space-between;
}

.asset-card__label {
  font-size: var(--text-caption-upper-size);
  color: var(--neutral-500);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.asset-card__value {
  font-size: var(--text-caption-size);
  font-weight: 600;
  color: var(--neutral-900);
}

.asset-card__health {
  padding-top: 10px;
  border-top: 1px solid var(--neutral-100);
}

.asset-card__health-label {
  display: block;
  font-size: var(--text-caption-upper-size);
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--neutral-500);
  text-transform: uppercase;
  margin-bottom: 4px;
}

.asset-card__health-value {
  display: block;
  font-size: var(--text-display-size);
  font-weight: 700;
  color: var(--dynamic-400);
  font-family: var(--font-mono);
  line-height: 1;
  margin-bottom: 6px;
  transition: color 0.3s;
}

.asset-card__health-value--warn {
  color: var(--kinetic-500);
}

.asset-card__bar {
  height: 3px;
  background: var(--neutral-50);
  border-radius: 2px;
  overflow: hidden;
}

.asset-card__bar-fill {
  height: 100%;
  background: var(--dynamic-300);
  border-radius: 2px;
  transition: width 0.6s ease;
}
</style>
