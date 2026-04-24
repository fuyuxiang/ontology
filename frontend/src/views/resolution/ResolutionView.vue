<template>
  <div class="res-page">
    <!-- 顶部标题 -->
    <div class="res-page__top">
      <div class="res-page__header">
        <h1 class="res-page__title">实体解析</h1>
        <p class="res-page__subtitle">将已映射的来源数据解析为可用的本体实体实例，验证数据完整性与唯一性</p>
      </div>
    </div>

    <div class="res-page__body">
      <!-- 左侧实体列表 -->
      <aside class="res-page__sidebar">
        <div class="res-sidebar__search">
          <a-input-search v-model:value="entitySearch" placeholder="搜索实体..." size="small" allow-clear />
        </div>
        <div class="res-sidebar__list">
          <div v-for="group in filteredEntityGroups" :key="group.tier" class="res-sidebar__group">
            <div class="res-sidebar__group-header">
              <span class="res-sidebar__tier-badge" :class="`tier-${group.tier}`">T{{ group.tier }}</span>
              <span class="res-sidebar__group-label">{{ group.label }}</span>
            </div>
            <div
              v-for="e in group.entities"
              :key="e.entity_id"
              class="res-sidebar__item"
              :class="{ 'res-sidebar__item--active': selectedEntityId === e.entity_id }"
              @click="selectEntity(e)"
            >
              <div class="res-sidebar__item-main">
                <span class="res-sidebar__item-name">{{ e.entity_name_cn }}</span>
                <span class="res-sidebar__item-code">{{ e.entity_name }}</span>
              </div>
              <span class="res-sidebar__item-badge">{{ e.mapped_count }}/{{ e.attr_count }}</span>
            </div>
          </div>
        </div>
      </aside>

      <!-- 右侧主区域 -->
      <div class="res-page__main">
        <template v-if="!selectedEntity">
          <div class="res-main__empty">
            <a-empty description="选择左侧实体查看解析详情" />
          </div>
        </template>

        <template v-else>
          <!-- 实体信息头部 -->
          <div class="res-main__header">
            <div class="res-main__entity-info">
              <span class="res-sidebar__tier-badge" :class="`tier-${selectedEntity.tier}`">T{{ selectedEntity.tier }}</span>
              <h2 class="res-main__entity-name">{{ selectedEntity.entity_name_cn }}</h2>
              <code class="res-main__entity-code">{{ selectedEntity.entity_name }}</code>
            </div>
          </div>

          <!-- 统计卡片 -->
          <div class="res-stats" v-if="stats">
            <div class="res-stat">
              <div class="res-stat__val">{{ stats.total_rows.toLocaleString() }}</div>
              <div class="res-stat__lbl">源数据总行数</div>
            </div>
            <div class="res-stat" :class="{ 'res-stat--warn': stats.null_identifier_rows && stats.null_identifier_rows > 0 }">
              <div class="res-stat__val">{{ stats.distinct_identifier_rows?.toLocaleString() ?? '-' }}</div>
              <div class="res-stat__lbl">唯一实体数</div>
            </div>
            <div class="res-stat">
              <div class="res-stat__val">{{ (stats.completeness * 100).toFixed(1) }}%</div>
              <div class="res-stat__lbl">数据完整度</div>
            </div>
            <div class="res-stat">
              <div class="res-stat__val">{{ selectedEntity.sources.length }}</div>
              <div class="res-stat__lbl">来源表数</div>
            </div>
          </div>

          <!-- 标识字段选择 -->
          <div class="res-identifier-bar">
            <span class="res-identifier-bar__label">实体标识字段：</span>
            <a-select
              v-model:value="identifierField"
              style="width: 240px"
              size="small"
              placeholder="选择唯一标识字段"
              allow-clear
              @change="loadStats"
            >
              <a-select-option v-for="f in sourceFields" :key="f.attribute_id" :value="f.source_field">
                {{ f.attribute_name }} <span style="color:var(--neutral-400)">→ {{ f.source_field }}</span>
              </a-select-option>
            </a-select>
            <a-button size="small" @click="loadStats" :loading="statsLoading">刷新统计</a-button>
          </div>

          <!-- 来源表标签页 -->
          <a-tabs v-model:activeKey="activeSourceTab" size="small" @change="onSourceTabChange">
            <a-tab-pane v-for="src in selectedEntity.sources" :key="src.table_name" :tab="`${src.table_name} (${src.datasource_name})`" />
          </a-tabs>

          <!-- 数据预览表 -->
          <div class="res-table-wrap" v-if="previewData">
            <PageState :loading="previewLoading" :empty="!previewLoading && previewData.rows.length === 0" empty-text="来源表无数据">
              <table class="res-table">
                <thead>
                  <tr>
                    <th style="width:50px">#</th>
                    <th v-for="col in previewData.columns" :key="col">
                      {{ col }}
                      <span v-if="getFieldAttrName(col)" class="res-col-attr" :title="`本体属性: ${getFieldAttrName(col)}`">
                        → {{ getFieldAttrName(col) }}
                      </span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, ri) in previewData.rows" :key="ri">
                    <td class="res-row-num">{{ (previewData.page - 1) * previewData.page_size + ri + 1 }}</td>
                    <td v-for="col in previewData.columns" :key="col" :class="{ 'res-null': row[previewData.columns.indexOf(col)] == null }">
                      {{ row[previewData.columns.indexOf(col)] != null ? String(row[previewData.columns.indexOf(col)]) : 'NULL' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </PageState>

            <!-- 分页 -->
            <div class="res-pagination" v-if="previewData && previewData.total_rows > 0">
              <span class="res-pagination__info">共 {{ previewData.total_rows }} 条</span>
              <div class="res-pagination__btns">
                <a-button size="small" :disabled="previewData.page <= 1" @click="goPage(previewData.page - 1)">上一页</a-button>
                <span class="res-pagination__cur">{{ previewData.page }} / {{ totalPreviewPages }}</span>
                <a-button size="small" :disabled="previewData.page >= totalPreviewPages" @click="goPage(previewData.page + 1)">下一页</a-button>
              </div>
            </div>
          </div>

          <!-- 字段映射表 -->
          <div class="res-section">
            <h3 class="res-section__title">字段映射明细</h3>
            <div class="res-section__table-wrap">
              <table class="res-fields-table" v-if="sourceFields.length">
                <thead>
                  <tr>
                    <th>本体属性</th>
                    <th>类型</th>
                    <th>来源表</th>
                    <th>来源字段</th>
                    <th>状态</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="f in sourceFields" :key="f.attribute_id">
                    <td><code class="res-attr-name">{{ f.attribute_name }}</code></td>
                    <td><a-tag size="small" :color="typeColor(f.attribute_type)">{{ f.attribute_type }}</a-tag></td>
                    <td>{{ f.source_table }}</td>
                    <td><code class="res-field-code">{{ f.source_field }}</code></td>
                    <td>
                      <a-tag size="small" :color="f.data_status === '已确认来源' ? 'green' : f.data_status === '待确认' ? 'orange' : 'default'">
                        {{ f.data_status === '已确认来源' ? '已确认' : f.data_status === '待确认' ? '待确认' : f.data_status }}
                      </a-tag>
                    </td>
                  </tr>
                </tbody>
              </table>
              <a-empty v-else description="该实体暂无可解析的映射字段" />
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import PageState from '../../components/common/PageState.vue'
import { resolutionApi } from '../../api/resolution'
import type { ResolvableEntity, SourceField, SourceDataPreview, ResolutionStats } from '../../api/resolution'

const entities = ref<ResolvableEntity[]>([])
const selectedEntity = ref<ResolvableEntity | null>(null)
const selectedEntityId = ref<string | null>(null)
const entitySearch = ref('')

const sourceFields = ref<SourceField[]>([])
const previewData = ref<SourceDataPreview | null>(null)
const previewLoading = ref(false)
const stats = ref<ResolutionStats | null>(null)
const statsLoading = ref(false)
const identifierField = ref<string | null>(null)
const activeSourceTab = ref('')
const currentPage = ref(1)

const tierLabels: Record<number, string> = { 1: '核心对象', 2: '领域对象', 3: '场景扩展' }

const entityGroups = computed(() => {
  const groups: { tier: number; label: string; entities: ResolvableEntity[] }[] = []
  for (const tier of [1, 2, 3]) {
    const items = entities.value.filter(e => e.tier === tier)
    if (items.length) groups.push({ tier, label: tierLabels[tier], entities: items })
  }
  return groups
})

const filteredEntityGroups = computed(() => {
  const q = entitySearch.value.toLowerCase()
  if (!q) return entityGroups.value
  return entityGroups.value
    .map(g => ({ ...g, entities: g.entities.filter(e => e.entity_name_cn.toLowerCase().includes(q) || e.entity_name.toLowerCase().includes(q)) }))
    .filter(g => g.entities.length > 0)
})

const totalPreviewPages = computed(() =>
  previewData.value ? Math.max(1, Math.ceil(previewData.value.total_rows / previewData.value.page_size)) : 1,
)

function getFieldAttrName(col: string) {
  return sourceFields.value.find(f => f.source_field === col)?.attribute_name || ''
}

async function selectEntity(e: ResolvableEntity) {
  selectedEntity.value = e
  selectedEntityId.value = e.entity_id
  currentPage.value = 1
  identifierField.value = null

  // 加载字段和统计数据
  const [fields, st] = await Promise.all([
    resolutionApi.getFields(e.entity_id),
    resolutionApi.stats(e.entity_id),
  ])
  sourceFields.value = fields
  stats.value = st

  // 自动选中第一个来源表并加载预览
  if (e.sources.length > 0) {
    activeSourceTab.value = e.sources[0].table_name
  }
  loadPreview()
}

async function loadPreview() {
  if (!selectedEntity.value) return
  previewLoading.value = true
  try {
    previewData.value = await resolutionApi.preview(selectedEntity.value.entity_id, {
      table_name: activeSourceTab.value || undefined,
      page: currentPage.value,
    })
  } finally {
    previewLoading.value = false
  }
}

async function loadStats() {
  if (!selectedEntity.value) return
  statsLoading.value = true
  try {
    stats.value = await resolutionApi.stats(selectedEntity.value.entity_id, identifierField.value || undefined)
  } finally {
    statsLoading.value = false
  }
}

function onSourceTabChange(_key: string) {
  currentPage.value = 1
  loadPreview()
}

function goPage(p: number) {
  currentPage.value = p
  loadPreview()
}

function typeColor(type: string) {
  const map: Record<string, string> = { string: 'blue', number: 'green', boolean: 'orange', date: 'purple', ref: 'magenta', computed: 'geekblue', json: 'gold' }
  return map[type] || 'default'
}

onMounted(async () => {
  entities.value = await resolutionApi.listEntities()
})
</script>

<style scoped>
.res-page { display: flex; flex-direction: column; height: 100%; overflow: hidden; }
.res-page__top { padding: 20px 24px 16px; border-bottom: 1px solid var(--neutral-200); flex-shrink: 0; }
.res-page__header { display: flex; justify-content: space-between; align-items: flex-start; }
.res-page__title { font-size: 20px; font-weight: 700; color: var(--neutral-900); margin: 0; }
.res-page__subtitle { font-size: var(--text-caption-size); color: var(--neutral-500); margin: 4px 0 0; }

.res-page__body { display: flex; flex: 1; overflow: hidden; }

/* 左栏 */
.res-page__sidebar { width: 260px; min-width: 260px; border-right: 1px solid var(--neutral-200); display: flex; flex-direction: column; overflow: hidden; background: var(--neutral-0); }
.res-sidebar__search { padding: 12px; border-bottom: 1px solid var(--neutral-100); flex-shrink: 0; }
.res-sidebar__list { flex: 1; overflow-y: auto; padding: 8px 0; }
.res-sidebar__group { padding: 4px 0; }
.res-sidebar__group-header { display: flex; align-items: center; gap: 6px; padding: 6px 12px; }
.res-sidebar__group-label { font-size: var(--text-caption-size); font-weight: 600; color: var(--neutral-500); text-transform: uppercase; letter-spacing: 0.3px; }
.res-sidebar__tier-badge { display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 18px; border-radius: var(--radius-sm); font-size: 11px; font-weight: 700; color: #fff; }
.tier-1 { background: var(--semantic-600); }
.tier-2 { background: var(--dynamic-500, #f59f00); }
.tier-3 { background: var(--kinetic-500, #20c997); }
.res-sidebar__item { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px 8px 16px; cursor: pointer; transition: background var(--transition-fast); }
.res-sidebar__item:hover { background: var(--neutral-50); }
.res-sidebar__item--active { background: var(--semantic-50); border-right: 2px solid var(--semantic-500); }
.res-sidebar__item-main { flex: 1; overflow: hidden; }
.res-sidebar__item-name { display: block; font-size: var(--text-body-size); color: var(--neutral-700); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.res-sidebar__item-code { display: block; font-size: 11px; color: var(--neutral-400); margin-top: 1px; }
.res-sidebar__item-badge { font-size: 11px; color: var(--neutral-400); background: var(--neutral-100); padding: 1px 6px; border-radius: var(--radius-sm); flex-shrink: 0; margin-left: 8px; }

/* 右栏 */
.res-page__main { flex: 1; overflow-y: auto; padding: 20px 24px; }
.res-main__empty { display: flex; align-items: center; justify-content: center; height: 100%; }
.res-main__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.res-main__entity-info { display: flex; align-items: center; gap: 10px; }
.res-main__entity-name { font-size: 18px; font-weight: 700; color: var(--neutral-900); margin: 0; }
.res-main__entity-code { font-size: var(--text-code-size); color: var(--neutral-500); background: var(--neutral-50); padding: 2px 8px; border-radius: var(--radius-sm); }

/* 统计卡片 */
.res-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.res-stat { padding: 14px 18px; border-radius: var(--radius-md); background: var(--neutral-50); border: 1px solid var(--neutral-200); }
.res-stat--warn { border-color: var(--status-warning); background: var(--status-warning-bg); }
.res-stat__val { font-size: 24px; font-weight: 700; color: var(--neutral-900); }
.res-stat__lbl { font-size: var(--text-caption-size); color: var(--neutral-500); margin-top: 2px; }

/* 标识字段栏 */
.res-identifier-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; padding: 10px 14px; background: var(--neutral-25, #fafbfc); border: 1px solid var(--neutral-200); border-radius: var(--radius-md); }
.res-identifier-bar__label { font-size: var(--text-body-size); font-weight: 600; color: var(--neutral-700); white-space: nowrap; }

/* 数据预览表 */
.res-table-wrap { margin-bottom: 24px; }
.res-table { width: 100%; border-collapse: collapse; font-size: var(--text-code-size); }
.res-table th { text-align: left; padding: 8px 10px; background: var(--neutral-50); border-bottom: 2px solid var(--neutral-200); font-weight: 600; font-size: var(--text-caption-size); color: var(--neutral-600); white-space: nowrap; }
.res-table td { padding: 6px 10px; border-bottom: 1px solid var(--neutral-100); max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.res-table tbody tr:hover { background: var(--neutral-25, #fafbfc); }
.res-row-num { color: var(--neutral-300); font-size: 11px; }
.res-null { color: var(--neutral-300); font-style: italic; }
.res-col-attr { font-size: 10px; color: var(--semantic-500); font-weight: 400; margin-left: 2px; }

.res-pagination { display: flex; align-items: center; justify-content: space-between; margin-top: 10px; }
.res-pagination__info { font-size: var(--text-code-size); color: var(--neutral-500); }
.res-pagination__btns { display: flex; align-items: center; gap: 8px; }
.res-pagination__cur { font-size: var(--text-code-size); color: var(--neutral-600); font-weight: 500; }

/* 字段映射明细 */
.res-section { margin-top: 8px; }
.res-section__title { font-size: 15px; font-weight: 600; color: var(--neutral-800); margin: 0 0 10px; }
.res-section__table-wrap { overflow-x: auto; }
.res-fields-table { width: 100%; border-collapse: collapse; font-size: var(--text-body-size); }
.res-fields-table th { text-align: left; padding: 8px 12px; background: var(--neutral-50); border-bottom: 2px solid var(--neutral-200); font-weight: 600; font-size: var(--text-caption-size); color: var(--neutral-600); }
.res-fields-table td { padding: 7px 12px; border-bottom: 1px solid var(--neutral-100); vertical-align: middle; }
.res-fields-table tbody tr:hover { background: var(--neutral-25, #fafbfc); }
.res-attr-name { font-size: var(--text-code-size); color: var(--semantic-700); }
.res-field-code { font-size: var(--text-code-size); color: var(--kinetic-600, #0ca678); background: var(--neutral-50); padding: 1px 6px; border-radius: var(--radius-sm); }
</style>
