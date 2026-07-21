<template>
  <div class="rp">
    <select class="rp__select" :value="modelValue" @change="onChange">
      <option value="">{{ placeholder || '请选择' }}</option>
      <option v-for="o in options" :key="o.id" :value="o.id">{{ o.label }}</option>
    </select>
    <button v-if="modelValue && jumpUrl" class="rp__jump" @click="jumpTo" title="在新页打开">↗</button>
    <button class="rp__refresh" @click="reload" title="刷新">⟳</button>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  listAgentsAsResources, listSkillsAsResources,
  listActionsAsResources, listFunctionsAsResources, listEntitiesAsResources,
  listModelsAsResources, listDatasourcesAsResources,
} from '../../api/aip'

type ResourceType = 'agent' | 'skill' | 'action' | 'function' | 'entity' | 'model' | 'datasource'

const props = defineProps<{
  type: ResourceType
  modelValue: string
  placeholder?: string
}>()
const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()

const items = ref<any[]>([])

const loaders: Record<ResourceType, () => Promise<any[]>> = {
  agent: listAgentsAsResources,
  skill: listSkillsAsResources,
  action: listActionsAsResources,
  function: listFunctionsAsResources,
  entity: listEntitiesAsResources,
  model: listModelsAsResources,
  datasource: listDatasourcesAsResources,
}

async function reload() {
  try {
    const list = await loaders[props.type]()
    items.value = Array.isArray(list) ? list : []
  } catch {
    items.value = []
  }
}

onMounted(reload)
watch(() => props.type, reload)

function pickLabel(o: any): string {
  return o.name_cn || o.name || o.label || o.title || o.id || '(未命名)'
}
function pickId(o: any): string {
  return o.id || o.name || o.code_ref || ''
}

const options = computed(() =>
  items.value.map((o) => ({ id: pickId(o), label: pickLabel(o) })).filter((o) => o.id),
)

function onChange(e: Event) {
  emit('update:modelValue', (e.target as HTMLSelectElement).value)
}

const jumpUrl = computed(() => {
  const map: Record<ResourceType, string> = {
    agent: '/service/agent',
    skill: '/logic/skills',
    action: '/logic/actions',
    function: '/logic/functions',
    entity: '/browser',
    model: '/settings/models',
    datasource: '/data/ingest',
  }
  return map[props.type] || ''
})

function jumpTo() {
  if (jumpUrl.value) window.open(jumpUrl.value, '_blank')
}
</script>

<style scoped>
.rp { display: flex; align-items: center; gap: 4px; }
.rp__select {
  flex: 1; min-width: 0;
  padding: 6px 10px; font-size: 12px;
  border: 1px solid #e2e8f0; border-radius: 4px; background: #fff;
  color: #1e293b; outline: none;
}
.rp__select:focus { border-color: #2E5BFF; box-shadow: 0 0 0 2px rgba(46,91,255,.15); }
.rp__jump, .rp__refresh {
  width: 24px; height: 24px; border-radius: 4px;
  border: 1px solid #e2e8f0; background: #fff; color: #64748b;
  cursor: pointer; flex-shrink: 0; font-size: 12px;
}
.rp__jump:hover, .rp__refresh:hover { border-color: #2E5BFF; color: #2E5BFF; }
</style>
