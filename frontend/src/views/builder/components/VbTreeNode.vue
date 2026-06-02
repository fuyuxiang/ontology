<template>
  <div>
    <div class="vb-tree-item" :class="{ 'vb-tree-item--selected': selectedId === node.id }" :style="{ paddingLeft: `${depth * 16 + 12}px` }" @click="emit('select', node.id)">
      <span v-if="node.children.length" class="vb-tree-item__toggle" @click.stop="expanded = !expanded">{{ expanded ? '▾' : '▸' }}</span>
      <span v-else class="vb-tree-item__toggle"></span>
      <span class="vb-tree-item__icon" style="background:#e5b000"></span>
      <span>{{ node.localName }}</span>
    </div>
    <template v-if="expanded">
      <VbTreeNode v-for="child in node.children" :key="child.id" :node="child" :depth="depth + 1" :selected-id="selectedId" @select="emit('select', $event)" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface TreeNode { id: string; iri: string; localName: string; children: TreeNode[] }

defineProps<{ node: TreeNode; depth: number; selectedId: string | null }>()
const emit = defineEmits<{ (e: 'select', id: string): void }>()
const expanded = ref(true)
</script>

<style scoped>
.vb-tree-item { display: flex; align-items: center; gap: 6px; padding: 5px 12px; cursor: pointer; font-size: 13px; }
.vb-tree-item:hover { background: #e3f2fd; }
.vb-tree-item--selected { background: #1976d2 !important; color: #fff; }
.vb-tree-item__toggle { width: 14px; font-size: 10px; text-align: center; flex-shrink: 0; }
.vb-tree-item__icon { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
</style>
