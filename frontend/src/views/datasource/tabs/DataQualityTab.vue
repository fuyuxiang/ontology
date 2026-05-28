<template>
  <div class="ql-tab">
    <!-- 顶部：健康度总览 -->
    <div class="ql-overview">
      <div class="ql-overview__stat ql-stat--healthy">
        <div class="ql-overview__num">{{ statBy('healthy') }}</div>
        <div class="ql-overview__label">健康</div>
      </div>
      <div class="ql-overview__stat ql-stat--warning">
        <div class="ql-overview__num">{{ statBy('warning') }}</div>
        <div class="ql-overview__label">告警</div>
      </div>
      <div class="ql-overview__stat ql-stat--failure">
        <div class="ql-overview__num">{{ statBy('failure') }}</div>
        <div class="ql-overview__label">失败</div>
      </div>
      <div class="ql-overview__stat ql-stat--unknown">
        <div class="ql-overview__num">{{ statBy('unknown') }}</div>
        <div class="ql-overview__label">未知</div>
      </div>
      <span class="ql-spacer" />
      <a-button :loading="evaluatingAll" @click="evaluateAll">
        <template #icon><SyncOutlined /></template>评估全部
      </a-button>
      <a-button type="primary" @click="openAssetPicker">
        <template #icon><PlusOutlined /></template>给资产挂规则
      </a-button>
    </div>

    <!-- 资产健康度卡片网格 -->
    <div class="ql-card">
      <div class="ql-card__title">受治理资产 ({{ overview.length }})</div>
      <a-empty v-if="overview.length === 0"
               description="尚未给任何资产挂规则。点「给资产挂规则」开始策展" style="padding:48px 0" />
      <a-row v-else :gutter="[12, 12]">
        <a-col v-for="row in overview" :key="row.asset_id" :xs="24" :sm="12" :md="8" :lg="6">
          <div class="ql-asset-card" :class="`ql-asset-card--${row.status}`"
               @click="openAsset(row.asset_id)">
            <div class="ql-asset-card__head">
              <span class="ql-asset-card__name">{{ row.asset_name }}</span>
              <a-tag :color="statusColor(row.status)">{{ statusLabel(row.status) }}</a-tag>
            </div>
            <div class="ql-asset-card__meta">
              <span class="ql-muted">{{ row.asset_kind }}</span>
              <span v-if="row.domain" class="ql-muted">· {{ row.domain }}</span>
            </div>
            <div class="ql-asset-card__bar">
              <span v-if="row.by_status.failure" class="ql-pill ql-pill--failure">失败 {{ row.by_status.failure }}</span>
              <span v-if="row.by_status.warning" class="ql-pill ql-pill--warning">告警 {{ row.by_status.warning }}</span>
              <span v-if="row.by_status.healthy" class="ql-pill ql-pill--healthy">健康 {{ row.by_status.healthy }}</span>
              <span v-if="row.by_status.unknown" class="ql-pill ql-pill--unknown">未知 {{ row.by_status.unknown }}</span>
            </div>
            <div class="ql-asset-card__count">{{ row.rule_count }} 条规则</div>
          </div>
        </a-col>
      </a-row>
    </div>

    <!-- 资产详情抽屉 -->
    <a-drawer v-model:open="detail.open" :title="detailTitle" width="720" destroy-on-close>
      <div v-if="detail.data" class="ql-detail">
        <div class="ql-detail__head">
          <div>
            <span class="ql-muted">聚合状态：</span>
            <a-tag :color="statusColor(detail.data.aggregate.status)">{{ statusLabel(detail.data.aggregate.status) }}</a-tag>
            <span class="ql-muted" style="margin-left:12px">{{ detail.data.aggregate.rule_count }} 条规则</span>
          </div>
          <a-space>
            <a-button :loading="detail.evaluating" @click="evaluateAsset">评估全部</a-button>
            <a-button type="primary" @click="openCreateRule">新增规则</a-button>
          </a-space>
        </div>

        <a-empty v-if="detail.data.rules.length === 0" description="该资产还没有规则" style="padding:48px 0" />
        <div v-else class="ql-rules">
          <div v-for="rs in detail.data.rules" :key="rs.rule.id" class="ql-rule">
            <div class="ql-rule__head">
              <a-tag :color="statusColor(rs.latest?.status || 'unknown')">
                {{ statusLabel(rs.latest?.status || 'unknown') }}
              </a-tag>
              <span class="ql-rule__name">{{ rs.rule.name }}</span>
              <a-tag color="default">{{ rs.rule.kind }}</a-tag>
              <a-tag v-if="rs.rule.column_name" color="blue">{{ rs.rule.column_name }}</a-tag>
              <a-tag :color="rs.rule.severity === 'failure' ? 'red' : 'orange'">
                触发=「{{ rs.rule.severity === 'failure' ? '失败' : '告警' }}」
              </a-tag>
              <span class="ql-spacer" />
              <a-switch :checked="rs.rule.enabled" size="small" @change="(v: any) => toggleRule(rs.rule.id, !!v)" />
              <a-button type="link" size="small" @click="evaluateRule(rs.rule.id)">立即评估</a-button>
              <a-popconfirm :title="`删除规则「${rs.rule.name}」？`" @confirm="deleteRule(rs.rule.id)">
                <a-button type="link" size="small" danger>删除</a-button>
              </a-popconfirm>
            </div>
            <div class="ql-rule__body">
              <span class="ql-muted">阈值：</span>
              <code>{{ JSON.stringify(rs.rule.params) }}</code>
              <span v-if="rs.latest" style="margin-left:16px">
                <span class="ql-muted">最新值：</span>
                <code>{{ rs.latest.value_numeric ?? '—' }}</code>
                <span class="ql-muted" style="margin-left:8px">{{ formatTime(rs.latest.ran_at) }}</span>
              </span>
            </div>
            <div v-if="rs.latest?.message" class="ql-rule__msg">{{ rs.latest.message }}</div>
          </div>
        </div>
      </div>
    </a-drawer>

    <!-- 新建规则抽屉 -->
    <a-drawer v-model:open="creator.open" title="新增规则" width="520" destroy-on-close>
      <a-form layout="vertical">
        <a-form-item label="资产 *">
          <a-select v-model:value="creator.asset_id" :options="assetOptions" :disabled="!!creator.lockedAssetId"
                    show-search :filter-option="filterOption" placeholder="选择要挂规则的资产" />
        </a-form-item>
        <a-form-item label="规则类型 *">
          <a-select v-model:value="creator.kind" :options="kindOptions" @change="onKindChange" />
        </a-form-item>
        <a-form-item label="规则名称 *">
          <a-input v-model:value="creator.name" :placeholder="creator.kind || '示例：行数 ≥ 1'" />
        </a-form-item>
        <a-form-item v-if="kindNeedsColumn" label="列名 *">
          <a-input v-model:value="creator.column_name" placeholder="user_id" />
        </a-form-item>
        <a-form-item v-if="kindNeedsThreshold" :label="thresholdLabel">
          <a-input-number v-model:value="creator.threshold" style="width:100%" :placeholder="String(creator.threshold ?? '')" />
        </a-form-item>
        <a-form-item label="触发级别">
          <a-segmented v-model:value="creator.severity"
                       :options="[{label:'告警',value:'warning'},{label:'失败',value:'failure'}]" />
        </a-form-item>
        <a-form-item label="说明">
          <a-textarea v-model:value="creator.description" :rows="2" />
        </a-form-item>
        <a-button type="primary" :loading="creator.saving" @click="saveRule">保存</a-button>
      </a-form>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  Button as AButton, Col as ACol, Drawer as ADrawer, Empty as AEmpty,
  Form as AForm, FormItem as AFormItem, Input as AInput, InputNumber as AInputNumber,
  Popconfirm as APopconfirm, Row as ARow, Segmented as ASegmented,
  Select as ASelect, Space as ASpace, Switch as ASwitch, Tag as ATag,
  Textarea as ATextarea, message,
} from 'ant-design-vue'
import { PlusOutlined, SyncOutlined } from '@ant-design/icons-vue'
import {
  qualityApi, type AssetHealth, type AssetHealthDetail,
  type HealthStatusValue, type RuleKind,
} from '../../../api/quality'
import { listAssets } from '../../../api/asset'
import type { Asset } from '../../../types/asset'

