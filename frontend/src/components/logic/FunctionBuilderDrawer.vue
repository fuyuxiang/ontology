<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { functionApi } from '../../api/functions'
import { entityApi } from '../../api/ontology'
import { useToast } from '../../composables/useToast'
import type { EntityListItem } from '../../types'

const props = defineProps<{
  visible: boolean
  editId?: string
  lockedEntityId?: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved', val: { id: string; name: string }): void
}>()

const toast = useToast()
const entities = ref<EntityListItem[]>([])
const saving = ref(false)
const testing = ref(false)
const testInput = ref('{}')
const testResult = ref<string | null>(null)
const testSuccess = ref<boolean | null>(null)
const savedId = ref<string | null>(null)

const form = ref({
  name: '',
  callable_name: '',
  description: '',
  entity_id: '',
  return_type: 'string',
  is_derived_property: false,
  tags: '',
  input_params: [] as { name: string; type: string; required: boolean; description: string }[],
  logic_type: 'expression' as 'expression' | 'sql' | 'python',
  logic_body: '',
})

async function load() {
  entities.value = await entityApi.list()
  if (props.lockedEntityId) form.value.entity_id = props.lockedEntityId
  if (props.editId) {
    const fn = await functionApi.detail(props.editId)
    savedId.value = fn.id
    form.value.name = fn.name
    form.value.callable_name = fn.callable_name
    form.value.description = fn.description
    form.value.entity_id = fn.entity_id ?? ''
    form.value.return_type = fn.return_type
    form.value.is_derived_property = fn.is_derived_property
    form.value.tags = Array.isArray(fn.tags) ? fn.tags.join(', ') : ''
    form.value.input_params = (fn.input_schema ?? []) as any
    form.value.logic_type = (fn.logic_type as any) ?? 'expression'
    form.value.logic_body = fn.logic_body ?? ''
  }
}

function resetForm() {
  savedId.value = null
  testResult.value = null
  testSuccess.value = null
  form.value = {
    name: '', callable_name: '', description: '',
    entity_id: props.lockedEntityId ?? '',
    return_type: 'string',
    is_derived_property: false,
    tags: '',
    input_params: [],
    logic_type: 'expression',
    logic_body: '',
  }
}

watch(() => props.visible, (v) => { if (v) { resetForm(); load() } })
onMounted(() => { if (props.visible) { resetForm(); load() } })

function addParam() {
  form.value.input_params.push({ name: '', type: 'string', required: false, description: '' })
}
function removeParam(idx: number) {
  form.value.input_params.splice(idx, 1)
}

async function save() {
  if (!form.value.name.trim()) { toast.error('请填写函数名称'); return }
  if (!form.value.callable_name.trim()) { toast.error('请填写调用名称'); return }
  saving.value = true
  try {
    const payload: any = {
      name: form.value.name.trim(),
      callable_name: form.value.callable_name.trim(),
      description: form.value.description,
      entity_id: form.value.entity_id || null,
      return_type: form.value.return_type,
      is_derived_property: form.value.is_derived_property,
      tags: form.value.tags.split(',').map(t => t.trim()).filter(Boolean),
      input_schema: form.value.input_params,
      logic_type: form.value.logic_type,
      logic_body: form.value.logic_body,
    }
    let result: any
    if (props.editId) {
      result = await functionApi.update(props.editId, payload)
    } else {
      result = await functionApi.create(payload)
    }
    savedId.value = result.id
    toast.success(props.editId ? '函数已更新' : '函数已创建')
    emit('saved', { id: result.id, name: result.name })
  } catch (e: any) {
    toast.error(e?.message ?? '保存失败')
  } finally {
    saving.value = false
  }
}

async function runTest() {
  if (!savedId.value && !props.editId) {
    toast.info('请先保存函数后再测试')
    return
  }
  testing.value = true
  testResult.value = null
  testSuccess.value = null
  try {
    let params: Record<string, any> = {}
    try { params = JSON.parse(testInput.value) } catch { toast.error('输入参数不是合法 JSON'); testing.value = false; return }
    const id = (props.editId ?? savedId.value)!
    const res = await functionApi.test(id, params)
    testSuccess.value = res.success
    testResult.value = res.success
      ? JSON.stringify(res.result, null, 2)
      : (res.error ?? '执行失败')
  } catch (e: any) {
    testSuccess.value = false
    testResult.value = e?.message ?? '请求失败'
  } finally {
    testing.value = false
  }
}
</script>

