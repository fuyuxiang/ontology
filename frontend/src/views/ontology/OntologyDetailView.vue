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
        <button class="btn-action" @click="goCreate('/builder/template')" :disabled="!canEdit">导入Excel</button>
        <button class="btn-action" :disabled="checking" @click="checkOntology(false)">测试</button>
        <button class="btn-action" :disabled="checking" @click="checkOntology(true)">仿真</button>
        <button class="btn-action btn-action--primary" :disabled="!canEdit || (publishing || ontologyStore.loading)" @click="publishOntology">{{ publishing ? '发布中…' : '发布' }}</button>
        <button class="btn-action" @click="openMetadata" :disabled="!canEdit">保存</button>
      </div>
    </div>

    <div class="ontology-detail__body">
      <aside class="ontology-detail__sidebar">
        <nav class="detail-nav">
          <button type="button" class="detail-nav__item" :class="{ active: activeTab === 'overview' }" :aria-pressed="activeTab === 'overview'" @click="activeTab = 'overview'">
            <span class="detail-nav__icon">📊</span> 总览
          </button>
          <button type="button" class="detail-nav__item" :class="{ active: activeTab === 'history' }" :aria-pressed="activeTab === 'history'" @click="activeTab = 'history'">
            <span class="detail-nav__icon">📋</span> 历史
          </button>

          <div class="detail-nav__section">本体资源</div>
          <button type="button" class="detail-nav__item" :class="{ active: activeTab === 'entities' }" :aria-pressed="activeTab === 'entities'" @click="activeTab = 'entities'">
            <span class="detail-nav__icon">🧩</span> 对象定义
            <span class="detail-nav__count">{{ entityCount }}</span>
          </button>
          <button type="button" class="detail-nav__item" :class="{ active: activeTab === 'relations' }" :aria-pressed="activeTab === 'relations'" @click="activeTab = 'relations'">
            <span class="detail-nav__icon">🔗</span> 关系定义
            <span class="detail-nav__count">{{ relationCount }}</span>
          </button>
          <button type="button" class="detail-nav__item" :class="{ active: activeTab === 'logic' }" :aria-pressed="activeTab === 'logic'" @click="activeTab = 'logic'">
            <span class="detail-nav__icon">⚡</span> 逻辑定义
            <span class="detail-nav__count">{{ logicCount }}</span>
          </button>