const overview = ref<AssetHealth[]>([])
const evaluatingAll = ref(false)
const allAssets = ref<Asset[]>([])

const detail = reactive<{
  open: boolean
  assetId: string
  data: AssetHealthDetail | null
  evaluating: boolean
}>({ open: false, assetId: '', data: null, evaluating: false })

const creator = reactive<{
  open: boolean
  saving: boolean
  asset_id: string
  lockedAssetId: string  // 从详情进入时锁定，从顶部进入时为空
  name: string
  kind: RuleKind
  column_name: string
  threshold: number | undefined
  severity: 'warning' | 'failure'
  description: string
}>({
  open: false, saving: false, asset_id: '', lockedAssetId: '',
  name: '', kind: 'row_count_min', column_name: '', threshold: 1,
  severity: 'warning', description: '',
})

const detailTitle = computed(() => {
  if (!detail.data) return '资产详情'
  return `${detail.data.asset.alias || detail.data.asset.name} · 健康度`
})

const kindOptions: { label: string; value: RuleKind }[] = [
  { label: '行数下限 (row_count_min)', value: 'row_count_min' },
  { label: '行数上限 (row_count_max)', value: 'row_count_max' },
  { label: '空值率上限 (null_ratio_max)', value: 'null_ratio_max' },
  { label: '主键唯一 (pk_uniqueness)', value: 'pk_uniqueness' },
  { label: 'Schema 稳定 (schema_stable)', value: 'schema_stable' },
  { label: '新鲜度 (freshness)', value: 'freshness' },
]

