<template>
  <ModalDialog :visible="visible" title="创建逻辑" width="560px" @close="$emit('close')">
    <div class="create-form">
      <div class="form-section">
        <label class="form-label form-label--required">中文名称</label>
        <div class="input-wrap">
          <input v-model="form.name" class="form-input" placeholder="请输入中文名称" maxlength="100" />
          <span class="input-count">{{ form.name.length }}/100</span>
        </div>
      </div>

      <div class="form-section">
        <label class="form-label form-label--required">英文名称</label>
        <div class="input-wrap">
          <input v-model="form.callable_name" class="form-input" placeholder="请输入英文名称" maxlength="100" />
          <span class="input-count">{{ form.callable_name.length }}/100</span>
        </div>
      </div>

      <div class="form-section">
        <label class="form-label">描述</label>
        <div class="input-wrap">
          <textarea v-model="form.description" class="form-input form-textarea" placeholder="请输入描述" maxlength="2000" rows="3" />
          <span class="input-count">{{ form.description.length }}/2000</span>
        </div>
      </div>
      <div class="form-section">
        <label class="form-label">对象</label>
        <select v-model="form.entity_id" class="form-input form-select">
          <option value="">请选择对象</option>
          <option v-for="e in entities" :key="e.id" :value="e.id">{{ e.name_cn || e.name }}</option>
        </select>
      </div>
    </div>

    <template #footer>
      <button class="btn-secondary" @click="$emit('close')">取消</button>
      <button class="btn-primary" :disabled="saving" @click="handleCreate">
        {{ saving ? '创建中…' : '创建' }}
      </button>
    </template>
  </ModalDialog>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { functionApi } from '../../api/functions'
import { entityApi } from '../../api/ontology'
import { useToast } from '../../composables/useToast'
import ModalDialog from '../common/ModalDialog.vue'
import type { EntityListItem } from '../../types'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'created', val: { id: string; name: string }): void
}>()

const router = useRouter()
const toast = useToast()
const entities = ref<EntityListItem[]>([])
const saving = ref(false)

const form = ref({
  name: '',
  callable_name: '',
  description: '',
  entity_id: '',
  logic_type: 'python',
})

function resetForm() {
  form.value = { name: '', callable_name: '', description: '', entity_id: '', logic_type: 'python' }
}

async function loadEntities() {
  entities.value = await entityApi.list()
}

watch(() => props.visible, (v) => { if (v) { resetForm(); loadEntities() } })
onMounted(() => { if (props.visible) loadEntities() })

async function handleCreate() {
  if (!form.value.name.trim()) { toast.error('请填写中文名称'); return }
  if (!form.value.callable_name.trim()) { toast.error('请填写英文名称'); return }
  saving.value = true
  try {
    const result = await functionApi.create({
      name: form.value.name.trim(),
      callable_name: form.value.callable_name.trim(),
      description: form.value.description,
      entity_id: form.value.entity_id || null,
      entity_ids: form.value.entity_id ? [form.value.entity_id] : [],
      logic_type: form.value.logic_type,
      logic_body: '',
      return_type: 'string',
      status: 'active',
    })
    toast.success('函数创建成功')
    emit('created', { id: result.id, name: result.name })
    router.push(`/logic/functions/${result.id}/code`)
  } catch (err: any) {
    toast.error(err?.message || '创建失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.create-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 8px 0;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--neutral-700, #333);
}

.form-label--required::before {
  content: '★';
  color: #e53e3e;
  font-size: 10px;
  margin-right: 4px;
}

.type-selector {
  display: flex;
  gap: 0;
}

.type-option {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border: 1px solid var(--neutral-200, #e5e5e5);
  background: var(--neutral-0, #fff);
  cursor: pointer;
  font-size: 13px;
  color: var(--neutral-700, #333);
  transition: all 0.15s;
}

.type-option:first-child {
  border-radius: 8px 0 0 8px;
}

.type-option:last-child {
  border-radius: 0 8px 8px 0;
}

.type-option:not(:first-child) {
  border-left: none;
}

.type-option--active {
  border-color: var(--semantic-500, #4f46e5);
  background: var(--semantic-50, #eef2ff);
  z-index: 1;
  position: relative;
}

.type-option--active + .type-option {
  border-left: 1px solid var(--semantic-500, #4f46e5);
}

.type-radio {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid var(--neutral-300, #d4d4d4);
  position: relative;
  flex-shrink: 0;
}

.type-radio--checked {
  border-color: var(--semantic-500, #4f46e5);
}

.type-radio--checked::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--semantic-500, #4f46e5);
}

.input-wrap {
  position: relative;
}

.input-count {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 11px;
  color: var(--neutral-400, #aaa);
  pointer-events: none;
}

.form-textarea + .input-count {
  top: auto;
  bottom: 8px;
  transform: none;
}

.form-input {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  border: 1px solid var(--neutral-200, #e5e5e5);
  border-radius: 8px;
  font-size: 13px;
  color: var(--neutral-800, #333);
  background: var(--neutral-50, #fafafa);
  transition: border-color 0.15s;
}

.form-input:focus {
  outline: none;
  border-color: var(--semantic-400, #818cf8);
  background: var(--neutral-0, #fff);
}

.form-input::placeholder {
  color: var(--neutral-400, #aaa);
}

.form-textarea {
  resize: vertical;
  min-height: 72px;
  padding-right: 60px;
}

.form-select {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg width='10' height='6' viewBox='0 0 10 6' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%23888' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 32px;
}

.btn-secondary {
  padding: 8px 20px;
  border: 1px solid var(--neutral-200, #e5e5e5);
  border-radius: 8px;
  background: var(--neutral-0, #fff);
  color: var(--neutral-700, #333);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-secondary:hover {
  background: var(--neutral-50, #fafafa);
}
</style>