<template>
  <Transition name="drawer">
    <div v-if="visible" class="drawer-overlay" @click.self="emit('close')">
      <div class="drawer-panel">
        <div class="drawer-panel__header">
          <h2>{{ editId ? '编辑函数' : '新建函数' }}</h2>
          <button class="btn-sm-edit" @click="emit('close')">✕</button>
        </div>

        <div class="drawer-panel__body">
          <!-- Basic info -->
          <div class="form-section">
            <div class="form-section__title">基本信息</div>
            <div class="rule-form">
              <div class="form-row-inline">
                <div class="form-row" style="flex:1;">
                  <label class="form-label">函数名称 *</label>
                  <input class="form-input" v-model="form.name" placeholder="显示名称" />
                </div>
                <div class="form-row" style="flex:1;">
                  <label class="form-label">调用名称 *</label>
                  <input class="form-input" v-model="form.callable_name" placeholder="snake_case" />
                </div>
              </div>
              <div class="form-row">
                <label class="form-label">描述</label>
                <textarea class="form-input" v-model="form.description" rows="2" placeholder="函数用途描述" />
              </div>
              <div class="form-row-inline">
                <div class="form-row" style="flex:1;">
                  <label class="form-label">关联实体（可选）</label>
                  <select class="form-input" v-model="form.entity_id" :disabled="!!lockedEntityId">
                    <option value="">— 不绑定实体 —</option>
                    <option v-for="e in entities" :key="e.id" :value="e.id">{{ e.name }}</option>
                  </select>
                </div>
                <div class="form-row" style="flex:1;">
                  <label class="form-label">返回类型</label>
                  <select class="form-input" v-model="form.return_type">
                    <option value="string">string</option>
                    <option value="number">number</option>
                    <option value="boolean">boolean</option>
                    <option value="date">date</option>
                    <option value="json">json</option>
                    <option value="array">array</option>
                  </select>
                </div>
              </div>
              <div class="form-row">
                <label style="display:flex;align-items:center;gap:6px;font-size:13px;cursor:pointer;">
                  <input type="checkbox" v-model="form.is_derived_property" />
                  作为派生属性使用
                </label>
              </div>
              <div class="form-row">
                <label class="form-label">标签（逗号分隔）</label>
                <input class="form-input" v-model="form.tags" placeholder="例如：聚合, 计算" />
              </div>
            </div>
          </div>

          <!-- Input params -->
          <div class="form-section">
            <div class="form-section__title">输入参数</div>
            <div v-for="(p, idx) in form.input_params" :key="idx" class="condition-row" style="flex-wrap:wrap;gap:6px;">
              <input class="form-input" style="flex:1.5;min-width:80px;" v-model="p.name" placeholder="参数名" />
              <select class="form-input" style="flex:1;min-width:80px;" v-model="p.type">
                <option value="string">string</option>
                <option value="number">number</option>
                <option value="boolean">boolean</option>
                <option value="date">date</option>
                <option value="json">json</option>
              </select>
              <input class="form-input" style="flex:2;min-width:100px;" v-model="p.description" placeholder="说明（可选）" />
              <label style="display:flex;align-items:center;gap:4px;font-size:12px;flex-shrink:0;">
                <input type="checkbox" v-model="p.required" /> 必填
              </label>
              <button class="btn-sm-del" @click="removeParam(idx)">✕</button>
            </div>
            <button class="btn-sm-exec" style="margin-top:4px;" @click="addParam">+ 添加参数</button>
          </div>

          <!-- Logic body -->
          <div class="form-section">
            <div class="form-section__title">逻辑体</div>
            <div class="mode-switch">
              <button :class="{ active: form.logic_type === 'expression' }" @click="form.logic_type = 'expression'">表达式</button>
              <button :class="{ active: form.logic_type === 'sql' }" @click="form.logic_type = 'sql'">SQL</button>
              <button :class="{ active: form.logic_type === 'python' }" @click="form.logic_type = 'python'">Python</button>
            </div>
            <textarea class="form-input form-input--code" v-model="form.logic_body" rows="8"
              :placeholder="form.logic_type === 'expression' ? '例如：entity.score * 0.8 + bonus' : form.logic_type === 'sql' ? 'SELECT ...' : 'def run(params):\n    return ...'" />
          </div>

          <!-- Test panel -->
          <div class="form-section">
            <div class="form-section__title">测试面板</div>
            <div class="form-row">
              <label class="form-label">输入参数（JSON）</label>
              <textarea class="form-input form-input--code" v-model="testInput" rows="3" placeholder='{"param1": "value1"}' />
            </div>
            <button class="btn-sm-exec" :disabled="testing" style="margin-top:8px;" @click="runTest">
              {{ testing ? '执行中…' : '▶ 运行测试' }}
            </button>
            <div v-if="testResult !== null" style="margin-top:12px;padding:10px 12px;border-radius:6px;font-size:12px;font-family:monospace;white-space:pre-wrap;"
              :style="testSuccess ? 'background:#f0fdf4;border:1px solid #86efac;' : 'background:#fef2f2;border:1px solid #fca5a5;'">
              {{ testResult }}
            </div>
          </div>
        </div>

        <div class="drawer-panel__footer">
          <button class="btn-sm-edit" @click="emit('close')">取消</button>
          <button class="btn-primary" :disabled="saving" @click="save">
            {{ saving ? '保存中…' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
@import '../../views/logic/logic-shared.css';
</style>
