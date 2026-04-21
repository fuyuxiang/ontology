<template>
  <div class="ds-page">
    <div class="ds-page__header">
      <div>
        <h1 class="text-display">数据源管理</h1>
        <p class="text-caption" style="margin-top: 4px;">连接配置 · 状态监控 · 数据接入</p>
      </div>
      <div class="ds-page__actions">
        <button class="btn-primary" @click="openCreate">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 2v10M2 7h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          新建数据源
        </button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="ds-page__stats">
      <div class="stat-card stat-card--semantic">
        <div class="stat-card__value">{{ store.stats.total }}</div>
        <div class="stat-card__label">总数据源</div>
      </div>
      <div class="stat-card stat-card--dynamic">
        <div class="stat-card__value">{{ store.stats.enabled }}</div>
        <div class="stat-card__label">运行中</div>
      </div>
      <div class="stat-card stat-card--kinetic">
        <div class="stat-card__value">{{ store.stats.stopped }}</div>
        <div class="stat-card__label">已停止</div>
      </div>
      <div class="stat-card stat-card--error">
        <div class="stat-card__value">{{ store.stats.error }}</div>
        <div class="stat-card__label">异常</div>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="ds-page__filter">
      <input v-model="search" class="ds-search" placeholder="搜索数据源名称..." @input="onSearch" />
      <div class="ds-filter-tags">
        <button v-for="f in typeFilters" :key="f.value" class="filter-tag" :class="{ 'filter-tag--active': activeType === f.value }" @click="setTypeFilter(f.value)">{{ f.label }}</button>
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="ds-page__table-wrap">
      <table class="ds-table">
        <thead>
          <tr>
            <th>数据源名称</th>
            <th>类别</th>
            <th>类型</th>
            <th>连接地址</th>
            <th>数据库</th>
            <th>记录条数</th>
            <th>管道状态</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="ds in store.items" :key="ds.id">
            <td class="text-body-medium">{{ TABLE_NAME_MAP[ds.table_name] || ds.name }}</td>
            <td><span class="ds-cat-badge" :class="`ds-cat-badge--${(ds as any).source_category || 'database'}`">{{ catLabel((ds as any).source_category) }}</span></td>
            <td><span class="ds-type-badge">{{ ds.type }}</span></td>
            <td class="text-code">{{ ds.host }}:{{ ds.port }}</td>
            <td>{{ ds.database || '-' }}</td>
            <td>{{ ds.record_count }}</td>
            <td>
              <button class="ds-toggle" :class="ds.enabled ? 'ds-toggle--on' : 'ds-toggle--off'" @click="handleToggle(ds)" :disabled="toggling === ds.id">
                <span class="ds-toggle__dot"></span>
                <span class="ds-toggle__label">{{ ds.enabled ? '运行中' : '已停止' }}</span>
              </button>
            </td>
            <td class="text-caption">{{ formatTime(ds.created_at) }}</td>
            <td class="ds-table__actions">
              <button class="btn-sm-sync" @click="handleRefresh(ds)" :disabled="refreshing === ds.id">
                {{ refreshing === ds.id ? '同步中...' : '同步' }}
              </button>
              <button class="btn-sm-detail" @click="openDetail(ds)">详情</button>
              <button class="btn-sm-del" @click="handleDelete(ds)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="store.items.length === 0 && !store.loading" class="ds-empty">
        <p class="text-caption">暂无数据源，点击「新建数据源」添加</p>
      </div>
    </div>

    <!-- 新建弹窗 -->
    <ModalDialog :visible="showModal" title="新建数据源" width="580px" @close="showModal = false">
      <!-- Step 1: 选择类别 -->
      <div v-if="createStep === 1" class="ds-category-grid">
        <div v-for="cat in categories" :key="cat.value" class="ds-category-card" @click="selectCategory(cat.value)">
          <span class="ds-category-icon" v-html="cat.icon"></span>
          <div class="ds-category-name">{{ cat.label }}</div>
          <div class="ds-category-desc">{{ cat.desc }}</div>
        </div>
      </div>

      <!-- Step 2: 数据库 -->
      <form v-else-if="createStep === 2 && createCategory === 'database'" class="ds-form" @submit.prevent="handleSave">
        <div class="ds-form__back" @click="createStep = 1">← 返回</div>
        <div class="form-row-inline">
          <div class="form-row" style="flex:1">
            <label class="form-label">类型</label>
            <select v-model="form.type" class="form-input" required>
              <option v-for="t in dsTypes" :key="t" :value="t">{{ t }}</option>
            </select>
          </div>
          <div class="form-row" style="flex:1">
            <label class="form-label">端口</label>
            <input v-model.number="form.port" class="form-input" type="number" required />
          </div>
        </div>
        <div class="form-row">
          <label class="form-label">主机地址</label>
          <input v-model="form.host" class="form-input form-input--code" placeholder="如：192.168.1.100" required />
        </div>
        <div class="form-row-inline">
          <div class="form-row" style="flex:1">
            <label class="form-label">数据库名</label>
            <input v-model="form.database" class="form-input" placeholder="可选" />
          </div>
        </div>
        <div class="form-row-inline">
          <div class="form-row" style="flex:1">
            <label class="form-label">用户名</label>
            <input v-model="form.username" class="form-input" />
          </div>
          <div class="form-row" style="flex:1">
            <label class="form-label">密码</label>
            <input v-model="form.password" class="form-input" type="password" />
          </div>
        </div>
        <div class="form-row">
          <label class="form-label">描述</label>
          <input v-model="form.description" class="form-input" placeholder="可选" />
        </div>
        <div class="ds-form__footer">
          <button type="button" class="btn-secondary" @click="showModal = false">取消</button>
          <button type="submit" class="btn-primary" :disabled="saving">{{ saving ? '连接中...' : '保存' }}</button>
        </div>
      </form>

      <!-- Step 2: 文件上传 -->
      <div v-else-if="createStep === 2 && createCategory === 'file'" class="ds-form">
        <div class="ds-form__back" @click="createStep = 1">← 返回</div>
        <div class="form-row">
          <label class="form-label">数据源名称</label>
          <input v-model="fileForm.name" class="form-input" placeholder="如：产品手册" required />
        </div>
        <div class="form-row">
          <label class="form-label">上传文件</label>
          <div class="ds-upload-zone" :class="{ 'ds-upload-zone--active': dragOver }"
            @dragover.prevent="dragOver = true" @dragleave="dragOver = false"
            @drop.prevent="onFileDrop" @click="fileInputRef?.click()">
            <input ref="fileInputRef" type="file" style="display:none"
              accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.gif,.mp4,.avi,.mov"
              @change="onFileChange" />
            <div v-if="!selectedFile" class="ds-upload-hint">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none"><path d="M12 16V8M8 12l4-4 4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><rect x="3" y="3" width="18" height="18" rx="3" stroke="currentColor" stroke-width="1.5"/></svg>
              <p>点击或拖拽文件到此处</p>
              <p class="ds-upload-types">支持 PDF / Word / Excel / 图片 / 视频</p>
            </div>
            <div v-else class="ds-upload-selected">
              <span class="ds-file-icon">{{ fileTypeIcon(selectedFile.name) }}</span>
              <span>{{ selectedFile.name }}</span>
              <span class="ds-file-size">{{ (selectedFile.size / 1024).toFixed(1) }} KB</span>
            </div>
          </div>
        </div>
        <div class="form-row">
          <label class="form-label">描述</label>
          <input v-model="fileForm.description" class="form-input" placeholder="可选" />
        </div>
        <div class="ds-form__footer">
          <button type="button" class="btn-secondary" @click="showModal = false">取消</button>
          <button class="btn-primary" :disabled="saving || !selectedFile" @click="handleFileUpload">{{ saving ? '上传中...' : '上传' }}</button>
        </div>
      </div>

      <!-- Step 2: REST API -->
      <div v-else-if="createStep === 2 && createCategory === 'api'" class="ds-form">
        <div class="ds-form__back" @click="createStep = 1">← 返回</div>
        <div class="form-row">
          <label class="form-label">数据源名称</label>
          <input v-model="apiForm.name" class="form-input" required />
        </div>
        <div class="form-row-inline">
          <div class="form-row" style="flex:0 0 90px">
            <label class="form-label">方法</label>
            <select v-model="apiForm.api_method" class="form-input">
              <option>GET</option><option>POST</option>
            </select>
          </div>
          <div class="form-row" style="flex:1">
            <label class="form-label">API URL</label>
            <input v-model="apiForm.api_url" class="form-input form-input--code" placeholder="https://..." required />
          </div>
        </div>
        <div class="form-row">
          <label class="form-label">请求头（JSON）</label>
          <textarea v-model="apiForm.api_headers_str" class="form-input form-input--ta" placeholder='{"Authorization": "Bearer ..."}' rows="2"></textarea>
        </div>
        <div class="form-row">
          <label class="form-label">轮询间隔（秒）</label>
          <input v-model.number="apiForm.poll_interval" class="form-input" type="number" min="10" />
        </div>
        <div class="form-row">
          <label class="form-label">描述</label>
          <input v-model="apiForm.description" class="form-input" placeholder="可选" />
        </div>
        <div class="ds-form__footer">
          <button type="button" class="btn-secondary" @click="showModal = false">取消</button>
          <button class="btn-primary" :disabled="saving" @click="handleApiSource">{{ saving ? '连接中...' : '保存' }}</button>
        </div>
      </div>

      <!-- Step 2: 消息队列 -->
      <div v-else-if="createStep === 2 && createCategory === 'mq'" class="ds-form">
        <div class="ds-form__back" @click="createStep = 1">← 返回</div>
        <div class="form-row">
          <label class="form-label">数据源名称</label>
          <input v-model="mqForm.name" class="form-input" required />
        </div>
        <div class="form-row-inline">
          <div class="form-row" style="flex:1">
            <label class="form-label">Broker 地址</label>
            <input v-model="mqForm.host" class="form-input form-input--code" placeholder="如：192.168.1.100" required />
          </div>
          <div class="form-row" style="flex:0 0 100px">
            <label class="form-label">端口</label>
            <input v-model.number="mqForm.port" class="form-input" type="number" />
          </div>
        </div>
        <div class="form-row-inline">
          <div class="form-row" style="flex:1">
            <label class="form-label">Topic</label>
            <input v-model="mqForm.mq_topic" class="form-input" required />
          </div>
          <div class="form-row" style="flex:1">
            <label class="form-label">Consumer Group</label>
            <input v-model="mqForm.mq_group" class="form-input" />
          </div>
        </div>
        <div class="form-row-inline">
          <div class="form-row" style="flex:1">
            <label class="form-label">用户名</label>
            <input v-model="mqForm.username" class="form-input" />
          </div>
          <div class="form-row" style="flex:1">
            <label class="form-label">密码</label>
            <input v-model="mqForm.password" class="form-input" type="password" />
          </div>
        </div>
        <div class="ds-form__footer">
          <button type="button" class="btn-secondary" @click="showModal = false">取消</button>
          <button class="btn-primary" :disabled="saving" @click="handleMqSource">{{ saving ? '保存中...' : '保存' }}</button>
        </div>
      </div>
    </ModalDialog>

    <!-- 详情弹窗 -->
    <ModalDialog :visible="showDetail" :title="detailName + ' — 数据预览'" width="800px" @close="showDetail = false">
      <div>
        <div v-if="detailLoading" class="ds-detail-loading">加载中...</div>
        <div v-else-if="detailParsed" class="ds-parsed-content">
          <p class="text-caption" style="margin-bottom: 8px;">解析内容预览</p>
          <pre class="ds-parsed-pre">{{ detailParsed.slice(0, 3000) }}{{ detailParsed.length > 3000 ? '\n...(内容已截断)' : '' }}</pre>
        </div>
        <div v-else class="ds-preview-table-wrap">
          <p class="text-caption" style="margin-bottom: 8px;">前 20 条数据</p>
          <table class="ds-table ds-preview-table">
            <thead>
              <tr>
                <th v-for="col in previewColumns" :key="col">{{ col }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in previewRows" :key="i">
                <td v-for="(cell, j) in row" :key="j">{{ cell ?? '-' }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="previewRows.length === 0 && previewColumns.length === 0" class="ds-detail-empty">
            <p class="text-caption">查询失败或该表暂无数据</p>
          </div>
        </div>
      </div>
    </ModalDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useDataSourceStore } from '../../store/datasource'
import ModalDialog from '../../components/common/ModalDialog.vue'
import * as api from '../../api/datasource'
import type { DataSource, DataSourceCreate } from '../../types/datasource'
import client from '../../api/client'

const store = useDataSourceStore()

const search = ref('')
const activeType = ref('')
const showModal = ref(false)
const saving = ref(false)
const toggling = ref<string | null>(null)
const refreshing = ref<string | null>(null)

// 多步骤新建
const createStep = ref(1)
const createCategory = ref<'database' | 'file' | 'api' | 'mq'>('database')

// 文件上传
const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const dragOver = ref(false)
const fileForm = ref({ name: '', description: '' })

// API 数据源
const apiForm = ref({ name: '', api_url: '', api_method: 'GET', api_headers_str: '', poll_interval: 60, description: '' })

// MQ 数据源
const mqForm = ref({ name: '', host: '', port: 9092, mq_topic: '', mq_group: 'ontology-consumer', username: '', password: '', description: '' })

// 详情弹窗状态
const showDetail = ref(false)
const detailName = ref('')
const detailLoading = ref(false)
const previewColumns = ref<string[]>([])
const previewRows = ref<unknown[][]>([])
const detailParsed = ref('')

const dsTypes = ['mysql', 'postgresql', 'oracle', 'sqlserver', 'clickhouse', 'hive', 'kafka', 'elasticsearch', 'api']

const TABLE_NAME_MAP: Record<string, string> = {
  'dwa_v_d_cus_cb_user_info': 'CBSS 用户信息系统',
  'dwd_d_cus_np_turn_query_user': '携转资格查询系统',
  'dwa_v_d_cus_cb_act_info': 'CBSS 活动合约系统',
  'dwa_v_m_cus_cb_sing_charge': 'CBSS 出账系统',
  'dwd_m_mrt_al_chl_owe': '欠费信息系统',
  'dwd_d_use_cb_f_voice': '语音详单系统',
  'dwd_d_evt_kf_order_main': '客服工单系统',
  'dwd_d_cus_qk_turn_maintain': '全客携转维系系统',
  'DWA_V_D_CUS_CB_OM_DATUM': '融合业务信息系统',
  't_mnp_risk_warning': '携转预警结果存储',
}

const categories = [
  { value: 'database', label: '关系型数据库', desc: 'MySQL / PostgreSQL / Oracle 等', icon: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><ellipse cx="12" cy="6" rx="8" ry="3" stroke="currentColor" stroke-width="1.5"/><path d="M4 6v6c0 1.66 3.58 3 8 3s8-1.34 8-3V6" stroke="currentColor" stroke-width="1.5"/><path d="M4 12v6c0 1.66 3.58 3 8 3s8-1.34 8-3v-6" stroke="currentColor" stroke-width="1.5"/></svg>` },
  { value: 'file', label: '文档 / 文件', desc: 'PDF / Word / Excel / 图片 / 视频', icon: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" stroke="currentColor" stroke-width="1.5"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { value: 'api', label: 'REST API', desc: 'HTTP 接口定时拉取', icon: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" stroke="currentColor" stroke-width="1.5"/><path d="M2 12h20M12 2a15.3 15.3 0 010 20M12 2a15.3 15.3 0 000 20" stroke="currentColor" stroke-width="1.5"/></svg>` },
  { value: 'mq', label: '消息队列', desc: 'Kafka / RabbitMQ 等', icon: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><rect x="2" y="7" width="20" height="10" rx="2" stroke="currentColor" stroke-width="1.5"/><path d="M6 12h12M2 10h20M2 14h20" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
]

const typeFilters = [
  { label: '全部', value: '' },
  { label: '数据库', value: 'database' },
  { label: '文件', value: 'file' },
  { label: 'API', value: 'api' },
  { label: 'MQ', value: 'mq' },
  { label: 'MySQL', value: 'mysql' },
  { label: 'PostgreSQL', value: 'postgresql' },
  { label: 'Kafka', value: 'kafka' },
]

function catLabel(cat: string) {
  const m: Record<string, string> = { database: '数据库', file: '文件', api: 'API', mq: 'MQ' }
  return m[cat] || '数据库'
}

function fileTypeIcon(name: string) {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  if (['pdf'].includes(ext)) return '📄'
  if (['doc', 'docx'].includes(ext)) return '📝'
  if (['xls', 'xlsx'].includes(ext)) return '📊'
  if (['png', 'jpg', 'jpeg', 'gif'].includes(ext)) return '🖼'
  if (['mp4', 'avi', 'mov'].includes(ext)) return '🎬'
  return '📁'
}

onMounted(() => store.fetchList())

function formatTime(t: string) {
  return new Date(t).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function setTypeFilter(v: string) {
  activeType.value = v
  store.fetchList({ type: v || undefined, q: search.value || undefined })
}

function onSearch() {
  store.fetchList({ type: activeType.value || undefined, q: search.value || undefined })
}

function openCreate() {
  createStep.value = 1
  selectedFile.value = null
  fileForm.value = { name: '', description: '' }
  apiForm.value = { name: '', api_url: '', api_method: 'GET', api_headers_str: '', poll_interval: 60, description: '' }
  mqForm.value = { name: '', host: '', port: 9092, mq_topic: '', mq_group: 'ontology-consumer', username: '', password: '', description: '' }
  showModal.value = true
}

function selectCategory(cat: string) {
  createCategory.value = cat as any
  createStep.value = 2
  if (cat === 'database') form.value = emptyForm()
}

const emptyForm = (): DataSourceCreate => ({
  type: 'mysql', host: '', port: 3306, database: '', username: '', password: '', description: '',
})
const form = ref<DataSourceCreate>(emptyForm())

async function handleSave() {
  saving.value = true
  try {
    await api.createDataSource(form.value)
    showModal.value = false
    store.fetchList({ type: activeType.value || undefined, q: search.value || undefined })
  } catch (e: any) {
    alert(e.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

function onFileDrop(e: DragEvent) {
  dragOver.value = false
  const f = e.dataTransfer?.files[0]
  if (f) { selectedFile.value = f; if (!fileForm.value.name) fileForm.value.name = f.name.replace(/\.[^.]+$/, '') }
}

function onFileChange(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (f) { selectedFile.value = f; if (!fileForm.value.name) fileForm.value.name = f.name.replace(/\.[^.]+$/, '') }
}

async function handleFileUpload() {
  if (!selectedFile.value) return
  saving.value = true
  try {
    const fd = new FormData()
    fd.append('file', selectedFile.value)
    fd.append('name', fileForm.value.name || selectedFile.value.name)
    fd.append('description', fileForm.value.description)
    await client.post('/datasources/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    showModal.value = false
    store.fetchList()
  } catch (e: any) {
    alert(e.response?.data?.detail || '上传失败')
  } finally {
    saving.value = false
  }
}

async function handleApiSource() {
  saving.value = true
  try {
    let headers: Record<string, string> | null = null
    if (apiForm.value.api_headers_str.trim()) {
      try { headers = JSON.parse(apiForm.value.api_headers_str) } catch { alert('请求头 JSON 格式错误'); saving.value = false; return }
    }
    await client.post('/datasources/api-source', { ...apiForm.value, api_headers: headers })
    showModal.value = false
    store.fetchList()
  } catch (e: any) {
    alert(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleMqSource() {
  saving.value = true
  try {
    await client.post('/datasources/mq-source', mqForm.value)
    showModal.value = false
    store.fetchList()
  } catch (e: any) {
    alert(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleToggle(ds: DataSource) {
  toggling.value = ds.id
  try {
    await api.toggleDataSource(ds.id)
    store.fetchList({ type: activeType.value || undefined, q: search.value || undefined })
  } catch {
    alert('操作失败')
  } finally {
    toggling.value = null
  }
}

async function handleDelete(ds: DataSource) {
  if (!confirm(`确认删除数据源「${TABLE_NAME_MAP[ds.table_name] || ds.name}」？`)) return
  try {
    await api.deleteDataSource(ds.id)
    store.fetchList({ type: activeType.value || undefined, q: search.value || undefined })
  } catch {
    alert('删除失败')
  }
}

async function handleRefresh(ds: DataSource) {
  refreshing.value = ds.id
  try {
    const res = await api.refreshTables(ds.id)
    alert(`同步完成，共 ${res.record_count} 条记录`)
    store.fetchList({ type: activeType.value || undefined, q: search.value || undefined })
  } catch (e: any) {
    alert(e.response?.data?.detail || '同步失败')
  } finally {
    refreshing.value = null
  }
}

async function openDetail(ds: DataSource) {
  detailName.value = TABLE_NAME_MAP[ds.table_name] || ds.name
  previewColumns.value = []
  previewRows.value = []
  detailParsed.value = (ds as any).parsed_content || ''
  showDetail.value = true
  if ((ds as any).source_category === 'file' || (ds as any).source_category === 'api') return
  detailLoading.value = true
  try {
    const res = await api.previewDatasource(ds.id)
    previewColumns.value = res.columns
    previewRows.value = res.rows
  } catch (e: any) {
    alert(e.response?.data?.detail || '查询数据失败')
  } finally {
    detailLoading.value = false
  }
}
</script>

<style scoped>
.ds-page { padding: 28px 32px; max-width: 1200px; }
.ds-page__header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.ds-page__actions { display: flex; gap: 8px; }

.ds-page__stats { display: flex; gap: 12px; margin-bottom: 20px; }
.stat-card { flex: 1; padding: 16px; border-radius: var(--radius-lg); border: 1px solid var(--neutral-100); background: var(--neutral-0); }
.stat-card__value { font-size: var(--text-h1-size); font-weight: 700; }
.stat-card__label { font-size: var(--text-code-size); color: var(--neutral-500); margin-top: 2px; }
.stat-card--semantic .stat-card__value { color: var(--semantic-600); }
.stat-card--dynamic .stat-card__value { color: var(--dynamic-600); }
.stat-card--kinetic .stat-card__value { color: var(--kinetic-600); }
.stat-card--error .stat-card__value { color: var(--status-error); }

.ds-page__filter { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.ds-search { padding: 8px 12px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); font-size: var(--text-body-size); width: 240px; color: var(--neutral-800); background: var(--neutral-0); outline: none; }
.ds-search:focus { border-color: var(--semantic-500); }
.ds-filter-tags { display: flex; gap: 6px; }
.filter-tag { padding: 4px 12px; border-radius: var(--radius-full); border: 1px solid var(--neutral-200); background: var(--neutral-0); font-size: var(--text-code-size); color: var(--neutral-600); cursor: pointer; }
.filter-tag--active { background: var(--semantic-600); color: var(--neutral-0); border-color: var(--semantic-600); }

.ds-page__table-wrap { border: 1px solid var(--neutral-100); border-radius: var(--radius-lg); overflow: hidden; background: var(--neutral-0); }
.ds-table { width: 100%; border-collapse: collapse; font-size: var(--text-body-size); }
.ds-table th { text-align: left; padding: 10px 14px; font-size: var(--text-code-size); font-weight: 600; color: var(--neutral-500); background: var(--neutral-50); border-bottom: 1px solid var(--neutral-100); }
.ds-table td { padding: 12px 14px; border-bottom: 1px solid var(--neutral-50); color: var(--neutral-800); }
.ds-table tbody tr:hover { background: var(--neutral-25, var(--neutral-50)); }
.ds-table tbody tr:last-child td { border-bottom: none; }

.ds-type-badge { display: inline-block; padding: 2px 8px; border-radius: var(--radius-full); font-size: var(--text-caption-size); font-weight: 600; background: var(--semantic-50); color: var(--semantic-600); text-transform: uppercase; }
.ds-status { display: inline-flex; align-items: center; gap: 5px; font-size: var(--text-code-size); font-weight: 500; }
.ds-status::before { content: ''; width: 6px; height: 6px; border-radius: 50%; }
.ds-status--active { color: var(--dynamic-600); }
.ds-status--active::before { background: var(--dynamic-500); }
.ds-status--inactive { color: var(--neutral-500); }
.ds-status--inactive::before { background: var(--neutral-400); }
.ds-status--error { color: var(--status-error); }
.ds-status--error::before { background: var(--status-error); }

.ds-table__actions { display: flex; gap: 6px; }
.btn-sm-sync, .btn-sm-detail, .btn-sm-edit, .btn-sm-del { display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px; border-radius: var(--radius-md); font-size: var(--text-caption-size); font-weight: 500; cursor: pointer; border: 1px solid; }
.btn-sm-sync { border-color: var(--kinetic-400); background: var(--kinetic-50); color: var(--kinetic-700); }
.btn-sm-sync:hover { background: var(--kinetic-500); color: var(--neutral-0); }
.btn-sm-sync:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-sm-detail { border-color: var(--semantic-400); background: var(--semantic-50); color: var(--semantic-600); }
.btn-sm-detail:hover { background: var(--semantic-500); color: var(--neutral-0); }
.btn-sm-edit { border-color: var(--semantic-400); background: var(--semantic-50); color: var(--semantic-600); }
.btn-sm-edit:hover { background: var(--semantic-500); color: var(--neutral-0); }
.btn-sm-del { border-color: var(--status-error); background: var(--status-error-bg); color: var(--status-error); }
.btn-sm-del:hover { background: var(--status-error); color: var(--neutral-0); }

.ds-toggle { display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: var(--radius-full); font-size: var(--text-code-size); font-weight: 500; cursor: pointer; border: none; transition: all var(--transition-fast); }
.ds-toggle:disabled { opacity: 0.6; cursor: not-allowed; }
.ds-toggle__dot { width: 8px; height: 8px; border-radius: 50%; transition: background var(--transition-fast); }
.ds-toggle--on { background: var(--dynamic-50); color: var(--dynamic-700); }
.ds-toggle--on .ds-toggle__dot { background: var(--dynamic-500); }
.ds-toggle--on:hover { background: var(--dynamic-100); }
.ds-toggle--off { background: var(--neutral-100); color: var(--neutral-500); }
.ds-toggle--off .ds-toggle__dot { background: var(--neutral-400); }
.ds-toggle--off:hover { background: var(--neutral-200); }

.ds-empty { padding: 48px; text-align: center; }

.ds-form { display: flex; flex-direction: column; gap: 14px; }
.ds-form__footer { display: flex; justify-content: flex-end; gap: 8px; padding-top: 8px; }
.form-row { display: flex; flex-direction: column; gap: 4px; }
.form-row-inline { display: flex; gap: 12px; }
.form-label { font-size: var(--text-code-size); font-weight: 500; color: var(--neutral-600); }
.form-input { padding: 8px 12px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); font-size: var(--text-body-size); color: var(--neutral-800); background: var(--neutral-0); outline: none; }
.form-input:focus { border-color: var(--semantic-500); }
.form-input--code { font-family: var(--font-mono); font-size: var(--text-code-size); }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: var(--radius-md); border: none; background: var(--semantic-600); color: var(--neutral-0); font-size: var(--text-body-size); font-weight: 500; cursor: pointer; }
.btn-primary:hover { background: var(--semantic-700); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-secondary { padding: 8px 16px; border-radius: var(--radius-md); border: 1px solid var(--neutral-200); background: var(--neutral-0); color: var(--neutral-700); font-size: var(--text-body-size); font-weight: 500; cursor: pointer; }
.btn-secondary:hover { background: var(--neutral-50); }

.ds-detail-loading { padding: 32px; text-align: center; color: var(--neutral-500); font-size: var(--text-body-size); }
.ds-detail-empty { padding: 32px; text-align: center; }
.ds-detail-tables { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px; }
.ds-detail-table-item { display: flex; align-items: center; gap: 8px; padding: 10px 12px; border: 1px solid var(--neutral-100); border-radius: var(--radius-md); cursor: pointer; font-size: var(--text-body-size); color: var(--neutral-700); transition: all var(--transition-fast); }
.ds-detail-table-item:hover { background: var(--semantic-50); border-color: var(--semantic-300); color: var(--semantic-700); }
.ds-detail-table-item svg { color: var(--neutral-400); flex-shrink: 0; }
.ds-detail-table-item:hover svg { color: var(--semantic-500); }

.ds-preview-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.btn-sm-back { font-size: var(--text-code-size); padding: 4px 12px; }
.ds-preview-table-wrap { overflow-x: auto; max-height: 400px; overflow-y: auto; }
.ds-preview-table { font-size: var(--text-code-size); }
.ds-preview-table th { white-space: nowrap; position: sticky; top: 0; z-index: 1; }
.ds-preview-table td { white-space: nowrap; max-width: 200px; overflow: hidden; text-overflow: ellipsis; }

/* 多模态新建 */
.ds-category-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 4px 0 8px; }
.ds-category-card {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 20px 16px; border: 1.5px solid var(--neutral-100); border-radius: var(--radius-lg);
  cursor: pointer; transition: all .15s; text-align: center;
}
.ds-category-card:hover { border-color: var(--semantic-400); background: var(--semantic-50, #f0f4ff); }
.ds-category-icon { color: var(--semantic-500); }
.ds-category-name { font-size: var(--text-body-size); font-weight: 600; color: var(--neutral-800); }
.ds-category-desc { font-size: var(--text-caption-size); color: var(--neutral-500); }
.ds-form__back { font-size: var(--text-code-size); color: var(--semantic-500); cursor: pointer; margin-bottom: 12px; display: inline-block; }
.ds-form__back:hover { text-decoration: underline; }
.ds-upload-zone {
  border: 2px dashed var(--neutral-200); border-radius: var(--radius-lg);
  padding: 28px 16px; text-align: center; cursor: pointer; transition: all .15s;
  color: var(--neutral-500);
}
.ds-upload-zone--active { border-color: var(--semantic-400); background: var(--semantic-50, #f0f4ff); }
.ds-upload-zone:hover { border-color: var(--semantic-300); }
.ds-upload-hint p { margin: 6px 0 0; font-size: var(--text-body-size); }
.ds-upload-types { font-size: var(--text-caption-size); color: var(--neutral-400); }
.ds-upload-selected { display: flex; align-items: center; gap: 10px; justify-content: center; font-size: var(--text-body-size); }
.ds-file-icon { font-size: var(--text-h1-size); }
.ds-file-size { font-size: var(--text-caption-size); color: var(--neutral-400); }
.ds-cat-badge { font-size: var(--text-caption-upper-size); font-weight: 600; padding: 2px 7px; border-radius: 4px; }
.ds-cat-badge--database { background: var(--semantic-100); color: var(--semantic-700); }
.ds-cat-badge--file { background: var(--dynamic-100); color: var(--dynamic-800); }
.ds-cat-badge--api { background: var(--kinetic-100); color: var(--kinetic-800); }
.ds-cat-badge--mq { background: var(--status-error-bg); color: var(--kinetic-900); }
.ds-parsed-content { max-height: 400px; overflow-y: auto; }
.ds-parsed-pre { font-size: var(--text-caption-size); font-family: var(--font-mono); white-space: pre-wrap; word-break: break-all; background: var(--neutral-50, #f8fafc); border: 1px solid var(--neutral-100); border-radius: var(--radius-md); padding: 12px; color: var(--neutral-700); line-height: 1.6; }
.form-input--ta { resize: vertical; min-height: 60px; }
</style>
