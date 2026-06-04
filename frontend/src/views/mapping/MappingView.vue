<template>
  <div class="mp-page">
    <div class="mp-page__top">
      <div class="mp-page__header">
        <div>
          <h1 class="mp-page__title">映射管理</h1>
          <p class="mp-page__subtitle">选 ObjectType，AI 自动从所有数据资产中推荐最匹配的 Backing Datasets</p>
        </div>
        <div v-if="overview" class="mp-coverage">
          <div class="mp-coverage__item">
            <span class="mp-pill mp-pill--high">{{ overview.combo.covered_attrs }}</span>
            / {{ overview.total_attrs }} 属性可被覆盖
          </div>
          <div v-if="overview.existing_bindings.length > 0" class="mp-coverage__item">
            已绑定 <span class="mp-pill mp-pill--medium">{{ overview.existing_bindings.length }}</span> 个资产
          </div>
        </div>
      </div>
    </div>

    <div class="mp-page__body">
      <!-- 左：实体列表 + 覆盖率徽章 -->
      <aside class="mp-page__sidebar">
        <div class="mp-sidebar__search">
          <a-input-search v-model:value="entitySearch" placeholder="搜索实体..." size="small" allow-clear />
        </div>
        <div class="mp-sidebar__list">
          <div v-for="group in filteredEntityGroups" :key="group.tier" class="mp-sidebar__group">
            <div class="mp-sidebar__group-header">
              <span class="mp-sidebar__tier-badge" :class="`tier-${group.tier}`">T{{ group.tier }}</span>
              <span class="mp-sidebar__group-label">{{ group.label }}</span>
            </div>
            <div v-for="e in group.entities" :key="e.id" class="mp-sidebar__item"
                 :class="{ 'mp-sidebar__item--active': selectedEntityId === e.id }"
                 @click="selectEntity(e.id)">
              <span class="mp-sidebar__item-name">{{ e.name_cn }}</span>
              <span class="mp-sidebar__item-cov" :class="coverageClass(e.id)">
                {{ coverageBadge(e.id) }}
              </span>
            </div>
          </div>
        </div>
      </aside>

      <!-- 右：工作台 -->
      <div class="mp-page__main">
        <template v-if="!selectedEntityId">
          <div class="mp-main__empty">
            <a-empty description="选择左侧实体开始映射" />
          </div>
        </template>

        <!-- ========== 视图 A：Asset 推荐列表 ========== -->
        <template v-else-if="view === 'list'">
          <div class="mp-main__header-row">
            <div class="mp-main__entity-info">
              <h2 class="mp-main__entity-name">{{ overview?.object_type.name_cn || currentEntity?.name_cn || '...' }}</h2>
              <code class="mp-main__entity-code">{{ overview?.object_type.name || currentEntity?.name }}</code>
              <span class="mp-muted" style="margin-left:12px">{{ overview?.total_attrs ?? 0 }} 属性</span>
            </div>
            <a-space>
              <a-button :loading="scanning" @click="scanAssets">
                <template #icon><ReloadOutlined /></template>重新扫描
              </a-button>
              <a-button v-if="overview?.combo.primary" type="primary" :loading="combinedSaving"
                        @click="oneClickCombo">
                <template #icon><ThunderboltOutlined /></template>
                一键组合 ({{ 1 + (overview?.combo.enrichments.length || 0) }} 个资产)
              </a-button>
            </a-space>
          </div>

          <div v-if="scanning" class="mp-main__empty">
            <a-spin tip="AI 正在扫描所有数据资产..." />
          </div>
          <div v-else-if="!overview" class="mp-main__empty">
            <a-empty description="点「重新扫描」开始" />
          </div>
          <div v-else-if="overview.asset_suggestions.length === 0" class="mp-main__empty">
            <a-empty description="资产目录为空。请先在「数据接入」注册数据资产并同步 schema" />
          </div>
          <div v-else class="mp-asset-list">
            <div
              v-for="(row, idx) in overview.asset_suggestions"
              :key="row.asset.id"
              class="mp-asset-card"
              :class="{
                'mp-asset-card--primary': overview.combo.primary === row.asset.id,
                'mp-asset-card--enrichment': overview.combo.enrichments.includes(row.asset.id),
                'mp-asset-card--bound': row.already_bound_role,
              }"
              @click="enterDetail(row.asset.id)"
            >
              <div class="mp-asset-card__rank">#{{ idx + 1 }}</div>
              <div class="mp-asset-card__main">
                <div class="mp-asset-card__head">
                  <span class="mp-asset-card__name">{{ row.asset.name }}</span>
                  <a-tag :color="row.asset.kind === 'table' ? 'blue' : 'cyan'" class="mp-tag-sm">
                    {{ row.asset.kind }}
                  </a-tag>
                  <a-tag v-if="row.asset.domain" color="default" class="mp-tag-sm">{{ row.asset.domain }}</a-tag>
                  <a-tag v-if="overview.combo.primary === row.asset.id" color="green" class="mp-tag-sm">
                    建议 PRIMARY
                  </a-tag>
                  <a-tag v-if="overview.combo.enrichments.includes(row.asset.id)" color="orange" class="mp-tag-sm">
                    建议 ENRICHMENT
                  </a-tag>
                  <a-tag v-if="row.already_bound_role" color="purple" class="mp-tag-sm">
                    已绑定 ({{ row.already_bound_role }})
                  </a-tag>
                </div>
                <div class="mp-asset-card__cov">
                  <div class="mp-cov-bar">
                    <span v-if="row.coverage.high"
                          class="mp-cov-bar__seg mp-cov-bar__seg--high"
                          :style="{ flex: row.coverage.high }">
                      {{ row.coverage.high }}
                    </span>
                    <span v-if="row.coverage.medium"
                          class="mp-cov-bar__seg mp-cov-bar__seg--medium"
                          :style="{ flex: row.coverage.medium }">
                      {{ row.coverage.medium }}
                    </span>
                    <span v-if="row.coverage.low"
                          class="mp-cov-bar__seg mp-cov-bar__seg--low"
                          :style="{ flex: row.coverage.low }">
                      {{ row.coverage.low }}
                    </span>
                    <span v-if="row.coverage.none"
                          class="mp-cov-bar__seg mp-cov-bar__seg--none"
                          :style="{ flex: row.coverage.none }">
                      {{ row.coverage.none }}
                    </span>
                  </div>
                  <span class="mp-asset-card__pct">
                    覆盖率 <b>{{ Math.round(((row.coverage.high + row.coverage.medium) / row.coverage.total) * 100) }}%</b>
                  </span>
                </div>
                <div v-if="row.top_attrs.length > 0" class="mp-asset-card__samples">
                  <span class="mp-muted">示例匹配：</span>
                  <span v-for="t in row.top_attrs.slice(0, 4)" :key="t.attribute_name" class="mp-sample">
                    <code>{{ t.attribute_name }}</code>
                    <span class="mp-sample__arrow">→</span>
                    <code>{{ t.column }}</code>
                  </span>
                  <span v-if="row.top_attrs.length > 4" class="mp-muted">+{{ row.top_attrs.length - 4 }}</span>
                </div>
              </div>
              <a-button type="link"><RightOutlined /></a-button>
            </div>
          </div>
        </template>

        <!-- ========== 视图 B：字段映射详情 ========== -->
        <template v-else-if="view === 'detail'">
          <div class="mp-main__header-row">
            <a-space>
              <a-button @click="exitDetail">
                <template #icon><ArrowLeftOutlined /></template>返回
              </a-button>
              <div class="mp-main__entity-info" style="margin-left:8px">
                <h2 class="mp-main__entity-name">
                  {{ currentEntity?.name_cn }} <span class="mp-muted">←</span> {{ detailAssetName }}
                </h2>
              </div>
            </a-space>
            <a-space>
              <span class="mp-muted">Role:</span>
              <a-segmented v-model:value="detailRole"
                           :options="[{label:'Primary',value:'primary'},{label:'Enrichment',value:'enrichment'}]" />
              <a-checkbox v-model:checked="useLlm">用 LLM 兜底</a-checkbox>
              <a-button :loading="suggesting" @click="reRunSuggest">
                <template #icon><ThunderboltOutlined /></template>重新推荐
              </a-button>
            </a-space>
          </div>

          <div v-if="suggesting" class="mp-main__empty">
            <a-spin tip="AI 正在分析..." />
          </div>
          <div v-else-if="suggestion" class="mp-table-wrap">
            <div class="mp-table-toolbar">
              <a-button size="small" @click="acceptHigh">采用全部高置信</a-button>
              <a-button size="small" @click="clearAll">清空选择</a-button>
              <span class="mp-spacer" />
              <span class="mp-muted">已选 {{ selectedCount }} / {{ suggestion.suggestions.length }}</span>
              <a-button type="primary" size="small" :loading="applying"
                        :disabled="selectedCount === 0" @click="applyMapping">
                保存（{{ detailRole }}）
              </a-button>
            </div>

            <table class="mp-table">
              <thead>
                <tr>
                  <th style="width:36px"></th>
                  <th style="width:200px">本体属性</th>
                  <th style="width:90px">类型</th>
                  <th>建议候选列</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in suggestion.suggestions" :key="row.attribute_id"
                    :class="{ 'mp-row--selected': selection[row.attribute_id] }">
                  <td>
                    <a-checkbox
                      :checked="!!selection[row.attribute_id]"
                      :disabled="row.candidates.length === 0"
                      @change="(e: any) => onSelectToggle(row, e.target.checked)" />
                  </td>
                  <td>
                    <div class="mp-attr">
                      <span class="mp-attr__name">{{ row.attribute_name }}</span>
                      <div v-if="row.attribute_description" class="mp-attr__desc">{{ row.attribute_description }}</div>
                    </div>
                  </td>
                  <td>
                    <a-tag :color="typeColor(row.attribute_type)" class="mp-type-tag">{{ row.attribute_type }}</a-tag>
                  </td>
                  <td>
                    <div v-if="row.candidates.length === 0" class="mp-no-cand">
                      <ExclamationCircleOutlined /> 无候选
                      <a-input v-model:value="manualCol[row.attribute_id]" size="small" placeholder="手填列名"
                              style="width:140px;margin-left:8px"
                              @input="onManualInput(row)" />
                    </div>
                    <a-radio-group v-else :value="selection[row.attribute_id]" size="small"
                                   @change="(e: any) => onChooseCandidate(row, e.target.value)">
                      <a-radio v-for="c in row.candidates" :key="c.column" :value="c.column" class="mp-cand-radio">
                        <div class="mp-cand">
                          <code class="mp-cand__col" :title="c.reason">{{ c.column }}</code>
                          <a-tag v-if="c.is_pk" color="purple" class="mp-cand__pk">PK</a-tag>
                          <span class="mp-cand__type">{{ c.column_type }}</span>
                          <span class="mp-cand__score" :class="`mp-tier-${c.tier}`">{{ (c.score * 100).toFixed(0) }}</span>
                          <span v-if="c.source === 'llm'" class="mp-cand__llm">LLM</span>
                          <span v-if="c.column_comment" class="mp-cand__comment">{{ c.column_comment }}</span>
                        </div>
                      </a-radio>
                    </a-radio-group>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  Button as AButton, Checkbox as ACheckbox, Empty as AEmpty,
  Input as AInput, InputSearch as AInputSearch,
  Radio as ARadio, RadioGroup as ARadioGroup, Segmented as ASegmented,
  Space as ASpace, Spin as ASpin, Tag as ATag, message,
} from 'ant-design-vue'
import {
  ArrowLeftOutlined, ExclamationCircleOutlined, ReloadOutlined,
  RightOutlined, ThunderboltOutlined,
} from '@ant-design/icons-vue'
import { entityApi } from '../../api/ontology'
import {
  mappingApi, type CoverageRow, type MappingSuggestResponse,
  type MappingSuggestionRow, type SuggestAssetsResponse,
} from '../../api/mapping'
import type { EntityListItem, OntologyEntity } from '../../types'

