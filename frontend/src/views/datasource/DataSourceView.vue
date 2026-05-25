<template>
  <div class="ds-page">
    <!-- 统计行（紧凑横排，仿 DataFoundry） -->
    <div class="ds-stats-row">
      <a-statistic title="数据源总数" :value="store.stats.total">
        <template #prefix><DatabaseOutlined style="color: var(--status-info)" /></template>
      </a-statistic>
      <a-statistic title="在线" :value="store.stats.enabled" :value-style="{ color: 'var(--status-success)' }">
        <template #prefix><CheckCircleOutlined style="color: var(--status-success)" /></template>
      </a-statistic>
      <a-statistic title="离线" :value="store.stats.stopped" :value-style="{ color: 'var(--status-error)' }">
        <template #prefix><CloseCircleOutlined style="color: var(--status-error)" /></template>
      </a-statistic>
      <span class="ds-stats-row__spacer"></span>
      <a-button type="primary" @click="openCreate">
        <template #icon><PlusOutlined /></template>
        新增数据源
      </a-button>
    </div>

    <!-- 工具栏 -->
    <div class="ds-toolbar">
      <a-input-search v-model:value="search" placeholder="搜索数据源名称..." style="width: 260px" allow-clear @search="onSearch" @change="onSearch" />
      <a-segmented v-model:value="activeType" :options="typeFilters" @change="onTypeChange" />
    </div>

    <!-- 数据表格 -->
    <a-table
      class="ds-table"
      :columns="columns"
      :data-source="store.items"
      :loading="store.loading"
      :pagination="false"
      row-key="id"
      size="middle"
      :scroll="{ x: 1180 }"
      @resizeColumn="onResizeColumn"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'name'">
          <span class="ds-cell-name">{{ TABLE_NAME_MAP[record.table_name] || record.name }}</span>
        </template>
        <template v-else-if="column.key === 'engine'">
          <a-tag :color="engineColor(record.type)" class="ds-engine-tag">{{ engineLabel(record.type) }}</a-tag>
        </template>
        <template v-else-if="column.key === 'status'">
          <span class="ds-status">
            <span class="ds-status__dot" :style="{ background: statusColor(record) }"></span>
            <span :style="{ color: statusColor(record) }">{{ statusLabel(record) }}</span>
            <SyncOutlined v-if="testing === record.id" spin :style="{ marginLeft: '4px', color: 'var(--status-warning)', fontSize: '12px' }" />
          </span>
        </template>
        <template v-else-if="column.key === 'host'">
          <span class="ds-cell-code">{{ record.host }}:{{ record.port }}</span>
        </template>
        <template v-else-if="column.key === 'actions'">
          <a-space :size="4" wrap>
            <a-button type="link" size="small" @click="openDetail(record)">
              <template #icon><EyeOutlined /></template>
              详情
            </a-button>
            <a-button type="link" size="small" :loading="testing === record.id" @click="handleTestConnection(record)">
              <template #icon><LinkOutlined /></template>
              测试连接
            </a-button>
            <a-button type="link" size="small" @click="handleCreateDataset(record)">
              <template #icon><PlusOutlined /></template>
              新建数据集
            </a-button>
            <a-popconfirm :title="`确认删除「${TABLE_NAME_MAP[record.table_name] || record.name}」？`" @confirm="handleDelete(record)">
              <a-button type="link" size="small" danger>
                <template #icon><DeleteOutlined /></template>
                删除
              </a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
      <template #emptyText>
        <a-empty description="暂无数据源，点击上方「新增数据源」按钮添加外部数据连接" />
      </template>
    </a-table>

    <!-- 新建数据源弹窗 -->
    <a-modal v-model:open="showModal" title="新建数据源" :width="580" :footer="null" destroy-on-close>
      <!-- Step 1: 选择类别 -->
      <div v-if="createStep === 1" class="ds-category-grid">
        <div v-for="cat in categories" :key="cat.value" class="ds-category-card" @click="selectCategory(cat.value)">
          <span class="ds-category-icon" v-html="cat.icon"></span>
          <div class="ds-category-name">{{ cat.label }}</div>
          <div class="ds-category-desc">{{ cat.desc }}</div>
        </div>
      </div>

      <!-- Step 2: 数据库 -->
      <a-form v-else-if="createStep === 2 && createCategory === 'database'" layout="vertical">
        <a-button type="link" size="small" @click="createStep = 1" style="padding:0;margin-bottom:12px">← 返回</a-button>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="类型">
              <a-select v-model:value="form.type" :options="dsTypes.map(t => ({ value: t, label: t }))" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="端口">
              <a-input-number v-model:value="form.port" style="width:100%" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="主机地址">
          <a-input v-model:value="form.host" placeholder="如：192.168.1.100" class="input-mono" />
        </a-form-item>
        <a-form-item label="数据库名">
          <a-input v-model:value="form.database" placeholder="可选" />
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="用户名">
              <a-input v-model:value="form.username" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="密码">
              <a-input-password v-model:value="form.password" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="描述">
          <a-input v-model:value="form.description" placeholder="可选" />
        </a-form-item>
        <div class="ds-form__footer">
          <a-button @click="showModal = false">取消</a-button>
          <a-button type="primary" :loading="saving" @click="handleSave">保存</a-button>
        </div>
      </a-form>

      <!-- Step 2: 多模态数据 - 子类型选择 -->
      <div v-else-if="createStep === 2 && createCategory === 'file' && !fileSubType">
        <a-button type="link" size="small" @click="createStep = 1" style="padding:0;margin-bottom:12px">← 返回</a-button>
        <div class="ds-category-grid ds-category-grid--3">
          <div class="ds-category-card" @click="fileSubType = 'upload'">
            <span class="ds-category-icon"><UploadOutlined style="font-size:28px" /></span>
            <div class="ds-category-name">上传文件</div>
            <div class="ds-category-desc">PDF / Word / Excel / 图片 / 视频</div>
          </div>
          <div class="ds-category-card" @click="fileSubType = 'oss'">
            <span class="ds-category-icon"><CloudServerOutlined style="font-size:28px" /></span>
            <div class="ds-category-name">OSS 存储</div>
            <div class="ds-category-desc">S3 / MinIO / 阿里云 OSS</div>
          </div>
          <div class="ds-category-card" @click="fileSubType = 'directory'">
            <span class="ds-category-icon"><FolderOpenOutlined style="font-size:28px" /></span>
            <div class="ds-category-name">本地目录</div>
            <div class="ds-category-desc">扫描服务器本地文件目录</div>
          </div>
        </div>
      </div>

      <!-- Step 2: 多模态 - 上传文件 -->
      <a-form v-else-if="createStep === 2 && createCategory === 'file' && fileSubType === 'upload'" layout="vertical">
        <a-button type="link" size="small" @click="fileSubType = null" style="padding:0;margin-bottom:12px">← 返回</a-button>
        <a-form-item label="数据源名称">
          <a-input v-model:value="fileForm.name" placeholder="如：产品手册" />
        </a-form-item>
        <a-form-item label="上传文件">
          <div class="ds-upload-zone" :class="{ 'ds-upload-zone--active': dragOver }"
            @dragover.prevent="dragOver = true" @dragleave="dragOver = false"
            @drop.prevent="onFileDrop" @click="fileInputRef?.click()">
            <input ref="fileInputRef" type="file" style="display:none"
              accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.gif,.mp4,.avi,.mov"
              @change="onFileChange" />
            <div v-if="!selectedFile" class="ds-upload-hint">
              <UploadOutlined style="font-size:32px;color:var(--neutral-400)" />
              <p>点击或拖拽文件到此处</p>
              <p class="ds-upload-types">支持 PDF / Word / Excel / 图片 / 视频</p>
            </div>
            <div v-else class="ds-upload-selected">
              <FileOutlined style="font-size:22px" />
              <span>{{ selectedFile.name }}</span>
              <span class="ds-file-size">{{ (selectedFile.size / 1024).toFixed(1) }} KB</span>
            </div>
          </div>
        </a-form-item>
        <a-form-item label="描述">
          <a-input v-model:value="fileForm.description" placeholder="可选" />
        </a-form-item>
        <div class="ds-form__footer">
          <a-button @click="showModal = false">取消</a-button>
          <a-button type="primary" :loading="saving" :disabled="!selectedFile" @click="handleFileUpload">上传</a-button>
        </div>
      </a-form>

      <!-- Step 2: 多模态 - OSS 存储 -->
      <a-form v-else-if="createStep === 2 && createCategory === 'file' && fileSubType === 'oss'" layout="vertical">
        <a-button type="link" size="small" @click="fileSubType = null" style="padding:0;margin-bottom:12px">← 返回</a-button>
        <a-form-item label="数据源名称">
          <a-input v-model:value="ossForm.name" placeholder="如：产品图片库" />
        </a-form-item>
        <a-form-item label="Endpoint">
          <a-input v-model:value="ossForm.endpoint" placeholder="https://oss-cn-hangzhou.aliyuncs.com" class="input-mono" />
        </a-form-item>
        <a-form-item label="Bucket">
          <a-input v-model:value="ossForm.bucket" placeholder="my-bucket" />
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="Access Key">
              <a-input v-model:value="ossForm.access_key" class="input-mono" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="Secret Key">
              <a-input-password v-model:value="ossForm.secret_key" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="路径前缀">
          <a-input v-model:value="ossForm.prefix" placeholder="可选，如：data/images/" />
        </a-form-item>
        <a-form-item label="描述">
          <a-input v-model:value="ossForm.description" placeholder="可选" />
        </a-form-item>
        <div class="ds-form__footer">
          <a-button @click="showModal = false">取消</a-button>
          <a-button type="primary" :loading="saving" @click="handleOssSource">保存</a-button>
        </div>
      </a-form>

      <!-- Step 2: 多模态 - 本地目录 -->
      <a-form v-else-if="createStep === 2 && createCategory === 'file' && fileSubType === 'directory'" layout="vertical">
        <a-button type="link" size="small" @click="fileSubType = null" style="padding:0;margin-bottom:12px">← 返回</a-button>
        <a-form-item label="数据源名称">
          <a-input v-model:value="dirForm.name" placeholder="如：合同文档库" />
        </a-form-item>
        <a-form-item label="目录路径">
          <a-input v-model:value="dirForm.directory_path" placeholder="/data/documents" class="input-mono" />
        </a-form-item>
        <a-form-item label="文件类型过滤">
          <a-input v-model:value="dirForm.file_extensions" placeholder="可选，如：pdf,docx,xlsx（留空扫描全部）" />
        </a-form-item>
        <a-form-item label="描述">
          <a-input v-model:value="dirForm.description" placeholder="可选" />
        </a-form-item>
        <div class="ds-form__footer">
          <a-button @click="showModal = false">取消</a-button>
          <a-button type="primary" :loading="saving" @click="handleDirSource">保存</a-button>
        </div>
      </a-form>

      <!-- Step 2: REST API -->
      <a-form v-else-if="createStep === 2 && createCategory === 'api'" layout="vertical">
        <a-button type="link" size="small" @click="createStep = 1" style="padding:0;margin-bottom:12px">← 返回</a-button>
        <a-form-item label="数据源名称">
          <a-input v-model:value="apiForm.name" />
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="6">
            <a-form-item label="方法">
              <a-select v-model:value="apiForm.api_method" :options="[{value:'GET',label:'GET'},{value:'POST',label:'POST'}]" />
            </a-form-item>
          </a-col>
          <a-col :span="18">
            <a-form-item label="API URL">
              <a-input v-model:value="apiForm.api_url" placeholder="https://..." class="input-mono" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="请求头（JSON）">
          <a-textarea v-model:value="apiForm.api_headers_str" :rows="2" placeholder='{"Authorization": "Bearer ..."}' />
        </a-form-item>
        <a-form-item label="轮询间隔（秒）">
          <a-input-number v-model:value="apiForm.poll_interval" :min="10" style="width:100%" />
        </a-form-item>
        <a-form-item label="描述">
          <a-input v-model:value="apiForm.description" placeholder="可选" />
        </a-form-item>
        <div class="ds-form__footer">
          <a-button @click="showModal = false">取消</a-button>
          <a-button type="primary" :loading="saving" @click="handleApiSource">保存</a-button>
        </div>
      </a-form>

      <!-- Step 2: 消息队列 -->
      <a-form v-else-if="createStep === 2 && createCategory === 'mq'" layout="vertical">
        <a-button type="link" size="small" @click="createStep = 1" style="padding:0;margin-bottom:12px">← 返回</a-button>
        <a-form-item label="数据源名称">
          <a-input v-model:value="mqForm.name" />
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="16">
            <a-form-item label="Broker 地址">
              <a-input v-model:value="mqForm.host" placeholder="如：192.168.1.100" class="input-mono" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="端口">
              <a-input-number v-model:value="mqForm.port" style="width:100%" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="Topic">
              <a-input v-model:value="mqForm.mq_topic" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="Consumer Group">
              <a-input v-model:value="mqForm.mq_group" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="用户名">
              <a-input v-model:value="mqForm.username" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="密码">
              <a-input-password v-model:value="mqForm.password" />
            </a-form-item>
          </a-col>
        </a-row>
        <div class="ds-form__footer">
          <a-button @click="showModal = false">取消</a-button>
          <a-button type="primary" :loading="saving" @click="handleMqSource">保存</a-button>
        </div>
      </a-form>
    </a-modal>

    <!-- 详情弹窗 -->
    <a-modal v-model:open="showDetail" :title="detailName + ' — 数据预览'" :width="800" :footer="null" destroy-on-close>
      <a-spin v-if="detailLoading" tip="加载中..." style="display:block;text-align:center;padding:40px" />
      <div v-else-if="detailParsed" class="ds-parsed-content">
        <p style="margin-bottom:8px;color:var(--neutral-500);font-size:12px">解析内容预览</p>
        <pre class="ds-parsed-pre">{{ detailParsed.slice(0, 3000) }}{{ detailParsed.length > 3000 ? '\n...(内容已截断)' : '' }}</pre>
      </div>
      <div v-else>
        <p style="margin-bottom:8px;color:var(--neutral-500);font-size:12px">前 20 条数据</p>
        <a-table
          :columns="previewColumns.map(c => ({ title: c, dataIndex: c, key: c, ellipsis: true }))"
          :data-source="previewTableData"
          :pagination="false"
          size="small"
          :scroll="{ x: true, y: 360 }"
          bordered
        />
        <a-empty v-if="previewRows.length === 0 && previewColumns.length === 0" description="查询失败或该表暂无数据" />
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDataSourceStore } from '../../store/datasource'
import * as api from '../../api/datasource'
import type { DataSource, DataSourceCreate } from '../../types/datasource'
import client from '../../api/client'
import {
  SyncOutlined, DeleteOutlined, PlusOutlined,
  DatabaseOutlined, CheckCircleOutlined, CloseCircleOutlined,
  EyeOutlined, LinkOutlined,
  UploadOutlined, CloudServerOutlined, FolderOpenOutlined, FileOutlined,
} from '@ant-design/icons-vue'