<!-- NAV_PLACEHOLDER -->
          <button type="button" class="detail-nav__item" :class="{ active: activeTab === 'actions' }" :aria-pressed="activeTab === 'actions'" @click="activeTab = 'actions'">
            <span class="detail-nav__icon">▶️</span> 动作定义
            <span class="detail-nav__count">{{ actionCount }}</span>
          </button>
          <button type="button" class="detail-nav__item" :class="{ active: activeTab === 'api' }" :aria-pressed="activeTab === 'api'" @click="activeTab = 'api'">
            <span class="detail-nav__icon">🔌</span> 接口定义

          </button>
          <button type="button" class="detail-nav__item" :class="{ active: activeTab === 'graph' }" :aria-pressed="activeTab === 'graph'" @click="activeTab = 'graph'">
            <span class="detail-nav__icon">🕸️</span> 本体图谱
          </button>
          <button type="button" class="detail-nav__item" :class="{ active: activeTab === 'application-references' }" :aria-pressed="activeTab === 'application-references'" @click="activeTab = 'application-references'">
            <span class="detail-nav__icon">◎</span> 应用引用
          </button>

          <div class="detail-nav__section">更多</div>
          <button type="button" class="detail-nav__item" :class="{ active: activeTab === 'shared-attrs' }" :aria-pressed="activeTab === 'shared-attrs'" @click="activeTab = 'shared-attrs'">
            <span class="detail-nav__icon">🏷️</span> 共享属性
          </button>
          <button type="button" class="detail-nav__item" :class="{ active: activeTab === 'groups' }" :aria-pressed="activeTab === 'groups'" @click="activeTab = 'groups'">
            <span class="detail-nav__icon">📁</span> 分组
          </button>
          <button type="button" class="detail-nav__item" :class="{ active: activeTab === 'tasks' }" :aria-pressed="activeTab === 'tasks'" @click="activeTab = 'tasks'">
            <span class="detail-nav__icon">📝</span> 任务记录
          </button>
        </nav>
      </aside>

      <main class="ontology-detail__content">
        <div v-if="dataLoading || ontologyStore.loading" class="attr-panel__loading" role="status">本体资源加载中...</div>
        <div v-else-if="loadError || ontologyStore.error" class="attr-panel__loading" role="alert">
          <p>{{ loadError || ontologyStore.error }}</p>
          <button class="btn-action" @click="loadData">重新加载</button>
        </div>
        <!-- 总览 -->
        <div v-else-if="activeTab === 'overview'" class="tab-overview">
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
                <span class="overview-info-value"><span class="badge">{{ scenario ? '已保存' : '—' }}</span></span>
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
                    <td class="link-cell">{{ e.name }}</td>
                    <td>{{ e.name_cn }}</td>
                    <td>{{ e.attr_count || 0 }}</td>
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
          <!-- 对象详情内嵌视图 -->
          <EntityAttrPanel
            v-if="selectedEntity"
            :entity="selectedEntity"
            @back="selectedEntityId = null"
            @changed="refreshCounts"
          />

          <!-- 对象列表 -->
          <template v-else>
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
                  <button class="entities-dropdown__item" @click="batchDelete" :disabled="!canDelete || (deleting || selectedIds.length === 0)">{{ deleting ? '删除中…' : '批量删除' }}</button>
                  <button class="entities-dropdown__item" :disabled="!canEdit || (deleting || !selectedIds.length)" @click="activateSelected">批量激活</button>
                  <button class="entities-dropdown__item" :disabled="!selectedIds.length" @click="exportSelected">批量导出</button>
                </div>
              </div>
              <div class="entities-dropdown" v-click-outside="() => showCreateMenu = false">
                <button class="entities-dropdown__btn entities-dropdown__btn--primary" @click="showCreateMenu = !showCreateMenu" :disabled="!canEdit">
                  新建对象
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M2.5 4L5 6.5 7.5 4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </button>
                <div v-if="showCreateMenu" class="entities-dropdown__menu entities-dropdown__menu--grid">
                  <button class="entities-dropdown__grid-item" @click="goCreate('/builder')" :disabled="!canEdit">
                    <span class="entities-dropdown__grid-icon">🛠️</span>
                    <span>手动构建</span>
                  </button>
                  <button class="entities-dropdown__grid-item" @click="goCreate('/builder/template')" :disabled="!canEdit">
                    <span class="entities-dropdown__grid-icon">📋</span>
                    <span>模板构建</span>
                  </button>
                  <button class="entities-dropdown__grid-item" @click="goCreate('/builder/doc')" :disabled="!canEdit">
                    <span class="entities-dropdown__grid-icon">📄</span>
                    <span>文档构建</span>
                  </button>
                  <button class="entities-dropdown__grid-item" @click="goCreate('/builder/ai')" :disabled="!canEdit">
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
                  <td class="link-cell" @click="selectedEntityId = e.id">{{ e.name_cn || '—' }}</td>
                  <td>{{ e.name }}</td>
                  <td><span class="badge" :class="e.status === 'active' ? 'badge--active' : 'badge--draft'">{{ e.status === 'active' ? '已激活' : '草稿' }}</span></td>
                  <td class="entities-table__actions">
                    <button class="entities-table__action-btn" @click="selectedEntityId = e.id">编辑</button>
                    <button class="entities-table__action-btn entities-table__action-btn--danger" @click="deleteEntity(e.id)" :disabled="!canDelete">删除</button>
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
          </template>
        </div>

        <!-- 关系定义 -->
        <div v-else-if="activeTab === 'relations'" class="tab-relations">
          <div class="relations-header">
            <span class="relations-title">关系定义</span>
            <span class="relations-count">共 {{ allRelations.length }} 条</span><button class="btn-action" :disabled="!canEdit" @click="openRelation()">新增关系</button>
          </div>
          <div v-if="relationsLoading" class="attr-panel__loading">加载中...</div>
          <div v-else-if="relationsError" class="attr-panel__loading" role="alert"><p>{{ relationsError }}</p><button class="btn-action" @click="loadRelations">重新加载</button></div>
          <table v-else-if="allRelations.length" class="entities-table">
            <thead>
              <tr>
                <th>源对象</th>
                <th>关系类型</th>
                <th>目标对象</th>
                <th>基数</th>
                <th>描述</th><th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="rel in allRelations" :key="rel.id">
                <td>{{ rel.from_entity_name }}</td>
                <td><span class="rel-type-tag">{{ rel.rel_type }}</span></td>
                <td>{{ rel.to_entity_name }}</td>
                <td><code class="text-code">{{ rel.cardinality }}</code></td>
                <td class="text-caption">{{ rel.description || '—' }}</td><td><button class="btn-action" :disabled="!canEdit" @click="openRelation(rel)">编辑</button><button class="btn-action" :disabled="!canDelete" @click="removeRelation(rel)">删除</button></td>
              </tr>
            </tbody>
          </table>
          <div v-else class="entities-empty">
            <p class="entities-empty__text">暂无关系数据</p>
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

        <!-- 本体图谱 -->
        <div v-else-if="activeTab === 'graph'" class="tab-graph">
          <div class="graph-header">
            <span class="graph-header__title">本体图谱</span>
            <span class="graph-header__desc">可视化展示本体对象与关系</span>
          </div>
          <div v-if="relationsLoading" class="attr-panel__loading" role="status">图谱关系加载中...</div>
          <div v-else-if="relationsError" class="attr-panel__loading" role="alert"><p>{{ relationsError }}</p><button class="btn-action" @click="loadRelations">重新加载</button></div>
          <div v-else class="graph-container">
            <SemanticCanvas
              :objects="graphObjects"
              :relations="graphRelations"
              :phase="'graph_done'"
              :editable="false"
            />
          </div>
        </div>

        <OntologyApplicationReferences v-else-if="activeTab === 'application-references' && scenario" :ontology-id="scenario.id" />

        <OntologyResourcesPanel v-else-if="scenario && ['history','api','shared-attrs','groups','tasks'].includes(activeTab)" :ontology-id="scenario.id" :kind="activeTab as any" :entities="scenarioEntities" />
      </main>
    </div>
    <a-modal v-model:open="relationOpen" :title="relationId ? '编辑关系' : '新增关系'" :confirm-loading="relationSaving" @ok="saveRelation">
      <div class="relation-editor"><label>名称 <a-input v-model:value="relationForm.name" /></label><label>源对象 <a-select v-model:value="relationForm.from_entity_id" :options="scenarioEntities.map(entity => ({value:entity.id,label:entity.name_cn || entity.name}))" /></label><label>目标对象 <a-select v-model:value="relationForm.to_entity_id" :options="scenarioEntities.map(entity => ({value:entity.id,label:entity.name_cn || entity.name}))" /></label><label>类型 <a-select v-model:value="relationForm.rel_type" :options="['has_one','has_many','belongs_to','many_to_many'].map(value => ({value,label:value}))" /></label><label>基数 <a-select v-model:value="relationForm.cardinality" :options="['1:1','1:N','N:1','N:N'].map(value => ({value,label:value}))" /></label><label>源关联属性或字段 <a-input v-model:value="relationForm.source_field" /></label><label>目标关联属性或字段 <a-input v-model:value="relationForm.target_field" /></label><label>说明 <a-textarea v-model:value="relationForm.description" /></label></div>
    </a-modal>
    <a-modal v-model:open="metadataOpen" title="本体信息" :confirm-loading="metadataSaving" @ok="saveMetadata">
      <label>名称 <a-input v-model:value="metadata.name" /></label><label>描述 <a-textarea v-model:value="metadata.description" /></label>
    </a-modal>
    <a-modal v-model:open="checkOpen" :title="checkTitle" :footer="null" width="800px">
      <p v-if="checking" role="status">验证中…</p><p v-if="checkError" role="alert">{{ checkError }}</p><pre class="check-log">{{ checkLog.join('\n') }}</pre>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { useManagementPermission } from '../../composables/useManagementPermission'
