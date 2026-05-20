<template>
  <div class="pl-tab">
    <!-- 顶部统计与操作 -->
    <div class="pl-header">
      <div class="pl-stats">
        <div class="pl-stat"><div class="pl-stat__lbl">管线总数</div><div class="pl-stat__num" style="color:#1f2937">{{ summary.total }}</div></div>
        <div class="pl-stat"><div class="pl-stat__lbl">运行中</div><div class="pl-stat__num" style="color:#10b981">{{ summary.running }}</div></div>
        <div class="pl-stat"><div class="pl-stat__lbl">成功</div><div class="pl-stat__num" style="color:#059669">{{ summary.success }}</div></div>
        <div class="pl-stat"><div class="pl-stat__lbl">已停止</div><div class="pl-stat__num" style="color:#6b7280">{{ summary.stopped }}</div></div>
        <div class="pl-stat"><div class="pl-stat__lbl">错误</div><div class="pl-stat__num" style="color:#ef4444">{{ summary.error }}</div></div>
        <div class="pl-stat"><div class="pl-stat__lbl">上次执行总记录</div><div class="pl-stat__num" style="color:#3b82f6">{{ fmtNum(summary.total_records_last_run) }}</div></div>
      </div>
      <div class="pl-toolbar">
        <a-input-search v-model:value="keyword" placeholder="搜索管线名称 / 描述 / 来源 / 目标" style="width: 280px" allow-clear />
        <a-select v-model:value="statusFilter" style="width: 140px" :options="statusOptions" />
        <a-button @click="refreshList">刷新</a-button>
        <a-button type="primary" @click="openCreate">+ 新建管线</a-button>
      </div>
    </div>

    <!-- 列表 -->
    <div v-if="filtered.length === 0 && !keyword && !statusFilter" class="pl-empty">
      <div class="pl-empty__title">暂无管线</div>
      <div class="pl-empty__sub">管线用于把数据源接入并按步骤推进，到达目标本体对象</div>
      <a-button type="primary" @click="openCreate">+ 新建第一条管线</a-button>
    </div>
    <div v-else-if="filtered.length === 0" class="pl-empty pl-empty--small">没有符合筛选条件的管线</div>
    <div v-else class="pl-list">
      <div v-for="p in filtered" :key="p.id" class="pl-card" :style="{ borderLeftColor: statusColor(activeStatus(p)) }">
        <div class="pl-card__body">
          <div class="pl-card__head">
            <span class="pl-card__name">{{ p.name }}</span>
            <span class="pl-tag" :style="tagStyle(activeStatus(p))">{{ statusLabel(activeStatus(p)) }}</span>
            <span v-if="activeRuns[p.id]" class="pl-tag" :style="tagStyle('pending')">
              步骤 {{ activeRuns[p.id].step_index + 1 }}/{{ p.steps.length }} · {{ activeRuns[p.id].step_label }}
            </span>
            <span v-else-if="p.last_run_at && p.last_records != null" class="pl-card__meta">
              上次同步 {{ fmtNum(p.last_records) }} 条 · {{ fmtDur(p.last_duration_ms) }} · {{ fmtDate(p.last_run_at) }}
            </span>
          </div>

          <div class="pl-steps">
            <span class="pl-step" :style="badgeStyle('#3b82f6', '#3b82f6', false)">{{ p.source || '数据源' }}</span>
            <template v-for="(s, i) in p.steps" :key="i">
              <span class="pl-arrow">›</span>
              <span class="pl-step" :style="stepBadgeStyle(p, i)">{{ s }}</span>
            </template>
            <span class="pl-arrow">›</span>
            <span class="pl-step" :style="badgeStyle('#7c3aed', '#7c3aed', false)">{{ p.target || '目标' }}</span>
          </div>

          <div v-if="activeRuns[p.id]" class="pl-progress">
            <div class="pl-progress__bar" :style="{ width: (activeRuns[p.id].progress || 0) + '%' }" />
          </div>

          <div v-else-if="p.last_records != null" class="pl-lastrun">
            上次执行：同步 {{ fmtNum(p.last_records) }} 条 → {{ fmtNum(p.last_objects || 0) }} 个本体对象，耗时 {{ fmtDur(p.last_duration_ms) }}
          </div>
        </div>

        <div class="pl-card__actions">
          <a-button v-if="activeStatus(p) === 'running'" danger size="small" @click="stopPipeline(p)">停止</a-button>
          <a-button v-else size="small" type="primary" ghost style="color:#10b981;border-color:#a7f3d0" @click="runPipeline(p)">运行</a-button>
          <a-button size="small" @click="openDetail(p)">详情</a-button>
          <a-button size="small" :disabled="activeStatus(p) === 'running'" @click="openEdit(p)">编辑</a-button>
          <a-popconfirm title="删除此管线？关联的运行历史也会被删除。" @confirm="deletePipeline(p)">
            <a-button size="small">删除</a-button>
          </a-popconfirm>
        </div>
      </div>
    </div>

    <!-- 新建/编辑抽屉 -->
    <a-drawer v-model:open="showEditor" :title="editing ? '编辑管线 — ' + editing.name : '新建管线'" width="560" destroy-on-close>
      <a-form layout="vertical">
        <a-form-item label="管线名称 *">
          <a-input v-model:value="form.name" placeholder="如：客户主数据接入" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="form.description" :rows="2" />
        </a-form-item>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="数据来源（展示用）">
              <a-input v-model:value="form.source" placeholder="例：B域数仓" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="目标对象">
              <a-input v-model:value="form.target" placeholder="例：Customer对象" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="关联数据源">
          <a-select v-model:value="form.datasource_id" :options="dsOptions" allow-clear placeholder="— 不绑定 —" />
          <div class="pl-help">执行成功后，将以该数据源的记录数作为本次同步记录数</div>
        </a-form-item>
        <a-form-item label="步骤定义（每行一个步骤）*">
          <a-textarea v-model:value="form.stepsText" :rows="4" />
          <div class="pl-help">至少一个步骤；运行时按顺序推进，每步耗时由下方“单步执行时长”控制</div>
        </a-form-item>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="单步执行时长（毫秒）">
              <a-input-number v-model:value="form.step_duration_ms" :min="100" :max="60000" style="width:100%" />
              <div class="pl-help">范围 100 - 60000</div>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="调度（Cron 文本）">
              <a-input v-model:value="form.schedule" placeholder="可选，仅作为展示字段" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="标签（逗号分隔）">
          <a-input v-model:value="form.tags" />
        </a-form-item>
      </a-form>
      <template #extra>
        <a-space>
          <a-button @click="showEditor = false">取消</a-button>
          <a-button type="primary" @click="handleSave">{{ editing ? '保存修改' : '创建管线' }}</a-button>
        </a-space>
      </template>
    </a-drawer>

    <!-- 详情抽屉 -->
    <a-drawer v-model:open="showDetail" :title="detail ? '管线详情 — ' + detail.name : ''" width="720" destroy-on-close>
      <div v-if="detail" class="pl-detail">
        <div class="pl-detail__grid">
          <div class="pl-detail__row"><div class="pl-detail__lbl">管线 ID</div><div class="pl-detail__val">{{ detail.id }}</div></div>
          <div class="pl-detail__row"><div class="pl-detail__lbl">状态</div><div class="pl-detail__val">{{ statusLabel(detail.status) }}</div></div>
          <div class="pl-detail__row"><div class="pl-detail__lbl">数据来源</div><div class="pl-detail__val">{{ detail.source || '—' }}</div></div>
          <div class="pl-detail__row"><div class="pl-detail__lbl">目标对象</div><div class="pl-detail__val">{{ detail.target || '—' }}</div></div>
          <div class="pl-detail__row"><div class="pl-detail__lbl">关联数据源</div><div class="pl-detail__val">{{ dsName(detail.datasource_id) || '—' }}</div></div>
          <div class="pl-detail__row"><div class="pl-detail__lbl">调度</div><div class="pl-detail__val">{{ detail.schedule || '—' }}</div></div>
          <div class="pl-detail__row"><div class="pl-detail__lbl">单步耗时</div><div class="pl-detail__val">{{ detail.step_duration_ms }} ms</div></div>
          <div class="pl-detail__row"><div class="pl-detail__lbl">标签</div><div class="pl-detail__val">{{ (detail.tags || []).join(', ') || '—' }}</div></div>
        </div>
        <div v-if="detail.description" class="pl-detail__desc">{{ detail.description }}</div>

        <div class="pl-detail__section">
          <div class="pl-detail__title">步骤定义（{{ detail.steps.length }}）</div>
          <div class="pl-detail__steps">
            <span v-for="(s, i) in detail.steps" :key="i" class="pl-detail__stepchip">{{ i + 1 }}. {{ s }}</span>
          </div>
        </div>

        <div class="pl-detail__section">
          <div class="pl-detail__title">执行历史（{{ (detail.recent_runs || []).length }}）</div>
          <div v-if="!detail.recent_runs || detail.recent_runs.length === 0" class="pl-detail__empty">暂无执行记录</div>
          <a-table v-else :columns="runCols" :data-source="detail.recent_runs" :pagination="false" size="small" row-key="id">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'status'">
                <span class="pl-tag" :style="tagStyle(record.status)">{{ statusLabel(record.status) }}</span>
              </template>
              <template v-else-if="column.key === 'step'">#{{ record.step_index + 1 }} {{ record.step_label || '—' }}</template>
              <template v-else-if="column.key === 'records'">{{ fmtNum(record.records) }}</template>
              <template v-else-if="column.key === 'duration'">{{ fmtDur(record.duration_ms) }}</template>
              <template v-else-if="column.key === 'started'">{{ fmtDate(record.started_at) }}</template>
            </template>
          </a-table>
        </div>
      </div>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { message } from 'ant-design-vue'