const store = useDataSourceStore()
const router = useRouter()

const search = ref('')
const activeType = ref('全部')
const showModal = ref(false)
const saving = ref(false)
const testing = ref<string | null>(null)

const columns = ref([
  { title: '数据源名称', key: 'name', width: 240, resizable: true, ellipsis: true },
  { title: '数据源类型', key: 'engine', width: 140, resizable: true },
  { title: '状态', key: 'status', width: 120, resizable: true },
  { title: '连接地址', key: 'host', width: 220, resizable: true, ellipsis: true },
  { title: '操作', key: 'actions', width: 280, fixed: 'right' as const },
])

function onResizeColumn(w: number, col: any) {
  col.width = w
}

const typeFilters = [
  { value: '全部', label: '全部' },
  { value: 'mysql', label: 'MySQL' },
  { value: 'postgresql', label: 'PostgreSQL' },
  { value: 'oracle', label: 'Oracle' },
  { value: 'clickhouse', label: 'ClickHouse' },
  { value: 'file', label: '文件' },
  { value: 'api', label: 'API' },
]

// 多步骤新建
const createStep = ref(1)
const createCategory = ref<'database' | 'file' | 'api' | 'mq'>('database')

// 文件上传
const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const dragOver = ref(false)
const fileForm = ref({ name: '', description: '' })
const fileSubType = ref<'upload' | 'oss' | 'directory' | null>(null)