const { canEdit, canDelete } = useManagementPermission('entity:write')
import { ref, computed, onMounted, onActivated, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useRoute, useRouter } from 'vue-router'
import { useScenarioStore } from '../../store/scenarios'
import { useOntologyStore } from '../../store/ontology'
import { entityApi } from '../../api/ontology'
import { ontologyPublishApi } from '../../api/ontologyPublish'
import type { EntityRelationDetail } from '../../types'
import type { OntologyObjectDraft, OntologyRelationDraft } from '../../types/builder'
import FunctionsView from '../logic/FunctionsView.vue'
import ActionsView from '../logic/ActionsView.vue'
import EntityAttrPanel from './EntityAttrPanel.vue'
import SemanticCanvas from '../builder/components/graph/SemanticCanvas.vue'
import OntologyApplicationReferences from '../skills/OntologyApplicationReferences.vue'
import OntologyResourcesPanel from './OntologyResourcesPanel.vue'
import { get, post, put, del } from '../../api/client'
import { scenarioApi } from '../../api/scenarios'
import { postJsonSse, readJsonSse } from '../../api/sse'

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

// 侧栏计数统一取后端 get_ontology_stats 的聚合结果（与本体列表卡片同源）：
// 逻辑与动作可以只挂 ontology_id 而不绑定实体，前端按实体累加会漏计这类记录。
const entityCount = computed(() => scenario.value?.entity_count ?? 0)
const relationCount = computed(() => scenario.value?.relation_count ?? 0)
const logicCount = computed(() => scenario.value?.logic_count ?? 0)
const actionCount = computed(() => scenario.value?.action_count ?? 0)

