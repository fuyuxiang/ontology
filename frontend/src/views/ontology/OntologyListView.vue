<template>
  <div class="ontology-list-page">
    <!-- 顶部 Banner -->
    <div class="page-banner">
      <div class="page-banner__content">
        <h1 class="page-banner__title">本体列表</h1>
        <p class="page-banner__desc">提供本体设计器，支持以人机协同方式，基于 AI 快速自动化构建本体；也支持通过手动定义的形式自顶向...</p>
      </div>
      <div class="page-banner__actions">
        <button class="btn-filled" @click="showCreate = true; createError = ''" :disabled="!canEdit">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 2v10M2 7h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          新建本体
        </button>
      </div>
    </div>

    <!-- 搜索筛选区 -->
    <div class="filter-bar">
      <div class="filter-bar__search">
        <svg class="filter-bar__search-icon" width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="6" cy="6" r="4.5" stroke="currentColor" stroke-width="1.3"/><path d="M9.5 9.5L12.5 12.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>
        <input v-model="search" class="filter-bar__input" placeholder="搜索本体" />
      </div>
    </div>

    <div v-if="scenarioStore.loading" class="card-grid__empty" role="status">本体列表加载中...</div>
    <div v-else-if="loadError" class="card-grid__empty" role="alert"><p>{{ loadError }}</p><button class="btn-cancel" @click="loadScenarios">重新加载</button></div>
    <!-- 卡片网格 -->
    <div class="card-grid">
      <div
        v-for="item in filteredList" :key="item.code"
        class="onto-card"
      >
        <div class="onto-card__top">
          <div class="onto-card__icon">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <circle cx="16" cy="8" r="4" stroke="#2563eb" stroke-width="1.5"/>
              <circle cx="8" cy="24" r="4" stroke="#2563eb" stroke-width="1.5"/>
              <circle cx="24" cy="24" r="4" stroke="#2563eb" stroke-width="1.5"/>
              <path d="M16 12v4M12 20l-2 2M20 20l2 2" stroke="#2563eb" stroke-width="1.5" stroke-linecap="round"/>
              <path d="M16 16l-4 4M16 16l4 4" stroke="#2563eb" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </div>
          <div class="onto-card__info">
            <div class="onto-card__name-row">
              <span class="onto-card__name" :title="item.name">{{ item.name }}</span>
            </div>
            <span class="onto-card__code">{{ item.code }}</span>
          </div>
          <span class="onto-card__badge">{{ item.entity_count > 0 ? '已建模' : '待构建' }}</span>
        </div>

        <p class="onto-card__desc">{{ item.description || '暂无描述' }}</p>

        <div class="onto-card__stats">
          <span class="onto-card__stat-item" title="对象">&#x1F4C4; {{ item.entity_count }}</span>
          <span class="onto-card__stat-item" title="关系">&#x1F517; {{ item.relation_count }}</span>
          <span class="onto-card__stat-item" title="逻辑">&#x26A1; {{ item.logic_count }}</span>
          <span class="onto-card__stat-item" title="动作">&#x1F3AF; {{ item.action_count }}</span>
        </div>

        <div class="onto-card__meta">
          <div class="onto-card__meta-item">
            <span class="onto-card__meta-label">更新</span>
            <span class="onto-card__meta-value">{{ item.updated_at?.slice(0, 10) || '—' }}</span>
          </div>
        </div>

        <div class="onto-card__footer">
          <span class="onto-card__status" :class="{'onto-card__status--active':item.active_version_id}">{{ item.active_version_id ? '已发布 · ' + (item.version_number || '活动版本') : '尚未发布' }}</span>
          <div class="onto-card__actions">
            <button class="onto-card__action-btn" @click.stop="goDetail(item.code)">详情</button>
            <button class="onto-card__action-btn onto-card__action-btn--del" :disabled="!canDelete || deletingId === item.id" :aria-label="`删除本体 ${item.name}`" @click.stop="handleDelete(item)">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 4h8M5 4V3h4v1M4 4v7h6V4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
          </div>
        </div>
      </div>

      <div v-if="filteredList.length === 0 && !scenarioStore.loading && !loadError" class="card-grid__empty">
        <p>{{ search.trim() ? '未找到匹配本体，请调整搜索关键词' : '暂无本体，点击新建本体开始构建' }}</p>
      </div>
    </div>

    <ModalDialog :visible="showCreate" title="构建本体" width="600px" @close="!creating && (showCreate = false)">
            <div class="modal-section-title"><span class="modal-section-bar"></span> 基础信息填写</div>

            <div class="modal-field">
              <label class="modal-label"><span class="required">*</span> 本体名称</label>
              <div class="modal-input-wrap">
                <input v-model="createForm.name" class="modal-input" maxlength="50" placeholder="请输入中文名称" />
                <span class="modal-input-count">{{ createForm.name.length }}/50</span>
              </div>
            </div>

            <div class="modal-field">
              <label class="modal-label"><span class="required">*</span> 本体标识</label>
              <div class="modal-input-wrap">
                <input v-model="createForm.code" class="modal-input" maxlength="100" placeholder="请输入英文标识" />
                <span class="modal-input-count">{{ createForm.code.length }}/100</span>
              </div>
            </div>

            <div class="modal-field">
              <label class="modal-label">本体描述</label>
              <div class="modal-input-wrap">
                <textarea v-model="createForm.description" class="modal-input modal-textarea" maxlength="2000" placeholder="简要说明该本体的业务领域和设计目标..." />
                <span class="modal-input-count modal-input-count--textarea">{{ createForm.description.length }}/2000</span>
              </div>
            </div>

      <p v-if="createError" class="modal-error" role="alert">{{ createError }}</p>
      <template #footer>
        <button class="btn-cancel" :disabled="creating" @click="showCreate = false">取消</button>
        <button class="btn-filled" :disabled="!canEdit || (creating || !createForm.name.trim() || !createForm.code.trim())" @click="handleCreate">{{ creating ? '创建中…' : '确认并查看本体' }}</button>
      </template>
    </ModalDialog>
  </div>
