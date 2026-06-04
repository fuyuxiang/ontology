<script setup lang="ts">
import { ref, watch, computed } from 'vue'

interface EntityAttr {
  field: string
  label: string
  type: string
}

interface AvailableFunction {
  callable_name: string
  name: string
}

interface ConditionRow {
  source: string
  operator: string
  value: string
}

const props = defineProps<{
  modelValue: any[]
  entityId: string
  entityAttributes: EntityAttr[]
  availableFunctions: AvailableFunction[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: any[]): void
}>()

const matchMode = ref<'all' | 'at_least_1' | 'at_least_2'>('all')
const rows = ref<ConditionRow[]>([{ source: '', operator: '==', value: '' }])

const OPERATORS_BY_TYPE: Record<string, { value: string; label: string }[]> = {
  string: [
    { value: '==', label: '等于' },
    { value: '!=', label: '不等于' },
    { value: 'contains', label: '包含' },
    { value: 'starts_with', label: '开头为' },
    { value: 'ends_with', label: '结尾为' },
    { value: 'is_null', label: '为空' },
    { value: 'not_null', label: '不为空' },
  ],
  number: [
    { value: '==', label: '等于' },
    { value: '!=', label: '不等于' },
    { value: '>', label: '大于' },
    { value: '>=', label: '大于等于' },
    { value: '<', label: '小于' },
    { value: '<=', label: '小于等于' },
    { value: 'is_null', label: '为空' },
    { value: 'not_null', label: '不为空' },
  ],
  boolean: [
    { value: '==', label: '等于' },
    { value: '!=', label: '不等于' },
  ],
  date: [
    { value: '==', label: '等于' },
    { value: '!=', label: '不等于' },
    { value: '>', label: '晚于' },
    { value: '<', label: '早于' },
    { value: 'is_null', label: '为空' },
    { value: 'not_null', label: '不为空' },
  ],
  default: [
    { value: '==', label: '等于' },
    { value: '!=', label: '不等于' },
    { value: 'is_null', label: '为空' },
    { value: 'not_null', label: '不为空' },
  ],
}

function getSourceType(source: string): string {
  if (source.startsWith('$fn.')) return 'default'
  const attr = props.entityAttributes.find(a => a.field === source)
  return attr?.type ?? 'default'
}

function operatorsFor(source: string) {
  const t = getSourceType(source)
  return OPERATORS_BY_TYPE[t] ?? OPERATORS_BY_TYPE.default
}

function noValueNeeded(op: string) {
  return op === 'is_null' || op === 'not_null'
}

function onSourceChange(idx: number) {
  const ops = operatorsFor(rows.value[idx].source)
  rows.value[idx].operator = ops[0]?.value ?? '=='
  rows.value[idx].value = ''
  emitUpdate()
}

function addRow() {
  rows.value.push({ source: '', operator: '==', value: '' })
  emitUpdate()
}

function removeRow(idx: number) {
  rows.value.splice(idx, 1)
  emitUpdate()
}

function emitUpdate() {
  const conditions = rows.value
    .filter(r => r.source)
    .map(r => {
      const isFn = r.source.startsWith('$fn.')
      return {
        type: isFn ? 'function_call' : 'field',
        source: r.source,
        operator: r.operator,
        value: noValueNeeded(r.operator) ? null : r.value,
        match_mode: matchMode.value,
      }
    })
  emit('update:modelValue', conditions)
}

watch(matchMode, emitUpdate)

// Initialise from modelValue
watch(() => props.modelValue, (val) => {
  if (!val || val.length === 0) return
  if (val[0]?.match_mode) matchMode.value = val[0].match_mode
  rows.value = val.map(c => ({
    source: c.source ?? '',
    operator: c.operator ?? '==',
    value: c.value ?? '',
  }))
}, { immediate: true })
</script>

<template>
  <div class="condition-builder">
    <div class="condition-builder__mode">
      <label class="form-label">匹配模式：</label>
      <div class="mode-switch" style="display:inline-flex;width:auto;">
        <button :class="{ active: matchMode === 'all' }" @click="matchMode = 'all'">全部满足</button>
        <button :class="{ active: matchMode === 'at_least_1' }" @click="matchMode = 'at_least_1'">至少1条</button>
        <button :class="{ active: matchMode === 'at_least_2' }" @click="matchMode = 'at_least_2'">至少2条</button>
      </div>
    </div>

    <div v-for="(row, idx) in rows" :key="idx" class="condition-row">
      <span class="condition-row__num">{{ idx + 1 }}</span>

      <select class="form-input" style="flex:2;min-width:0;" :value="row.source"
        @change="row.source = ($event.target as HTMLSelectElement).value; onSourceChange(idx)">
        <option value="">— 选择字段或函数 —</option>
        <optgroup v-if="entityAttributes.length" label="实体属性">
          <option v-for="attr in entityAttributes" :key="attr.field" :value="attr.field">
            {{ attr.label }}（{{ attr.type }}）
          </option>
        </optgroup>
        <optgroup v-if="availableFunctions.length" label="函数">
          <option v-for="fn in availableFunctions" :key="fn.callable_name" :value="`$fn.${fn.callable_name}`">
            {{ fn.name }}
          </option>
        </optgroup>
      </select>

      <select class="form-input" style="flex:1.2;min-width:0;" v-model="row.operator" @change="emitUpdate">
        <option v-for="op in operatorsFor(row.source)" :key="op.value" :value="op.value">{{ op.label }}</option>
      </select>

      <input v-if="!noValueNeeded(row.operator)" class="form-input" style="flex:2;min-width:0;"
        v-model="row.value" placeholder="值" @input="emitUpdate" />
      <span v-else style="flex:2;" />

      <button class="btn-sm-del" style="flex-shrink:0;" @click="removeRow(idx)">✕</button>
    </div>

    <button class="btn-sm-exec" style="margin-top:4px;" @click="addRow">+ 添加条件</button>
  </div>
</template>

<style scoped>
@import '../../views/logic/logic-shared.css';

.condition-builder__mode {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
