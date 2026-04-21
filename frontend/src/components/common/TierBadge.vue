<template>
  <span class="tier-badge" :class="`tier-badge--tier${tier}`">
    T{{ tier }}
  </span>
</template>

<script setup lang="ts">
defineProps<{ tier: 1 | 2 | 3 }>()
</script>

<style scoped>
.tier-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: var(--radius-sm);
  font-size: var(--text-caption-size);
  font-weight: 700;
  color: var(--neutral-0);
  flex-shrink: 0;
}
.tier-badge--tier1 { background: var(--tier1-primary); }
.tier-badge--tier2 { background: var(--tier2-primary); }
.tier-badge--tier3 { background: var(--tier3-primary); }
</style>
