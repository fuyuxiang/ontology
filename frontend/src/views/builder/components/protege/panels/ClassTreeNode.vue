<template>
  <div v-show="visible">
    <div class="pg-tree-node" :class="{ 'pg-tree-node--selected': isSelected }" :style="{ '--depth': depth }" @click="select">
      <span class="pg-tree-node__toggle" @click.stop="toggle">
        <template v-if="node.children.length">{{ expanded ? '▾' : '▸' }}</template>
      </span>
      <span class="pg-tree-node__icon"><span class="pg-icon-class"></span></span>
      <span class="pg-tree-node__label">{{ node.localName }}</span>
    </div>
    <template v-if="expanded">
      <ClassTreeNode v-for="child in node.children" :key="child.id" :node="child" :depth="depth + 1" :filter="filter" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useOwlEditorStore } from '../../../../../store/owlEditor'

interface TreeNode {
  id: string
  iri: string
  localName: string
  children: TreeNode[]
}

const props = defineProps<{ node: TreeNode; depth: number; filter: string }>()
const store = useOwlEditorStore()
const expanded = ref(props.depth < 2)

const isSelected = computed(() => store.selectedClassId === props.node.id)

const visible = computed(() => {
  if (!props.filter) return true
  if (props.node.localName.toLowerCase().includes(props.filter.toLowerCase())) return true
  return hasMatchingChild(props.node)
})

function hasMatchingChild(n: TreeNode): boolean {
  for (const c of n.children) {
    if (c.localName.toLowerCase().includes(props.filter.toLowerCase())) return true
    if (hasMatchingChild(c)) return true
  }
  return false
}

function toggle() { expanded.value = !expanded.value }
function select() { store.selectedClassId = props.node.id }
</script>