const entities = ref<EntityListItem[]>([])
const coverageMap = ref<Record<string, CoverageRow>>({})
const selectedEntityId = ref<string | null>(null)
const currentEntity = ref<OntologyEntity | null>(null)
const entitySearch = ref('')

const view = ref<'list' | 'detail'>('list')

// list view 状态
const overview = ref<SuggestAssetsResponse | null>(null)
const scanning = ref(false)
const combinedSaving = ref(false)

// detail view 状态
const detailAssetId = ref<string | null>(null)
const detailRole = ref<'primary' | 'enrichment'>('primary')
const useLlm = ref(true)
const suggesting = ref(false)
const applying = ref(false)
const suggestion = ref<MappingSuggestResponse | null>(null)
const selection = reactive<Record<string, string | null>>({})
const manualCol = reactive<Record<string, string>>({})

const tierLabels: Record<number, string> = { 1: '核心对象', 2: '领域对象', 3: '场景扩展' }

const entityGroups = computed(() => {
  const groups: { tier: number; label: string; entities: EntityListItem[] }[] = []
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
    .map(g => ({ ...g, entities: g.entities.filter(e => e.name_cn.toLowerCase().includes(q) || e.name.toLowerCase().includes(q)) }))
    .filter(g => g.entities.length > 0)
})

