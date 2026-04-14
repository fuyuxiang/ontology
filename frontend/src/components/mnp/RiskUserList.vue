<template>
  <div class="risk-list">
    <div class="risk-list__header">
      <span class="risk-list__title">风险用户</span>
      <span class="risk-list__count">{{ filteredUsers.length }}</span>
    </div>
    <div class="risk-list__filters">
      <button v-for="f in filters" :key="f.value" class="risk-filter" :class="{ 'risk-filter--active': filter === f.value }" @click="$emit('filter', f.value)">{{ f.label }}</button>
    </div>
    <div class="risk-list__items">
      <div
        v-for="u in filteredUsers" :key="u.name"
        class="risk-item" :class="[`risk-item--${u.riskLevel}`, { 'risk-item--selected': selectedId === u.entityId + u.name }]"
        @click="$emit('select', u)"
      >
        <div class="risk-item__score" :class="`score--${u.riskLevel}`">{{ u.riskScore }}</div>
        <div class="risk-item__info">
          <div class="risk-item__name">{{ u.name }}</div>
          <div class="risk-item__meta">{{ u.phone }} · ¥{{ u.arpu }}/月</div>
        </div>
        <div class="risk-item__status">{{ u.mnpStatus }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RiskUser } from '../../views/scene/MnpWorkbench.vue'

const props = defineProps<{ users: RiskUser[]; selectedId: string | null; filter: string }>()
defineEmits<{ select: [u: RiskUser]; filter: [f: string] }>()

const filters = [
  { value: 'all', label: '全部' },
  { value: 'high', label: '高风险' },
  { value: 'medium', label: '中风险' },
  { value: 'retaining', label: '维挽中' },
]

const filteredUsers = computed(() => {
  if (props.filter === 'all') return props.users
  if (props.filter === 'retaining') return props.users.filter(u => u.mnpStatus === '维挽中')
  return props.users.filter(u => u.riskLevel === props.filter)
})
</script>

<style scoped>
.risk-list { width: 260px; flex-shrink: 0; background: #fff; border-radius: 10px; border: 1px solid #e9ecef; display: flex; flex-direction: column; overflow: hidden; }
.risk-list__header { display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; border-bottom: 1px solid #f1f3f5; }
.risk-list__title { font-size: 14px; font-weight: 600; color: #343a40; }
.risk-list__count { font-size: 11px; color: #adb5bd; background: #f1f3f5; padding: 1px 8px; border-radius: 10px; }
.risk-list__filters { display: flex; gap: 4px; padding: 8px 10px; }
.risk-filter { padding: 4px 10px; border: 1px solid #e9ecef; border-radius: 6px; background: #fff; font-size: 11px; color: #868e96; cursor: pointer; }
.risk-filter--active { background: #4c6ef5; color: #fff; border-color: #4c6ef5; }
.risk-list__items { flex: 1; overflow-y: auto; padding: 4px 8px 8px; }
.risk-item { display: flex; align-items: center; gap: 10px; padding: 10px; border-radius: 8px; cursor: pointer; margin-bottom: 4px; transition: background 0.15s; }
.risk-item:hover { background: #f8f9fa; }
.risk-item--selected { background: #eef2ff; }
.risk-item__score { width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 700; flex-shrink: 0; }
.score--high { background: #fff5f5; color: #fa5252; }
.score--medium { background: #fff8e1; color: #f59f00; }
.score--low { background: #e7f5ff; color: #339af0; }
.score--safe { background: #e6fcf5; color: #12b886; }
.risk-item__info { flex: 1; min-width: 0; }
.risk-item__name { font-size: 13px; font-weight: 500; color: #343a40; }
.risk-item__meta { font-size: 11px; color: #868e96; margin-top: 1px; }
.risk-item__status { font-size: 10px; color: #868e96; background: #f1f3f5; padding: 2px 6px; border-radius: 4px; white-space: nowrap; }
</style>