const kindNeedsColumn = computed(() =>
  ['null_ratio_max', 'pk_uniqueness', 'freshness'].includes(creator.kind))

const kindNeedsThreshold = computed(() =>
  ['row_count_min', 'row_count_max', 'null_ratio_max', 'freshness'].includes(creator.kind))

const thresholdLabel = computed(() => ({
  row_count_min: '最小行数',
  row_count_max: '最大行数',
  null_ratio_max: '空值率上限（0~1）',
  freshness: '最大停滞秒数',
} as Record<string, string>)[creator.kind] || '阈值')

const assetOptions = computed(() =>
  allAssets.value
    .filter(a => a.kind !== 'document')
    .map(a => ({ label: `${a.alias || a.name} (${a.kind})`, value: a.id })))

const filterOption = (input: string, option: any) =>
  ((option?.label || '') as string).toLowerCase().includes(input.toLowerCase())

function statBy(s: HealthStatusValue) {
  return overview.value.filter(r => r.status === s).length
}
function statusColor(s: HealthStatusValue) {
  return ({ healthy: 'green', warning: 'orange', failure: 'red', unknown: 'default' } as any)[s]
}
function statusLabel(s: HealthStatusValue) {
  return ({ healthy: '健康', warning: '告警', failure: '失败', unknown: '未知' } as any)[s]
}
function formatTime(s: string) {
  return new Date(s).toLocaleString()
}

async function load() {
  overview.value = await qualityApi.overview()
}

async function loadAssets() {
  if (allAssets.value.length === 0) {
    allAssets.value = await listAssets()
  }
}

async function openAsset(assetId: string) {
  detail.assetId = assetId
  detail.open = true
  detail.data = null
  detail.data = await qualityApi.assetHealth(assetId)
}

async function refreshDetail() {
  if (detail.assetId) detail.data = await qualityApi.assetHealth(detail.assetId)
  await load()
}

async function evaluateAll() {
  evaluatingAll.value = true
  try {
    // 逐个资产并发评估
    await Promise.all(overview.value.map(r => qualityApi.evaluateAsset(r.asset_id)))
    message.success('已评估全部')
    await load()
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  } finally { evaluatingAll.value = false }
}

async function evaluateAsset() {
  detail.evaluating = true
  try {
    await qualityApi.evaluateAsset(detail.assetId)
    await refreshDetail()
    message.success('已评估')
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  } finally { detail.evaluating = false }
}

async function evaluateRule(ruleId: string) {
  try {
    await qualityApi.evaluateRule(ruleId)
    await refreshDetail()
    message.success('已评估')
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  }
}

async function toggleRule(ruleId: string, enabled: boolean) {
  try {
    await qualityApi.updateRule(ruleId, { enabled })
    await refreshDetail()
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  }
}

async function deleteRule(ruleId: string) {
  try {
    await qualityApi.deleteRule(ruleId)
    await refreshDetail()
    message.success('已删除')
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  }
}

async function openAssetPicker() {
  await loadAssets()
  Object.assign(creator, {
    open: true, saving: false, asset_id: '', lockedAssetId: '',
    name: '', kind: 'row_count_min', column_name: '', threshold: 1,
    severity: 'warning', description: '',
  })
}

async function openCreateRule() {
  await loadAssets()
  Object.assign(creator, {
    open: true, saving: false,
    asset_id: detail.assetId, lockedAssetId: detail.assetId,
    name: '', kind: 'row_count_min', column_name: '', threshold: 1,
    severity: 'warning', description: '',
  })
}

