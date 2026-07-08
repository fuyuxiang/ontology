<template>
  <div class="ontology-detail">
    <div class="ontology-detail__topbar">
      <button class="btn-back" @click="goBack">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M10 12L6 8l4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        返回列表
      </button>
      <span class="ontology-detail__title">{{ scenario?.name || code }}</span>
      <div class="ontology-detail__actions">
        <button class="btn-action">导入Excel</button>
        <button class="btn-action">测试</button>
        <button class="btn-action">仿真</button>
        <button class="btn-action btn-action--primary">发布</button>
        <button class="btn-action">保存</button>
      </div>
    </div>

    <div class="ontology-detail__body">
      <aside class="ontology-detail__sidebar">
        <nav class="detail-nav">
          <a class="detail-nav__item" :class="{ active: activeTab === 'overview' }" @click="activeTab = 'overview'">
            <span class="detail-nav__icon">📊</span> 总览
          </a>
          <a class="detail-nav__item" :class="{ active: activeTab === 'history' }" @click="activeTab = 'history'">
            <span class="detail-nav__icon">📋</span> 历史
          </a>

          <div class="detail-nav__section">本体资源</div>
          <a class="detail-nav__item" :class="{ active: activeTab === 'entities' }" @click="activeTab = 'entities'">
            <span class="detail-nav__icon">🧩</span> 对象定义
            <span class="detail-nav__count">{{ entityCount }}</span>
          </a>
          <a class="detail-nav__item" :class="{ active: activeTab === 'relations' }" @click="activeTab = 'relations'">
            <span class="detail-nav__icon">🔗</span> 关系定义
            <span class="detail-nav__count">{{ relationCount }}</span>
          </a>
          <a class="detail-nav__item" :class="{ active: activeTab === 'logic' }" @click="activeTab = 'logic'">
            <span class="detail-nav__icon">⚡</span> 逻辑定义
            <span class="detail-nav__count">{{ logicCount }}</span>
          </a>
