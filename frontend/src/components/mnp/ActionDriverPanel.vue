<template>
  <div class="action-driver">
    <div class="action-driver__title">动作驱动关系</div>
    <div class="driver-list">
      <div v-for="(act, i) in actions" :key="i" class="driver-item">
        <div class="driver-header">
          <span class="driver-index">动作 {{ i + 1 }}</span>
          <span class="driver-name">{{ act.actionName }}</span>
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
}
defineProps<{ actions: ActionDriver[] }>()
</script>

<style scoped>
.action-driver { background: #fff; border-radius: 10px; border: 1px solid #e9ecef; padding: 16px; }
.action-driver__title { font-size: 14px; font-weight: 600; color: #343a40; margin-bottom: 12px; }
.driver-list { display: flex; flex-direction: column; gap: 10px; }
.driver-item { padding: 10px 12px; border: 1px solid #e9ecef; border-radius: 8px; }
.driver-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.driver-index { font-size: 11px; color: #4c6ef5; font-weight: 600; background: #eef2ff; padding: 2px 6px; border-radius: 4px; }
.driver-name { font-size: 13px; font-weight: 600; color: #343a40; }
.driver-basis { font-size: 11px; color: #868e96; margin-bottom: 6px; }
.basis-label { color: #4c6ef5; font-weight: 500; }
.driver-sources { display: flex; flex-direction: column; gap: 4px; }
.source-item { display: flex; align-items: center; gap: 6px; font-size: 12px; padding: 4px 8px; background: #f8f9fa; border-radius: 4px; }
.source-entity { color: #4c6ef5; font-weight: 500; }
.source-dot { color: #ced4da; }
.source-attr { font-family: monospace; font-size: 11px; color: #7048e8; }
.source-reason { color: #495057; margin-left: auto; }
</style>