// OSS 数据源
const ossForm = ref({ name: '', endpoint: '', bucket: '', access_key: '', secret_key: '', prefix: '', description: '' })

// 本地目录数据源
const dirForm = ref({ name: '', directory_path: '', file_extensions: '', description: '' })

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

const previewTableData = computed(() =>
  previewRows.value.map((row, i) => {
    const obj: Record<string, unknown> = { _key: i }
    previewColumns.value.forEach((col, j) => { obj[col] = row[j] ?? '-' })
    return obj
  })
)

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
  { value: 'file', label: '多模态数据', desc: 'PDF / Word / Excel / 图片 / 视频', icon: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" stroke="currentColor" stroke-width="1.5"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { value: 'api', label: 'REST API', desc: 'HTTP 接口定时拉取', icon: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" stroke="currentColor" stroke-width="1.5"/><path d="M2 12h20M12 2a15.3 15.3 0 010 20M12 2a15.3 15.3 0 000 20" stroke="currentColor" stroke-width="1.5"/></svg>` },
  { value: 'mq', label: '消息队列', desc: 'Kafka / RabbitMQ 等', icon: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><rect x="2" y="7" width="20" height="10" rx="2" stroke="currentColor" stroke-width="1.5"/><path d="M6 12h12M2 10h20M2 14h20" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>` },
]

