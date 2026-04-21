<template>
  <div class="mp-page">
    <!-- 顶部标题 + 统计 -->
    <div class="mp-page__top">
      <div class="mp-page__header">
        <div>
          <h1 class="mp-page__title">本体映射</h1>
          <p class="mp-page__subtitle">属性级数据源映射 · 来源追溯 · 数据确认</p>
        </div>
      </div>
      <div class="mp-page__stats">
        <div class="stat-card stat-card--semantic">
          <div class="stat-card__icon"><LinkOutlined /></div>
          <a-statistic title="属性总数" :value="totalAttrs" />
        </div>
        <div class="stat-card stat-card--success">
          <div class="stat-card__icon"><CheckCircleOutlined /></div>
          <a-statistic title="已确认" :value="confirmedAttrs" />
        </div>
        <div class="stat-card stat-card--warning">
          <div class="stat-card__icon"><ClockCircleOutlined /></div>
          <a-statistic title="待确认" :value="pendingAttrs" />
        </div>
        <div class="stat-card stat-card--muted">
          <div class="stat-card__icon"><MinusCircleOutlined /></div>
          <a-statistic title="未映射" :value="unmappedAttrs" />
        </div>
      </div>
    </div>

    <div class="mp-page__body">
      <!-- 左侧实体列表 -->
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
            <div
              v-for="e in group.entities"
              :key="e.id"
              class="mp-sidebar__item"
              :class="{ 'mp-sidebar__item--active': selectedEntityId === e.id }"
              @click="selectEntity(e.id)"
            >
              <span class="mp-sidebar__item-name">{{ e.name_cn }}</span>
              <span class="mp-sidebar__item-count">{{ e.attr_count }}属性</span>
            </div>
          </div>
        </div>
      </aside>

      <!-- 右侧映射详情 -->
      <div class="mp-page__main">
        <template v-if="!selectedEntityId">
          <div class="mp-main__empty">
            <a-empty description="选择左侧实体查看属性映射" />
          </div>
        </template>
        <template v-else-if="loadingDetail">
          <div class="mp-main__empty"><a-spin /></div>
        </template>
        <template v-else-if="currentEntity">
          <div class="mp-main__header">
            <div class="mp-main__entity-info">
              <span class="mp-sidebar__tier-badge" :class="`tier-${currentEntity.tier}`">T{{ currentEntity.tier }}</span>
              <h2 class="mp-main__entity-name">{{ currentEntity.name_cn }}</h2>
              <code class="mp-main__entity-code">{{ currentEntity.name }}</code>
            </div>
            <a-space>
              <a-button size="small" @click="toggleEditMode" :type="editMode ? 'primary' : 'default'">
                {{ editMode ? '完成编辑' : '编辑映射' }}
              </a-button>
              <a-button v-if="editMode" size="small" @click="handleSave" :loading="saving">保存</a-button>
            </a-space>
          </div>

          <div class="mp-main__table-wrap">
            <table class="mp-table">
              <thead>
                <tr>
                  <th style="width:160px">属性名称</th>
                  <th style="width:80px">类型</th>
                  <th style="width:200px">来源数据表</th>
                  <th style="width:160px">来源字段</th>
                  <th style="width:100px">数据状态</th>
                  <th>描述</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="attr in currentEntity.attributes" :key="attr.id" class="mp-table__row">
                  <td>
                    <code class="mp-attr-name">{{ attr.name }}</code>
                    <span v-if="attr.required" class="mp-required">*</span>
                  </td>
                  <td><a-tag size="small" :color="typeColor(attr.type)">{{ attr.type }}</a-tag></td>
                  <td>
                    <template v-if="editMode">
                      <a-input v-model:value="editData[attr.id].source_table" size="small" placeholder="数据表名" />
                    </template>
                    <template v-else>
                      <span v-if="attr.source_table" class="mp-source">{{ attr.source_table }}</span>
                      <span v-else class="mp-empty">—</span>
                    </template>
                  </td>
                  <td>
                    <template v-if="editMode">
                      <a-input v-model:value="editData[attr.id].source_field" size="small" placeholder="字段名" />
                    </template>
                    <template v-else>
                      <code v-if="attr.source_field" class="mp-field">{{ attr.source_field }}</code>
                      <span v-else class="mp-empty">—</span>
                    </template>
                  </td>
                  <td>
                    <template v-if="editMode">
                      <a-select v-model:value="editData[attr.id].data_status" size="small" style="width:100%">
                        <a-select-option value="已确认来源">已确认</a-select-option>
                        <a-select-option value="待确认">待确认</a-select-option>
                        <a-select-option value="未确认来源">未确认</a-select-option>
                      </a-select>
                    </template>
                    <template v-else>
                      <a-tag :color="statusColor(attr.data_status)">{{ statusLabel(attr.data_status) }}</a-tag>
                    </template>
                  </td>
                  <td class="mp-desc">{{ attr.description }}</td>
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
import { ref, reactive, computed, onMounted } from 'vue'
import { entityApi } from '../../api/ontology'
import type { EntityListItem, OntologyEntity } from '../../types'
import {
  LinkOutlined, CheckCircleOutlined, ClockCircleOutlined, MinusCircleOutlined,
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'

const entities = ref<EntityListItem[]>([])
const selectedEntityId = ref<string | null>(null)
const currentEntity = ref<OntologyEntity | null>(null)
const loadingDetail = ref(false)
const editMode = ref(false)
const saving = ref(false)
const entitySearch = ref('')

const editData = reactive<Record<string, { source_table: string; source_field: string; data_status: string }>>({})

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

const totalAttrs = computed(() => currentEntity.value?.attributes.length ?? 0)
const confirmedAttrs = computed(() => currentEntity.value?.attributes.filter(a => a.data_status === '已确认来源').length ?? 0)
const pendingAttrs = computed(() => currentEntity.value?.attributes.filter(a => a.data_status === '待确认').length ?? 0)
const unmappedAttrs = computed(() => currentEntity.value?.attributes.filter(a => !a.source_table && !a.source_field).length ?? 0)

function typeColor(type: string) {
  const map: Record<string, string> = { string: 'blue', number: 'green', boolean: 'orange', date: 'purple', enum: 'cyan', ref: 'magenta', computed: 'geekblue', json: 'gold' }
  return map[type] || 'default'
}

function statusColor(status?: string) {
  if (status === '已确认来源') return 'green'
  if (status === '待确认') return 'orange'
  return 'default'
}

function statusLabel(status?: string) {
  if (status === '已确认来源') return '已确认'
  if (status === '待确认') return '待确认'
  return '未确认'
}

async function selectEntity(id: string) {
  selectedEntityId.value = id
  editMode.value = false
  loadingDetail.value = true
  try {
    currentEntity.value = await entityApi.detail(id)
  } finally {
    loadingDetail.value = false
  }
}

function toggleEditMode() {
  if (!editMode.value && currentEntity.value) {
    for (const attr of currentEntity.value.attributes) {
      editData[attr.id] = {
        source_table: attr.source_table || '',
        source_field: attr.source_field || '',
        data_status: attr.data_status || '未确认来源',
      }
    }
  }
  editMode.value = !editMode.value
}

async function handleSave() {
  if (!currentEntity.value) return
  saving.value = true
  try {
    const items = currentEntity.value.attributes.map(attr => ({
      attribute_id: attr.id,
      source_table: editData[attr.id]?.source_table || null,
      source_field: editData[attr.id]?.source_field || null,
      data_status: editData[attr.id]?.data_status || '未确认来源',
    }))
    await entityApi.updateAttributeMappings(currentEntity.value.id, items)
    currentEntity.value = await entityApi.detail(currentEntity.value.id)
    editMode.value = false
    message.success('映射保存成功')
  } catch {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  entities.value = await entityApi.list()
})
</script>

<style scoped>
.mp-page { display: flex; flex-direction: column; height: 100%; overflow: hidden; }
.mp-page__top { padding: 20px 24px 16px; border-bottom: 1px solid var(--neutral-200); flex-shrink: 0; }
.mp-page__header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.mp-page__title { font-size: 20px; font-weight: 700; color: var(--neutral-900); margin: 0; }
.mp-page__subtitle { font-size: var(--text-caption-size); color: var(--neutral-500); margin: 4px 0 0; }

.mp-page__stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.stat-card { display: flex; align-items: center; gap: 10px; padding: 12px 16px; background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); }
.stat-card__icon { font-size: 18px; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; border-radius: var(--radius-md); }
.stat-card--semantic .stat-card__icon { background: var(--semantic-50); color: var(--semantic-600); }
.stat-card--success .stat-card__icon { background: var(--status-success-bg); color: var(--status-success); }
.stat-card--warning .stat-card__icon { background: var(--status-warning-bg); color: var(--status-warning); }
.stat-card--muted .stat-card__icon { background: var(--neutral-100); color: var(--neutral-500); }

