<template>
  <div class="wizard-mask" @click.self="$emit('close')">
    <div class="wizard">
      <!-- 头部 -->
      <div class="wizard__header">
        <span class="wizard__title">新建场景</span>
        <button class="wizard__close" @click="$emit('close')">
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </button>
      </div>

      <!-- 步骤指示器 -->
      <div class="wizard__steps">
        <div v-for="(s, i) in steps" :key="i" class="wizard__step" :class="{ 'wizard__step--active': step === i, 'wizard__step--done': step > i }">
          <span class="wizard__step-num">{{ step > i ? '✓' : i + 1 }}</span>
          <span class="wizard__step-label">{{ s }}</span>
        </div>
      </div>

      <!-- Step 1: 基本信息 -->
      <div v-if="step === 0" class="wizard__body">
        <div class="wiz-field">
          <label>场景名称 <span class="wiz-req">*</span></label>
          <input class="wiz-input" v-model="form.name" placeholder="如：宽带退单稽核场景" autofocus />
        </div>
        <div class="wiz-field">
          <label>业务目标</label>
          <textarea class="wiz-input wiz-textarea" v-model="form.description" placeholder="描述该场景要解决的核心业务问题" rows="3" />
        </div>
        <div class="wiz-field">
          <label>命名空间</label>
          <input class="wiz-input" v-model="form.namespace" placeholder="如 s1（可选）" />
        </div>
      </div>

      <!-- Step 2: 选择本体对象 -->
      <div v-if="step === 1" class="wizard__body">
        <div class="wiz-hint">选择该场景涉及的本体对象，创建后将自动预置为画布节点</div>
        <div class="wiz-search">
          <input class="wiz-input" v-model="entitySearch" placeholder="搜索实体..." />
        </div>
        <div class="wiz-tier-group" v-for="tier in [1,2,3]" :key="tier">
          <div class="wiz-tier-label">
            <span class="wiz-tier-badge" :class="`wiz-tier-badge--t${tier}`">T{{ tier }}</span>
            <span>{{ { 1:'核心对象（跨场景复用）', 2:'领域对象（领域内共享）', 3:'场景对象（场景专属）' }[tier] }}</span>
          </div>
          <div class="wiz-entity-list">
            <label
              v-for="e in filteredEntities(tier)"
              :key="e.id"
              class="wiz-entity-item"
              :class="{ 'wiz-entity-item--checked': selectedEntityIds.has(e.id) }"
            >
              <input type="checkbox" :value="e.id" @change="toggleEntity(e.id)" :checked="selectedEntityIds.has(e.id)" style="display:none" />
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <rect x="1" y="1" width="12" height="12" rx="3" :stroke="selectedEntityIds.has(e.id) ? 'var(--semantic-600)' : 'var(--neutral-300)'" stroke-width="1.5" :fill="selectedEntityIds.has(e.id) ? 'var(--semantic-600)' : 'none'" />
                <path v-if="selectedEntityIds.has(e.id)" d="M3.5 7l2.5 2.5 4.5-5" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <span class="wiz-entity-name">{{ e.name_cn }}</span>
              <span class="wiz-entity-en">{{ e.name }}</span>
            </label>
            <div v-if="filteredEntities(tier).length === 0" class="wiz-empty-tier">暂无</div>
          </div>
        </div>
        <div class="wiz-selected-count">已选 {{ selectedEntityIds.size }} 个实体</div>
      </div>

      <!-- Step 3: 关联数据源 -->
      <div v-if="step === 2" class="wizard__body">
        <div class="wiz-hint">选择该场景需要接入的数据源</div>
        <div v-if="datasources.length === 0" class="wiz-empty">暂无可用数据源，可跳过此步骤</div>
        <div class="wiz-ds-list">
          <label
            v-for="ds in datasources"
            :key="ds.id"
            class="wiz-ds-item"
            :class="{ 'wiz-ds-item--checked': selectedDsIds.has(ds.id) }"
          >
            <input type="checkbox" :value="ds.id" @change="toggleDs(ds.id)" :checked="selectedDsIds.has(ds.id)" style="display:none" />
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <rect x="1" y="1" width="12" height="12" rx="3" :stroke="selectedDsIds.has(ds.id) ? 'var(--semantic-600)' : 'var(--neutral-300)'" stroke-width="1.5" :fill="selectedDsIds.has(ds.id) ? 'var(--semantic-600)' : 'none'" />
              <path v-if="selectedDsIds.has(ds.id)" d="M3.5 7l2.5 2.5 4.5-5" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <div class="wiz-ds-info">
              <span class="wiz-ds-name">{{ ds.name }}</span>
              <span class="wiz-ds-meta">{{ ds.db_type }} · {{ ds.table_name }}</span>
            </div>
            <span class="wiz-ds-status" :class="ds.status === 'active' ? 'wiz-ds-status--ok' : 'wiz-ds-status--off'">{{ ds.status === 'active' ? '已连接' : '未连接' }}</span>
          </label>
        </div>
        <div class="wiz-selected-count">已选 {{ selectedDsIds.size }} 个数据源</div>
      </div>

      <!-- Step 4: 选择智能体模板 -->
      <div v-if="step === 3" class="wizard__body">
        <div class="wiz-hint">选择一个智能体作为起点，或从空白画布开始</div>
        <div class="wiz-agent-list">
          <label class="wiz-agent-item" :class="{ 'wiz-agent-item--checked': selectedAgentId === '' }">
            <input type="radio" value="" v-model="selectedAgentId" style="display:none" />
            <div class="wiz-agent-icon wiz-agent-icon--blank">+</div>
            <div class="wiz-agent-info">
              <span class="wiz-agent-name">空白画布</span>
              <span class="wiz-agent-desc">从零开始编排工作流</span>
            </div>
          </label>
          <label v-for="a in agents" :key="a.id" class="wiz-agent-item" :class="{ 'wiz-agent-item--checked': selectedAgentId === a.id }">
            <input type="radio" :value="a.id" v-model="selectedAgentId" style="display:none" />
            <div class="wiz-agent-icon">{{ a.name.charAt(0) }}</div>
            <div class="wiz-agent-info">
              <span class="wiz-agent-name">{{ a.name }}</span>
              <span class="wiz-agent-desc">{{ a.description }}</span>
            </div>
            <span class="wiz-agent-nodes" v-if="a.node_count">{{ a.node_count }} 节点</span>
          </label>
        </div>
      </div>

      <!-- 底部操作 -->
      <div class="wizard__footer">
        <button class="wiz-btn" @click="$emit('close')">取消</button>
        <div class="wizard__footer-right">
          <button class="wiz-btn" v-if="step > 0" @click="step--">← 上一步</button>
          <button class="wiz-btn wiz-btn--skip" v-if="step > 0 && step < 3" @click="step++">跳过</button>
          <button class="wiz-btn wiz-btn--primary" v-if="step < 3" @click="nextStep" :disabled="step === 0 && !form.name">下一步 →</button>
          <button class="wiz-btn wiz-btn--primary" v-if="step === 3" @click="handleCreate" :disabled="creating">
            {{ creating ? '创建中...' : '开始构建' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useOntologyStore } from '../../store/ontology'
import { listDataSources } from '../../api/datasource'
import { get } from '../../api/client'

const emit = defineEmits<{ close: []; created: [name: string, description: string, namespace: string, entityIds: string[], dsIds: string[], agentId: string] }>()

const steps = ['基本信息', '本体对象', '数据源', '智能体模板']
const step = ref(0)
const creating = ref(false)

const form = ref({ name: '', description: '', namespace: '' })
const entitySearch = ref('')
const selectedEntityIds = ref(new Set<string>())
const selectedDsIds = ref(new Set<string>())
const selectedAgentId = ref('')

const ontologyStore = useOntologyStore()
const datasources = ref<any[]>([])
const agents = ref<any[]>([])

onMounted(async () => {
  await ontologyStore.fetchEntities()
  try { datasources.value = await listDataSources({ status: 'active' }) } catch {}
  try {
    const list = await get<any[]>('/agents')
    agents.value = list.map(a => ({ ...a, node_count: a.nodes_json?.length || 0 }))
  } catch {}
})

function filteredEntities(tier: number) {
  return ontologyStore.entities
    .filter(e => e.tier === tier)
    .filter(e => !entitySearch.value || e.name_cn.includes(entitySearch.value) || e.name.includes(entitySearch.value))
}

function toggleEntity(id: string) {
  if (selectedEntityIds.value.has(id)) selectedEntityIds.value.delete(id)
  else selectedEntityIds.value.add(id)
}

function toggleDs(id: string) {
  if (selectedDsIds.value.has(id)) selectedDsIds.value.delete(id)
  else selectedDsIds.value.add(id)
}

function nextStep() { if (step.value < 3) step.value++ }

async function handleCreate() {
  creating.value = true
  try {
    emit('created',
      form.value.name,
      form.value.description,
      form.value.namespace,
      [...selectedEntityIds.value],
      [...selectedDsIds.value],
      selectedAgentId.value,
    )
  } finally { creating.value = false }
}
</script>

<style scoped>
.wizard-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.wizard { background: var(--neutral-0); border-radius: var(--radius-xl); width: 560px; max-height: 80vh; display: flex; flex-direction: column; box-shadow: 0 8px 32px rgba(0,0,0,0.16); }

.wizard__header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--neutral-100); }
.wizard__title { font-size: 15px; font-weight: 700; color: var(--neutral-900); }
.wizard__close { width: 24px; height: 24px; border: none; background: transparent; cursor: pointer; color: var(--neutral-400); border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center; }
.wizard__close:hover { background: var(--neutral-100); color: var(--neutral-700); }

