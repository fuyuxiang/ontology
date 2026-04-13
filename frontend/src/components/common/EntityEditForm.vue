<template>
  <ModalDialog :visible="visible" :title="`编辑 ${entity?.name ?? ''}`" width="640px" @close="$emit('close')">
    <form v-if="entity" @submit.prevent="handleSubmit" class="entity-form">
      <div class="form-row">
        <label class="form-label">对象名称 (英文)</label>
        <input v-model="form.name" class="form-input" required />
      </div>
      <div class="form-row">
        <label class="form-label">中文名称</label>
        <input v-model="form.name_cn" class="form-input" required />
      </div>
      <div class="form-row">
        <label class="form-label">Tier 层级</label>
        <div class="form-radio-group">
          <label v-for="t in [1,2,3]" :key="t" class="form-radio" :class="{ 'form-radio--active': form.tier === t }">
            <input type="radio" :value="t" v-model="form.tier" />
            <span class="tier-dot" :style="{ background: `var(--tier${t}-primary)` }"></span>
            Tier {{ t }} {{ tierNames[t] }}
          </label>
        </div>
      </div>
      <div class="form-row">
        <label class="form-label">状态</label>
        <select v-model="form.status" class="form-input">
          <option value="active">活跃</option>
          <option value="warning">警告</option>
          <option value="error">异常</option>
        </select>
      </div>
      <div class="form-row">
        <label class="form-label">描述</label>
        <textarea v-model="form.description" class="form-input form-textarea" rows="2" />
      </div>
    </form>

    <template #footer>
      <button class="btn-danger" @click="handleDelete" :disabled="submitting">删除对象</button>
      <div style="flex:1"></div>
      <button class="btn-secondary" @click="$emit('close')">取消</button>
      <button class="btn-primary" @click="handleSubmit" :disabled="submitting">
        {{ submitting ? '保存中...' : '保存' }}
      </button>
    </template>
  </ModalDialog>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import ModalDialog from './ModalDialog.vue'
import { entityApi } from '../../api/ontology'

interface EntityData {
  id: string; name: string; name_cn: string; tier: number; status: string; description: string
}

const props = defineProps<{ visible: boolean; entity: EntityData | null }>()
const emit = defineEmits<{ close: []; updated: []; deleted: [] }>()

const tierNames: Record<number, string> = { 1: '核心', 2: '领域', 3: '场景' }
const submitting = ref(false)

const form = reactive({ name: '', name_cn: '', tier: 1, status: 'active', description: '' })

watch(() => props.entity, (e) => {
  if (e) {
    form.name = e.name
    form.name_cn = e.name_cn
    form.tier = e.tier
    form.status = e.status
    form.description = e.description || ''
  }
}, { immediate: true })

async function handleSubmit() {
  if (!props.entity || !form.name) return
  submitting.value = true
  try {
    await entityApi.update(props.entity.id, form as never)
    emit('updated')
    emit('close')
  } catch (e) {
    alert(`保存失败: ${(e as Error).message}`)
  } finally {
    submitting.value = false
  }
}

async function handleDelete() {
  if (!props.entity) return
  if (!confirm(`确定删除 ${props.entity.name}？此操作不可撤销。`)) return
  submitting.value = true
  try {
    await entityApi.remove(props.entity.id)
    emit('deleted')
    emit('close')
  } catch (e) {
    alert(`删除失败: ${(e as Error).message}`)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.entity-form { display: flex; flex-direction: column; gap: 14px; }
.form-row { display: flex; flex-direction: column; gap: 4px; }
.form-label { font-size: 12px; font-weight: 500; color: var(--neutral-600); }
.form-input {
  padding: 8px 12px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md);
  font-size: 13px; color: var(--neutral-800); background: var(--neutral-0); outline: none;
}
.form-input:focus { border-color: var(--semantic-500); }
.form-textarea { resize: vertical; font-family: inherit; }
.form-radio-group { display: flex; gap: 12px; }
.form-radio {
  display: flex; align-items: center; gap: 6px; padding: 6px 12px;
  border: 1px solid var(--neutral-200); border-radius: var(--radius-md);
  font-size: 12px; cursor: pointer; transition: all var(--transition-fast);
}
.form-radio input { display: none; }
.form-radio--active { border-color: var(--semantic-500); background: var(--semantic-50); }
.tier-dot { width: 8px; height: 8px; border-radius: 50%; }
.btn-primary {
  padding: 8px 20px; border-radius: var(--radius-md); border: none;
  background: var(--semantic-600); color: #fff; font-size: 13px; font-weight: 500; cursor: pointer;
}
.btn-primary:hover { background: var(--semantic-700); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-secondary {
  padding: 8px 16px; border-radius: var(--radius-md); border: 1px solid var(--neutral-300);
  background: var(--neutral-0); color: var(--neutral-700); font-size: 13px; cursor: pointer;
}
.btn-secondary:hover { background: var(--neutral-50); }
.btn-danger {
  padding: 8px 16px; border-radius: var(--radius-md); border: 1px solid var(--status-error);
  background: var(--status-error-bg); color: var(--status-error); font-size: 13px; cursor: pointer;
}
.btn-danger:hover { background: var(--status-error); color: #fff; }
.btn-danger:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
