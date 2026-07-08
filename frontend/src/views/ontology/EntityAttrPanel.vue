<template>
  <div class="attr-panel">
    <div class="attr-panel__header">
      <button class="attr-panel__back" @click="emit('back')">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M10 12L6 8l4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        返回对象列表
      </button>
      <div class="attr-panel__info">
        <span class="attr-panel__name">{{ entity.name }}</span>
        <span v-if="entity.name_cn" class="attr-panel__name-cn">{{ entity.name_cn }}</span>
        <span class="attr-panel__tier" :class="`attr-panel__tier--${entity.tier}`">Tier {{ entity.tier }}</span>
      </div>
    </div>

    <div v-if="loading" class="attr-panel__loading">加载中...</div>

    <template v-else>
      <div class="attr-panel__count">属性 ({{ attrs.length }}个)</div>

      <div class="attr-panel__grid">
        <div v-for="attr in attrs" :key="attr.id" class="attr-card">
          <div class="attr-card__head">
            <code class="attr-card__name">{{ attr.name }}</code>
            <span class="attr-card__type" :class="`attr-card__type--${attr.type}`">{{ attr.type }}</span>
          </div>
          <div v-if="attr.required" class="attr-card__required">
            <span class="attr-card__dot"></span>必填
          </div>
          <div v-if="attr.description" class="attr-card__desc">{{ attr.description }}</div>
        </div>
      </div>

      <div v-if="attrs.length === 0" class="attr-panel__empty">该对象暂无属性</div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useOntologyStore } from '../../store/ontology'
import type { EntityListItem } from '../../types'

const props = defineProps<{
  entity: EntityListItem
}>()

const emit = defineEmits<{ back: [] }>()

const store = useOntologyStore()
const loading = ref(false)

const attrs = ref<{ id: string; name: string; type: string; required: boolean; description: string }[]>([])

async function loadDetail() {
  loading.value = true
  try {
    await store.fetchEntity(props.entity.id)
    const detail = store.currentEntity
    if (detail) {
      attrs.value = detail.attributes.map(a => ({
        id: a.id,
        name: a.name,
        type: a.type,
        required: a.required,
        description: a.description || '',
      }))
    }
  } finally {
    loading.value = false
  }
}

onMounted(loadDetail)
watch(() => props.entity.id, loadDetail)
</script>

<style scoped>
.attr-panel { padding: 0; }

.attr-panel__header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.attr-panel__back {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: 1px solid var(--neutral-200, #e5e5e5);
  border-radius: 6px;
  background: var(--neutral-0, #fff);
  color: var(--neutral-700, #333);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s;
}

.attr-panel__back:hover { background: var(--neutral-50, #fafafa); }

.attr-panel__info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.attr-panel__name {
  font-size: 15px;
  font-weight: 600;
  color: var(--neutral-900, #111);
}

.attr-panel__name-cn {
  font-size: 13px;
  color: var(--neutral-500, #888);
}

.attr-panel__tier {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}

.attr-panel__tier--1 { background: #eff6ff; color: #2563eb; }
.attr-panel__tier--2 { background: #f0fdf4; color: #16a34a; }
.attr-panel__tier--3 { background: #fefce8; color: #ca8a04; }

.attr-panel__loading {
  padding: 40px 0;
  text-align: center;
  color: var(--neutral-400, #aaa);
  font-size: 13px;
}

.attr-panel__count {
  font-size: 13px;
  font-weight: 500;
  color: var(--neutral-600, #666);
  margin-bottom: 12px;
}

.attr-panel__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.attr-card {
  background: var(--neutral-0, #fff);
  border: 1px solid var(--neutral-100, #f0f0f0);
  border-radius: 8px;
  padding: 12px;
  transition: border-color 0.15s;
}

.attr-card:hover { border-color: var(--neutral-200, #e5e5e5); }

.attr-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.attr-card__name {
  font-size: 13px;
  font-weight: 600;
  color: var(--neutral-800, #222);
}

.attr-card__type {
  font-size: 11px;
  font-weight: 500;
  padding: 1px 6px;
  border-radius: 3px;
  background: var(--neutral-100, #f0f0f0);
  color: var(--neutral-600, #666);
}

.attr-card__type--string { background: #eff6ff; color: #2563eb; }
.attr-card__type--number { background: #f0fdf4; color: #16a34a; }
.attr-card__type--boolean { background: #fefce8; color: #ca8a04; }
.attr-card__type--date { background: #fdf4ff; color: #a855f7; }
.attr-card__type--ref { background: #fff7ed; color: #ea580c; }
.attr-card__type--enum { background: #f5f3ff; color: #7c3aed; }
.attr-card__type--json { background: #f0fdfa; color: #0d9488; }
.attr-card__type--computed { background: #fef2f2; color: #dc2626; }

.attr-card__required {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #16a34a;
  margin-bottom: 4px;
}

.attr-card__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #16a34a;
}

.attr-card__desc {
  font-size: 12px;
  color: var(--neutral-500, #888);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.attr-panel__empty {
  padding: 60px 0;
  text-align: center;
  color: var(--neutral-400, #aaa);
  font-size: 13px;
}
</style>