<template>
  <div class="schema-editor">
    <div class="schema-toolbar">
      <span>{{ title }}</span
      ><a-space
        ><a-button
          size="small"
          :disabled="!!jsonError || !!fieldError"
          @click="mode = mode === 'fields' ? 'json' : 'fields'"
          >{{ mode === 'fields' ? '编辑 JSON' : '字段视图' }}</a-button
        ><a-button v-if="mode === 'fields'" size="small" :disabled="disabled" @click="addField"
          >＋ 添加字段</a-button
        ></a-space
      >
    </div>
    <div v-if="mode === 'json'" class="json-area">
      <a-textarea
        :value="jsonText"
        :rows="10"
        :disabled="disabled"
        @update:value="editJson"
        aria-label="编辑结构定义 JSON"
      />
      <p v-if="jsonError" class="schema-error">{{ jsonError }}</p>
      <p v-else class="schema-help">使用 JSON Schema 定义输入与输出；支持嵌套对象、枚举和约束。</p>
    </div>
    <template v-else>
      <p v-if="complexSchema" class="schema-help">
        包含嵌套或高级约束。字段视图保留这些设置，可切换到 JSON 编辑完整定义。
      </p>
      <div v-for="field in fields" :key="field.name" class="schema-row">
        <a-input
          :value="field.name"
          :disabled="disabled"
          placeholder="字段名"
          aria-label="字段名"
          @change="rename(field.name, $event.target.value)"
        />
        <a-select
          :value="field.type"
          :disabled="disabled"
          :options="typeOptions"
          style="width: 108px"
          aria-label="字段类型"
          @update:value="changeField(field.name, 'type', $event)"
        />
        <a-input
          :value="field.description"
          :disabled="disabled"
          placeholder="业务含义"
          aria-label="字段业务含义"
          @update:value="changeField(field.name, 'description', $event)"
        />
        <a-checkbox
          :checked="field.required"
          :disabled="disabled"
          @update:checked="requireField(field.name, $event)"
          >必填</a-checkbox
        >
        <a-button type="text" danger :disabled="disabled" @click="removeField(field.name)"
          >移除</a-button
        >
      </div>
      <div v-if="!fields.length" class="schema-empty">
        暂无字段。可按业务需要添加，或使用 JSON 编辑复杂结构。
      </div>
      <p v-if="fieldError" class="schema-error">{{ fieldError }}</p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