// --- 对象定义 Tab 逻辑 ---
const entitySearch = ref('')
const selectedIds = ref<string[]>([])
const showBatchMenu = ref(false)
const showCreateMenu = ref(false)
const deleting = ref(false)
const publishing = ref(false)
const dataLoading = ref(false)
const loadError = ref('')
let dataRequest = 0
const selectedEntityId = ref<string | null>(null)
const selectedEntity = computed(() => {
  if (!selectedEntityId.value) return null
  return scenarioEntities.value.find((e: any) => e.id === selectedEntityId.value) || null
})

const filteredEntities = computed(() => {
  const q = entitySearch.value.trim().toLowerCase()
  if (!q) return scenarioEntities.value
  return scenarioEntities.value.filter(
    (e: any) => (e.name_cn || '').toLowerCase().includes(q) || (e.name || '').toLowerCase().includes(q)
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
  router.push({ path, query: { from: 'ontology-detail', code: code.value, ontology_id: scenario.value?.id || '' } })
}

async function deleteEntity(id: string) {
  if (!confirm('确定删除该对象？')) return
  try {
    await ontologyStore.removeEntity(id)
  } catch (e: any) {
    const status = e?.response?.status
    const detail = e?.response?.data?.detail
    if (status === 409 && detail?.message) {
      const msg = `${detail.message}\n（关联绑定: ${detail.bindings} 个，关系: ${detail.relations} 个，属性: ${detail.attributes} 个）\n\n是否强制删除？`
      if (confirm(msg)) {
        await ontologyStore.removeEntity(id, true)
      }
    } else {
      alert(typeof detail === 'string' ? detail : detail?.message || '删除失败')
    }
  }
}

async function batchDelete() {
  if (deleting.value || selectedIds.value.length === 0) return
  if (!confirm(`确定删除选中的 ${selectedIds.value.length} 个对象？`)) return
  showBatchMenu.value = false
  deleting.value = true
  const ids = [...selectedIds.value]
  try {
    const results = await Promise.allSettled(ids.map(id => ontologyStore.removeEntity(id)))
    const failedIds = ids.filter((_, index) => results[index]?.status === 'rejected')
    selectedIds.value = failedIds
    const removed = ids.length - failedIds.length
    if (removed) message.success(`已删除 ${removed} 个对象`)
    if (failedIds.length) message.error(`${failedIds.length} 个对象删除失败，已保留选择；请检查关联数据后重试`)
    await scenarioStore.fetchScenarios(true).catch(() => message.warning('对象已处理，本体资源统计加载失败，请刷新'))
  } finally {
    deleting.value = false
  }
}

async function publishOntology() {
  if (!canEdit.value) return
  if (publishing.value || !scenario.value) return
  const ontology = scenario.value
  if (ontologyStore.entities.length === 0) {
    alert('当前本体下没有对象，无法发布')
    return
  }
  if (!confirm(`确定发布本体「${scenario.value.name}」？将包含 ${ontologyStore.entities.length} 个对象。`)) return
  publishing.value = true
  try {
    const res = await ontologyPublishApi.quickPublish(ontology.id, ontology.name)
    alert(`发布成功！${res.message}`)
    router.push('/ontology/publish')
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    alert(typeof detail === 'string' ? detail : '发布失败')
  } finally {
    publishing.value = false
  }
}

const metadataOpen = ref(false)
const metadataSaving = ref(false)
const metadata = ref({ name: '', description: '' })
function openMetadata() { metadata.value = { name: scenario.value?.name || '', description: scenario.value?.description || '' }; metadataOpen.value = true }
async function saveMetadata() {
  if (!canEdit.value) return
  if (!scenario.value || metadataSaving.value || !metadata.value.name.trim()) return
  metadataSaving.value = true
  try { await scenarioApi.update(scenario.value.id, { name: metadata.value.name.trim(), description: metadata.value.description }); await scenarioStore.fetchScenarios(true); metadataOpen.value = false; message.success('本体信息已保存') }
  catch (exception: any) { message.error(exception?.response?.data?.detail || '保存失败') }
  finally { metadataSaving.value = false }
}
async function activateSelected() {
  if (!canEdit.value || deleting.value) return
  deleting.value = true; showBatchMenu.value = false
  try {
    const ids = [...selectedIds.value]
    const results = await Promise.allSettled(ids.map(id => entityApi.update(id, { status: 'active' })))
    const failed = ids.filter((_, index) => results[index]?.status === 'rejected')
    if (failed.length) message.error(`${failed.length} 个对象激活失败`)
    else message.success('选中对象已激活')
    await loadData(); selectedIds.value = failed
  } finally { deleting.value = false }
}
async function exportSelected() {
  try {
    const entities = await Promise.all(selectedIds.value.map(id => entityApi.detail(id)))
    const idToName = new Map(entities.map(entity => [entity.id, entity.name]))
    const relations = (await entityApi.relations(undefined, scenario.value?.id)).filter(relation => idToName.has(relation.from_entity_id) && idToName.has(relation.to_entity_id))
    const payload = { objects: entities.map(entity => ({ name: entity.name, display_name: entity.name_cn, tier: entity.tier, description: entity.description, primary_key: entity.config_json?.primary_key || 'id', properties: entity.attributes.map(attribute => ({ name: attribute.name, display_name: attribute.name, type: attribute.type, required: attribute.required, description: attribute.description, source_table: attribute.source_table, source_field: attribute.source_field })) })), relations: relations.map(relation => ({ name: relation.name, source: idToName.get(relation.from_entity_id), target: idToName.get(relation.to_entity_id), cardinality: relation.cardinality, description: relation.description, source_field: relation.source_field, target_field: relation.target_field })) }
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }))
    const link = document.createElement('a'); link.href = url; link.download = `${scenario.value?.code || 'ontology'}.json`; link.click(); URL.revokeObjectURL(url)
    showBatchMenu.value = false
  } catch (exception: any) { message.error(exception?.response?.data?.detail || '导出失败') }
}
const checking = ref(false)
const checkOpen = ref(false)
const checkTitle = ref('')
const checkError = ref('')
const checkLog = ref<string[]>([])
async function checkOntology(simulate: boolean) {
  if (checking.value || !scenario.value) return
  const ontologyId = scenario.value.id
  checking.value = true; checkOpen.value = true; checkError.value = ''; checkLog.value = []
  checkTitle.value = simulate ? '真实数据水合仿真' : '结构与绑定测试'
  try {
    const entities = await Promise.all(scenarioEntities.value.filter(entity => !entity.is_shared).map(entity => entityApi.detail(entity.id)))
    if (!entities.length) throw new Error('本体没有对象')
    const objects = []
    const assets = new Set<string>()
    for (const entity of entities) {
      if (!entity.name || !entity.attributes.length) throw new Error(`${entity.name_cn} 缺少名称或属性`)
      const bindings = await get<any[]>('/object-bindings', { params: { object_type_id: entity.id } })
      for (const binding of bindings) assets.add(binding.asset_id)
      bindings.sort((a,b) => (a.role === 'primary' ? -1 : 1) - (b.role === 'primary' ? -1 : 1))
      objects.push({ name: entity.name, displayName: entity.name_cn, primaryKey: entity.config_json?.primary_key || 'id', backing_asset_ids: bindings.map(binding => binding.asset_id), enrichment_bindings: bindings.filter(binding=>binding.role==='enrichment').map(binding=>({asset_id:binding.asset_id,primary_source_column:binding.primary_source_column,enrichment_source_column:binding.enrichment_source_column})), properties: entity.attributes.map(attribute => { const binding = bindings.find(binding => binding.field_mappings?.some((mapping: any) => mapping.attribute_id === attribute.id)); const mapping = binding?.field_mappings.find((mapping: any) => mapping.attribute_id === attribute.id); return { name: attribute.name, type: attribute.type, required: attribute.required, source_asset_id: binding?.asset_id, source_column: mapping?.source_column, transform:mapping?.transform, source_table: attribute.source_table, source_field: attribute.source_field } }) })
      checkLog.value.push(`${entity.name_cn}: ${entity.attributes.length} 个属性，${bindings.length} 个绑定`)
    }
    const idNames = new Map(entities.map(entity => [entity.id, entity.name]))
    const relations = (await entityApi.relations(undefined, ontologyId)).map(relation => ({ name: relation.name, source: idNames.get(relation.from_entity_id), target: idNames.get(relation.to_entity_id), cardinality: relation.cardinality, sourceField: relation.source_field, targetField: relation.target_field }))
    if (relations.some(relation => !relation.source || !relation.target)) throw new Error('关系包含不可见的对象')
    if (simulate) {
      const response = await postJsonSse('/builder/hydrate', { session_id: `test-${ontologyId}`, objects, relations, asset_ids: [...assets] })
      let completed = false
      await readJsonSse(response, event => { if (event.type === 'phase_log') checkLog.value.push(`${event.level}: ${event.msg}`); if (event.type === 'drill_complete') { completed = true; checkLog.value.push(`仿真结果：${event.status}`); if (event.status === 'error') checkError.value = '仿真存在错误，请检查日志修复后重试' } })
      if (!completed) throw new Error('仿真未返回完成结果')
    } else checkLog.value.push(`结构测试通过：${entities.length} 个对象，${relations.length} 条关系；真实源数据请运行仿真验证`)
  } catch (exception: any) { checkError.value = exception?.response?.data?.detail || exception.message || '验证失败' }
  finally { checking.value = false }
}