function catLabel(cat?: string) {
  const m: Record<string, string> = { database: '数据库', file: '文件', api: 'API', mq: '消息队列' }
  return m[cat || 'database'] || '数据库'
}
void catLabel

function catColor(cat?: string) {
  const m: Record<string, string> = { database: 'blue', file: 'green', api: 'orange', mq: 'red' }
  return m[cat || 'database'] || 'blue'
}
void catColor

// ── 引擎 / 状态 / 数据质量 渲染辅助 ──────────────────────────
const ENGINE_COLOR_MAP: Record<string, string> = {
  mysql: 'blue', postgresql: 'cyan', oracle: 'purple', sqlserver: 'geekblue',
  clickhouse: 'magenta', hive: 'green', kafka: 'red', elasticsearch: 'gold',
  api: 'orange',
}

function engineLabel(type?: string) {
  return (type || '').toUpperCase() || '—'
}

function engineColor(type?: string) {
  return ENGINE_COLOR_MAP[(type || '').toLowerCase()] || 'default'
}

function statusLabel(record: DataSource) {
  if (testing.value === record.id) return '测试中'
  if (record.status === 'error') return '连接异常'
  if (record.enabled) return '在线'
  return '离线'
}

function statusColor(record: DataSource) {
  if (testing.value === record.id) return 'var(--status-warning)'
  if (record.status === 'error') return 'var(--status-error)'
  if (record.enabled) return 'var(--status-success)'
  return 'var(--status-error)'
}

