<template>
  <div class="step2">
    <header class="step2-topbar">
      <button class="ob-back-btn" @click="$emit('prev')">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M9 11L5 7l4-4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        返回
      </button>
      <div class="step2-topbar__title">本体走测 · 专家审批</div>
      <div class="step2-topbar__progress">
        <span>已通过 {{ approvedCount }} / {{ classes.length }}</span>
        <div class="step2-progress-bar">
          <div class="step2-progress-fill" :style="{ width: progressPct + '%' }"></div>
        </div>
      </div>
      <button class="step2-btn step2-btn--ghost" @click="approveAll">✅ 一键全部通过</button>
      <button class="step2-btn step2-btn--primary" :disabled="approvedCount < classes.length" @click="finishReview">完成走测</button>
    </header>

    <div v-if="!hasPermission" class="step2-no-perm">
      <span>当前角色（场景策划）无审批权限，请联系分析师或管理员</span>
      <button class="step2-no-perm__btn" @click="hasPermission = true">以管理员身份继续</button>
    </div>

    <div class="step2-body">
      <!-- 左侧：本体清单 -->
      <aside class="step2-left">
        <div class="step2-section-title">本体对象 · {{ classes.length }}</div>
        <div class="step2-class-list">
          <div
            v-for="c in classes"
            :key="c.id"
            class="step2-class-row"
            :class="{
              'step2-class-row--active': selectedId === c.id,
              'step2-class-row--approved': c.approved,
            }"
            @click="selectedId = c.id"
          >
            <div class="step2-class-row__icon" :class="`step2-class-row__icon--t${c.tier}`">{{ c.icon }}</div>
            <div class="step2-class-row__main">
              <div class="step2-class-row__name">{{ c.displayName }}</div>
              <div class="step2-class-row__en">{{ c.name }} · T{{ c.tier }}</div>
            </div>
            <span v-if="c.approved" class="step2-check-icon">✓</span>
          </div>
        </div>
      </aside>

      <!-- 中央：网络视图 -->
      <main class="step2-mid">
        <div class="step2-mid__head">
          <div class="step2-mid__title">本体视图区</div>
          <div class="step2-mid__hint">点击本体在右侧编辑；新增关系时依次点击起点和终点</div>
          <button
            class="step2-relation-toggle"
            :class="{ active: relationMode.active }"
            @click="toggleRelationMode"
          >
            {{ relationMode.active ? '退出连线' : '+ 新增关系' }}
          </button>
        </div>
        <div class="step2-mid__canvas">
          <SemanticCanvas
            :objects="classes"
            :relations="relations"
            :phase="'graph_done'"
            :editable="false"
            @add="onAddClass"
            @delete="onDeleteClass"
          />
        </div>
      </main>

      <!-- 右侧：编辑器 -->
      <aside class="step2-right">
        <!-- 本体编辑卡 -->
        <div v-if="selected" class="step2-editor-card">
          <div class="step2-editor-card__head">
            <div class="step2-editor-card__title">本体编辑</div>
            <span class="step2-status-badge" :class="{ approved: selected.approved }">
              {{ selected.approved ? '已通过' : '待确认' }}
            </span>
          </div>
          <div class="step2-form">
            <div class="step2-form__row">
              <label>本体名称</label>
              <a-input v-model:value="selected.displayName" size="middle" @change="syncStore" />
            </div>
            <div class="step2-form__row">
              <label>英文名 (API)</label>
              <a-input v-model:value="selected.name" size="middle" @change="syncStore" />
            </div>
            <div class="step2-form__row">
              <label>层级</label>
              <a-select v-model:value="selected.tier" :options="tierOptions" @change="syncStore" />
            </div>
            <div class="step2-form__meta">
              <span>关系：{{ relationCountFor(selected.id) }} 条</span>
              <span>属性：{{ selected.properties.length }} 个</span>
            </div>
          </div>

          <div class="step2-prop-title">属性表</div>
          <div class="step2-prop-list">
            <div v-for="p in selected.properties" :key="p.id" class="step2-editor-prop">
              <a-input v-model:value="p.name" size="small" placeholder="属性名" @change="syncStore" />
              <a-select v-model:value="p.type" size="small" :options="typeOptions" @change="syncStore" />
              <button class="step2-icon-btn step2-icon-btn--danger" @click="removeProp(p.id)">×</button>
            </div>
            <button class="step2-add-prop" @click="addProp">+ 增加属性</button>
          </div>

          <button
            class="step2-editor-approve"
            :disabled="selected.approved"
            @click="approveSelected"
          >
            {{ selected.approved ? '✓ 已通过' : '确认通过' }}
          </button>
        </div>

        <!-- 关系新增卡 -->
        <div class="step2-editor-card step2-relation-card">
          <div class="step2-editor-card__head">
            <div class="step2-editor-card__title">关系新增</div>
            <span class="step2-status-badge" :class="{ active: relationMode.active }">
              {{ relationMode.active ? '连线中' : '待启动' }}
            </span>
          </div>
          <div class="step2-form">
            <div class="step2-form__row">
              <label>起点本体</label>
              <a-select
                v-model:value="relationMode.from"
                placeholder="选择起点"
                size="middle"
                :options="classOptions"
              />
            </div>
            <div class="step2-form__row">
              <label>终点本体</label>
              <a-select
                v-model:value="relationMode.to"
                placeholder="选择终点"
                size="middle"
                :options="classOptions"
              />
            </div>
            <div class="step2-form__row">
              <label>关系名称</label>
              <a-input v-model:value="relationMode.label" placeholder="例如：持有合约" size="middle" />
            </div>
            <div class="step2-form__row">
              <label>基数</label>
              <a-select v-model:value="relationMode.cardinality" size="middle" :options="cardOptions" />
            </div>
          </div>
          <button
            class="step2-editor-approve"
            :disabled="!canSaveRelation"
            @click="saveRelation"
          >保存关系</button>

          <div v-if="relations.length" class="step2-relations-list">
            <div class="step2-prop-title">已有关系</div>
            <div v-for="r in relations" :key="r.id" class="step2-relation-row">
              <span class="step2-relation-from">{{ classNameOf(r.source) }}</span>
              <span class="step2-relation-arrow">→</span>
              <span class="step2-relation-to">{{ classNameOf(r.target) }}</span>
              <span class="step2-relation-label">{{ r.displayName }}</span>
              <button class="step2-icon-btn step2-icon-btn--danger" @click="removeRelation(r.id)">×</button>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useBuilderStore } from '../../../store/builder'