<!-- NAV_PLACEHOLDER -->
          <a class="detail-nav__item" :class="{ active: activeTab === 'actions' }" @click="activeTab = 'actions'">
            <span class="detail-nav__icon">▶️</span> 动作定义
            <span class="detail-nav__count">{{ actionCount }}</span>
          </a>
          <a class="detail-nav__item" :class="{ active: activeTab === 'api' }" @click="activeTab = 'api'">
            <span class="detail-nav__icon">🔌</span> 接口定义
            <span class="detail-nav__count">0</span>
          </a>

          <div class="detail-nav__section">更多</div>
          <a class="detail-nav__item" :class="{ active: activeTab === 'shared-attrs' }" @click="activeTab = 'shared-attrs'">
            <span class="detail-nav__icon">🏷️</span> 共享属性
          </a>
          <a class="detail-nav__item" :class="{ active: activeTab === 'groups' }" @click="activeTab = 'groups'">
            <span class="detail-nav__icon">📁</span> 分组
          </a>
          <a class="detail-nav__item" :class="{ active: activeTab === 'tasks' }" @click="activeTab = 'tasks'">
            <span class="detail-nav__icon">📝</span> 任务记录
          </a>
        </nav>
      </aside>

      <main class="ontology-detail__content">
        <!-- 总览 -->
        <div v-if="activeTab === 'overview'" class="tab-overview">
          <h2 class="tab-title">总览</h2>
          <p class="tab-subtitle">本体「{{ scenario?.name }}」资源总览</p>

          <div class="overview-stats">
            <div class="overview-stat-card">
              <div class="overview-stat-card__label">对象</div>
              <div class="overview-stat-card__value">{{ entityCount }}</div>
            </div>
            <div class="overview-stat-card">
              <div class="overview-stat-card__label">关系</div>
              <div class="overview-stat-card__value">{{ relationCount }}</div>
            </div>
            <div class="overview-stat-card">
              <div class="overview-stat-card__label">逻辑</div>
              <div class="overview-stat-card__value">{{ logicCount }}</div>
            </div>
            <div class="overview-stat-card">
              <div class="overview-stat-card__label">动作</div>
              <div class="overview-stat-card__value">{{ actionCount }}</div>
            </div>
          </div>

          <div class="overview-info">
            <h3 class="overview-section-title">基础信息</h3>
            <div class="overview-info-grid">
              <div class="overview-info-item">
                <span class="overview-info-label">中文名</span>
                <span class="overview-info-value">{{ scenario?.name }}</span>
              </div>
              <div class="overview-info-item">
                <span class="overview-info-label">英文名</span>
                <span class="overview-info-value">{{ scenario?.code }}</span>
              </div>
              <div class="overview-info-item">
                <span class="overview-info-label">状态</span>
                <span class="overview-info-value"><span class="badge badge--active">启用</span></span>
              </div>
              <div class="overview-info-item">
                <span class="overview-info-label">创建</span>
                <span class="overview-info-value">{{ scenario?.created_at?.slice(0, 10) || '—' }}</span>
              </div>
              <div class="overview-info-item" style="grid-column: 1 / -1;">
                <span class="overview-info-label">描述</span>
                <span class="overview-info-value">{{ scenario?.description || '暂无描述' }}</span>
              </div>
            </div>
          </div>

          <div class="overview-tables">
            <div class="overview-table-section">
              <h3 class="overview-section-title">对象 ({{ entityCount }})</h3>
              <table class="mini-table" v-if="scenarioEntities.length">
                <thead><tr><th>名称</th><th>中文名</th><th>属性</th></tr></thead>
                <tbody>
                  <tr v-for="e in scenarioEntities.slice(0, 5)" :key="e.id">
                    <td class="link-cell">{{ e.className }}</td>
                    <td>{{ e.label }}</td>
                    <td>{{ e.attributeCount || 0 }}</td>
                  </tr>
                </tbody>
              </table>
              <p v-else class="text-caption">暂无对象</p>
            </div>
            <div class="overview-table-section">
              <h3 class="overview-section-title">逻辑 ({{ logicCount }})</h3>
              <p class="text-caption">详见逻辑定义 Tab</p>
            </div>
          </div>
        </div>

        <!-- 对象定义 -->
        <div v-else-if="activeTab === 'entities'" class="tab-entities">
          <div class="entities-toolbar">
            <div class="entities-toolbar__left">
              <span class="entities-toolbar__title">
                <span class="entities-toolbar__indicator"></span>
                对象
              </span>
              <span class="entities-toolbar__count">{{ filteredEntities.length }}</span>
            </div>
            <div class="entities-toolbar__right">
              <div class="entities-search">
                <input v-model="entitySearch" class="entities-search__input" placeholder="请输入" />
                <svg class="entities-search__icon" width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <circle cx="6" cy="6" r="4" stroke="currentColor" stroke-width="1.5"/>
                  <path d="M9 9l2.5 2.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                </svg>
              </div>
              <div class="entities-dropdown" v-click-outside="() => showBatchMenu = false">
                <button class="entities-dropdown__btn" @click="showBatchMenu = !showBatchMenu">
                  批量操作
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M2.5 4L5 6.5 7.5 4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </button>
                <div v-if="showBatchMenu" class="entities-dropdown__menu">
                  <button class="entities-dropdown__item" @click="batchDelete" :disabled="selectedIds.length === 0">批量删除</button>
                  <button class="entities-dropdown__item" @click="batchActivate" :disabled="selectedIds.length === 0">批量激活</button>
                  <button class="entities-dropdown__item" @click="batchExport" :disabled="selectedIds.length === 0">批量导出</button>
                </div>
              </div>
              <div class="entities-dropdown" v-click-outside="() => showCreateMenu = false">
                <button class="entities-dropdown__btn entities-dropdown__btn--primary" @click="showCreateMenu = !showCreateMenu">
                  新建对象
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M2.5 4L5 6.5 7.5 4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </button>
                <div v-if="showCreateMenu" class="entities-dropdown__menu entities-dropdown__menu--grid">
                  <button class="entities-dropdown__grid-item" @click="goCreate('/builder')">
                    <span class="entities-dropdown__grid-icon">🛠️</span>
                    <span>手动构建</span>
                  </button>
                  <button class="entities-dropdown__grid-item" @click="goCreate('/builder/template')">
                    <span class="entities-dropdown__grid-icon">📋</span>
                    <span>模板构建</span>
                  </button>
                  <button class="entities-dropdown__grid-item" @click="goCreate('/builder/doc')">
                    <span class="entities-dropdown__grid-icon">📄</span>
                    <span>文档构建</span>
                  </button>
                  <button class="entities-dropdown__grid-item" @click="goCreate('/builder/ai')">
                    <span class="entities-dropdown__grid-icon">🤖</span>
                    <span>资产构建</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div class="entities-table-wrap">
            <table class="entities-table" v-if="filteredEntities.length">
              <thead>
                <tr>
                  <th class="entities-table__check"><input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll" /></th>
                  <th>中文名称</th>
                  <th>英文名称</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="e in filteredEntities" :key="e.id">
                  <td class="entities-table__check"><input type="checkbox" :checked="selectedIds.includes(e.id)" @change="toggleSelect(e.id)" /></td>
                  <td class="link-cell" @click="router.push(`/ontology/${e.id}`)">{{ e.label || '—' }}</td>
                  <td>{{ e.className }}</td>
                  <td><span class="badge" :class="e.status === 'active' ? 'badge--active' : 'badge--draft'">{{ e.status === 'active' ? '已激活' : '草稿' }}</span></td>
                  <td class="entities-table__actions">
                    <button class="entities-table__action-btn" @click="router.push(`/ontology/${e.id}`)">编辑</button>
                    <button class="entities-table__action-btn entities-table__action-btn--danger" @click="deleteEntity(e.id)">删除</button>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-else class="entities-empty">
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                <rect x="8" y="12" width="32" height="24" rx="3" stroke="#d0d5dd" stroke-width="1.5"/>
                <path d="M8 18h32" stroke="#d0d5dd" stroke-width="1.5"/>
                <circle cx="14" cy="15" r="1.5" fill="#d0d5dd"/>
                <circle cx="19" cy="15" r="1.5" fill="#d0d5dd"/>
              </svg>
              <p class="entities-empty__text">暂无数据</p>
            </div>
          </div>
        </div>

        <!-- 逻辑定义 -->
        <div v-else-if="activeTab === 'logic'" class="tab-logic">
          <FunctionsView :embedded="true" />
        </div>

        <!-- 动作定义 -->
        <div v-else-if="activeTab === 'actions'" class="tab-actions">
          <ActionsView :embedded="true" />
        </div>

        <!-- 其他 tab 占位 -->
        <div v-else class="tab-placeholder">
          <p class="text-caption">{{ activeTabLabel }} — 开发中</p>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useScenarioStore } from '../../store/scenarios'