async function refreshCounts() { await Promise.all([scenarioStore.fetchScenarios(true), ontologyStore.fetchEntities()]) }
const relationOpen = ref(false), relationSaving = ref(false), relationId = ref<string | null>(null)
const relationForm = ref({ name:'', from_entity_id:'', to_entity_id:'', rel_type:'has_many', cardinality:'1:N', source_field:'', target_field:'', description:'' })
function openRelation(current?: EntityRelationDetail) { relationId.value = current?.id || null; relationForm.value = { name:current?.name || '', from_entity_id:current?.from_entity_id || '', to_entity_id:current?.to_entity_id || '', rel_type:current?.rel_type || 'has_many', cardinality:current?.cardinality || '1:N', source_field:current?.source_field || '', target_field:current?.target_field || '', description:current?.description || '' }; relationOpen.value = true }
async function saveRelation() { if (!canEdit.value || relationSaving.value) return; const form = relationForm.value; if (!form.name.trim() || !form.from_entity_id || !form.to_entity_id) { message.error('请填写名称、源对象和目标对象'); return } relationSaving.value = true; try { const payload = { ...form, source_field:form.source_field || null, target_field:form.target_field || null }; if (relationId.value) await put(`/relations/${relationId.value}`, payload); else await post('/relations', payload); relationOpen.value = false; await Promise.all([loadRelations(), scenarioStore.fetchScenarios(true)]); message.success('关系已保存') } catch (exception: any) { message.error(exception?.response?.data?.detail || '关系保存失败') } finally { relationSaving.value = false } }
async function removeRelation(current: EntityRelationDetail) { if (!canDelete.value || !confirm(`删除关系 ${current.name}？`)) return; try { await del(`/relations/${current.id}`); await Promise.all([loadRelations(), scenarioStore.fetchScenarios(true)]); message.success('关系已删除') } catch (exception: any) { message.error(exception?.response?.data?.detail || '关系删除失败') } }