import type { BuilderSession } from '../../../types/builder'
import SemanticCanvas from './graph/SemanticCanvas.vue'

const props = defineProps<{ session: BuilderSession }>()
const emit = defineEmits<{ (e: 'prev'): void; (e: 'next'): void }>()
const store = useBuilderStore()

const hasPermission = ref(true)
const selectedId = ref<string | null>(props.session.ontologyClasses[0]?.id || null)
const classes = ref([...props.session.ontologyClasses])
const relations = ref([...props.session.ontologyRelations])

const relationMode = reactive<{
  active: boolean
  from?: string
  to?: string
  label: string
  cardinality: '1:1' | '1:N' | 'N:N'
}>({
  active: false,
  label: '',
  cardinality: '1:N',
})

const tierOptions = [
  { label: 'Tier 1 核心', value: 1 },
  { label: 'Tier 2 领域', value: 2 },
  { label: 'Tier 3 场景', value: 3 },
]
const typeOptions = [
  { label: '字符串', value: 'string' },
  { label: '数值', value: 'number' },
  { label: '日期', value: 'date' },
  { label: '布尔', value: 'boolean' },
  { label: '枚举', value: 'enum' },
]
const cardOptions = [
  { label: '1:1', value: '1:1' },
  { label: '1:N', value: '1:N' },
  { label: 'N:N', value: 'N:N' },
]