.mp-page__body { display: flex; flex: 1; overflow: hidden; }

/* 左侧实体列表 */
.mp-page__sidebar { width: 240px; min-width: 240px; border-right: 1px solid var(--neutral-200); display: flex; flex-direction: column; overflow: hidden; background: var(--neutral-0); }
.mp-sidebar__search { padding: 12px; border-bottom: 1px solid var(--neutral-100); flex-shrink: 0; }
.mp-sidebar__list { flex: 1; overflow-y: auto; padding: 8px 0; }
/* STYLE_PART2 */
.mp-sidebar__group { padding: 4px 0; }
.mp-sidebar__group-header { display: flex; align-items: center; gap: 6px; padding: 6px 12px; }
.mp-sidebar__group-label { font-size: var(--text-caption-size); font-weight: 600; color: var(--neutral-500); text-transform: uppercase; letter-spacing: 0.3px; }
.mp-sidebar__tier-badge { display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 18px; border-radius: var(--radius-sm); font-size: 11px; font-weight: 700; color: #fff; }
.tier-1 { background: var(--semantic-600); }
.tier-2 { background: var(--dynamic-500, #f59f00); }
.tier-3 { background: var(--kinetic-500, #20c997); }
.mp-sidebar__item { display: flex; justify-content: space-between; align-items: center; padding: 7px 12px 7px 16px; cursor: pointer; transition: background var(--transition-fast); font-size: var(--text-body-size); color: var(--neutral-700); }
.mp-sidebar__item:hover { background: var(--neutral-50); }
.mp-sidebar__item--active { background: var(--semantic-50); color: var(--semantic-700); border-right: 2px solid var(--semantic-500); }
.mp-sidebar__item-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mp-sidebar__item-count { font-size: 11px; color: var(--neutral-400); flex-shrink: 0; margin-left: 6px; }

/* 右侧主区域 */
.mp-page__main { flex: 1; overflow-y: auto; padding: 20px 24px; }
.mp-main__empty { display: flex; align-items: center; justify-content: center; height: 100%; }
.mp-main__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.mp-main__entity-info { display: flex; align-items: center; gap: 10px; }
.mp-main__entity-name { font-size: 18px; font-weight: 700; color: var(--neutral-900); margin: 0; }
.mp-main__entity-code { font-size: var(--text-code-size); color: var(--neutral-500); background: var(--neutral-50); padding: 2px 8px; border-radius: var(--radius-sm); }

/* 映射表格 */
.mp-main__table-wrap { overflow-x: auto; }
.mp-table { width: 100%; border-collapse: collapse; font-size: var(--text-body-size); }
.mp-table th { text-align: left; padding: 10px 12px; background: var(--neutral-50); border-bottom: 2px solid var(--neutral-200); font-weight: 600; font-size: var(--text-caption-size); color: var(--neutral-600); white-space: nowrap; }
.mp-table td { padding: 8px 12px; border-bottom: 1px solid var(--neutral-100); vertical-align: middle; }
.mp-table__row:hover { background: var(--neutral-25, #fafbfc); }
.mp-attr-name { font-size: var(--text-code-size); color: var(--semantic-700); }
.mp-required { color: var(--status-error); margin-left: 2px; font-size: 12px; }
.mp-source { font-size: var(--text-caption-size); color: var(--neutral-700); }
.mp-field { font-size: var(--text-code-size); color: var(--kinetic-600, #0ca678); background: var(--neutral-50); padding: 1px 6px; border-radius: var(--radius-sm); }
.mp-empty { color: var(--neutral-300); }
.mp-desc { font-size: var(--text-caption-size); color: var(--neutral-500); max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