// --- 本体图谱数据转换 ---
function tierIcon(tier: number): string {
  return tier === 1 ? '⭐' : tier === 2 ? '🔷' : '🔹'
}
const graphObjects = computed<OntologyObjectDraft[]>(() =>
  scenarioEntities.value.map((e: any) => {
    const attrs = (e.attributes || []).map((a: any) => ({
      id: a.id,
      name: a.name,
      displayName: a.name,
      type: a.type || 'string',
      required: a.required || false,
      description: a.description || '',
    }))
    return {
      id: e.id,
      name: e.name,
      displayName: e.name_cn || e.name,
      tier: (e.tier || 3) as 1 | 2 | 3,
      description: e.description || '',
      primaryKey: 'id',
      icon: tierIcon(e.tier),
      instanceCount: 0,
      properties: attrs,
      // 列表接口不返回属性明细，用真实属性总数供画布计算节点大小
      propertyCount: e.attr_count || attrs.length,
      derivedProperties: [],
      actions: [],
    }
  })
)

const graphRelations = computed<OntologyRelationDraft[]>(() =>
  allRelations.value.map(r => ({
    id: r.id,
    name: r.name,
    displayName: r.description || r.name,
    source: r.from_entity_id,
    target: r.to_entity_id,
    cardinality: (r.cardinality || '1:N') as '1:1' | '1:N' | 'N:N',
    description: r.description || '',
    relationType: 'ObjectProperty' as const,
    semanticType: 'association' as const,
  }))
)