import * as dsApi from '../../../api/datasource'
import type { DataSource } from '../../../types/datasource'

interface PipelineRun {
  id: string
  pipeline_id: string
  status: 'running' | 'success' | 'error' | 'stopped' | 'pending' | 'idle'
  step_index: number
  step_label: string
  records: number
  duration_ms: number
  progress: number
  started_at: string
}

interface Pipeline {
  id: string
  name: string
  description: string
  source: string
  target: string
  datasource_id: string | null
  steps: string[]
  tags: string[]
  schedule: string
  step_duration_ms: number
  status: 'idle' | 'running' | 'success' | 'error' | 'stopped'
  last_run_at?: string
  last_records?: number
  last_objects?: number
  last_duration_ms?: number
  recent_runs?: PipelineRun[]
}

const STORAGE_KEY = 'dataworkshop.pipelines.v1'

const STATUS_LABEL: Record<string, string> = {
  idle: '空闲', running: '运行中', stopped: '已停止', error: '错误', success: '成功', pending: '排队中',
}
const STATUS_COLOR: Record<string, string> = {
  running: '#10b981', success: '#10b981', idle: '#9ca3af',
  stopped: '#9ca3af', error: '#ef4444', pending: '#3b82f6',
}

const pipelines = ref<Pipeline[]>([])
const activeRuns = reactive<Record<string, PipelineRun>>({})
const datasources = ref<DataSource[]>([])
const keyword = ref('')
const statusFilter = ref<string | undefined>(undefined)

