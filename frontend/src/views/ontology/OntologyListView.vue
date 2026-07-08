<template>
  <div class="ontology-list-page">
    <div class="ontology-list-page__header">
      <div>
        <h1 class="text-display">本体列表</h1>
        <p class="text-caption" style="margin-top: 4px;">按场景管理本体</p>
      </div>
      <div class="ontology-list-page__actions">
        <button class="btn-primary" @click="showCreate = true">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 2v10M2 7h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          新建本体
        </button>
      </div>
    </div>

    <div class="ontology-list-page__stats">
      <div class="stat-card stat-card--semantic">
        <div class="stat-card__value">{{ scenarios.length }}</div>
        <div class="stat-card__label">本体总数</div>
      </div>
      <div class="stat-card stat-card--dynamic">
        <div class="stat-card__value">{{ totalEntities }}</div>
        <div class="stat-card__label">对象总数</div>
      </div>
    </div>

    <div class="ontology-list-page__toolbar">
      <input v-model="search" class="ontology-search" placeholder="搜索本体名称..." />
    </div>

    <div class="ontology-list-page__grid">
      <div
        v-for="item in filteredList" :key="item.code"
        class="ontology-card"
        @click="goDetail(item.code)"
      >
        <div class="ontology-card__header">
          <span class="ontology-card__dot" :style="{ background: item.color || '#94a3b8' }"></span>
          <span class="ontology-card__name">{{ item.name }}</span>
        </div>
        <p class="ontology-card__desc">{{ item.description || '暂无描述' }}</p>
        <div class="ontology-card__stats">
          <span class="ontology-card__stat">对象 <b>{{ item.entityCount }}</b></span>
          <span class="ontology-card__stat">逻辑 <b>{{ item.logicCount }}</b></span>
        </div>
      </div>
      <div v-if="filteredList.length === 0" class="ontology-list-page__empty">
        <p class="text-caption">无匹配本体</p>
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
            <button class="btn-primary" :disabled="!createForm.name || !createForm.code" @click="handleCreate">创建</button>
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
const totalEntities = computed(() => ontologyStore.entities.length)

const filteredList = computed(() => {
  const items = scenarios.value.map(s => {
    const entityCount = ontologyStore.entities.filter(
      e => (e.scenarioCodes || []).includes(s.code)
    ).length
    const logicCount = functions.value.filter(
      f => (f as any).scenario_code === s.code
    ).length
    return { ...s, entityCount, logicCount }
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

onMounted(async () => {
  await Promise.all([
    scenarioStore.fetchScenarios(),
    ontologyStore.fetchEntities(),
    functionApi.list().then(list => { functions.value = list }),
  ])
})
</script>

<!-- STYLE_PLACEHOLDER -->
<style scoped>
.ontology-list-page {
  max-width: 1200px;
  margin: 0 auto;
}

.ontology-list-page__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.ontology-list-page__actions {
  display: flex;
  gap: 8px;
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--primary, #2563eb);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.15s;
}

.btn-primary:hover { opacity: 0.9; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.ontology-list-page__stats {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  flex: 1;
  padding: 20px 24px;
  border-radius: var(--radius-lg, 12px);
  border: 1px solid var(--neutral-100, #f0f0f0);
  background: var(--neutral-0, #fff);
}

.stat-card__value {
  font-size: 28px;
  font-weight: 700;
  color: var(--neutral-900, #111);
}

.stat-card__label {
  font-size: 12px;
  color: var(--neutral-500, #888);
  margin-top: 4px;
}

.ontology-list-page__toolbar {
  margin-bottom: 20px;
}

.ontology-search {
  width: 100%;
  max-width: 320px;
  padding: 8px 12px;
  border: 1px solid var(--neutral-200, #e5e5e5);
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
}

.ontology-search:focus {
  border-color: var(--primary, #2563eb);
}

.ontology-list-page__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.ontology-card {
  padding: 20px;
  background: var(--neutral-0, #fff);
  border: 1px solid var(--neutral-100, #f0f0f0);
  border-radius: var(--radius-lg, 12px);
  cursor: pointer;
  transition: box-shadow 0.15s, border-color 0.15s;
}

.ontology-card:hover {
  border-color: var(--primary, #2563eb);
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.08);
}

.ontology-card__header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.ontology-card__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.ontology-card__name {
  font-size: 15px;
  font-weight: 600;
  color: var(--neutral-900, #111);
}

.ontology-card__desc {
  font-size: 12px;
  color: var(--neutral-500, #888);
  margin: 0 0 12px;
  line-height: 1.4;
}

.ontology-card__stats {
  display: flex;
  gap: 16px;
}

.ontology-card__stat {
  font-size: 12px;
  color: var(--neutral-500, #888);
}

.ontology-card__stat b {
  color: var(--neutral-800, #333);
  font-weight: 600;
}

.ontology-list-page__empty {
  grid-column: 1 / -1;
  text-align: center;
  padding: 48px 0;
  color: var(--neutral-400, #aaa);
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

.modal-field {
  margin-bottom: 16px;
}

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

.modal-input:focus {
  border-color: var(--primary, #2563eb);
}

.modal-textarea {
  min-height: 72px;
  resize: vertical;
}

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
