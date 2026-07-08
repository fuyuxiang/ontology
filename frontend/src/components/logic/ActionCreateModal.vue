<template>
  <ModalDialog :visible="visible" title="创建动作" width="560px" @close="$emit('close')">
    <div class="create-form">
      <div class="form-section">
        <label class="form-label form-label--required">动作名称</label>
        <div class="input-wrap">
          <input v-model="form.name" class="form-input" placeholder="请输入动作名称" maxlength="200" />
          <span class="input-count">{{ form.name.length }}/200</span>
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
        <label class="form-label form-label--required">分类</label>
        <select v-model="form.category" class="form-input form-select">
          <option value="domain">领域行动</option>
          <option value="system">系统行动</option>
        </select>
      </div>

      <div class="form-section">
        <label class="form-label form-label--required">行动类型</label>
        <select v-model="form.action_type" class="form-input form-select">
          <option v-for="t in actionTypes" :key="t.type_key" :value="t.type_key">{{ t.label }}</option>
        </select>
      </div>

      <div v-if="form.category === 'domain'" class="form-section">
        <label class="form-label form-label--required">关联对象</label>
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
import { actionApi, type ActionTypeInfo } from '../../api/actions'
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
const actionTypes = ref<ActionTypeInfo[]>([])
const saving = ref(false)

const form = ref({
  name: '',
  description: '',
  category: 'domain' as 'domain' | 'system',
  action_type: 'python_script',
  entity_id: '',
})

function resetForm() {
  form.value = { name: '', description: '', category: 'domain', action_type: 'python_script', entity_id: '' }
}

async function loadData() {
  const [ents, types] = await Promise.all([entityApi.list(), actionApi.types()])
  entities.value = ents
  actionTypes.value = types
}

watch(() => props.visible, (v) => { if (v) { resetForm(); loadData() } })
onMounted(() => { if (props.visible) loadData() })

async function handleCreate() {
  if (!form.value.name.trim()) { toast.error('请填写动作名称'); return }
  if (form.value.category === 'domain' && !form.value.entity_id) {
    toast.error('领域行动必须绑定实体'); return
  }
  saving.value = true
  try {
    const result = await actionApi.create({
      name: form.value.name.trim(),
      description: form.value.description,
      category: form.value.category,
      action_type: form.value.action_type,
      entity_id: form.value.category === 'domain' ? form.value.entity_id : undefined,
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