const showEditor = ref(false)
const showDetail = ref(false)
const editing = ref<Pipeline | null>(null)
const detail = ref<Pipeline | null>(null)

const form = reactive({
  name: '', description: '', source: '', target: '',
  datasource_id: undefined as string | undefined,
  stepsText: '抽取\n清洗\n本体映射',
  tags: '', schedule: '', step_duration_ms: 1500,
})

const statusOptions = [
  { value: undefined, label: '全部状态' },
  { value: 'idle', label: '空闲' },
  { value: 'running', label: '运行中' },
  { value: 'success', label: '成功' },
  { value: 'stopped', label: '已停止' },
  { value: 'error', label: '错误' },
]

const summary = computed(() => {
  const s = { total: pipelines.value.length, running: 0, success: 0, stopped: 0, error: 0, idle: 0, total_records_last_run: 0 }
  pipelines.value.forEach((p) => {
    const st = activeRuns[p.id]?.status || p.status
    if (st === 'running') s.running++
    else if (st === 'success') s.success++
    else if (st === 'stopped') s.stopped++
    else if (st === 'error') s.error++
    else s.idle++
    if (p.last_records) s.total_records_last_run += p.last_records
  })
  return s
})

const filtered = computed(() => {
  const kw = keyword.value.toLowerCase().trim()
  return pipelines.value.filter((p) => {
    const st = activeRuns[p.id]?.status || p.status
    if (statusFilter.value && st !== statusFilter.value) return false
    if (!kw) return true
    return [p.name, p.description, p.source, p.target].some((s) => (s || '').toLowerCase().includes(kw))
  })
})

