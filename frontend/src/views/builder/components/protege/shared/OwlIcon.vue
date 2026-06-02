<template>
  <div class="pg-owl-icon" :class="iconClass"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ type: 'class' | 'object-property' | 'data-property' | 'individual' }>()
const iconClass = computed(() => ({
  'pg-icon-class': props.type === 'class',
  'pg-icon-obj-prop': props.type === 'object-property',
  'pg-icon-data-prop': props.type === 'data-property',
  'pg-icon-individual': props.type === 'individual',
}))
</script>
