<template>
  <div class="glass-panel tier-panel">
    <div class="tier-panel__title">TIER DISTRIBUTION</div>
    <div class="tier-panel__chart">
      <svg viewBox="0 0 80 80" class="tier-donut">
        <circle v-for="(seg, i) in segments" :key="i"
          cx="40" cy="40" r="30" fill="none"
          :stroke="seg.color" stroke-width="10"
          :stroke-dasharray="seg.dash"
          :stroke-dashoffset="seg.offset"
          :opacity="seg.pct > 0 ? 0.8 : 0"
        />
        <text x="40" y="38" text-anchor="middle" fill="#E2E8F0" font-size="14" font-weight="800">{{ total }}</text>
        <text x="40" y="50" text-anchor="middle" fill="#94A3B8" font-size="7">实体</text>
      </svg>
    </div>
    <div class="tier-legend">
      <div v-for="t in tiers" :key="t.tier" class="tier-row">
        <span class="tier-dot" :style="{ background: t.color }"></span>
        <span class="tier-name">{{ t.name }}</span>
        <span class="tier-count">{{ t.count }}</span>
      </div>
    </div>
    <div v-if="nsList.length" class="tier-panel__ns">
      <div class="tier-panel__title" style="margin-top:10px">NAMESPACE</div>
      <div v-for="ns in nsList" :key="ns.ns" class="ns-row">
        <span class="ns-name">{{ ns.ns }}</span>
        <span class="ns-count">{{ ns.count }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DashboardStatsEx } from '../../../api/dashboard'

const props = defineProps<{ stats: DashboardStatsEx | null }>()

const tierColors = ['#5C7CFA', '#A855F7', '#20C997']

const tiers = computed(() => {
  const dist = props.stats?.tier_distribution ?? []
  return dist.map((t, i) => ({ ...t, color: tierColors[i] || '#64748B' }))
})

const total = computed(() => props.stats?.entity_count ?? 0)
const circ = 2 * Math.PI * 30

const segments = computed(() => {
  let offset = 0
  return tiers.value.map(t => {
    const pct = total.value > 0 ? t.count / total.value : 0
    const len = pct * circ
    const dash = `${len} ${circ - len}`
    const seg = { color: t.color, dash, offset: -offset, pct }
    offset += len
    return seg
  })
})

const nsList = computed(() => props.stats?.ns_distribution ?? [])
</script>

<style scoped>
.glass-panel {
  position: absolute;
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 12px;
  color: #E2E8F0;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  padding: 14px;
  pointer-events: auto;
  z-index: 10;
}
.tier-panel {
  bottom: 16px;
  left: 16px;
  width: 200px;
}
.tier-panel__title {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: .12em;
  color: #64748B;
  margin-bottom: 8px;
}
.tier-donut { width: 80px; height: 80px; display: block; margin: 0 auto 8px; }
.tier-legend { display: flex; flex-direction: column; gap: 4px; }
.tier-row { display: flex; align-items: center; gap: 6px; font-size: 11px; }
.tier-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.tier-name { color: #CBD5E1; flex: 1; }
.tier-count { color: #E2E8F0; font-weight: 700; }
.ns-row { display: flex; justify-content: space-between; font-size: 10px; padding: 2px 0; }
.ns-name { color: #94A3B8; }
.ns-count { color: #CBD5E1; font-weight: 600; }
</style>
