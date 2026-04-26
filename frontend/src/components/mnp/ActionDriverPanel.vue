<template>
  <div class="action-driver">
    <div class="action-driver__title">动作驱动关系</div>
    <div class="driver-list">
      <div v-for="(act, i) in actions" :key="i" class="driver-item">
        <div class="driver-header">
          <span class="driver-index">动作 {{ i + 1 }}</span>
          <span class="driver-name">{{ act.actionName }}</span>
          <span v-if="act.recommended" class="driver-recommended">已推荐</span>
        </div>
        <div class="driver-basis">
          <span class="basis-label">本体依据:</span> {{ act.basis }}
        </div>
        <div class="driver-sources">
          <div v-for="(d, j) in act.drivenBy" :key="j" class="source-item">
            <span class="source-entity">{{ d.entity }}</span>
            <span class="source-dot">·</span>
            <span class="source-attr">{{ d.attribute }}</span>
            <span class="source-reason">{{ d.reason }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
export interface ActionDriver {
  actionName: string
  basis: string
  drivenBy: Array<{ entity: string; attribute: string; reason: string }>
  recommended?: boolean
}
defineProps<{ actions: ActionDriver[] }>()
</script>

<style scoped>
.action-driver { background: var(--neutral-0); border-radius: 10px; border: 1px solid var(--neutral-200); padding: 16px; }
.action-driver__title { font-size: var(--text-body-size); font-weight: 600; color: var(--neutral-800); margin-bottom: 12px; }
.driver-list { display: flex; flex-direction: column; gap: 10px; }
.driver-item { padding: 10px 12px; border: 1px solid var(--neutral-200); border-radius: 8px; }
.driver-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.driver-index { font-size: var(--text-caption-size); color: var(--semantic-600); font-weight: 600; background: var(--semantic-50); padding: 2px 6px; border-radius: 4px; }
.driver-name { font-size: var(--text-body-size); font-weight: 600; color: var(--neutral-800); }
.driver-recommended { font-size: var(--text-caption-upper-size); font-weight: 600; padding: 2px 8px; border-radius: 4px; background: var(--status-success-bg); color: var(--dynamic-700); margin-left: auto; }
.driver-basis { font-size: var(--text-caption-size); color: var(--neutral-600); margin-bottom: 6px; }
.basis-label { color: var(--semantic-600); font-weight: 500; }
.driver-sources { display: flex; flex-direction: column; gap: 4px; }
.source-item { display: flex; align-items: center; gap: 6px; font-size: var(--text-code-size); padding: 4px 8px; background: var(--neutral-50); border-radius: 4px; }
.source-entity { color: var(--semantic-600); font-weight: 500; }
.source-dot { color: var(--neutral-400); }
.source-attr { font-family: var(--font-mono); font-size: var(--text-caption-size); color: var(--tier2-primary); }
.source-reason { color: var(--neutral-700); margin-left: auto; }
</style>
