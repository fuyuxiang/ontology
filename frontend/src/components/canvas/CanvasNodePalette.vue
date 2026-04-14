<template>
  <div class="node-palette">
    <div class="node-palette__header">
      <span class="text-caption-upper">对象面板</span>
    </div>
    <div class="node-palette__search">
      <input v-model="search" placeholder="搜索对象..." class="palette-search" />
    </div>
    <div class="node-palette__groups">
      <div v-for="group in filteredGroups" :key="group.tier" class="palette-group">
        <div class="palette-group__title" @click="toggleGroup(group.tier)">
          <span class="palette-dot" :style="{ background: tierColors[group.tier] }"></span>
          <span>{{ group.label }}</span>
          <span class="palette-group__count">{{ group.entities.length }}</span>
          <svg :class="['palette-chevron', { 'palette-chevron--open': openGroups.has(group.tier) }]" width="12" height="12" viewBox="0 0 12 12"><path d="M3 4.5l3 3 3-3" stroke="currentColor" stroke-width="1.5" fill="none"/></svg>
        </div>
        <div v-if="openGroups.has(group.tier)" class="palette-group__items">
          <div
            v-for="e in group.entities" :key="e.id"
            class="palette-item"
            draggable="true"
            @dragstart="onDragStart($event, e)"
          >
            <span class="palette-item__name">{{ e.name }}</span>
            <span class="palette-item__cn">{{ e.name_cn }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { EntityListItem, Tier } from '../../types'

const props = defineProps<{
  grouped: { tier: Tier; label: string; entities: EntityListItem[] }[]
}>()

const search = ref('')
const openGroups = ref(new Set<Tier>([1, 2, 3]))
const tierColors: Record<number, string> = { 1: '#4c6ef5', 2: '#7950f2', 3: '#20c997' }

const filteredGroups = computed(() => {
  const q = search.value.toLowerCase()
  if (!q) return props.grouped
  return props.grouped.map(g => ({
    ...g,
    entities: g.entities.filter(e => e.name.toLowerCase().includes(q) || e.name_cn.includes(q)),
  })).filter(g => g.entities.length > 0)
})

function toggleGroup(tier: Tier) {
  openGroups.value.has(tier) ? openGroups.value.delete(tier) : openGroups.value.add(tier)
}

function onDragStart(event: DragEvent, entity: EntityListItem) {
  if (!event.dataTransfer) return
  event.dataTransfer.setData('application/vueflow', JSON.stringify({
    id: entity.id, name: entity.name, nameCn: entity.name_cn, tier: entity.tier,
  }))
  event.dataTransfer.effectAllowed = 'move'
}
</script>

<style scoped>
.node-palette {
  width: 200px; flex-shrink: 0; background: #f8f9fa;
  border-right: 1px solid #e9ecef; display: flex; flex-direction: column;
  overflow: hidden;
}
.node-palette__header { padding: 12px 14px 8px; font-size: 11px; font-weight: 600; color: #868e96; letter-spacing: 0.5px; }
.node-palette__search { padding: 0 10px 8px; }
.palette-search {
  width: 100%; padding: 6px 10px; border: 1px solid #dee2e6; border-radius: 6px;
  font-size: 12px; background: #fff; outline: none; box-sizing: border-box;
}
.palette-search:focus { border-color: #4c6ef5; }
.node-palette__groups { flex: 1; overflow-y: auto; padding: 0 6px 12px; }
.palette-group { margin-bottom: 4px; }
.palette-group__title {
  display: flex; align-items: center; gap: 6px; padding: 6px 8px;
  font-size: 12px; font-weight: 600; color: #495057; cursor: pointer;
  border-radius: 4px; user-select: none;
}
.palette-group__title:hover { background: #e9ecef; }
.palette-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.palette-group__count { margin-left: auto; font-size: 10px; color: #adb5bd; font-weight: 400; }
.palette-chevron { transition: transform 0.15s; color: #adb5bd; }
.palette-chevron--open { transform: rotate(180deg); }
.palette-group__items { padding: 2px 0 4px 8px; }
.palette-item {
  display: flex; flex-direction: column; padding: 6px 10px; margin-bottom: 2px;
  border-radius: 6px; cursor: grab; transition: background 0.1s;
}
.palette-item:hover { background: #e9ecef; }
.palette-item__name { font-size: 12px; font-weight: 500; color: #343a40; }
.palette-item__cn { font-size: 10px; color: #868e96; }
</style>
