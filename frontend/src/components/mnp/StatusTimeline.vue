<template>
  <div class="timeline">
    <div class="timeline__title">状态时间线</div>
    <div class="timeline__track">
      <div v-for="(log, i) in logs" :key="i" class="timeline__item">
        <div class="timeline__dot" :class="`dot--${log.toLevel === '高风险' ? 'high' : log.toLevel === '中风险' ? 'medium' : log.toLevel === '低风险' ? 'low' : 'safe'}`"></div>
        <div class="timeline__line" v-if="i < logs.length - 1"></div>
        <div class="timeline__content">
          <div class="timeline__levels">
            <span v-if="log.fromLevel" class="timeline__from">{{ log.fromLevel }}</span>
            <span v-if="log.fromLevel" class="timeline__arrow">→</span>
            <span class="timeline__to" :class="`to--${log.toLevel === '高风险' ? 'high' : log.toLevel === '中风险' ? 'medium' : log.toLevel === '低风险' ? 'low' : 'safe'}`">{{ log.toLevel }}</span>
          </div>
          <div class="timeline__reason">{{ log.reason }}</div>
          <div class="timeline__meta">{{ log.time }} · {{ log.triggeredBy }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { StatusLog } from '../../views/scene/MnpWorkbench.vue'
defineProps<{ logs: StatusLog[] }>()
</script>

<style scoped>
.timeline { background: #fff; border-radius: 10px; border: 1px solid #e9ecef; padding: 16px; }
.timeline__title { font-size: 14px; font-weight: 600; color: #343a40; margin-bottom: 12px; }
.timeline__track { position: relative; }
.timeline__item { display: flex; gap: 12px; position: relative; padding-bottom: 16px; }
.timeline__item:last-child { padding-bottom: 0; }
.timeline__dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; margin-top: 4px; z-index: 1; }
.dot--high { background: #fa5252; }
.dot--medium { background: #f59f00; }
.dot--low { background: #339af0; }
.dot--safe { background: #12b886; }
.timeline__line { position: absolute; left: 5px; top: 16px; bottom: 0; width: 2px; background: #e9ecef; }
.timeline__content { flex: 1; }
.timeline__levels { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 500; }
.timeline__from { color: #868e96; }
.timeline__arrow { color: #ced4da; }
.to--high { color: #fa5252; }
.to--medium { color: #f59f00; }
.to--low { color: #339af0; }
.to--safe { color: #12b886; }
.timeline__reason { font-size: 12px; color: #495057; margin-top: 2px; }
.timeline__meta { font-size: 10px; color: #adb5bd; margin-top: 2px; }
</style>