function goBack() {
  router.push('/ontology/list')
}

async function loadData() {
  const request = ++dataRequest
  const requestedCode = code.value
  relationOpen.value = false
  dataLoading.value = true
  loadError.value = ''
  ++relationsRequest
  selectedEntityId.value = null
  selectedIds.value = []
  showBatchMenu.value = false
  showCreateMenu.value = false
  allRelations.value = []
  relationsLoaded.value = false
  try {
    await scenarioStore.fetchScenarios()
    if (request !== dataRequest || code.value !== requestedCode) return
    const sc = scenarioStore.byCode(requestedCode)
    if (!sc) {
      loadError.value = '本体不存在或已被删除，请返回本体列表'
      return
    }
    await ontologyStore.switchOntology(sc.id)
    if (code.value === requestedCode && (activeTab.value === 'relations' || activeTab.value === 'graph')) await loadRelations()
  } catch {
    if (request === dataRequest) loadError.value = '本体资源加载失败，请重新加载'
  } finally {
    if (request === dataRequest) dataLoading.value = false
  }
}

onMounted(loadData)
onActivated(loadData)

// --- 关系定义 Tab ---
const allRelations = ref<EntityRelationDetail[]>([])
const relationsLoaded = ref(false)
const relationsLoading = ref(false)
const relationsError = ref('')
let relationsRequest = 0