function onKindChange() {
  const def: Record<string, number | undefined> = {
    row_count_min: 1, row_count_max: 10000000,
    null_ratio_max: 0.05, freshness: 86400,
    pk_uniqueness: undefined, schema_stable: undefined,
  }
  creator.threshold = def[creator.kind]
}

async function saveRule() {
  if (!creator.asset_id) { message.error('请选择资产'); return }
  if (!creator.name) { message.error('请填写规则名'); return }
  if (kindNeedsColumn.value && !creator.column_name) {
    message.error('该规则需要列名'); return
  }
  const params: Record<string, unknown> = {}
  if (creator.kind === 'row_count_min') params.min = creator.threshold
  else if (creator.kind === 'row_count_max') params.max = creator.threshold
  else if (creator.kind === 'null_ratio_max') params.max = creator.threshold
  else if (creator.kind === 'freshness') params.max_age_seconds = creator.threshold
  creator.saving = true
  try {
    await qualityApi.createRule({
      asset_id: creator.asset_id, name: creator.name, kind: creator.kind,
      column_name: kindNeedsColumn.value ? creator.column_name : null,
      params, severity: creator.severity, description: creator.description || null,
    })
    message.success('已新建规则')
    creator.open = false
    if (detail.open) await refreshDetail()
    else await load()
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  } finally { creator.saving = false }
}

onMounted(load)
</script>

<style scoped>
.ql-tab { display: flex; flex-direction: column; gap: 12px; }
.ql-card {
  background: #fff; border: 1px solid var(--neutral-200, #e5e7eb);
  border-radius: 8px; padding: 16px;
}
.ql-card__title { font-weight: 600; font-size: 14px; color: var(--neutral-900, #111827); margin-bottom: 12px; }
.ql-muted { color: var(--neutral-500, #6b7280); font-size: 12px; }
.ql-spacer { flex: 1; }

.ql-overview {
  display: flex; align-items: center; gap: 24px; padding: 16px;
  background: #fff; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.ql-overview__stat { text-align: left; }
.ql-overview__num { font-size: 26px; font-weight: 600; line-height: 1.2; }
.ql-overview__label { font-size: 12px; color: var(--neutral-500); margin-top: 2px; }
.ql-stat--healthy .ql-overview__num { color: #10b981; }
.ql-stat--warning .ql-overview__num { color: #f59e0b; }
.ql-stat--failure .ql-overview__num { color: #ef4444; }
.ql-stat--unknown .ql-overview__num { color: #6b7280; }

.ql-asset-card {
  background: #fff; border: 1px solid #e5e7eb; border-radius: 10px;
  padding: 14px; cursor: pointer;
  transition: all 0.15s; height: 100%;
  border-left: 4px solid #d1d5db;
}
.ql-asset-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.06); transform: translateY(-1px); }
.ql-asset-card--healthy { border-left-color: #10b981; }
.ql-asset-card--warning { border-left-color: #f59e0b; }
.ql-asset-card--failure { border-left-color: #ef4444; }
.ql-asset-card--unknown { border-left-color: #9ca3af; }

.ql-asset-card__head {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  margin-bottom: 4px;
}
.ql-asset-card__name {
  font-weight: 600; font-size: 13px; color: #111827;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1;
}
.ql-asset-card__meta { font-size: 11px; color: #6b7280; margin-bottom: 8px; }
.ql-asset-card__meta > span + span { margin-left: 4px; }
.ql-asset-card__bar { display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 8px; }
.ql-asset-card__count { font-size: 11px; color: #9ca3af; }

.ql-pill {
  font-size: 10px; padding: 1px 6px; border-radius: 4px; font-weight: 500;
}
.ql-pill--healthy { background: #d1fae5; color: #065f46; }
.ql-pill--warning { background: #fef3c7; color: #92400e; }
.ql-pill--failure { background: #fee2e2; color: #991b1b; }
.ql-pill--unknown { background: #f3f4f6; color: #4b5563; }

.ql-detail__head {
  display: flex; align-items: center; justify-content: space-between;
  padding-bottom: 12px; border-bottom: 1px solid #e5e7eb; margin-bottom: 12px;
}
.ql-rules { display: flex; flex-direction: column; gap: 10px; }
.ql-rule { border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px 14px; }
.ql-rule__head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.ql-rule__name { font-weight: 600; font-size: 13px; }
.ql-rule__body { margin-top: 6px; font-size: 12px; color: #4b5563; }
.ql-rule__body code { background: #f3f4f6; padding: 1px 4px; border-radius: 3px; font-size: 11px; }
.ql-rule__msg { margin-top: 4px; font-size: 12px; color: #ef4444; }
</style>
