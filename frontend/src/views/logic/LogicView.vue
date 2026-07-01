<template>
  <div class="logic-page" :class="{ 'logic-page--embedded': embedded }">
    <BuilderReturnBanner kind-label="规则" />
    <div class="logic-page__header">
      <div v-if="!embedded">
        <h1 class="text-display">规则管理</h1>
        <p class="text-caption" style="margin-top: 4px;">业务规则配置与管理</p>
      </div>
      <div class="logic-page__actions">
        <button class="btn-primary" @click="showAdd = true">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 2v10M2 7h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          新建规则
        </button>
      </div>
    </div>

    <div class="logic-page__stats">
      <div class="stat-card stat-card--semantic">
        <div class="stat-card__value">{{ store.stats.total }}</div>
        <div class="stat-card__label">总规则数</div>
      </div>
      <div class="stat-card stat-card--dynamic">
        <div class="stat-card__value">{{ store.stats.active }}</div>
        <div class="stat-card__label">活跃规则</div>
      </div>
      <div class="stat-card stat-card--kinetic">
        <div class="stat-card__value">{{ store.stats.warning }}</div>
        <div class="stat-card__label">需关注</div>
      </div>
      <div class="stat-card stat-card--error">
        <div class="stat-card__value">{{ store.stats.disabled }}</div>
        <div class="stat-card__label">已禁用</div>
      </div>
    </div>

    <div class="master-detail">
      <div class="master-detail__list">
        <div class="master-detail__toolbar">
          <input v-model="search" class="logic-search" placeholder="搜索规则名称..." />
          <div class="logic-filter-tags">
            <button
              v-for="f in filters" :key="f.value"
              class="filter-tag"
              :class="{ 'filter-tag--active': activeFilter === f.value }"
              @click="activeFilter = f.value"
            >{{ f.label }}</button>
          </div>
        </div>

        <div class="master-detail__items">
          <div
            v-for="rule in filteredRules" :key="rule.id"
            class="list-item"
            :class="{ 'list-item--active': selectedId === rule.id }"
            @click="selectedId = rule.id"
          >
            <span class="list-item__status" :class="`list-item__status--${rule.status}`"></span>
            <span class="list-item__name">{{ rule.name }}</span>
            <span class="list-item__badge" :class="`priority--${rule.priority}`">{{ rule.priority === 'high' ? '高' : rule.priority === 'medium' ? '中' : '低' }}</span>
            <span class="list-item__meta">{{ rule.entity }}</span>
          </div>
          <div v-if="filteredRules.length === 0" class="logic-empty">
            <p class="text-caption">无匹配规则</p>
          </div>
        </div>
      </div>

      <div class="master-detail__detail">
        <template v-if="selectedRule">
          <div class="detail-panel__header">
            <h2 class="detail-panel__title">{{ selectedRule.name }}</h2>
            <span class="list-item__badge" :class="`priority--${selectedRule.priority}`">{{ selectedRule.priority === 'high' ? '高优先级' : selectedRule.priority === 'medium' ? '中优先级' : '低优先级' }}</span>
          </div>

          <div class="detail-panel__meta">
            <div class="detail-meta-item">
              <span class="detail-meta-label">状态</span>
              <span class="detail-meta-value">
                <span class="list-item__status" :class="`list-item__status--${selectedRule.status}`"></span>
                {{ selectedRule.status === 'active' ? '活跃' : selectedRule.status === 'warning' ? '需关注' : '已禁用' }}
              </span>
            </div>
            <div class="detail-meta-item">
              <span class="detail-meta-label">关联实体</span>
              <span class="detail-meta-value">{{ selectedRule.entity || '—' }}</span>
            </div>
            <div class="detail-meta-item">
              <span class="detail-meta-label">触发次数</span>
              <span class="detail-meta-value">{{ selectedRule.triggerCount }} 次（近30天）</span>
            </div>
            <div class="detail-meta-item">
              <span class="detail-meta-label">最后触发</span>
              <span class="detail-meta-value">{{ selectedRule.lastTriggered }}</span>
            </div>
          </div>

          <div class="detail-panel__section">
            <h3 class="detail-section-title">触发条件</h3>
            <code class="detail-code-block">{{ selectedRule.condition || '—' }}</code>
          </div>

          <div class="detail-panel__section">
            <h3 class="detail-section-title">执行动作</h3>
            <p class="detail-section-text">{{ selectedRule.action || '—' }}</p>
          </div>

          <div class="detail-panel__actions">
            <button class="btn-sm-exec" @click="handleExecute(selectedRule.id)">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M3 1.5l7 4.5-7 4.5V1.5z" fill="currentColor"/></svg>
              执行
            </button>
            <button class="btn-sm-edit" @click="openEdit(selectedRule)">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M9 1l2 2-6 6H3V7l6-6z" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
              编辑
            </button>
            <button class="btn-sm-del" @click="handleDelete(selectedRule.id, selectedRule.name)">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2 3h8M4 3V2h4v1M3 3v7h6V3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
              删除
            </button>
          </div>
        </template>
        <div v-else class="detail-panel__empty">
          <p class="text-caption">选择一条规则查看详情</p>
        </div>
      </div>
    </div>

    <RuleBuilderDrawer
      :visible="showAdd || showEdit"
      :edit-id="editingRuleId"
      :locked-entity-id="prefill.entityId || undefined"
      @close="showAdd = false; showEdit = false; editingRuleId = undefined"
      @saved="onRuleSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRulesStore } from '../../store/rules'