const dsOptions = computed(() =>
  datasources.value.map((d) => ({
    value: d.id,
    label: `${d.name} (${(d as any).type || (d as any).engine || ''})`,
  }))
)

const runCols = [
  { title: '运行 ID', dataIndex: 'id', key: 'id', ellipsis: true, width: 200 },
  { title: '状态', key: 'status', width: 90 },
  { title: '步骤', key: 'step' },
  { title: '记录数', key: 'records', width: 90 },
  { title: '耗时', key: 'duration', width: 80 },
  { title: '开始时间', key: 'started', width: 140 },
]

function fmtNum(v: number | string | undefined | null) {
  if (v == null || v === '' || isNaN(Number(v))) return '—'
  return Number(v).toLocaleString()
}
function fmtDur(ms?: number | null) {
  if (ms == null) return '—'
  if (ms < 1000) return ms + ' ms'
  return (ms / 1000).toFixed(1) + ' s'
}
function fmtDate(s?: string | null) {
  if (!s) return '—'
  const d = new Date(s)
  if (isNaN(d.getTime())) return s
  const p = (n: number) => (n < 10 ? '0' + n : '' + n)
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}
function statusLabel(s: string) { return STATUS_LABEL[s] || s }
function statusColor(s: string) { return STATUS_COLOR[s] || '#9ca3af' }
function activeStatus(p: Pipeline) { return activeRuns[p.id]?.status || p.status }
function tagStyle(s: string) {
  const c = STATUS_COLOR[s] || '#9ca3af'
  return { background: c + '15', color: c, border: '1px solid ' + c + '30' }
}
function badgeStyle(color: string, _border: string, _bold: boolean) {
  return { color, border: '1px solid #e5e7eb', background: '#fff', fontWeight: 400 }
}
function stepBadgeStyle(p: Pipeline, idx: number) {
  const run = activeRuns[p.id]
  if (run && run.step_index === idx) return { color: '#10b981', border: '1px solid #10b981', background: '#fff', fontWeight: 600 }
  if (run && run.step_index > idx) return { color: '#10b981', border: '1px solid #a7f3d0', background: '#fff', fontWeight: 400 }
  return { color: '#9ca3af', border: '1px solid #e5e7eb', background: '#fff', fontWeight: 400 }
}
function dsName(id?: string | null) {
  if (!id) return ''
  const d = datasources.value.find((x) => x.id === id)
  return d?.name || id
}

function loadPersisted(): Pipeline[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch (e) { /* ignore */ }
  return seedPipelines()
}
function persist() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(pipelines.value))
}

