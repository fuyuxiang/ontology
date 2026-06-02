<template>
  <div class="pg-search-input">
    <input class="pg-input" :value="modelValue" :placeholder="placeholder" @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)" />
  </div>
</template>

<script setup lang="ts">
defineProps<{ modelValue: string; placeholder?: string }>()
defineEmits<{ (e: 'update:modelValue', v: string): void }>()
</script>

<style scoped>
.pg-search-input { padding: 4px 6px; }
.pg-search-input .pg-input { font-size: 11px; }
</style>