import RuleBuilderDrawer from '../../components/logic/RuleBuilderDrawer.vue'
import BuilderReturnBanner from '../../components/common/BuilderReturnBanner.vue'
import { ruleApi } from '../../api/rules'
import { useToast } from '../../composables/useToast'

defineProps<{ embedded?: boolean }>()

const store = useRulesStore()
const toast = useToast()
const route = useRoute()
const router = useRouter()
const selectedId = ref<string | null>(null)
const showAdd = ref(false)
const showEdit = ref(false)
const editingRuleId = ref<string | undefined>()

const prefill = reactive({ name: '', condition: '', action: '', entityId: '' })

const selectedRule = computed(() => filteredRules.value.find(r => r.id === selectedId.value) || null)

function onRuleSaved(rule: { id: string; name: string }) {
  showAdd.value = false
  showEdit.value = false
  editingRuleId.value = undefined
  store.fetchRules()
  if (route.query.from === 'builder') {
    const sid = route.query.session_id as string
    const oid = route.query.object_id as string
    if (sid && oid) {
      router.push({ path: '/builder', query: { session_id: sid, attach_to: oid, new_id: rule.id, kind: 'rule' } })
    }
  }
}

function openEdit(rule: { id: string }) {
  editingRuleId.value = rule.id
  showEdit.value = true
}

async function handleDelete(id: string, name: string) {
  if (!confirm(`确定删除规则 "${name}"？`)) return
  try {
    await ruleApi.remove(id)
    toast.success('规则已删除')
    if (selectedId.value === id) selectedId.value = null
    store.fetchRules()
  } catch (e) { toast.error(`删除失败: ${(e as Error).message}`) }
}

async function handleExecute(id: string) {
  const result = await store.executeRule(id)
  if (result) {
    toast.success(result.message)
    store.fetchRules()
  }
}

onMounted(() => {
  store.fetchRules()
  if (route.query.from === 'builder') {
    prefill.name = (route.query.prefill_name || '') as string
    prefill.condition = (route.query.prefill_condition || '') as string
    prefill.action = (route.query.prefill_action || '') as string
    prefill.entityId = (route.query.object_id || '') as string
    showAdd.value = true
  }
})