function seedPipelines(): Pipeline[] {
  const now = new Date()
  const t = (h: number) => new Date(now.getTime() - h * 3600_000).toISOString()
  return [
    {
      id: 'pl-customer-001', name: '客户主数据接入', description: '从 B 域数仓抽取客户主数据，落入 Customer 本体对象',
      source: 'B域数仓 · DWA_V_D_CUS_CB_USER_INFO', target: 'Customer 对象',
      datasource_id: null, steps: ['抽取', '清洗', '主键解析', '本体映射'], tags: ['核心', '日更'],
      schedule: '0 2 * * *', step_duration_ms: 1500, status: 'success',
      last_run_at: t(2), last_records: 40929, last_objects: 40929, last_duration_ms: 6800,
      recent_runs: [
        { id: 'run-' + Date.now() + '-1', pipeline_id: 'pl-customer-001', status: 'success', step_index: 3, step_label: '本体映射', records: 40929, duration_ms: 6800, progress: 100, started_at: t(2) },
        { id: 'run-' + Date.now() + '-2', pipeline_id: 'pl-customer-001', status: 'success', step_index: 3, step_label: '本体映射', records: 38741, duration_ms: 7200, progress: 100, started_at: t(26) },
      ],
    },
    {
      id: 'pl-contract-001', name: '合约数据接入', description: '同步合约表，构建 Contract 实例',
      source: 'CBSS · DWA_V_D_CUS_CB_ACT_INFO', target: 'Contract 对象',
      datasource_id: null, steps: ['抽取', '过期标记', '本体映射'], tags: ['日更'],
      schedule: '0 3 * * *', step_duration_ms: 1500, status: 'success',
      last_run_at: t(3), last_records: 40929, last_objects: 40929, last_duration_ms: 4900, recent_runs: [],
    },
    {
      id: 'pl-workorder-001', name: '工单数据接入', description: '客服工单全量接入',
      source: '客服工单系统 · DWD_D_EVT_KF_ORDER_MAIN', target: 'WorkOrder 对象',
      datasource_id: null, steps: ['抽取', '工单去重', '本体映射'], tags: [],
      schedule: '*/30 * * * *', step_duration_ms: 1500, status: 'idle',
      last_run_at: t(8), last_records: 82757, last_objects: 82757, last_duration_ms: 12300, recent_runs: [],
    },
    {
      id: 'pl-mnp-warning', name: '携转预警结果回写', description: '将携转风险评分写入 t_mnp_risk_warning',
      source: '风险评分模型', target: 't_mnp_risk_warning',
      datasource_id: null, steps: ['模型推理', '阈值过滤', '结果落库'], tags: ['MNP'],
      schedule: '', step_duration_ms: 1500, status: 'idle',
      last_run_at: t(36), last_records: 1284, last_objects: 1284, last_duration_ms: 5400, recent_runs: [],
    },
  ]
}

let pollTimer: number | null = null
function startPolling() {
  if (pollTimer) return
  const tick = () => {
    advanceRuns()
    pollTimer = window.setTimeout(tick, 800)
  }
  tick()
}
function stopPolling() {
  if (pollTimer) { clearTimeout(pollTimer); pollTimer = null }
}

function advanceRuns() {
  const ids = Object.keys(activeRuns)
  let changed = false
  for (const id of ids) {
    const run = activeRuns[id]
    const p = pipelines.value.find((x) => x.id === id)
    if (!p) { delete activeRuns[id]; continue }
    const stepCount = p.steps.length
    const stepDur = p.step_duration_ms || 1500
    const totalDur = stepCount * stepDur
    const elapsed = Date.now() - new Date(run.started_at).getTime()
    const progress = Math.min(100, Math.round((elapsed / totalDur) * 100))
    const stepIdx = Math.min(stepCount - 1, Math.floor(elapsed / stepDur))
    run.progress = progress
    run.step_index = stepIdx
    run.step_label = p.steps[stepIdx]
    if (elapsed >= totalDur) {
      const records = mockRecords(p)
      const finalRun: PipelineRun = {
        ...run, status: 'success', step_index: stepCount - 1, step_label: p.steps[stepCount - 1],
        records, duration_ms: totalDur, progress: 100,
      }
      p.status = 'success'
      p.last_run_at = new Date().toISOString()
      p.last_records = records
      p.last_objects = records
      p.last_duration_ms = totalDur
      p.recent_runs = [finalRun, ...(p.recent_runs || [])].slice(0, 10)
      delete activeRuns[id]
      changed = true
    }
  }
  if (changed) persist()
}