const detailAssetName = computed(() => {
  const row = overview.value?.asset_suggestions.find(r => r.asset.id === detailAssetId.value)
  return row?.asset.name || ''
})

const selectedCount = computed(() => Object.values(selection).filter(v => !!v).length)

function coverageBadge(eid: string) {
  const r = coverageMap.value[eid]
  if (!r || r.total === 0) return ''
  return `${r.mapped}/${r.total}`
}
function coverageClass(eid: string) {
  const r = coverageMap.value[eid]
  if (!r || r.total === 0) return 'mp-cov--none'
  if (r.mapped === 0) return 'mp-cov--none'
  if (r.mapped === r.total) return 'mp-cov--full'
  return 'mp-cov--partial'
}

function typeColor(t: string) {
  return ({ string: 'blue', number: 'green', int: 'green', boolean: 'orange',
            date: 'purple', datetime: 'purple', enum: 'cyan', ref: 'magenta',
            json: 'gold', text: 'default' } as any)[t] || 'default'
}

async function selectEntity(id: string) {
  selectedEntityId.value = id
  currentEntity.value = await entityApi.detail(id)
  view.value = 'list'
  overview.value = null
  await scanAssets()
}

async function scanAssets() {
  if (!selectedEntityId.value) return
  scanning.value = true
  try {
    overview.value = await mappingApi.suggestAssets(selectedEntityId.value)
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  } finally { scanning.value = false }
}

