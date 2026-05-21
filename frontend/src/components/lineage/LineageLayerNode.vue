<template>
  <div class="ln-layer" :class="`ln-layer--${data.tone}`">{{ data.label }}</div>
</template>

<script setup lang="ts">
defineProps<{ data: { label: string; tone: 'source' | 'etl' | 'ontology' | 'app' } }>()
</script>

<style scoped>
.ln-layer {
  width: 118px;
  text-align: center;
  font-size: 12px;
  font-weight: 700;
  border-radius: 6px;
  padding: 6px 10px;
  box-sizing: border-box;
}
.ln-layer--source { color: #1a3db5; background: #DBEAFE; }
.ln-layer--etl { color: #047857; background: #D1FAE5; }
.ln-layer--ontology { color: #5b21b6; background: #EDE9FE; }
.ln-layer--app { color: #9a3412; background: #FFEDD5; }
</style>