function mockRecords(p: Pipeline) {
  if (p.datasource_id) {
    const ds = datasources.value.find((d) => d.id === p.datasource_id)
    if (ds && ds.record_count != null) return ds.record_count
  }
  if (p.last_records) {
    const jitter = Math.floor((Math.random() - 0.5) * Math.max(100, p.last_records * 0.05))
    return Math.max(0, p.last_records + jitter)
  }
  return 1000 + Math.floor(Math.random() * 100000)
}

function refreshList() { pipelines.value = loadPersisted() }

function openCreate() {
  editing.value = null
  Object.assign(form, {
    name: '', description: '', source: '', target: '',
    datasource_id: undefined, stepsText: '抽取\n清洗\n本体映射',
    tags: '', schedule: '', step_duration_ms: 1500,
  })
  showEditor.value = true
}

function openEdit(p: Pipeline) {
  editing.value = p
  Object.assign(form, {
    name: p.name, description: p.description, source: p.source, target: p.target,
    datasource_id: p.datasource_id || undefined,
    stepsText: p.steps.join('\n'),
    tags: p.tags.join(','), schedule: p.schedule, step_duration_ms: p.step_duration_ms,
  })
  showEditor.value = true
}

function openDetail(p: Pipeline) {
  detail.value = p
  showDetail.value = true
}

function handleSave() {
  if (!form.name.trim()) { message.warning('请输入管线名称'); return }
  const steps = form.stepsText.split(/\r?\n/).map((s) => s.trim()).filter(Boolean)
  if (steps.length === 0) { message.warning('至少需要一个步骤'); return }
  const dur = Number(form.step_duration_ms)
  if (!Number.isFinite(dur) || dur < 100 || dur > 60000) { message.warning('单步耗时范围 100~60000'); return }
  const tags = form.tags.split(',').map((s) => s.trim()).filter(Boolean)
  if (editing.value) {
    const idx = pipelines.value.findIndex((x) => x.id === editing.value!.id)
    if (idx >= 0) {
      const p = pipelines.value[idx]
      pipelines.value[idx] = {
        ...p, name: form.name.trim(), description: form.description, source: form.source,
        target: form.target, datasource_id: form.datasource_id || null, steps, tags,
        schedule: form.schedule, step_duration_ms: dur,
      }
    }
    message.success('管线已更新')
  } else {
    const id = 'pl-' + Math.random().toString(36).slice(2, 10)
    pipelines.value.unshift({
      id, name: form.name.trim(), description: form.description, source: form.source,
      target: form.target, datasource_id: form.datasource_id || null, steps, tags,
      schedule: form.schedule, step_duration_ms: dur, status: 'idle', recent_runs: [],
    })
    message.success('管线已创建')
  }
  persist()
  showEditor.value = false
}

function runPipeline(p: Pipeline) {
  if (activeRuns[p.id]) return
  const run: PipelineRun = {
    id: 'run-' + Date.now() + '-' + Math.random().toString(36).slice(2, 6),
    pipeline_id: p.id, status: 'running', step_index: 0,
    step_label: p.steps[0] || '步骤 1', records: 0, duration_ms: 0, progress: 0,
    started_at: new Date().toISOString(),
  }
  activeRuns[p.id] = run
  p.status = 'running'
  message.success('管线已开始执行')
  persist()
}

function stopPipeline(p: Pipeline) {
  delete activeRuns[p.id]
  p.status = 'stopped'
  message.success('已停止')
  persist()
}

function deletePipeline(p: Pipeline) {
  pipelines.value = pipelines.value.filter((x) => x.id !== p.id)
  delete activeRuns[p.id]
  message.success('管线已删除')
  persist()
}

watch(pipelines, persist, { deep: true })

onMounted(async () => {
  pipelines.value = loadPersisted()
  try {
    const r = await dsApi.listDataSources()
    datasources.value = Array.isArray(r) ? r : ((r as any).items || [])
  } catch (e) { /* ignore */ }
  startPolling()
})
onBeforeUnmount(stopPolling)
</script>