const search = computed({
  get: () => store.filter.search,
  set: (v: string) => { store.filter.search = v },
})
const activeFilter = computed({
  get: () => store.filter.status,
  set: (v: string) => { store.filter.status = v as 'all' | 'active' | 'warning' | 'disabled' },
})

const filters = [
  { label: '全部', value: 'all' },
  { label: '活跃', value: 'active' },
  { label: '需关注', value: 'warning' },
  { label: '已禁用', value: 'disabled' },
]

const filteredRules = computed(() =>
  store.filtered.map(r => ({
    id: r.id,
    name: r.name,
    entity: r.entityName,
    condition: r.condition,
    action: r.action,
    status: r.status as 'active' | 'warning' | 'disabled',
    priority: r.priority as 'high' | 'medium' | 'low',
    triggerCount: r.triggerCount,
    lastTriggered: r.lastTriggered || '—',
  }))
)
</script>

<style scoped>
@import './logic-shared.css';

.logic-page--embedded { padding: 0; max-width: none; }
.logic-page--embedded .logic-page__header { margin-bottom: 16px; justify-content: flex-end; }

.master-detail {
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 1px;
  background: var(--neutral-200, #e5e5e5);
  border: 1px solid var(--neutral-200, #e5e5e5);
  border-radius: var(--radius-lg, 12px);
  overflow: hidden;
  min-height: 480px;
}

.master-detail__list {
  background: var(--neutral-0, #fff);
  display: flex;
  flex-direction: column;
}

.master-detail__toolbar {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  border-bottom: 1px solid var(--neutral-100, #f0f0f0);
}

.master-detail__toolbar .logic-search {
  width: 100%;
  box-sizing: border-box;
}

.master-detail__items {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.list-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: var(--radius-md, 8px);
  cursor: pointer;
  transition: background 0.15s;
}

.list-item:hover {
  background: var(--neutral-50, #fafafa);
}

.list-item--active {
  background: var(--semantic-50, #eef2ff);
  border: 1px solid var(--semantic-200, #c7d2fe);
}

.list-item__status {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.list-item__status--active { background: var(--status-success, #22c55e); }
.list-item__status--warning { background: var(--status-warning, #f59e0b); }
.list-item__status--disabled { background: var(--neutral-300, #d4d4d4); }

.list-item__name {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.list-item__badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  flex-shrink: 0;
}

.list-item__meta {
  font-size: 11px;
  color: var(--neutral-500, #888);
  flex-shrink: 0;
  max-width: 60px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.master-detail__detail {
  background: var(--neutral-0, #fff);
  padding: 24px;
  overflow-y: auto;
}

.detail-panel__header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.detail-panel__title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.detail-panel__meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 24px;
  padding: 16px;
  background: var(--neutral-50, #fafafa);
  border-radius: var(--radius-md, 8px);
}

.detail-meta-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.detail-meta-label {
  font-size: 11px;
  color: var(--neutral-500, #888);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.detail-meta-value {
  font-size: 13px;
  font-weight: 500;
  color: var(--neutral-800, #333);
  display: flex;
  align-items: center;
  gap: 6px;
}

.detail-panel__section {
  margin-bottom: 20px;
}

.detail-section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--neutral-500, #888);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin: 0 0 8px;
}

.detail-code-block {
  display: block;
  padding: 12px 16px;
  background: var(--neutral-50, #fafafa);
  border: 1px solid var(--neutral-100, #f0f0f0);
  border-radius: var(--radius-md, 8px);
  font-family: var(--font-mono, monospace);
  font-size: 12px;
  color: var(--neutral-700, #495057);
  white-space: pre-wrap;
  word-break: break-all;
}

.detail-section-text {
  font-size: 13px;
  color: var(--neutral-700, #495057);
  margin: 0;
}

.detail-panel__actions {
  display: flex;
  gap: 8px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--neutral-100, #f0f0f0);
}

.detail-panel__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--neutral-400, #aaa);
}
</style>
