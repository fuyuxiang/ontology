<template>
  <ModalDialog :visible="visible" title="创建动作" width="560px" @close="$emit('close')">
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
import { useRoute, useRouter } from 'vue-router'
import { actionApi } from '../../api/actions'
import { entityApi } from '../../api/ontology'
import { useOntologyStore } from '../../store/ontology'
import { useToast } from '../../composables/useToast'
import ModalDialog from '../common/ModalDialog.vue'
import type { EntityListItem } from '../../types'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'created', val: { id: string; name: string }): void
}>()

const route = useRoute()
const router = useRouter()
const toast = useToast()
const ontologyStore = useOntologyStore()
const entities = ref<EntityListItem[]>([])
const saving = ref(false)

const form = ref({
  name: '',
  callable_name: '',
  description: '',
  entity_id: '',
})

function resetForm() {
  form.value = { name: '', callable_name: '', description: '', entity_id: '' }
}

async function loadEntities() {
  entities.value = await entityApi.list()
}

watch(() => props.visible, (v) => { if (v) { resetForm(); loadEntities() } })
onMounted(() => { if (props.visible) loadEntities() })

async function handleCreate() {
  if (!form.value.name.trim()) { toast.error('请填写中文名称'); return }
  if (!form.value.callable_name.trim()) { toast.error('请填写英文名称'); return }
  if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(form.value.callable_name.trim())) {
    toast.error('英文名称必须是合法标识符（字母或下划线开头，仅含字母、数字、下划线）')
    return
  }
  saving.value = true
  try {
    const result = await actionApi.create({
      name: form.value.callable_name.trim(),
      description: form.value.description,
      category: form.value.entity_id ? 'domain' : 'system',
      action_type: 'python_script',
      entity_id: form.value.entity_id || undefined,
      ontology_id: ontologyStore.currentOntologyId || undefined,
    } as any)
    toast.success('动作创建成功')
    emit('created', { id: result.id, name: result.name })
    const query: Record<string, string> = {}
    if (route.params.code) {
      query.from = 'ontology'
      query.code = route.params.code as string
    }
    router.push({ path: `/logic/actions/${result.id}/code`, query })
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
