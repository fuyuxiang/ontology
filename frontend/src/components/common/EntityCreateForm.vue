<template>
  <ModalDialog :visible="visible" title="新建本体对象" width="640px" @close="$emit('close')">
    <form @submit.prevent="handleSubmit" class="entity-form">
      <div class="form-row">
        <label class="form-label">对象名称 (英文)</label>
        <input v-model="form.name" class="form-input" placeholder="如 Customer, FTTRSubscription" required />
      </div>
      <div class="form-row">
        <label class="form-label">中文名称</label>
        <input v-model="form.name_cn" class="form-input" placeholder="如 客户, FTTR订阅" required />
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
        <label class="form-label">描述</label>
        <textarea v-model="form.description" class="form-input form-textarea" placeholder="对象描述..." rows="2" />
      </div>

      <div class="form-section">
        <div class="form-section-header">
          <span class="form-label">属性列表</span>
          <button type="button" class="btn-sm" @click="addAttr">+ 添加属性</button>
        </div>
        <div v-for="(attr, i) in form.attributes" :key="i" class="attr-row">
          <input v-model="attr.name" class="form-input form-input--sm" placeholder="属性名" />
          <select v-model="attr.type" class="form-input form-input--sm">
            <option v-for="t in attrTypes" :key="t" :value="t">{{ t }}</option>
          </select>
          <input v-model="attr.description" class="form-input form-input--sm" placeholder="描述" style="flex:2" />
          <label class="form-checkbox"><input type="checkbox" v-model="attr.required" /> 必填</label>
          <button type="button" class="btn-icon" @click="form.attributes.splice(i, 1)">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </button>
        </div>
      </div>
    </form>

    <template #footer>
      <button class="btn-secondary" @click="$emit('close')">取消</button>
      <button class="btn-primary" @click="handleSubmit" :disabled="submitting">
        {{ submitting ? '创建中...' : '创建对象' }}
      </button>
    </template>
  </ModalDialog>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import ModalDialog from './ModalDialog.vue'
import { entityApi } from '../../api/ontology'

defineProps<{ visible: boolean }>()
const emit = defineEmits<{ close: []; created: [] }>()

const tierNames: Record<number, string> = { 1: '核心', 2: '领域', 3: '场景' }
const attrTypes = ['string', 'number', 'boolean', 'date', 'ref', 'computed', 'enum', 'json']

const submitting = ref(false)
const form = reactive({
  name: '',
  name_cn: '',
  tier: 1,
  description: '',
  attributes: [] as { name: string; type: string; description: string; required: boolean }[],
})

function addAttr() {
  form.attributes.push({ name: '', type: 'string', description: '', required: false })
}

async function handleSubmit() {
  if (!form.name || !form.name_cn) return
  submitting.value = true
  try {
    await entityApi.create({
      name: form.name,
      name_cn: form.name_cn,
      tier: form.tier,
      description: form.description,
      attributes: form.attributes.filter(a => a.name),
    } as never)
    form.name = ''
    form.name_cn = ''
    form.tier = 1
    form.description = ''
    form.attributes = []
    emit('created')
    emit('close')
  } catch (e) {
    alert(`创建失败: ${(e as Error).message}`)
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
.form-input--sm { padding: 6px 8px; font-size: 12px; }
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
.form-section { margin-top: 4px; }
.form-section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.attr-row { display: flex; gap: 6px; align-items: center; margin-bottom: 6px; }
.attr-row .form-input { flex: 1; }
.form-checkbox { display: flex; align-items: center; gap: 4px; font-size: 11px; color: var(--neutral-600); white-space: nowrap; }
.btn-sm {
  padding: 4px 10px; border-radius: var(--radius-md); border: 1px solid var(--semantic-400);
  background: transparent; color: var(--semantic-600); font-size: 11px; cursor: pointer;
}
.btn-sm:hover { background: var(--semantic-50); }
.btn-icon {
  width: 24px; height: 24px; border: none; background: transparent;
  color: var(--neutral-400); cursor: pointer; display: flex; align-items: center; justify-content: center;
}
.btn-icon:hover { color: var(--status-error); }
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
</style>