const selected = computed(() => classes.value.find(c => c.id === selectedId.value))
const approvedCount = computed(() => classes.value.filter(c => c.approved).length)
const progressPct = computed(() => classes.value.length ? (approvedCount.value / classes.value.length) * 100 : 0)
const classOptions = computed(() => classes.value.map(c => ({
  label: `${c.displayName}（${c.name}）`,
  value: c.id,
})))
const canSaveRelation = computed(() =>
  relationMode.from && relationMode.to && relationMode.label.trim() && relationMode.from !== relationMode.to,
)

function classNameOf(id: string) {
  return classes.value.find(c => c.id === id)?.displayName || id
}
function relationCountFor(id: string) {
  return relations.value.filter(r => r.source === id || r.target === id).length
}

function syncStore() {
  store.patchActive({
    ontologyClasses: [...classes.value],
    ontologyRelations: [...relations.value],
  })
}

function toggleRelationMode() {
  relationMode.active = !relationMode.active
  if (!relationMode.active) {
    relationMode.from = undefined
    relationMode.to = undefined
    relationMode.label = ''
  }
}

function approveSelected() {
  if (!selected.value) return
  selected.value.approved = true
  syncStore()
  // 自动跳到下一个未通过对象
  const next = classes.value.find(c => !c.approved)
  if (next) selectedId.value = next.id
}

function approveAll() {
  classes.value = classes.value.map(c => ({ ...c, approved: true }))
  syncStore()
  message.success('已一键通过全部对象')
}

function addProp() {
  if (!selected.value) return
  selected.value.properties.push({
    id: 'p-' + Date.now(),
    name: 'newField',
    displayName: '新属性',
    type: 'string',
    required: false,
  })
  syncStore()
}
function removeProp(id: string) {
  if (!selected.value) return
  selected.value.properties = selected.value.properties.filter(p => p.id !== id)
  syncStore()
}

function onAddClass() {
  const cls = {
    id: 'cls-' + Date.now().toString(36),
    name: 'NewClass' + (classes.value.length + 1),
    displayName: '新对象',
    tier: 2 as const,
    description: '',
    primaryKey: 'id',
    icon: '🆕',
    instanceCount: 0,
    properties: [{ id: 'p-' + Date.now(), name: 'id', displayName: '主键', type: 'string', required: true }],
    rules: [],
    actions: [],
    approved: false,
  }
  classes.value.push(cls)
  syncStore()
}
function onDeleteClass(id: string) {
  classes.value = classes.value.filter(c => c.id !== id)
  relations.value = relations.value.filter(r => r.source !== id && r.target !== id)
  if (selectedId.value === id) selectedId.value = classes.value[0]?.id || null
  syncStore()
}

function saveRelation() {
  if (!canSaveRelation.value) return
  relations.value.push({
    id: 'rel-' + Date.now().toString(36),
    name: relationMode.label.trim().replace(/\s+/g, '_'),
    displayName: relationMode.label.trim(),
    source: relationMode.from!,
    target: relationMode.to!,
    cardinality: relationMode.cardinality,
    description: relationMode.label.trim(),
    relationType: 'ObjectProperty',
    semanticType: 'association',
  })
  relationMode.from = undefined
  relationMode.to = undefined
  relationMode.label = ''
  relationMode.active = false
  syncStore()
  message.success('已保存关系')
}
function removeRelation(id: string) {
  relations.value = relations.value.filter(r => r.id !== id)
  syncStore()
}

function finishReview() {
  if (approvedCount.value < classes.value.length) {
    message.warning('请将所有对象审批通过后再完成走测')
    return
  }
  store.patchActive({
    ontologyClasses: classes.value,
    ontologyRelations: relations.value,
    status: 'pending_hydration',
    approvedScenarios: classes.value.map(c => c.id),
    reviewLog: [
      {
        storyId: 'review-all',
        storyName: '全部走测节点',
        action: 'approved',
        reviewer: localStorage.getItem('username') || '当前用户',
        reviewedAt: new Date().toISOString(),
        comment: '走测节点全部通过',
      },
    ],
  })
  message.success('走测完成，进入水合演练')
  emit('next')
}