</template>

<script setup lang="ts">
import { useManagementPermission } from '../../composables/useManagementPermission'
const { canEdit } = useManagementPermission('entity:write')
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useScenarioStore } from '../../store/scenarios'
import { scenarioApi } from '../../api/scenarios'
import { message } from 'ant-design-vue'
import ModalDialog from '../../components/common/ModalDialog.vue'

const { canEdit:canDelete } = useManagementPermission('entity:delete')
const router = useRouter()
const scenarioStore = useScenarioStore()

const search = ref('')
const showCreate = ref(false)
const creating = ref(false)
const deletingId = ref<string | null>(null)
const loadError = ref('')
const createError = ref('')
const createForm = reactive({ name: '', code: '', description: '' })

const scenarios = computed(() => scenarioStore.scenarios)

const filteredList = computed(() => {
  const items = scenarios.value
  if (!search.value) return items
  const q = search.value.toLowerCase()
  return items.filter(i => i.name.toLowerCase().includes(q) || (i.description || '').toLowerCase().includes(q))
})

function goDetail(code: string) {
  router.push(`/ontology/list/${code}`)
}

function errorText(error: any, fallback: string) {
  const detail = error?.response?.data?.detail
  return typeof detail === 'string' ? detail : error?.message || fallback
}

async function handleCreate() {
  if (creating.value || !createForm.name.trim() || !createForm.code.trim()) return
  creating.value = true
  createError.value = ''
  try {
    const created = await scenarioApi.create({
      code: createForm.code.trim(), name: createForm.name.trim(), description: createForm.description.trim() || null,
    })
    showCreate.value = false
    createForm.name = ''
    createForm.code = ''
    createForm.description = ''
    await loadScenarios()
    router.push(`/ontology/list/${created.code}`)
  } catch (error) {
    createError.value = errorText(error, '本体创建失败，请重试')
  } finally {
    creating.value = false
  }
}

async function handleDelete(item: any) {
  if (!canDelete.value || deletingId.value || !confirm(`确定删除本体「${item.name}」？`)) return
  deletingId.value = item.id
  try {
    await scenarioApi.remove(item.id)
    message.success('本体已删除')
    await loadScenarios()
  } catch (error) {
    message.error(errorText(error, '本体删除失败，请重试'))
  } finally {
    deletingId.value = null
  }
}

async function loadScenarios() {
  loadError.value = ''
  try { await scenarioStore.fetchScenarios(true) }
  catch (error) { loadError.value = errorText(error, '本体列表加载失败') }
}

onMounted(loadScenarios)
</script>

<!-- STYLES -->
<style scoped>
.ontology-list-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 32px 32px;
  background: linear-gradient(135deg, #e8f4fd 0%, #dbeafe 50%, #eff6ff 100%);
  border-radius: var(--radius-lg, 12px);
  margin-bottom: 24px;
}