.wizard__steps { display: flex; padding: 14px 20px; gap: 0; border-bottom: 1px solid var(--neutral-100); }
.wizard__step { display: flex; align-items: center; gap: 6px; flex: 1; }
.wizard__step:not(:last-child)::after { content: ''; flex: 1; height: 1px; background: var(--neutral-200); margin: 0 8px; }
.wizard__step-num { width: 20px; height: 20px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; background: var(--neutral-200); color: var(--neutral-500); flex-shrink: 0; transition: all var(--transition-fast); }
.wizard__step-label { font-size: 12px; color: var(--neutral-500); white-space: nowrap; }
.wizard__step--active .wizard__step-num { background: var(--semantic-600); color: #fff; }
.wizard__step--active .wizard__step-label { color: var(--semantic-700); font-weight: 600; }
.wizard__step--done .wizard__step-num { background: var(--status-success); color: #fff; }

.wizard__body { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 14px; }
.wizard__footer { display: flex; align-items: center; justify-content: space-between; padding: 14px 20px; border-top: 1px solid var(--neutral-100); }
.wizard__footer-right { display: flex; gap: 8px; }

.wiz-hint { font-size: var(--text-caption-size); color: var(--neutral-500); background: var(--neutral-50); padding: 8px 12px; border-radius: var(--radius-md); }
.wiz-field { display: flex; flex-direction: column; gap: 6px; }
.wiz-field label { font-size: var(--text-body-size); font-weight: 500; color: var(--neutral-700); }
.wiz-req { color: var(--status-error); }
.wiz-input { padding: 7px 10px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); font-size: var(--text-body-size); color: var(--neutral-800); background: var(--neutral-0); outline: none; transition: border-color var(--transition-fast); font-family: inherit; }
.wiz-input:focus { border-color: var(--semantic-400); }
.wiz-textarea { resize: vertical; }
.wiz-search { margin-bottom: -4px; }
.wiz-empty { color: var(--neutral-400); font-size: var(--text-caption-size); padding: 20px 0; text-align: center; }
.wiz-empty-tier { font-size: var(--text-caption-size); color: var(--neutral-300); padding: 4px 0; }
.wiz-selected-count { font-size: var(--text-caption-size); color: var(--semantic-600); font-weight: 500; text-align: right; }

.wiz-tier-group { display: flex; flex-direction: column; gap: 6px; }
.wiz-tier-label { display: flex; align-items: center; gap: 8px; font-size: var(--text-caption-size); font-weight: 600; color: var(--neutral-600); }
.wiz-tier-badge { padding: 1px 7px; border-radius: 4px; font-size: 10px; font-weight: 700; }
.wiz-tier-badge--t1 { background: var(--tier1-bg); color: var(--tier1-text); }
.wiz-tier-badge--t2 { background: var(--tier2-bg); color: var(--tier2-text); }
.wiz-tier-badge--t3 { background: var(--tier3-bg); color: var(--tier3-text); }
.wiz-entity-list { display: flex; flex-direction: column; gap: 3px; padding-left: 8px; }
.wiz-entity-item { display: flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: var(--radius-md); cursor: pointer; border: 1px solid transparent; transition: all var(--transition-fast); }
.wiz-entity-item:hover { background: var(--neutral-50); }
.wiz-entity-item--checked { background: var(--semantic-50); border-color: var(--semantic-200); }
.wiz-entity-name { font-size: var(--text-body-size); font-weight: 500; color: var(--neutral-800); }
.wiz-entity-en { font-size: var(--text-caption-size); color: var(--neutral-400); margin-left: 4px; }

.wiz-ds-list { display: flex; flex-direction: column; gap: 6px; }
.wiz-ds-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); cursor: pointer; transition: all var(--transition-fast); }
.wiz-ds-item:hover { border-color: var(--neutral-300); }
.wiz-ds-item--checked { border-color: var(--semantic-300); background: var(--semantic-50); }
.wiz-ds-info { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.wiz-ds-name { font-size: var(--text-body-size); font-weight: 500; color: var(--neutral-800); }
.wiz-ds-meta { font-size: var(--text-caption-size); color: var(--neutral-400); }
.wiz-ds-status { font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: var(--radius-full); }
.wiz-ds-status--ok { background: var(--status-success-bg); color: var(--status-success); }
.wiz-ds-status--off { background: var(--neutral-100); color: var(--neutral-500); }

.wiz-agent-list { display: flex; flex-direction: column; gap: 8px; }
.wiz-agent-item { display: flex; align-items: center; gap: 12px; padding: 12px 14px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); cursor: pointer; transition: all var(--transition-fast); }
.wiz-agent-item:hover { border-color: var(--neutral-300); }
.wiz-agent-item--checked { border-color: var(--semantic-400); background: var(--semantic-50); }
.wiz-agent-icon { width: 36px; height: 36px; border-radius: var(--radius-md); background: var(--semantic-100); color: var(--semantic-700); display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 700; flex-shrink: 0; }
.wiz-agent-icon--blank { background: var(--neutral-100); color: var(--neutral-500); font-size: 20px; }
.wiz-agent-info { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.wiz-agent-name { font-size: var(--text-body-size); font-weight: 600; color: var(--neutral-800); }
.wiz-agent-desc { font-size: var(--text-caption-size); color: var(--neutral-500); }
.wiz-agent-nodes { font-size: 11px; color: var(--semantic-500); font-weight: 500; }

.wiz-btn { padding: 7px 16px; border-radius: var(--radius-md); border: 1px solid var(--neutral-200); background: var(--neutral-0); color: var(--neutral-700); font-size: var(--text-body-size); font-weight: 500; cursor: pointer; transition: all var(--transition-fast); }
.wiz-btn:hover:not(:disabled) { border-color: var(--neutral-400); }
.wiz-btn--primary { background: var(--semantic-600); border-color: var(--semantic-600); color: #fff; }
.wiz-btn--primary:hover:not(:disabled) { background: var(--semantic-700); }
.wiz-btn--primary:disabled { opacity: 0.5; cursor: not-allowed; }
.wiz-btn--skip { color: var(--neutral-400); border-color: transparent; }
.wiz-btn--skip:hover { color: var(--neutral-600); border-color: var(--neutral-200); }
</style>