import { useOntologyStore } from '../../store/ontology'
import FunctionsView from '../logic/FunctionsView.vue'
import ActionsView from '../logic/ActionsView.vue'

const vClickOutside = {
  mounted(el: any, binding: any) {
    el._clickOutside = (e: MouseEvent) => {
      if (!el.contains(e.target)) binding.value()
    }
    document.addEventListener('click', el._clickOutside)
  },
  unmounted(el: any) {
    document.removeEventListener('click', el._clickOutside)
  }
}

const route = useRoute()
const router = useRouter()
const scenarioStore = useScenarioStore()
const ontologyStore = useOntologyStore()

const code = computed(() => route.params.code as string)
const activeTab = ref('overview')

const scenario = computed(() => scenarioStore.byCode(code.value))

// Entities are now fetched by backend filtered by ontology_id via switchOntology
const scenarioEntities = computed(() => ontologyStore.entities)

const entityCount = computed(() => ontologyStore.entities.length)
const relationCount = computed(() => {
  return ontologyStore.entities.reduce((sum, e) => sum + ((e as any).relationCount || 0), 0)
})
const logicCount = computed(() => ontologyStore.entities.reduce((sum, e) => sum + ((e as any).functionCount || 0), 0))
const actionCount = computed(() => 0)

// --- 对象定义 Tab 逻辑 ---
const entitySearch = ref('')
const selectedIds = ref<string[]>([])
const showBatchMenu = ref(false)
const showCreateMenu = ref(false)