function enterDetail(assetId: string) {
  detailAssetId.value = assetId
  // 已绑定的资产，role 保留原值
  const row = overview.value?.asset_suggestions.find(r => r.asset.id === assetId)
  if (row?.already_bound_role === 'enrichment') detailRole.value = 'enrichment'
  else if (overview.value?.combo.enrichments.includes(assetId)) detailRole.value = 'enrichment'
  else detailRole.value = 'primary'
  view.value = 'detail'
  suggestion.value = null
  for (const k of Object.keys(selection)) delete selection[k]
  reRunSuggest()
}

function exitDetail() {
  view.value = 'list'
  detailAssetId.value = null
  suggestion.value = null
}

async function reRunSuggest() {
  if (!selectedEntityId.value || !detailAssetId.value) return
  suggesting.value = true
  try {
    const data = await mappingApi.suggest({
      object_type_id: selectedEntityId.value,
      asset_id: detailAssetId.value,
      use_llm: useLlm.value,
    })
    suggestion.value = data
    for (const k of Object.keys(selection)) delete selection[k]
    for (const row of data.suggestions) {
      const top = row.candidates[0]
      if (top && (top.tier === 'high' || top.tier === 'medium')) {
        selection[row.attribute_id] = top.column
      } else {
        selection[row.attribute_id] = null
      }
    }
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  } finally { suggesting.value = false }
}