function formatRecords(n: number) {
  if (n == null) return '-'
  if (n >= 1e8) return (n / 1e8).toFixed(2) + '亿'
  if (n >= 1e4) return (n / 1e4).toFixed(1).replace(/\.0$/, '') + '万'
  return n.toLocaleString()
}

onMounted(() => store.fetchList())

function formatTime(t: string) {
  return new Date(t).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function onTypeChange(v: string) {
  const type = v === '全部' ? undefined : v
  store.fetchList({ type, q: search.value || undefined })
}

function onSearch() {
  const type = activeType.value === '全部' ? undefined : activeType.value
  store.fetchList({ type, q: search.value || undefined })
}

function openCreate() {
  createStep.value = 1
  fileSubType.value = null
  selectedFile.value = null
  fileForm.value = { name: '', description: '' }
  ossForm.value = { name: '', endpoint: '', bucket: '', access_key: '', secret_key: '', prefix: '', description: '' }
  dirForm.value = { name: '', directory_path: '', file_extensions: '', description: '' }
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
    onSearch()
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

async function handleOssSource() {
  saving.value = true
  try {
    await client.post('/datasources/oss-source', ossForm.value)
    showModal.value = false
    store.fetchList()
  } catch (e: any) {
    alert(e.response?.data?.detail || 'OSS 连接失败')
  } finally {
    saving.value = false
  }
}

async function handleDirSource() {
  saving.value = true
  try {
    const extensions = dirForm.value.file_extensions
      .split(',').map((s: string) => s.trim()).filter(Boolean)
    await client.post('/datasources/dir-source', {
      name: dirForm.value.name,
      directory_path: dirForm.value.directory_path,
      file_extensions: extensions,
      description: dirForm.value.description,
    })
    showModal.value = false
    store.fetchList()
  } catch (e: any) {
    alert(e.response?.data?.detail || '目录连接失败')
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

async function handleTestConnection(ds: DataSource) {
  testing.value = ds.id
  try {
    const res = await api.testConnection(ds.id)
    alert(res.success ? `连接正常：${res.message || 'OK'}` : `连接失败：${res.message || '请检查配置'}`)
    onSearch()
  } catch (e: any) {
    alert(e.response?.data?.detail || '测试连接失败')
  } finally {
    testing.value = null
  }
}

async function handleCreateDataset(ds: DataSource) {
  await router.push({ path: '/data/mapping', query: { datasourceId: ds.id } })
}

async function handleDelete(ds: DataSource) {
  try {
    await api.deleteDataSource(ds.id)
    onSearch()
  } catch {
    alert('删除失败')
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
.ds-page { padding: var(--space-8) var(--space-8); }

.ds-page__header {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: var(--space-5);
}
.ds-page__title {
  font-size: var(--text-display-size); font-weight: var(--text-display-weight);
  line-height: var(--text-display-leading); letter-spacing: var(--text-display-tracking);
  color: var(--neutral-900); margin: 0;
}
.ds-page__subtitle {
  font-size: var(--text-caption-size); color: var(--neutral-500); margin-top: 4px;
}

/* 紧凑统计行（仿 DataFoundry） */
.ds-stats-row {
  display: flex; align-items: center; gap: 56px;
  padding: var(--space-4) var(--space-5);
  margin-bottom: var(--space-4);
  background: var(--neutral-0);
  border: 1px solid var(--neutral-100);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xs);
}
.ds-stats-row :deep(.ant-statistic-title) {
  font-size: var(--text-caption-size); color: var(--neutral-500); margin-bottom: 4px;
}
.ds-stats-row :deep(.ant-statistic-content) {
  font-size: 22px; font-weight: 600; line-height: 1.2;
}
.ds-stats-row :deep(.ant-statistic-content-prefix) { margin-right: 6px; font-size: 18px; }
.ds-stats-row__spacer { flex: 1; }

/* 工具栏 */
.ds-toolbar {
  display: flex; align-items: center; gap: var(--space-4);
  margin-bottom: var(--space-3);
}

/* 表格单元 */
.ds-cell-name { font-weight: 600; color: var(--neutral-900); }
.ds-cell-code { font-family: var(--font-mono); font-size: var(--text-code-size); color: var(--neutral-600); }
.ds-cell-secondary { font-size: 12px; color: var(--neutral-500); }

.ds-engine-tag { font-weight: 500; letter-spacing: 0.4px; border-radius: 4px; }

.ds-status { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; }
.ds-status__dot {
  width: 7px; height: 7px; border-radius: 999px; display: inline-block;
  box-shadow: 0 0 0 2px rgba(255,255,255,0.6);
}

/* 表格容器：圆角 / 阴影 / 表头 */
:deep(.ds-table .ant-table) { font-size: var(--text-body-size); background: var(--neutral-0); }
:deep(.ds-table .ant-table-wrapper) {
  border: 1px solid var(--neutral-100); border-radius: 10px;
  overflow: hidden; box-shadow: var(--shadow-xs);
}
:deep(.ds-table .ant-table-thead > tr > th) {
  font-size: var(--text-caption-size); font-weight: 600;
  letter-spacing: 0.3px; color: var(--neutral-600);
  background: var(--neutral-50) !important;
  border-bottom: 1px solid var(--neutral-100);
}
:deep(.ds-table .ant-table-tbody > tr > td) {
  border-bottom: 1px solid var(--neutral-100);
}
:deep(.ds-table .ant-table-tbody > tr:hover > td) {
  background: var(--semantic-50) !important;
}
:deep(.ds-table .ant-table-tbody > tr:last-child > td) { border-bottom: none; }
:deep(.ds-table .ant-progress-inner) { background: var(--neutral-100); }

/* 操作链接按钮 */
:deep(.ds-table .ant-btn-link) { padding: 0 4px; height: auto; font-size: 13px; }

/* 表单弹窗 */
.ds-form__footer {
  display: flex; justify-content: flex-end; gap: var(--space-2);
  padding-top: var(--space-3); border-top: 1px solid var(--neutral-100); margin-top: var(--space-1);
}
.input-mono { font-family: var(--font-mono); font-size: var(--text-code-size); }

/* 类别选择卡片 */
.ds-category-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3); padding: var(--space-1) 0 var(--space-2); }
.ds-category-grid--3 { grid-template-columns: repeat(3, 1fr); }
.ds-category-card {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-2);
  padding: var(--space-5) var(--space-3); border-radius: var(--radius-xl);
  border: 1px solid var(--neutral-100); background: var(--neutral-0);
  cursor: pointer; transition: all var(--transition-fast); text-align: center;
}
.ds-category-card:hover {
  border-color: var(--semantic-300); background: var(--semantic-50);
  box-shadow: var(--shadow-sm); transform: translateY(-2px);
}
.ds-category-icon { color: var(--semantic-500); display: flex; }
.ds-category-name { font-size: var(--text-body-size); font-weight: 600; color: var(--neutral-800); }
.ds-category-desc { font-size: var(--text-caption-size); color: var(--neutral-500); line-height: 1.4; }

/* 文件上传 */
.ds-upload-zone {
  border: 2px dashed var(--neutral-200); border-radius: var(--radius-xl);
  padding: var(--space-8) var(--space-4); text-align: center; cursor: pointer;
  transition: all var(--transition-fast); color: var(--neutral-500); background: var(--neutral-50);
}
.ds-upload-zone--active { border-color: var(--semantic-400); background: var(--semantic-50); }
.ds-upload-zone:hover { border-color: var(--semantic-300); background: var(--semantic-50); }
.ds-upload-hint p { margin: 6px 0 0; font-size: var(--text-body-size); }
.ds-upload-types { font-size: var(--text-caption-size); color: var(--neutral-400); }
.ds-upload-selected { display: flex; align-items: center; gap: var(--space-2); justify-content: center; font-size: var(--text-body-size); }
.ds-file-size { font-size: var(--text-caption-size); color: var(--neutral-400); }

/* 解析内容预览 */
.ds-parsed-content { max-height: 400px; overflow-y: auto; }
.ds-parsed-pre {
  font-size: var(--text-caption-size); font-family: var(--font-mono);
  white-space: pre-wrap; word-break: break-all;
  background: var(--neutral-50); border: 1px solid var(--neutral-100);
  border-radius: var(--radius-lg); padding: var(--space-3); color: var(--neutral-700); line-height: 1.6;
}

/* Ant Design 覆盖 */
:deep(.ant-modal-header) { border-bottom: 1px solid var(--neutral-100); padding-bottom: var(--space-3); }
:deep(.ant-segmented) { background: var(--neutral-100); }
:deep(.ant-segmented-item-selected) { background: var(--neutral-0); }
</style>