async function loadRelations() {
  const ontologyId = scenario.value?.id
  if (!ontologyId) return
  const request = ++relationsRequest
  relationsLoading.value = true
  relationsError.value = ''
  try {
    const relations = await entityApi.relations(undefined, ontologyId)
    if (request !== relationsRequest || scenario.value?.id !== ontologyId) return
    allRelations.value = relations
    relationsLoaded.value = true
  } catch {
    if (request === relationsRequest) relationsError.value = '关系加载失败，请重新加载'
  } finally {
    if (request === relationsRequest) relationsLoading.value = false
  }
}

watch(code, loadData)
watch(activeTab, (tab) => {
  selectedEntityId.value = null
  if ((tab === 'relations' || tab === 'graph') && !relationsLoaded.value) {
    loadRelations()
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
.btn-action:disabled { color: var(--neutral-400); background: var(--neutral-50); cursor: not-allowed; }
.btn-action:disabled:hover { background: var(--neutral-50); }
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
  width: 100%; border: 0; background: transparent; font: inherit; text-align: left;
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

.detail-nav__item:focus-visible { outline: 2px solid var(--semantic-500); outline-offset: -2px; }
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
  background: var(--neutral-0);
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

.relations-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.relations-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--neutral-900, #111);
}

.relations-count {
  font-size: 12px;
  color: var(--neutral-400, #aaa);
}

.rel-type-tag {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 4px;
  background: #f5f3ff;
  color: #7c3aed;
}

.attr-panel__loading {
  padding: 40px 0;
  text-align: center;
  color: var(--neutral-400, #aaa);
  font-size: 13px;
}

/* 本体图谱 Tab */
.tab-graph {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.graph-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.graph-header__title {
  font-size: 15px;
  font-weight: 600;
  color: var(--neutral-900, #111);
}

.graph-header__desc {
  font-size: 12px;
  color: var(--neutral-400, #aaa);
}

.graph-container {
  flex: 1;
  min-height: 0;
  background: var(--neutral-0, #fff);
  border: 1px solid var(--neutral-100, #f0f0f0);
  border-radius: 8px;
  overflow: hidden;
  position: relative;
}

.graph-container :deep(.canvas-wrap) {
  height: 100%;
}
@media (max-width: 768px) {
  .ontology-detail { margin: -16px -12px; height: auto; min-height: 100%; }
  .ontology-detail__topbar { flex-wrap: wrap; height: auto; padding: 12px; gap: 10px; }
  .ontology-detail__title { min-width: 0; overflow-wrap: anywhere; }
  .ontology-detail__actions { flex-wrap: wrap; gap: 6px; }
  .ontology-detail__body { flex-direction: column; }
  .ontology-detail__sidebar { width: 100%; min-width: 0; border-right: 0; border-bottom: 1px solid #e2e8f0; }
  .detail-nav { display: flex; overflow-x: auto; padding: 8px; gap: 4px; }
  .detail-nav__section { display: none; }
  .detail-nav__item {
  width: 100%; border: 0; background: transparent; font: inherit; text-align: left; flex: 0 0 auto; white-space: nowrap; padding: 8px 10px; }
  .ontology-detail__content { padding: 16px 12px; min-width: 0; }
  .overview-stats, .overview-info-grid, .overview-tables { grid-template-columns: 1fr; }
}
.relation-editor { display:grid; gap:12px; } .relation-editor label { display:grid; gap:6px; }
</style>

<style scoped>
.check-log { white-space: pre-wrap; overflow-wrap: anywhere; max-height: 60vh; overflow: auto; }
@media (max-width: 900px) { .ontology-detail__topbar { flex-wrap: wrap; } .ontology-detail__actions { flex-wrap: wrap; } .ontology-detail__body { overflow: auto; } }
.relation-editor { display:grid; gap:12px; } .relation-editor label { display:grid; gap:6px; }
</style>