.page-banner__title {
  font-size: 24px;
  font-weight: 700;
  color: var(--neutral-900, #111);
  margin: 0 0 8px;
}

.page-banner__desc {
  font-size: 13px;
  color: var(--neutral-600, #555);
  margin: 0;
  max-width: 600px;
  line-height: 1.5;
}

.page-banner__actions {
  display: flex;
  gap: 12px;
}

.btn-outline {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  border: 1px solid var(--neutral-300, #d1d5db);
  border-radius: 8px;
  background: var(--neutral-0, #fff);
  color: var(--neutral-700, #333);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: border-color 0.15s;
}

.btn-outline:hover { border-color: var(--primary, #2563eb); color: var(--primary, #2563eb); }

.btn-filled {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  background: var(--primary, #2563eb);
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.15s;
}

.btn-filled:hover { opacity: 0.9; }
.btn-filled:disabled { opacity: 0.5; cursor: not-allowed; }

.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.filter-bar__search {
  position: relative;
  width: 280px;
}

.filter-bar__search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--neutral-400, #aaa);
}

.filter-bar__input {
  width: 100%;
  padding: 9px 12px 9px 32px;
  border: 1px solid var(--neutral-200, #e5e5e5);
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
  background: var(--neutral-0, #fff);
}

.filter-bar__input:focus { border-color: var(--primary, #2563eb); }

.card-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

@media (max-width: 1100px) { .card-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 700px) { .card-grid { grid-template-columns: 1fr; } }

.onto-card {
  background: var(--neutral-0, #fff);
  border: 1px solid var(--neutral-100, #f0f0f0);
  border-radius: var(--radius-lg, 12px);
  padding: 20px;
  display: flex;
  flex-direction: column;
  transition: box-shadow 0.15s, border-color 0.15s;
}

.onto-card:hover {
  border-color: var(--primary, #2563eb);
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.08);
}

.onto-card__top {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.onto-card__icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: #eff6ff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.onto-card__info {
  flex: 1;
  min-width: 0;
}

.onto-card__name-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.onto-card__name {
  font-size: 15px;
  font-weight: 600;
  color: var(--neutral-900, #111);
}

.onto-card__code {
  font-size: 12px;
  color: var(--neutral-400, #aaa);
}

.onto-card__badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: #dcfce7;
  color: #166534;
  font-weight: 500;
  white-space: nowrap;
}

.onto-card__desc {
  font-size: 12px;
  color: var(--neutral-500, #888);
  margin: 0 0 12px;
  line-height: 1.5;
}

.onto-card__stats {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--neutral-100, #f0f0f0);
}

.onto-card__stat-item {
  font-size: 12px;
  color: var(--neutral-600, #555);
}

.onto-card__meta {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.onto-card__meta-item {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.onto-card__meta-label {
  font-size: 11px;
  color: var(--neutral-400, #aaa);
}

.onto-card__meta-value {
  font-size: 12px;
  color: var(--neutral-700, #333);
}

.onto-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid var(--neutral-100, #f0f0f0);
}

.onto-card__status {
  font-size: 12px;
  font-weight: 500;
}

.onto-card__status--active { color: #16a34a; }

.onto-card__actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.onto-card__action-btn {
  padding: 4px 10px;
  font-size: 12px;
  color: var(--primary, #2563eb);
  background: none;
  border: none;
  cursor: pointer;
  font-weight: 500;
}

.onto-card__action-btn:hover { text-decoration: underline; }

.onto-card__action-btn--del {
  color: var(--neutral-400, #aaa);
  padding: 4px;
}

.onto-card__action-btn--del:hover { color: #dc2626; }

.card-grid__empty {
  grid-column: 1 / -1;
  text-align: center;
  padding: 48px 0;
  color: var(--neutral-400, #aaa);
  font-size: 13px;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-box {
  background: var(--neutral-0, #fff);
  border-radius: var(--radius-lg, 12px);
  width: 520px;
  max-width: 90vw;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 0;
}

.modal-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0;
  color: var(--neutral-900, #111);
}

.modal-close {
  width: 28px;
  height: 28px;
  border: none;
  background: none;
  font-size: 22px;
  color: var(--neutral-400, #aaa);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}

.modal-close:hover { background: var(--neutral-100, #f0f0f0); }

.modal-body {
  padding: 20px 24px;
  overflow-y: auto;
  flex: 1;
}

.modal-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--neutral-800, #333);
  margin-bottom: 16px;
}

.modal-section-bar {
  width: 3px;
  height: 14px;
  background: var(--primary, #2563eb);
  border-radius: 2px;
}

.modal-field { margin-bottom: 16px; }

.modal-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--neutral-700, #333);
  margin-bottom: 6px;
}

.required { color: #dc2626; margin-right: 2px; }

.modal-input-wrap { position: relative; }

.modal-input {
  width: 100%;
  padding: 10px 50px 10px 12px;
  border: 1px solid var(--neutral-200, #e5e5e5);
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
  box-sizing: border-box;
  background: var(--neutral-50, #fafafa);
}

.modal-input:focus { border-color: var(--primary, #2563eb); background: var(--neutral-0); }

.modal-input-count {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 11px;
  color: var(--neutral-400, #aaa);
}

.modal-input-count--textarea {
  top: auto;
  bottom: 10px;
  transform: none;
}

.modal-textarea {
  min-height: 80px;
  resize: vertical;
  padding-bottom: 24px;
}


.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px;
  border-top: 1px solid var(--neutral-100, #f0f0f0);
}

.btn-cancel {
  padding: 10px 20px;
  border: 1px solid var(--neutral-200, #e5e5e5);
  border-radius: 6px;
  background: var(--neutral-0, #fff);
  color: var(--neutral-700, #333);
  font-size: 13px;
  cursor: pointer;
}

.btn-cancel:hover { background: var(--neutral-50, #fafafa); }
.modal-error { margin: 0; padding: 12px 24px; color: var(--color-error, #dc2626); font-size: 13px; overflow-wrap: anywhere; }
</style>
