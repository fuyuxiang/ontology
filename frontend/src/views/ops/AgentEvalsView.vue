<template>
  <div class="evals-view">
    <header class="evals-view__header">
      <h2>Agent 评测</h2>
      <p class="evals-view__desc">为 Agent 定义测试用例，批量运行并评估输出质量</p>
    </header>

    <div class="evals-view__body">
      <aside class="evals-view__sidebar">
        <a-button type="primary" block @click="showCreateModal = true">新建套件</a-button>
        <div class="evals-view__suite-list">
          <div
            v-for="s in suites" :key="s.id"
            class="evals-view__suite-item"
            :class="{ 'evals-view__suite-item--active': currentSuite?.id === s.id }"
            @click="selectSuite(s.id)"
          >
            <div class="evals-view__suite-name">{{ s.name }}</div>
            <div class="evals-view__suite-meta">{{ s.agent_name }} · {{ s.case_count }}条</div>
            <a-button type="text" size="small" danger class="evals-view__suite-del" @click.stop="deleteSuite(s.id)">
              <template #icon><span style="font-size:12px">✕</span></template>
            </a-button>
          </div>
          <div v-if="!suites.length" class="evals-view__empty">暂无评测套件</div>
        </div>
      </aside>

      <main class="evals-view__main" v-if="currentSuite">
        <div class="evals-view__suite-header">
          <h3>{{ currentSuite.name }}</h3>
          <span class="evals-view__suite-agent">{{ currentSuite.agent_name }}</span>
          <a-button type="primary" :loading="running" @click="runEval" style="margin-left:auto">运行评测</a-button>
        </div>

        <div class="evals-view__cases-section">
          <div class="evals-view__section-bar">
            <strong>测试用例 ({{ cases.length }})</strong>
            <a-button size="small" @click="showCaseModal = true">添加用例</a-button>
          </div>
          <a-table :columns="caseColumns" :data-source="cases" row-key="id" size="small" :pagination="false">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'expected_keywords'">
                <a-tag v-for="kw in record.expected_keywords" :key="kw" size="small">{{ kw }}</a-tag>
                <span v-if="!record.expected_keywords?.length" style="color:#999">无</span>
              </template>
              <template v-if="column.key === 'action'">
                <a-button type="text" size="small" danger @click="deleteCase(record.id)">删除</a-button>
              </template>
            </template>
          </a-table>
        </div>
        <div class="evals-view__results-section" v-if="runResult">
          <div class="evals-view__section-bar"><strong>评测结果</strong></div>
          <div class="evals-view__metrics">
            <div class="evals-view__metric-card">
              <a-progress type="circle" :percent="runResult.metrics?.pass_rate ?? 0" :size="64" :stroke-color="(runResult.metrics?.pass_rate ?? 0) >= 80 ? '#52c41a' : '#faad14'" />
              <span>通过率</span>
            </div>
            <div class="evals-view__metric-card">
              <div class="evals-view__metric-value">{{ runResult.metrics?.avg_latency_ms ?? 0 }}ms</div>
              <span>平均耗时</span>
            </div>
            <div class="evals-view__metric-card">
              <div class="evals-view__metric-value">{{ runResult.metrics?.passed ?? 0 }}/{{ runResult.metrics?.total ?? 0 }}</div>
              <span>通过/总数</span>
            </div>
          </div>
          <a-table :columns="resultColumns" :data-source="runResult.results" row-key="id" size="small" :pagination="false">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'passed'">
                <a-tag :color="record.passed ? 'green' : 'red'">{{ record.passed ? '通过' : '失败' }}</a-tag>
              </template>
              <template v-if="column.key === 'latency_ms'">
                {{ record.latency_ms != null ? `${record.latency_ms}ms` : '-' }}
              </template>
            </template>
          </a-table>
        </div>
      </main>
      <main class="evals-view__main evals-view__main--empty" v-else>
        <p>选择左侧套件或新建一个开始评测</p>
      </main>
    </div>

    <a-modal v-model:open="showCreateModal" title="新建评测套件" @ok="createSuite" :confirm-loading="creating">
      <a-form layout="vertical">
        <a-form-item label="Agent">
          <a-select v-model:value="newSuite.agent_id" placeholder="选择 Agent" style="width:100%">
            <a-select-option v-for="a in agents" :key="a.id" :value="a.id">{{ a.name }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="套件名称">
          <a-input v-model:value="newSuite.name" placeholder="输入名称" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal v-model:open="showCaseModal" title="添加测试用例" @ok="createCase" :confirm-loading="creatingCase">
      <a-form layout="vertical">
        <a-form-item label="输入 Prompt">
          <a-textarea v-model:value="newCase.input_prompt" :rows="3" placeholder="输入测试问题" />
        </a-form-item>
        <a-form-item label="期望关键词">
          <div class="evals-view__kw-input">
            <a-input v-model:value="kwInput" placeholder="输入关键词后回车" @pressEnter="addKeyword" />
            <div class="evals-view__kw-tags">
              <a-tag v-for="(kw, i) in newCase.expected_keywords" :key="i" closable @close="newCase.expected_keywords.splice(i, 1)">{{ kw }}</a-tag>
            </div>
          </div>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { evalsApi, type EvalSuiteItem, type EvalSuiteDetail, type EvalCaseItem, type EvalRunDetail } from '../../api/ops'
import { agentsApi } from '../../api/agents'

const agents = ref<{ id: string; name: string }[]>([])
const suites = ref<EvalSuiteItem[]>([])
const currentSuite = ref<EvalSuiteDetail | null>(null)
const cases = ref<EvalCaseItem[]>([])
const runResult = ref<EvalRunDetail | null>(null)
const running = ref(false)

const showCreateModal = ref(false)
const creating = ref(false)
const newSuite = reactive({ agent_id: '', name: '' })

const showCaseModal = ref(false)
const creatingCase = ref(false)
const newCase = reactive({ input_prompt: '', expected_keywords: [] as string[] })
const kwInput = ref('')

const caseColumns = [
  { title: '输入 Prompt', dataIndex: 'input_prompt', key: 'input_prompt', ellipsis: true },
  { title: '期望关键词', key: 'expected_keywords', width: 240 },
  { title: '操作', key: 'action', width: 70 },
]

const resultColumns = [
  { title: '输入', dataIndex: 'input_prompt', key: 'input_prompt', ellipsis: true, width: 200 },
  { title: '实际输出', dataIndex: 'actual_output', key: 'actual_output', ellipsis: true },
  { title: '通过', key: 'passed', width: 70 },
  { title: '耗时', key: 'latency_ms', width: 90 },
]

function addKeyword() {
  const kw = kwInput.value.trim()
  if (kw && !newCase.expected_keywords.includes(kw)) {
    newCase.expected_keywords.push(kw)
  }
  kwInput.value = ''
}

async function fetchSuites() {
  suites.value = await evalsApi.listSuites()
}

async function selectSuite(id: string) {
  const detail = await evalsApi.getSuite(id)
  currentSuite.value = detail
  cases.value = detail.cases
  runResult.value = null
}

async function createSuite() {
  if (!newSuite.agent_id || !newSuite.name) return
  creating.value = true
  try {
    await evalsApi.createSuite({ agent_id: newSuite.agent_id, name: newSuite.name })
    showCreateModal.value = false
    newSuite.agent_id = ''
    newSuite.name = ''
    await fetchSuites()
  } finally {
    creating.value = false
  }
}
async function deleteSuite(id: string) {
  await evalsApi.deleteSuite(id)
  if (currentSuite.value?.id === id) {
    currentSuite.value = null
    cases.value = []
    runResult.value = null
  }
  await fetchSuites()
}

async function createCase() {
  if (!newCase.input_prompt || !currentSuite.value) return
  creatingCase.value = true
  try {
    await evalsApi.createCase(currentSuite.value.id, {
      input_prompt: newCase.input_prompt,
      expected_keywords: newCase.expected_keywords,
    })
    showCaseModal.value = false
    newCase.input_prompt = ''
    newCase.expected_keywords = []
    await selectSuite(currentSuite.value.id)
  } finally {
    creatingCase.value = false
  }
}

async function deleteCase(cid: string) {
  await evalsApi.deleteCase(cid)
  if (currentSuite.value) {
    await selectSuite(currentSuite.value.id)
  }
}

async function runEval() {
  if (!currentSuite.value) return
  running.value = true
  try {
    const result = await evalsApi.runSuite(currentSuite.value.id)
    const caseMap = new Map(cases.value.map(c => [c.id, c.input_prompt]))
    result.results = result.results.map(r => ({ ...r, input_prompt: caseMap.get(r.case_id) || '' }))
    runResult.value = result
  } finally {
    running.value = false
  }
}

onMounted(async () => {
  const list = await agentsApi.list()
  agents.value = list.map((a: any) => ({ id: a.id, name: a.name }))
  await fetchSuites()
})
</script>

<style scoped>
.evals-view { padding: 24px; height: 100%; display: flex; flex-direction: column; }
.evals-view__header h2 { margin: 0 0 4px; font-size: 20px; font-weight: 600; }
.evals-view__desc { color: var(--text-secondary, #666); font-size: 13px; margin-bottom: 16px; }
.evals-view__body { display: flex; gap: 20px; flex: 1; min-height: 0; }
.evals-view__sidebar { width: 240px; flex-shrink: 0; display: flex; flex-direction: column; gap: 12px; }
.evals-view__suite-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 4px; }
.evals-view__suite-item { padding: 10px 12px; border-radius: 8px; cursor: pointer; position: relative; background: var(--bg-secondary, #f5f5f5); transition: background 0.15s; }
.evals-view__suite-item:hover { background: var(--bg-hover, #e8e8e8); }
.evals-view__suite-item--active { background: var(--semantic-50, #eef2ff); border: 1px solid var(--semantic-300, #a5b4fc); }
.evals-view__suite-name { font-size: 13px; font-weight: 500; }
.evals-view__suite-meta { font-size: 11px; color: var(--text-secondary, #999); margin-top: 2px; }
.evals-view__suite-del { position: absolute; top: 6px; right: 6px; opacity: 0; }
.evals-view__suite-item:hover .evals-view__suite-del { opacity: 1; }
.evals-view__empty { text-align: center; color: #999; font-size: 13px; padding: 24px 0; }
.evals-view__main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 16px; overflow-y: auto; }
.evals-view__main--empty { align-items: center; justify-content: center; color: #999; }
.evals-view__suite-header { display: flex; align-items: center; gap: 12px; }
.evals-view__suite-header h3 { margin: 0; font-size: 16px; }
.evals-view__suite-agent { font-size: 12px; color: var(--text-secondary, #999); background: var(--bg-secondary, #f0f0f0); padding: 2px 8px; border-radius: 4px; }
.evals-view__section-bar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.evals-view__metrics { display: flex; gap: 24px; margin-bottom: 16px; }
.evals-view__metric-card { display: flex; flex-direction: column; align-items: center; gap: 6px; }
.evals-view__metric-card span { font-size: 12px; color: var(--text-secondary, #666); }
.evals-view__metric-value { font-size: 22px; font-weight: 600; }
.evals-view__kw-input { display: flex; flex-direction: column; gap: 8px; }
.evals-view__kw-tags { display: flex; flex-wrap: wrap; gap: 4px; }
</style>