function onChooseCandidate(row: MappingSuggestionRow, col: string) {
  selection[row.attribute_id] = col
}
function onSelectToggle(row: MappingSuggestionRow, checked: boolean) {
  if (checked) {
    if (row.candidates.length > 0) selection[row.attribute_id] = row.candidates[0].column
    else if (manualCol[row.attribute_id]) selection[row.attribute_id] = manualCol[row.attribute_id]
  } else {
    selection[row.attribute_id] = null
  }
}
function onManualInput(row: MappingSuggestionRow) {
  selection[row.attribute_id] = manualCol[row.attribute_id] || null
}
function acceptHigh() {
  if (!suggestion.value) return
  for (const row of suggestion.value.suggestions) {
    const top = row.candidates[0]
    if (top && top.tier === 'high') selection[row.attribute_id] = top.column
  }
}
function clearAll() {
  for (const k of Object.keys(selection)) selection[k] = null
}

async function applyMapping() {
  if (!selectedEntityId.value || !detailAssetId.value) return
  const field_mappings = Object.entries(selection)
    .filter(([, col]) => !!col)
    .map(([attribute_id, col]) => ({ attribute_id, source_column: col as string }))
  if (field_mappings.length === 0) { message.warning('请至少选择一条'); return }
  let id_column: string | null = null
  if (suggestion.value) {
    for (const row of suggestion.value.suggestions) {
      const sel = selection[row.attribute_id]
      if (!sel) continue
      const cand = row.candidates.find(c => c.column === sel)
      if (cand?.is_pk) { id_column = sel; break }
    }
  }
  applying.value = true
  try {
    const r = await mappingApi.apply({
      object_type_id: selectedEntityId.value,
      asset_id: detailAssetId.value,
      field_mappings, id_column, role: detailRole.value,
    })
    message.success(`已${r.action === 'created' ? '建立' : '更新'} ${detailRole.value} binding（${r.field_mappings_count} 字段）`)
    await refreshAfterApply()
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  } finally { applying.value = false }
}

async function oneClickCombo() {
  if (!overview.value || !overview.value.combo.primary) return
  combinedSaving.value = true
  try {
    const ids = [overview.value.combo.primary, ...overview.value.combo.enrichments]
    let ok = 0, fail = 0
    for (const aid of ids) {
      const role = aid === overview.value.combo.primary ? 'primary' : 'enrichment'
      // 跑 suggest 拿字段，自动取 top 候选
      const data = await mappingApi.suggest({
        object_type_id: selectedEntityId.value!, asset_id: aid, use_llm: false,
      })
      const fm = data.suggestions
        .map(r => ({ attribute_id: r.attribute_id, top: r.candidates[0] }))
        .filter(x => x.top && (x.top.tier === 'high' || x.top.tier === 'medium'))
        .map(x => ({ attribute_id: x.attribute_id, source_column: x.top!.column }))
      if (fm.length === 0) { fail++; continue }
      let id_column: string | null = null
      for (const r of data.suggestions) {
        const top = r.candidates[0]
        if (top?.is_pk) { id_column = top.column; break }
      }
      try {
        await mappingApi.apply({
          object_type_id: selectedEntityId.value!, asset_id: aid,
          field_mappings: fm, id_column, role,
        })
        ok++
      } catch { fail++ }
    }
    if (fail === 0) message.success(`一键组合完成：${ok} 个 binding 已建立`)
    else message.warning(`完成 ${ok}，失败 ${fail}`)
    await refreshAfterApply()
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  } finally { combinedSaving.value = false }
}