const filteredEntities = computed(() => {
  const q = entitySearch.value.trim().toLowerCase()
  if (!q) return scenarioEntities.value
  return scenarioEntities.value.filter(
    (e: any) => (e.label || '').toLowerCase().includes(q) || (e.className || '').toLowerCase().includes(q)
  )
})

const isAllSelected = computed(() => {
  return filteredEntities.value.length > 0 && filteredEntities.value.every((e: any) => selectedIds.value.includes(e.id))
})

function toggleSelectAll() {
  if (isAllSelected.value) {
    selectedIds.value = []
  } else {
    selectedIds.value = filteredEntities.value.map((e: any) => e.id)
  }
}

function toggleSelect(id: string) {
  const idx = selectedIds.value.indexOf(id)
  if (idx >= 0) selectedIds.value.splice(idx, 1)
  else selectedIds.value.push(id)
}

function goCreate(path: string) {
  showCreateMenu.value = false
  router.push({ path, query: { from: 'ontology-detail', code: code.value } })
}

async function deleteEntity(id: string) {
  if (!confirm('确定删除该对象？')) return
  await ontologyStore.removeEntity(id)
}

function batchDelete() {
  if (selectedIds.value.length === 0) return
  if (!confirm(`确定删除选中的 ${selectedIds.value.length} 个对象？`)) return
  selectedIds.value.forEach(id => ontologyStore.removeEntity(id))
  selectedIds.value = []
  showBatchMenu.value = false
}

function batchActivate() {
  showBatchMenu.value = false
}

function batchExport() {
  showBatchMenu.value = false
}

const activeTabLabel = computed(() => {
  const map: Record<string, string> = {
    history: '历史', relations: '关系定义', actions: '动作定义',
    api: '接口定义', 'shared-attrs': '共享属性', groups: '分组', tasks: '任务记录',
  }
  return map[activeTab.value] || activeTab.value
})

function goBack() {
  router.push('/ontology/list')
}

onMounted(async () => {
  await scenarioStore.fetchScenarios()
  const sc = scenarioStore.byCode(code.value)
  if (sc) {
    await ontologyStore.switchOntology(sc.id)
  }
})
</script>