const props = defineProps<{
  modelValue: Record<string, unknown>
  title: string
  disabled?: boolean
}>()
const emit = defineEmits<{ 'update:modelValue': [Record<string, unknown>]; validity: [boolean] }>()
const mode = ref('fields')
const jsonText = ref('')
const jsonError = ref('')
const fieldError = ref('')
const typeOptions = ['string', 'number', 'integer', 'boolean', 'object', 'array'].map((v) => ({
  value: v,
  label: (
    {
      string: '文本',
      number: '数字',
      integer: '整数',
      boolean: '是 / 否',
      object: '对象',
      array: '列表',
    } as Record<string, string>
  )[v],
}))
const properties = computed<Record<string, unknown>>(() => {
  const value = props.modelValue.properties
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
})
const requiredFields = computed<string[]>(() =>
  Array.isArray(props.modelValue.required)
    ? props.modelValue.required.filter((name): name is string => typeof name === 'string')
    : [],
)
const fields = computed(() =>
  Object.entries(properties.value).map(([name, value]) => {
    const p = value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
    return {
      name,
      type: p.type || 'string',
      description: String(p.description || ''),
      required: requiredFields.value.includes(name),
    }
  }),
)
const complexSchema = computed(() =>
  fields.value.some((f) => f.type === 'object' || f.type === 'array'),
)
watch(
  () => props.modelValue,
  (value) => {
    if (!jsonError.value) jsonText.value = JSON.stringify(value, null, 2)
  },
  { deep: true, immediate: true },
)
watch(mode, () => {
  if (mode.value === 'json') jsonText.value = JSON.stringify(props.modelValue, null, 2)
  jsonError.value = ''
  fieldError.value = ''
  emit('validity', true)
})
function commit(schema: Record<string, unknown>) {
  emit('update:modelValue', schema)
}
function addField() {
  const p = { ...properties.value }
  let n = Object.keys(p).length + 1
  while (p[`field_${n}`]) n++
  p[`field_${n}`] = { type: 'string', description: '' }
  commit({ ...props.modelValue, type: 'object', properties: p })
}
function changeField(name: string, key: string, value: unknown) {
  const p = { ...properties.value } as Record<string, Record<string, unknown>>
  p[name] = { ...p[name], [key]: value }
  if (key === 'type' && value === 'array' && !p[name].items) p[name].items = { type: 'string' }
  commit({ ...props.modelValue, type: 'object', properties: p })
}
function rename(name: string, value: string | undefined) {
  const next = (value || '').trim()
  const p = { ...properties.value }
  if (!next || (next !== name && next in p)) {
    fieldError.value = '字段名不能为空或重复'
    emit('validity', false)
    return
  }
  fieldError.value = ''
  emit('validity', true)
  if (name === next) return
  p[next] = p[name]
  delete p[name]
  commit({
    ...props.modelValue,
    type: 'object',
    properties: p,
    required: requiredFields.value.map((n) => (n === name ? next : n)),
  })
}
function removeField(name: string) {
  const p = { ...properties.value }
  delete p[name]
  commit({
    ...props.modelValue,
    properties: p,
    required: requiredFields.value.filter((n) => n !== name),
  })
  fieldError.value = ''
  emit('validity', true)
}
function requireField(name: string, checked: boolean) {
  const r = new Set(requiredFields.value)
  if (checked) r.add(name)
  else r.delete(name)
  commit({ ...props.modelValue, required: [...r] })
}
function editJson(value: string) {
  jsonText.value = value
  try {
    const parsed = JSON.parse(value)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed))
      throw new Error('结构定义必须是 JSON 对象')
    if (
      parsed.properties !== undefined &&
      (!parsed.properties ||
        typeof parsed.properties !== 'object' ||
        Array.isArray(parsed.properties))
    )
      throw new Error('properties 必须是字段定义对象')
    if (
      Object.values(parsed.properties || {}).some(
        (field) =>
          field === null ||
          (typeof field !== 'object' && typeof field !== 'boolean') ||
          Array.isArray(field),
      )
    )
      throw new Error('每个字段必须是结构定义对象或布尔约束')
    if (
      parsed.required !== undefined &&
      (!Array.isArray(parsed.required) ||
        parsed.required.some((name: unknown) => typeof name !== 'string'))
    )
      throw new Error('required 必须是字段名称数组')
    jsonError.value = ''
    emit('validity', true)
    commit(parsed)
  } catch (e) {
    jsonError.value = e instanceof Error ? e.message : 'JSON 格式错误'
    emit('validity', false)
  }
}
</script>

<style scoped>
.schema-editor {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  margin-bottom: 16px;
  overflow: hidden;
}
.schema-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 600;
}
.schema-row {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 10px 12px;
  border-top: 1px solid #f1f5f9;
}
.schema-row > .ant-input {
  min-width: 90px;
  flex: 1;
}
.schema-row > .ant-checkbox-wrapper {
  white-space: nowrap;
  font-size: 12px;
}
.schema-row > .ant-btn {
  padding: 4px;
  font-size: 12px;
}
.schema-empty {
  padding: 24px;
  text-align: center;
  font-size: 12px;
  color: #64748b;
}
.json-area {
  padding: 12px;
}
.json-area textarea {
  font:
    12px/1.7 ui-monospace,
    monospace;
}
.schema-help {
  font-size: 12px;
  color: #64748b;
  padding: 0 12px;
  margin: 12px 0;
}
.schema-error {
  font-size: 12px;
  color: #b91c1c;
  margin: 8px 12px;
}
@media (max-width: 1100px) {
  .schema-row {
    flex-wrap: wrap;
  }
  .schema-row > .ant-input {
    min-width: 140px;
  }
}
</style>