watch(() => props.session.sessionId, () => {
  classes.value = [...props.session.ontologyClasses]
  relations.value = [...props.session.ontologyRelations]
  selectedId.value = classes.value[0]?.id || null
})
</script>

<style scoped>
.step2 {
  display: flex; flex-direction: column;
  height: calc(100vh - 64px - 56px - 76px);
  background: #f1f5f9;
}

.step2-topbar {
  display: flex; align-items: center; gap: 16px;
  padding: 12px 20px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
}
.step2-topbar__title { font-size: 14px; font-weight: 600; color: #0f172a; }
.step2-topbar__progress {
  display: flex; align-items: center; gap: 10px; flex: 1;
  font-size: 12px; color: #64748b;
}
.step2-progress-bar {
  flex: 1; max-width: 280px;
  height: 6px; border-radius: 999px;
  background: #f1f5f9;
  overflow: hidden;
}
.step2-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4f46e5, #06b6d4);
  border-radius: 999px;
  transition: width 200ms ease;
}
.step2-btn {
  padding: 6px 14px; border-radius: 8px;
  border: 1px solid transparent; cursor: pointer;
  font-size: 12px; font-weight: 600;
  transition: all 150ms ease;
}
.step2-btn--ghost { background: #fff; color: #475569; border-color: #e2e8f0; }
.step2-btn--ghost:hover { border-color: #4f46e5; color: #4f46e5; }
.step2-btn--primary {
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  color: #fff;
}
.step2-btn--primary:disabled { opacity: 0.5; cursor: not-allowed; }
.ob-back-btn {
  display: inline-flex; align-items: center; gap: 6px;
  background: transparent; border: 0; padding: 4px 10px;
  border-radius: 6px; color: #475569; font-size: 12px; cursor: pointer;
}
.ob-back-btn:hover { background: #f1f5f9; color: #0f172a; }

.step2-no-perm {
  margin: 12px 16px;
  padding: 10px 16px;
  border-radius: 10px;
  background: rgba(245, 158, 11, 0.1);
  color: #b45309;
  display: flex; gap: 12px; align-items: center;
  font-size: 12px;
}
.step2-no-perm__btn {
  margin-left: auto;
  padding: 4px 12px; border-radius: 6px;
  background: #fff; border: 1px solid #fbbf24;
  color: #b45309; font-size: 11px; cursor: pointer;
}

.step2-body {
  display: grid;
  grid-template-columns: 280px 1fr 360px;
  gap: 12px;
  padding: 12px 16px;
  flex: 1;
  overflow: hidden;
}

.step2-left, .step2-right {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  overflow-y: auto;
}
.step2-mid {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  display: flex; flex-direction: column;
  overflow: hidden;
}
.step2-mid__head {
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
  display: flex; align-items: center; gap: 12px;
}
.step2-mid__title { font-size: 13px; font-weight: 600; color: #0f172a; }
.step2-mid__hint { font-size: 11px; color: #94a3b8; flex: 1; }
.step2-relation-toggle {
  padding: 5px 12px; border-radius: 6px;
  border: 1px solid #cbd5e1; background: #fff;
  font-size: 12px; color: #475569; cursor: pointer;
}
.step2-relation-toggle.active {
  background: rgba(79, 70, 229, 0.08); color: #4f46e5; border-color: #4f46e5;
}
.step2-mid__canvas { flex: 1; overflow: hidden; }

.step2-section-title {
  font-size: 11px; font-weight: 600; color: #94a3b8;
  text-transform: uppercase; letter-spacing: 0.5px;
  padding: 14px 16px 8px;
}
.step2-class-list { padding: 0 12px 12px; }
.step2-class-row {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: background 150ms ease;
}
.step2-class-row:hover { background: #f8fafc; }
.step2-class-row--active { background: rgba(79, 70, 229, 0.06); }
.step2-class-row--approved { opacity: 0.85; }
.step2-class-row__icon {
  width: 28px; height: 28px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 12px; flex-shrink: 0;
}
.step2-class-row__icon--t1 { background: linear-gradient(135deg, #4c6ef5, #364fc7); }
.step2-class-row__icon--t2 { background: linear-gradient(135deg, #7950f2, #5f3dc4); }
.step2-class-row__icon--t3 { background: linear-gradient(135deg, #20c997, #087f5b); }
.step2-class-row__main { flex: 1; min-width: 0; line-height: 1.3; }
.step2-class-row__name { font-size: 12px; font-weight: 600; color: #0f172a; }
.step2-class-row__en { font-size: 10px; color: #94a3b8; }
.step2-check-icon { color: #10b981; font-weight: 700; }

.step2-editor-card {
  margin: 14px;
  padding: 14px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}
.step2-editor-card__head {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 12px;
}
.step2-editor-card__title { font-size: 13px; font-weight: 600; color: #0f172a; }
.step2-status-badge {
  padding: 2px 8px; border-radius: 999px;
  font-size: 10px; font-weight: 500;
  background: rgba(245, 158, 11, 0.12); color: #b45309;
}
.step2-status-badge.approved { background: rgba(16, 185, 129, 0.12); color: #059669; }
.step2-status-badge.active { background: rgba(79, 70, 229, 0.12); color: #4f46e5; }

.step2-form { display: grid; gap: 10px; margin-bottom: 12px; }
.step2-form__row { display: grid; gap: 4px; }
.step2-form__row label { font-size: 11px; color: #94a3b8; font-weight: 500; }
.step2-form__meta {
  font-size: 11px; color: #64748b;
  display: flex; gap: 12px;
  padding-top: 4px; border-top: 1px dashed #e2e8f0;
}

.step2-prop-title {
  font-size: 11px; font-weight: 600; color: #94a3b8;
  text-transform: uppercase; letter-spacing: 0.5px;
  margin-top: 12px; margin-bottom: 8px;
}
.step2-prop-list { display: grid; gap: 6px; }
.step2-editor-prop {
  display: grid; grid-template-columns: 1fr 90px 28px; gap: 6px;
  align-items: center;
}
.step2-icon-btn {
  width: 28px; height: 28px; border-radius: 6px;
  border: 0; cursor: pointer; font-size: 14px; line-height: 1;
}
.step2-icon-btn--danger { background: #fee2e2; color: #ef4444; }
.step2-icon-btn--danger:hover { background: #fecaca; }
.step2-add-prop {
  padding: 6px; border-radius: 6px;
  border: 1px dashed #cbd5e1; background: transparent;
  color: #64748b; font-size: 12px; cursor: pointer;
}
.step2-add-prop:hover { border-color: #4f46e5; color: #4f46e5; }

.step2-editor-approve {
  margin-top: 14px;
  width: 100%;
  padding: 8px;
  border-radius: 8px; border: 0;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  color: #fff; font-size: 13px; font-weight: 600;
  cursor: pointer;
}
.step2-editor-approve:disabled { opacity: 0.5; cursor: not-allowed; }
.step2-editor-approve:hover:not(:disabled) { box-shadow: 0 6px 14px -4px rgba(79, 70, 229, 0.4); }

.step2-relations-list { margin-top: 12px; }
.step2-relation-row {
  display: grid; grid-template-columns: auto 12px auto 1fr 24px;
  gap: 6px; align-items: center;
  padding: 6px 8px;
  border-radius: 6px;
  background: #f8fafc;
  margin-bottom: 4px;
  font-size: 11px;
}
.step2-relation-from, .step2-relation-to { color: #1e293b; font-weight: 500; }
.step2-relation-arrow { color: #94a3b8; }
.step2-relation-label { color: #4f46e5; font-weight: 500; }
.step2-relation-row .step2-icon-btn {
  width: 22px; height: 22px; padding: 0;
  font-size: 13px;
}
</style>