<!-- STYLE_SECTION -->
<style scoped>
.ontology-detail {
  display: flex;
  flex-direction: column;
  height: 100%;
  margin: -24px -32px;
  background: var(--neutral-50, #fafafa);
}

.ontology-detail__topbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 24px;
  background: var(--neutral-0, #fff);
  border-bottom: 1px solid var(--neutral-200, #e5e5e5);
  flex-shrink: 0;
}

.btn-back {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: 1px solid var(--neutral-200, #e5e5e5);
  border-radius: 6px;
  background: var(--neutral-0, #fff);
  color: var(--neutral-700, #333);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-back:hover { background: var(--neutral-50, #fafafa); }

.ontology-detail__title {
  font-size: 15px;
  font-weight: 600;
  color: var(--neutral-900, #111);
  flex: 1;
}

.ontology-detail__actions {
  display: flex;
  gap: 8px;
}

.btn-action {
  padding: 6px 14px;
  font-size: 12px;
  border: 1px solid var(--neutral-200, #e5e5e5);
  border-radius: 6px;
  background: var(--neutral-0, #fff);
  color: var(--neutral-700, #333);
  cursor: pointer;
  transition: background 0.15s;
}

.btn-action:hover { background: var(--neutral-50, #fafafa); }
.btn-action--primary {
  background: var(--primary, #2563eb);
  color: #fff;
  border-color: var(--primary, #2563eb);
}
.btn-action--primary:hover { opacity: 0.9; }

.ontology-detail__body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.ontology-detail__sidebar {
  width: 200px;
  background: var(--neutral-0, #fff);
  border-right: 1px solid var(--neutral-200, #e5e5e5);
  overflow-y: auto;
  flex-shrink: 0;
  padding: 12px 0;
}

.detail-nav__item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  font-size: 13px;
  color: var(--neutral-700, #495057);
  cursor: pointer;
  transition: background 0.1s;
  text-decoration: none;
}

.detail-nav__item:hover { background: var(--neutral-50, #fafafa); }
.detail-nav__item.active {
  background: var(--primary-50, #eff6ff);
  color: var(--primary, #2563eb);
  font-weight: 500;
  border-left: 3px solid var(--primary, #2563eb);
  padding-left: 13px;
}

.detail-nav__icon { font-size: 14px; }
.detail-nav__count {
  margin-left: auto;
  font-size: 11px;
  color: var(--neutral-400, #aaa);
}

.detail-nav__section {
  font-size: 11px;
  color: var(--neutral-400, #aaa);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  padding: 16px 16px 4px;
  font-weight: 600;
}

.ontology-detail__content {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
}

.tab-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 4px;
  color: var(--neutral-900, #111);
}

.tab-subtitle {
  font-size: 13px;
  color: var(--neutral-500, #888);
  margin: 0 0 24px;
}

.overview-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.overview-stat-card {
  padding: 20px;
  background: var(--neutral-0, #fff);
  border: 1px solid var(--neutral-100, #f0f0f0);
  border-radius: var(--radius-lg, 12px);
}

.overview-stat-card__label {
  font-size: 12px;
  color: var(--neutral-500, #888);
  margin-bottom: 4px;
}

.overview-stat-card__value {
  font-size: 28px;
  font-weight: 700;
  color: var(--neutral-900, #111);
}

.overview-info {
  background: var(--neutral-0, #fff);
  border: 1px solid var(--neutral-100, #f0f0f0);
  border-radius: var(--radius-lg, 12px);
  padding: 20px;
  margin-bottom: 24px;
}

.overview-section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--neutral-800, #333);
  margin: 0 0 12px;
}

.overview-info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.overview-info-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.overview-info-label {
  font-size: 11px;
  color: var(--neutral-500, #888);
}

.overview-info-value {
  font-size: 13px;
  font-weight: 500;
  color: var(--neutral-800, #333);
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.badge--active { background: #dcfce7; color: #166534; }
.badge--draft { background: var(--neutral-100, #f0f0f0); color: var(--neutral-600, #666); }

.overview-tables {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.overview-table-section {
  background: var(--neutral-0, #fff);
  border: 1px solid var(--neutral-100, #f0f0f0);
  border-radius: var(--radius-lg, 12px);
  padding: 20px;
}

.mini-table, .data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.mini-table th, .data-table th {
  text-align: left;
  font-size: 11px;
  color: var(--neutral-500, #888);
  padding: 8px 12px;
  border-bottom: 1px solid var(--neutral-100, #f0f0f0);
}

.mini-table td, .data-table td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--neutral-50, #fafafa);
  color: var(--neutral-700, #495057);
}

.link-cell {
  color: var(--primary, #2563eb);
  cursor: pointer;
  font-weight: 500;
}

.link-cell:hover { text-decoration: underline; }

.tab-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  color: var(--neutral-400, #aaa);
}

/* 对象定义 Tab */
.tab-entities {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.entities-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.entities-toolbar__left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.entities-toolbar__title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  color: var(--neutral-900, #111);
}

.entities-toolbar__indicator {
  width: 3px;
  height: 16px;
  background: var(--primary, #2563eb);
  border-radius: 2px;
}

.entities-toolbar__count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 10px;
  background: var(--neutral-100, #f0f0f0);
  font-size: 11px;
  font-weight: 500;
  color: var(--neutral-600, #666);
}

.entities-toolbar__right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.entities-search {
  position: relative;
}

.entities-search__input {
  width: 180px;
  height: 32px;
  padding: 0 32px 0 12px;
  border: 1px solid var(--neutral-200, #e5e5e5);
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
}

.entities-search__input:focus {
  border-color: var(--primary, #2563eb);
}

.entities-search__icon {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--neutral-400, #aaa);
  pointer-events: none;
}

.entities-dropdown {
  position: relative;
}

.entities-dropdown__btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  font-size: 13px;
  border: 1px solid var(--neutral-200, #e5e5e5);
  border-radius: 6px;
  background: var(--neutral-0, #fff);
  color: var(--neutral-700, #333);
  cursor: pointer;
  transition: background 0.15s;
  white-space: nowrap;
}

.entities-dropdown__btn:hover { background: var(--neutral-50, #fafafa); }

.entities-dropdown__btn--primary {
  background: var(--primary, #2563eb);
  color: #fff;
  border-color: var(--primary, #2563eb);
}

.entities-dropdown__btn--primary:hover { opacity: 0.9; background: var(--primary, #2563eb); }

.entities-dropdown__menu {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  min-width: 120px;
  background: #fff;
  border: 1px solid var(--neutral-200, #e5e5e5);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  z-index: 100;
  padding: 4px;
}

.entities-dropdown__item {
  display: block;
  width: 100%;
  padding: 8px 12px;
  font-size: 13px;
  text-align: left;
  border: none;
  background: none;
  color: var(--neutral-700, #333);
  cursor: pointer;
  border-radius: 4px;
}

.entities-dropdown__item:hover { background: var(--neutral-50, #fafafa); }
.entities-dropdown__item:disabled { color: var(--neutral-300, #ccc); cursor: not-allowed; }

.entities-dropdown__menu--grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  min-width: 200px;
  padding: 8px;
}

.entities-dropdown__grid-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 8px;
  border: none;
  background: none;
  border-radius: 6px;
  font-size: 12px;
  color: var(--neutral-700, #333);
  cursor: pointer;
}

.entities-dropdown__grid-item:hover { background: var(--neutral-50, #fafafa); }

.entities-dropdown__grid-icon {
  font-size: 20px;
}

.entities-table-wrap {
  flex: 1;
  background: var(--neutral-0, #fff);
  border: 1px solid var(--neutral-100, #f0f0f0);
  border-radius: 8px;
  overflow: hidden;
}

.entities-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.entities-table th {
  text-align: left;
  font-size: 13px;
  font-weight: 500;
  color: var(--neutral-600, #666);
  padding: 12px 16px;
  background: var(--neutral-50, #fafafa);
  border-bottom: 1px solid var(--neutral-100, #f0f0f0);
}

.entities-table td {
  padding: 12px 16px;
  border-bottom: 1px solid var(--neutral-50, #fafafa);
  color: var(--neutral-700, #495057);
}

.entities-table tbody tr:hover {
  background: var(--neutral-50, #fafafa);
}

.entities-table__check {
  width: 40px;
  text-align: center;
}

.entities-table__actions {
  display: flex;
  gap: 8px;
}

.entities-table__action-btn {
  padding: 4px 10px;
  font-size: 12px;
  border: 1px solid var(--neutral-200, #e5e5e5);
  border-radius: 4px;
  background: var(--neutral-0, #fff);
  color: var(--neutral-700, #333);
  cursor: pointer;
}

.entities-table__action-btn:hover { background: var(--neutral-50, #fafafa); }

.entities-table__action-btn--danger {
  color: #dc2626;
  border-color: #fecaca;
}

.entities-table__action-btn--danger:hover { background: #fef2f2; }

.entities-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  color: var(--neutral-400, #aaa);
}

.entities-empty__text {
  margin-top: 12px;
  font-size: 13px;
  color: var(--neutral-400, #aaa);
}
</style>
