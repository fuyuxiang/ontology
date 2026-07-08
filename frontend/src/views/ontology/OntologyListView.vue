<template>
  <div class="ontology-list-page">
    <!-- 顶部 Banner -->
    <div class="page-banner">
      <div class="page-banner__content">
        <h1 class="page-banner__title">本体列表</h1>
        <p class="page-banner__desc">提供本体设计器，支持以人机协同方式，基于 AI 快速自动化构建本体；也支持通过手动定义的形式自顶向...</p>
      </div>
      <div class="page-banner__actions">
        <button class="btn-outline" @click="showCreate = true">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 2v10M2 7h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          手动构建
        </button>
        <button class="btn-filled" @click="showCreate = true">
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
              <span class="onto-card__name">{{ item.name }}</span>
            </div>
            <span class="onto-card__code">{{ item.code }}</span>
          </div>
          <span class="onto-card__badge">已构建</span>
        </div>

        <p class="onto-card__desc">{{ item.description || '暂无描述' }}</p>

        <div class="onto-card__stats">
          <span class="onto-card__stat-item" title="对象">&#x1F4C4; {{ item.entityCount }}</span>
          <span class="onto-card__stat-item" title="逻辑">&#x26A1; {{ item.logicCount }}</span>
          <span class="onto-card__stat-item" title="关系">&#x1F517; {{ item.relationCount }}</span>
        </div>

        <div class="onto-card__meta">
          <div class="onto-card__meta-item">
            <span class="onto-card__meta-label">更新</span>
            <span class="onto-card__meta-value">{{ item.updated_at?.slice(0, 10) || '—' }}</span>
          </div>
        </div>

        <div class="onto-card__footer">
          <span class="onto-card__status onto-card__status--active">已启用</span>
          <div class="onto-card__actions">
            <button class="onto-card__action-btn" @click.stop="goDetail(item.code)">详情</button>
            <button class="onto-card__action-btn onto-card__action-btn--del" @click.stop="handleDelete(item)">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 4h8M5 4V3h4v1M4 4v7h6V4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
          </div>
        </div>
      </div>

      <div v-if="filteredList.length === 0" class="card-grid__empty">
        <p>无匹配本体</p>
      </div>
    </div>

    <!-- 新建本体弹窗 -->
    <Teleport to="body">
      <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
        <div class="modal-box">
          <h3 class="modal-title">新建本体</h3>
          <div class="modal-field">
            <label class="modal-label">本体名称</label>
            <input v-model="createForm.name" class="modal-input" placeholder="输入本体名称" />
          </div>
          <div class="modal-field">
            <label class="modal-label">编码 (code)</label>
            <input v-model="createForm.code" class="modal-input" placeholder="英文编码，如 revenue_analysis" />
          </div>
          <div class="modal-field">
            <label class="modal-label">描述</label>
            <textarea v-model="createForm.description" class="modal-input modal-textarea" placeholder="本体描述（可选）" />
          </div>
          <div class="modal-actions">
            <button class="btn-cancel" @click="showCreate = false">取消</button>
            <button class="btn-filled" :disabled="!createForm.name || !createForm.code" @click="handleCreate">创建</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useScenarioStore } from '../../store/scenarios'
import { useOntologyStore } from '../../store/ontology'
import { functionApi, type FunctionItem } from '../../api/functions'
import { scenarioApi } from '../../api/scenarios'

const router = useRouter()
const scenarioStore = useScenarioStore()
const ontologyStore = useOntologyStore()

const search = ref('')
const functions = ref<FunctionItem[]>([])
const showCreate = ref(false)
const createForm = reactive({ name: '', code: '', description: '' })

const scenarios = computed(() => scenarioStore.scenarios)

const filteredList = computed(() => {
  const items = scenarios.value.map(s => {
    const entityCount = ontologyStore.entities.filter(
      e => (e.scenarioCodes || []).includes(s.code)
    ).length
    const logicCount = functions.value.filter(
      f => (f as any).scenario_code === s.code
    ).length
    const relationCount = 0
    return { ...s, entityCount, logicCount, relationCount }
  })
  if (!search.value) return items
  const q = search.value.toLowerCase()
  return items.filter(i => i.name.toLowerCase().includes(q) || (i.description || '').toLowerCase().includes(q))
})

function goDetail(code: string) {
  router.push(`/ontology/list/${code}`)
}

async function handleCreate() {
  await scenarioApi.create({
    code: createForm.code,
    name: createForm.name,
    description: createForm.description || null,
  })
  showCreate.value = false
  createForm.name = ''
  createForm.code = ''
  createForm.description = ''
  await scenarioStore.fetchScenarios(true)
}

async function handleDelete(item: any) {
  if (!confirm(`确定删除本体「${item.name}」？`)) return
  await scenarioApi.remove(item.id)
  await scenarioStore.fetchScenarios(true)
}

onMounted(async () => {
  await Promise.all([
    scenarioStore.fetchScenarios(),
    ontologyStore.fetchEntities(),
    functionApi.list().then(list => { functions.value = list }),
  ])
})
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
  padding: 24px;
  width: 420px;
  max-width: 90vw;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
}

.modal-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 20px;
  color: var(--neutral-900, #111);
}

.modal-field { margin-bottom: 16px; }

.modal-label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--neutral-600, #666);
  margin-bottom: 4px;
}

.modal-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--neutral-200, #e5e5e5);
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
  box-sizing: border-box;
}

.modal-input:focus { border-color: var(--primary, #2563eb); }
.modal-textarea { min-height: 72px; resize: vertical; }

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}

.btn-cancel {
  padding: 8px 16px;
  border: 1px solid var(--neutral-200, #e5e5e5);
  border-radius: 6px;
  background: var(--neutral-0, #fff);
  color: var(--neutral-700, #333);
  font-size: 13px;
  cursor: pointer;
}

.btn-cancel:hover { background: var(--neutral-50, #fafafa); }
</style>