<style scoped>
.pl-tab { display: flex; flex-direction: column; gap: 16px; }

.pl-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  flex-wrap: wrap; gap: 16px;
  background: #fff; border: 1px solid var(--neutral-100); border-radius: var(--radius-xl);
  padding: 16px 20px; box-shadow: var(--shadow-xs);
}
.pl-stats { display: flex; gap: 32px; align-items: center; flex-wrap: wrap; }
.pl-stat { min-width: 80px; }
.pl-stat__lbl { font-size: 12px; color: var(--neutral-600); }
.pl-stat__num { font-size: 22px; font-weight: 700; margin-top: 2px; }
.pl-toolbar { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }

.pl-empty {
  text-align: center; padding: 60px 20px; color: var(--neutral-500);
  background: #fff; border: 1px dashed var(--neutral-300); border-radius: 10px;
}
.pl-empty--small { padding: 36px; border-style: solid; border-color: var(--neutral-200); }
.pl-empty__title { font-size: 15px; margin-bottom: 8px; color: var(--neutral-800); font-weight: 600; }
.pl-empty__sub { font-size: 13px; margin-bottom: 20px; }

.pl-list { display: flex; flex-direction: column; gap: 10px; }
.pl-card {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 16px;
  padding: 14px 18px; background: #fff;
  border: 1px solid var(--neutral-100); border-left: 3px solid #9ca3af;
  border-radius: 8px; box-shadow: var(--shadow-xs);
  transition: box-shadow var(--transition-fast);
}
.pl-card:hover { box-shadow: var(--shadow-sm); }
.pl-card__body { flex: 1; min-width: 0; }
.pl-card__head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.pl-card__name { font-weight: 600; font-size: 14px; color: var(--neutral-900); }
.pl-card__meta { font-size: 12px; color: var(--neutral-600); }
.pl-card__actions { display: flex; gap: 6px; flex-shrink: 0; }

.pl-tag {
  display: inline-block; padding: 1px 8px; border-radius: 4px;
  font-size: 11px; line-height: 1.6;
}
.pl-steps { display: flex; align-items: center; flex-wrap: wrap; gap: 0; }
.pl-step {
  padding: 2px 8px; font-size: 12px;
  border: 1px solid var(--neutral-200); border-radius: 4px; background: #fff;
}
.pl-arrow { color: var(--neutral-300); margin: 0 6px; font-size: 11px; }

.pl-progress {
  margin-top: 8px; max-width: 480px; height: 6px;
  background: var(--neutral-100); border-radius: 3px; overflow: hidden;
}
.pl-progress__bar { height: 100%; background: #10b981; transition: width 0.3s; }

.pl-lastrun {
  margin-top: 8px; padding: 6px 12px; background: #f0fdf4; border-radius: 6px;
  border: 1px solid #bbf7d0; font-size: 12px; display: inline-flex;
}

.pl-help { font-size: 11px; color: var(--neutral-500); margin-top: 4px; }

.pl-detail__grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }
.pl-detail__row { }
.pl-detail__lbl { font-size: 11px; color: var(--neutral-600); margin-bottom: 2px; }
.pl-detail__val { font-size: 13px; color: var(--neutral-900); word-break: break-all; }
.pl-detail__desc {
  margin-bottom: 20px; padding: 12px; background: var(--neutral-50);
  border-radius: 6px; font-size: 13px; color: var(--neutral-700); line-height: 1.6;
}
.pl-detail__section { margin-bottom: 20px; }
.pl-detail__title { font-size: 13px; font-weight: 600; margin-bottom: 8px; color: var(--neutral-800); }
.pl-detail__steps { display: flex; flex-wrap: wrap; gap: 6px; }
.pl-detail__stepchip {
  padding: 4px 10px; background: var(--neutral-100); border-radius: 4px;
  font-size: 12px; color: var(--neutral-700);
}
.pl-detail__empty { color: var(--neutral-500); font-size: 12px; padding: 20px; text-align: center; }
</style>
