<template>
  <div class="rpm">
    <div v-if="modelValue.length" class="rpm-tags">
      <span v-for="id in modelValue" :key="id" class="rpm-tag">
        {{ labelOf(id) }}
        <button class="rpm-tag-x" @click="remove(id)">×</button>
      </span>
    </div>
    <div class="rpm-add">
      <select :value="''" @change="onPick">
        <option value="">+ 添加 {{ typeLabel }}</option>
        <option
          v-for="o in availableOptions"
          :key="o.id"
          :value="o.id"
        >{{ o.label }}</option>
      </select>
      <button class="rpm-refresh" @click="reload" title="刷新">⟳</button>
    </div>
    <div v-if="!availableOptions.length && !modelValue.length" class="rpm-empty">
      {{ loading ? '加载中…' : `暂无可选 ${typeLabel}` }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  listRulesAsResources, listActionsAsResources, listFunctionsAsResources,
  listEntitiesAsResources, listAgentsAsResources, listSkillsAsResources,
  listModelsAsResources, listDatasourcesAsResources,
} from '../../../../api/aip'

type ResourceType = 'rule' | 'action' | 'function' | 'entity' | 'agent' | 'skill' | 'model' | 'datasource'

const props = defineProps<{ type: ResourceType; modelValue: string[] }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: string[]): void }>()

const loading = ref(false)
const items = ref<any[]>([])
const loaders: Record<ResourceType, () => Promise<any[]>> = {
  rule: listRulesAsResources,
  action: listActionsAsResources,
  function: listFunctionsAsResources,
  entity: listEntitiesAsResources,
  agent: listAgentsAsResources,
  skill: listSkillsAsResources,
  model: listModelsAsResources,
  datasource: listDatasourcesAsResources,
}
const TYPE_LABELS: Record<ResourceType, string> = {
  rule: '规则', action: '动作', function: '函数',
  entity: '对象', agent: '智能体', skill: '技能', model: '模型', datasource: '数据源',
}
const typeLabel = computed(() => TYPE_LABELS[props.type])

async function reload() {
  loading.value = true
  try {
    const list = await loaders[props.type]()
    items.value = Array.isArray(list) ? list : []
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}
onMounted(reload)
watch(() => props.type, reload)

function pickLabel(o: any) { return o.name_cn || o.name || o.label || o.title || o.id }
function pickId(o: any) { return o.id || o.name || o.code_ref || '' }

const allOptions = computed(() =>
  items.value.map(o => ({ id: pickId(o), label: pickLabel(o) })).filter(o => o.id),
)
const availableOptions = computed(() =>
  allOptions.value.filter(o => !props.modelValue.includes(o.id)),
)

function labelOf(id: string) {
  return allOptions.value.find(o => o.id === id)?.label || id
}

function onPick(e: Event) {
  const id = (e.target as HTMLSelectElement).value
  if (!id) return
  emit('update:modelValue', [...props.modelValue, id])
  ;(e.target as HTMLSelectElement).value = ''
}
function remove(id: string) {
  emit('update:modelValue', props.modelValue.filter(v => v !== id))
}
</script>

<style scoped>
.rpm { display: flex; flex-direction: column; gap: 6px; }
.rpm-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.rpm-tag {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 8px; border-radius: 6px;
  background: #eef2ff; color: #4f46e5;
  font-size: 11px;
}
.rpm-tag-x { background: transparent; border: 0; color: #4f46e5; cursor: pointer; font-size: 12px; line-height: 1; padding: 0; }
.rpm-tag-x:hover { color: #ef4444; }
.rpm-add { display: flex; gap: 4px; }
.rpm-add select {
  flex: 1; padding: 5px 8px; border: 1px dashed #cbd5e1; border-radius: 6px;
  background: #fff; color: #64748b; font-size: 12px; outline: none;
}
.rpm-add select:focus { border-color: #4f46e5; color: #0f172a; }
.rpm-refresh {
  width: 26px; height: 26px; border: 1px solid #e2e8f0; border-radius: 6px;
  background: #fff; color: #64748b; cursor: pointer;
}
.rpm-refresh:hover { color: #4f46e5; border-color: #4f46e5; }
.rpm-empty { font-size: 11px; color: #94a3b8; }
</style>
