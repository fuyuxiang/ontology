<template>
  <div class="scenario-page">
    <div class="scenario-page__header">
      <div>
        <h1 class="text-display">场景管理</h1>
        <p class="text-caption" style="margin-top: 4px;">维护本体对象的业务场景划分</p>
      </div>
      <button class="btn-primary" @click="openCreate">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M7 2v10M2 7h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        新建场景
      </button>
    </div>

    <div class="scenario-list">
      <div v-for="s in store.scenarios" :key="s.id" class="scenario-item">
        <span class="scenario-item__color" :style="{ background: s.color || '#94a3b8' }"></span>
        <div class="scenario-item__info">
          <div class="scenario-item__name">
            {{ s.name }}
            <code class="scenario-item__code">{{ s.code }}</code>
          </div>
          <div class="scenario-item__desc">{{ s.description || '—' }}</div>
        </div>
        <div class="scenario-item__actions">
          <button class="btn-sm" @click="openEdit(s)">编辑</button>
          <button class="btn-sm btn-sm--del" @click="handleDelete(s)">删除</button>
        </div>
      </div>
      <div v-if="store.scenarios.length === 0" class="scenario-empty">
        <p class="text-caption">暂无场景，点击右上角新建</p>
      </div>
    </div>

    <ModalDialog :visible="showForm" :title="editing ? '编辑场景' : '新建场景'" width="480px" @close="showForm = false">
      <form class="scenario-form" @submit.prevent="handleSubmit">
        <div class="form-row">
          <label class="form-label">场景代码 (英文，唯一)</label>
          <input v-model="form.code" class="form-input" :disabled="!!editing" placeholder="如 churn" required />
        </div>
        <div class="form-row">
          <label class="form-label">场景名称</label>
          <input v-model="form.name" class="form-input" placeholder="如 退单智能归因" required />
        </div>
        <div class="form-row">
          <label class="form-label">颜色</label>
          <div class="color-row">
            <input v-model="form.color" type="color" class="color-input" />
            <input v-model="form.color" class="form-input" placeholder="#FF6B35" />
          </div>
        </div>
        <div class="form-row">
          <label class="form-label">描述</label>
          <textarea v-model="form.description" class="form-input" rows="2" />
        </div>
      </form>
      <template #footer>
        <div style="flex:1"></div>
        <button class="btn-secondary" @click="showForm = false">取消</button>
        <button class="btn-primary" @click="handleSubmit" :disabled="submitting">
          {{ submitting ? '保存中...' : '保存' }}
        </button>
      </template>
    </ModalDialog>
  </div>
</template>

<!-- PLACEHOLDER_SCRIPT -->
<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import ModalDialog from '../../components/common/ModalDialog.vue'
import { scenarioApi, type Scenario } from '../../api/scenarios'
import { useScenarioStore } from '../../store/scenarios'
import { useToast } from '../../composables/useToast'

const store = useScenarioStore()
const toast = useToast()

const showForm = ref(false)
const submitting = ref(false)
const editing = ref<Scenario | null>(null)
const form = reactive({ code: '', name: '', color: '#4c6ef5', description: '' })

onMounted(() => store.fetchScenarios(true))

function openCreate() {
  editing.value = null
  form.code = ''
  form.name = ''
  form.color = '#4c6ef5'
  form.description = ''
  showForm.value = true
}

function openEdit(s: Scenario) {
  editing.value = s
  form.code = s.code
  form.name = s.name
  form.color = s.color || '#4c6ef5'
  form.description = s.description || ''
  showForm.value = true
}

async function handleSubmit() {
  if (!form.code || !form.name) return
  submitting.value = true
  try {
    if (editing.value) {
      await scenarioApi.update(editing.value.id, {
        name: form.name, color: form.color, description: form.description,
      })
      toast.success('场景已更新')
    } else {
      await scenarioApi.create({
        code: form.code, name: form.name, color: form.color, description: form.description,
      })
      toast.success('场景已创建')
    }
    showForm.value = false
    await store.fetchScenarios(true)
  } catch (e) {
    toast.error(`保存失败: ${(e as Error).message}`)
  } finally {
    submitting.value = false
  }
}

async function handleDelete(s: Scenario) {
  if (!confirm(`确定删除场景「${s.name}」？`)) return
  try {
    await scenarioApi.remove(s.id)
    toast.success('场景已删除')
    await store.fetchScenarios(true)
  } catch (e) {
    toast.error(`删除失败: ${(e as Error).message}`)
  }
}
</script>

<!-- PLACEHOLDER_STYLE -->
<style scoped>
.scenario-page { padding: 24px 32px; max-width: 900px; }
.scenario-page__header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 24px; }

.scenario-list { display: flex; flex-direction: column; gap: 8px; }
.scenario-item {
  display: flex; align-items: center; gap: 14px;
  padding: 14px 18px; border-radius: var(--radius-lg, 12px);
  border: 1px solid var(--neutral-100, #f0f0f0); background: var(--neutral-0, #fff);
}
.scenario-item__color { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
.scenario-item__info { flex: 1; min-width: 0; }
.scenario-item__name { font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
.scenario-item__code { font-size: 11px; padding: 1px 6px; border-radius: 4px; background: var(--neutral-100, #f0f0f0); color: var(--neutral-500, #888); font-weight: 400; }
.scenario-item__desc { font-size: 12px; color: var(--neutral-500, #888); margin-top: 3px; }
.scenario-item__actions { display: flex; gap: 8px; }
.scenario-empty { text-align: center; padding: 40px; color: var(--neutral-400, #aaa); }

.btn-sm { padding: 4px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; border: 1px solid var(--neutral-200, #e5e5e5); background: var(--neutral-0, #fff); color: var(--neutral-600, #666); }
.btn-sm:hover { border-color: var(--semantic-400, #818cf8); color: var(--semantic-600, #4c6ef5); }
.btn-sm--del:hover { border-color: var(--status-error, #ef4444); color: var(--status-error, #ef4444); }

.scenario-form { display: flex; flex-direction: column; gap: 14px; }
.form-row { display: flex; flex-direction: column; gap: 4px; }
.form-label { font-size: 12px; font-weight: 500; color: var(--neutral-600, #666); }
.form-input { padding: 8px 12px; border: 1px solid var(--neutral-200, #e5e5e5); border-radius: var(--radius-md, 8px); font-size: 13px; color: var(--neutral-800, #333); background: var(--neutral-0, #fff); outline: none; font-family: inherit; }
.form-input:focus { border-color: var(--semantic-500, #4c6ef5); }
.form-input:disabled { background: var(--neutral-50, #fafafa); color: var(--neutral-400, #aaa); }
.color-row { display: flex; gap: 8px; align-items: center; }
.color-input { width: 40px; height: 36px; padding: 2px; border: 1px solid var(--neutral-200, #e5e5e5); border-radius: var(--radius-md, 8px); cursor: pointer; background: none; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: var(--radius-md, 8px); border: none; background: var(--semantic-600, #4c6ef5); color: var(--neutral-0, #fff); font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-primary:hover { background: var(--semantic-700, #4338ca); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-secondary { padding: 8px 16px; border-radius: var(--radius-md, 8px); border: 1px solid var(--neutral-300, #d4d4d4); background: var(--neutral-0, #fff); color: var(--neutral-700, #555); font-size: 13px; cursor: pointer; }
.btn-secondary:hover { background: var(--neutral-50, #fafafa); }
</style>