async function refreshAfterApply() {
  await loadCoverage()
  if (selectedEntityId.value) {
    overview.value = await mappingApi.suggestAssets(selectedEntityId.value)
    currentEntity.value = await entityApi.detail(selectedEntityId.value)
  }
  view.value = 'list'
}

async function loadCoverage() {
  const list = await mappingApi.coverage()
  coverageMap.value = Object.fromEntries(list.map(r => [r.object_type_id, r]))
}

onMounted(async () => {
  entities.value = await entityApi.list()
  await loadCoverage()
})
</script>

<style scoped>
.mp-page { display: flex; flex-direction: column; height: 100%; overflow: hidden; }
.mp-page__top { padding: 20px 24px 16px; border-bottom: 1px solid #e5e7eb; flex-shrink: 0; }
.mp-page__header { display: flex; justify-content: space-between; align-items: flex-start; gap: 24px; }
.mp-page__title { font-size: 20px; font-weight: 700; color: #111827; margin: 0; }
.mp-page__subtitle { font-size: 12px; color: #6b7280; margin: 4px 0 0; }
.mp-coverage { display: flex; gap: 16px; align-items: center; padding: 8px 14px; background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; }
.mp-coverage__item { font-size: 12px; color: #4b5563; }
.mp-pill { display: inline-block; padding: 1px 6px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.mp-pill--high { background: #d1fae5; color: #065f46; }
.mp-pill--medium { background: #fef3c7; color: #92400e; }
.mp-pill--low { background: #fee2e2; color: #991b1b; }
.mp-pill--none { background: #f3f4f6; color: #6b7280; }

.mp-page__body { display: flex; flex: 1; overflow: hidden; }
.mp-page__sidebar { width: 240px; flex-shrink: 0; border-right: 1px solid #e5e7eb; display: flex; flex-direction: column; }
.mp-sidebar__search { padding: 12px; }
.mp-sidebar__list { flex: 1; overflow-y: auto; padding: 0 8px 12px; }
.mp-sidebar__group-header { display: flex; align-items: center; gap: 6px; padding: 8px; font-size: 11px; color: #6b7280; font-weight: 600; }
.mp-sidebar__tier-badge { font-size: 10px; padding: 1px 6px; border-radius: 4px; background: #f3f4f6; color: #4b5563; font-weight: 600; }
.mp-sidebar__tier-badge.tier-1 { background: #dbeafe; color: #1d4ed8; }
.mp-sidebar__tier-badge.tier-2 { background: #d1fae5; color: #065f46; }
.mp-sidebar__tier-badge.tier-3 { background: #fef3c7; color: #92400e; }
.mp-sidebar__item { display: flex; justify-content: space-between; align-items: center; gap: 6px; padding: 6px 10px; cursor: pointer; border-radius: 6px; font-size: 13px; color: #374151; }
.mp-sidebar__item:hover { background: #f3f4f6; }
.mp-sidebar__item--active { background: #dbeafe; color: #1d4ed8; font-weight: 600; }
.mp-sidebar__item-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mp-sidebar__item-cov { font-size: 10px; padding: 1px 5px; border-radius: 3px; flex-shrink: 0; }
.mp-cov--none { background: #f3f4f6; color: #9ca3af; }
.mp-cov--partial { background: #fef3c7; color: #92400e; }
.mp-cov--full { background: #d1fae5; color: #065f46; }

.mp-page__main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.mp-main__empty { flex: 1; display: flex; align-items: center; justify-content: center; }
.mp-main__header-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 14px 24px; border-bottom: 1px solid #e5e7eb; flex-shrink: 0; }
.mp-main__entity-info { display: flex; align-items: center; gap: 10px; }
.mp-main__entity-name { margin: 0; font-size: 16px; font-weight: 600; color: #111827; }
.mp-main__entity-code { background: #f3f4f6; padding: 2px 8px; border-radius: 4px; font-family: monospace; font-size: 12px; color: #4b5563; }
.mp-muted { color: #9ca3af; font-size: 12px; }

.mp-asset-list { flex: 1; overflow-y: auto; padding: 16px 24px; display: flex; flex-direction: column; gap: 12px; }
.mp-asset-card { display: flex; align-items: center; gap: 12px; padding: 14px 16px; background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; cursor: pointer; transition: all 0.15s; }
.mp-asset-card:hover { border-color: #3b82f6; box-shadow: 0 4px 12px rgba(59,130,246,0.08); }
.mp-asset-card--primary { border-left: 4px solid #10b981; }
.mp-asset-card--enrichment { border-left: 4px solid #f59e0b; }
.mp-asset-card--bound { background: #faf5ff; }
.mp-asset-card__rank { font-size: 14px; font-weight: 700; color: #9ca3af; min-width: 32px; }
.mp-asset-card__main { flex: 1; min-width: 0; }
.mp-asset-card__head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
.mp-asset-card__name { font-weight: 600; font-size: 14px; color: #111827; }
.mp-tag-sm { font-size: 10px; }
.mp-asset-card__cov { display: flex; align-items: center; gap: 12px; }
.mp-cov-bar { flex: 1; max-width: 320px; height: 12px; display: flex; border-radius: 6px; overflow: hidden; background: #f3f4f6; }
.mp-cov-bar__seg { display: flex; align-items: center; justify-content: center; font-size: 10px; color: #fff; font-weight: 600; }
.mp-cov-bar__seg--high { background: #10b981; }
.mp-cov-bar__seg--medium { background: #f59e0b; }
.mp-cov-bar__seg--low { background: #ef4444; }
.mp-cov-bar__seg--none { background: #d1d5db; color: #6b7280; }
.mp-asset-card__pct { font-size: 12px; color: #4b5563; }
.mp-asset-card__samples { margin-top: 6px; font-size: 11px; color: #6b7280; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.mp-sample { display: inline-flex; align-items: center; gap: 2px; }
.mp-sample code { background: #f3f4f6; padding: 1px 5px; border-radius: 3px; font-family: monospace; font-size: 10px; color: #1d4ed8; }
.mp-sample__arrow { color: #9ca3af; }

.mp-table-wrap { flex: 1; overflow-y: auto; padding: 16px 24px; }
.mp-table-toolbar { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; margin-bottom: 12px; }
.mp-spacer { flex: 1; }
.mp-table { width: 100%; border-collapse: collapse; background: #fff; }
.mp-table th, .mp-table td { padding: 10px 12px; border-bottom: 1px solid #e5e7eb; font-size: 13px; vertical-align: top; text-align: left; }
.mp-table th { background: #f9fafb; font-weight: 600; color: #4b5563; font-size: 11px; }
.mp-table tr.mp-row--selected { background: #eff6ff; }
.mp-attr__name { font-weight: 600; color: #111827; }
.mp-attr__desc { font-size: 11px; color: #9ca3af; margin-top: 2px; }
.mp-type-tag { font-size: 10px; }
.mp-cand-radio { display: flex !important; padding: 4px 0; }
.mp-cand { display: inline-flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.mp-cand__col { font-family: monospace; font-size: 12px; color: #1d4ed8; font-weight: 600; }
.mp-cand__pk { font-size: 9px !important; padding: 0 4px; line-height: 16px; }
.mp-cand__type { font-size: 11px; color: #6b7280; }
.mp-cand__score { display: inline-block; min-width: 32px; text-align: center; font-size: 10px; font-weight: 600; padding: 1px 5px; border-radius: 4px; }
.mp-tier-high { background: #d1fae5; color: #065f46; }
.mp-tier-medium { background: #fef3c7; color: #92400e; }
.mp-tier-low { background: #fee2e2; color: #991b1b; }
.mp-tier-none { background: #f3f4f6; color: #6b7280; }
.mp-cand__llm { font-size: 9px; padding: 0 5px; background: #ede9fe; color: #5b21b6; border-radius: 3px; font-weight: 600; }
.mp-cand__comment { font-size: 11px; color: #9ca3af; }
.mp-no-cand { font-size: 12px; color: #ef4444; display: flex; align-items: center; gap: 6px; }
</style>
