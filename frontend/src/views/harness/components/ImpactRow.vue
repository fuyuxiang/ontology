<template>
  <div v-if="impact" class="impact-row">
    <svg width="14" height="14" viewBox="0 0 14 14">
      <circle cx="7" cy="7" r="5" fill="none" stroke="#d9d9d9" stroke-width="1" />
      <circle cx="7" cy="7" r="2" fill="#1677ff" />
      <template v-if="hasNumber">
        <line x1="9" y1="5" x2="13" y2="2" stroke="#d9d9d9" stroke-width="0.8" />
        <line x1="9" y1="9" x2="13" y2="12" stroke="#d9d9d9" stroke-width="0.8" />
      </template>
    </svg>
    <span>{{ impact }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ impact?: string }>()
const hasNumber = computed(() => !!props.impact && /[\d,]+/.test(props.impact))
</script>

<style scoped>
.impact-row { display: flex; align-items: center; gap: 4px; font-size: 11px; color: #999; margin-top: 4px; }
</style>
