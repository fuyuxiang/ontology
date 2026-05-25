<template>
  <a-drawer :open="open" :title="title" width="560"
            @update:open="(v: boolean) => emit('update:open', v)" destroy-on-close>
    <!-- file 上传 -->
    <a-form v-if="sourceType === 'file'" layout="vertical">
      <a-form-item label="文件 *">
        <a-upload :before-upload="handleFileSelect" :show-upload-list="false"
                  accept=".pdf,.docx,.doc,.xlsx,.xls,.txt,.md,.csv">
          <a-button>
            <UploadOutlined /> 选择文件
          </a-button>
        </a-upload>
        <span v-if="form.file" style="margin-left:12px">{{ form.file.name }}（{{ (form.file.size/1024).toFixed(1) }} KB）</span>
      </a-form-item>
      <a-form-item label="资产名称（可选，默认用文件名）">
        <a-input v-model:value="form.name" />
      </a-form-item>
      <a-form-item label="领域">
        <a-input v-model:value="form.domain" />
      </a-form-item>
      <a-form-item label="标签（逗号分隔）">
        <a-input v-model:value="form.tags" placeholder="rule,sop,kpi" />
      </a-form-item>
      <a-form-item label="描述">
        <a-textarea v-model:value="form.description" :rows="2" />
      </a-form-item>
      <a-button type="primary" :loading="saving" :disabled="!form.file" @click="saveFile">上传并注册</a-button>
    </a-form>

    <!-- oss -->
    <a-form v-else-if="sourceType === 'oss'" layout="vertical">
      <a-form-item label="资产名称 *"><a-input v-model:value="oss.name" /></a-form-item>
      <a-form-item label="Endpoint *"><a-input v-model:value="oss.endpoint" placeholder="https://oss.aliyun.com" /></a-form-item>
      <a-form-item label="Bucket *"><a-input v-model:value="oss.bucket" /></a-form-item>
      <a-row :gutter="12">
        <a-col :span="12"><a-form-item label="Access Key *"><a-input v-model:value="oss.access_key" /></a-form-item></a-col>
        <a-col :span="12"><a-form-item label="Secret Key *"><a-input-password v-model:value="oss.secret_key" /></a-form-item></a-col>
      </a-row>
      <a-form-item label="Prefix"><a-input v-model:value="oss.prefix" placeholder="可选" /></a-form-item>
      <a-form-item label="描述"><a-textarea v-model:value="oss.description" :rows="2" /></a-form-item>
      <a-button type="primary" :loading="saving" @click="saveOss">连通性测试 + 注册</a-button>
    </a-form>

    <!-- directory -->
    <a-form v-else-if="sourceType === 'directory'" layout="vertical">
      <a-form-item label="资产名称 *"><a-input v-model:value="dir.name" /></a-form-item>
      <a-form-item label="目录路径 *">
        <a-input v-model:value="dir.directory_path" placeholder="/data/inbox" />
      </a-form-item>
      <a-form-item label="文件后缀（逗号分隔）">
        <a-input v-model:value="dir.file_extensions" placeholder="pdf,docx" />
      </a-form-item>
      <a-form-item label="描述"><a-textarea v-model:value="dir.description" :rows="2" /></a-form-item>
      <a-button type="primary" :loading="saving" @click="saveDir">注册</a-button>
    </a-form>

    <!-- api -->
    <a-form v-else-if="sourceType === 'api'" layout="vertical">
      <a-form-item label="资产名称 *"><a-input v-model:value="api.name" /></a-form-item>
      <a-form-item label="API URL *"><a-input v-model:value="api.api_url" /></a-form-item>
      <a-row :gutter="12">
        <a-col :span="12">
          <a-form-item label="Method">
            <a-select v-model:value="api.api_method" :options="[{value:'GET'},{value:'POST'},{value:'PUT'}]" />
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="轮询周期（秒）">
            <a-input-number v-model:value="api.poll_interval" :min="10" style="width:100%" />
          </a-form-item>
        </a-col>
      </a-row>
      <a-form-item label="Headers (JSON)">
        <a-textarea v-model:value="api.headers_json" :rows="4"
                    placeholder='{"Authorization":"Bearer xxx","Accept":"json"}' />
      </a-form-item>
      <a-form-item label="Body">
        <a-textarea v-model:value="api.api_body" :rows="3" />
      </a-form-item>
      <a-form-item label="描述"><a-textarea v-model:value="api.description" :rows="2" /></a-form-item>
      <a-button type="primary" :loading="saving" @click="saveApi">试调一次 + 注册</a-button>
    </a-form>

    <!-- mq -->
    <a-form v-else-if="sourceType === 'mq'" layout="vertical">
      <a-form-item label="资产名称 *"><a-input v-model:value="mq.name" /></a-form-item>
      <a-row :gutter="12">
        <a-col :span="16"><a-form-item label="Host *"><a-input v-model:value="mq.host" /></a-form-item></a-col>
        <a-col :span="8"><a-form-item label="Port"><a-input-number v-model:value="mq.port" :min="1" style="width:100%" /></a-form-item></a-col>
      </a-row>
      <a-form-item label="Topic *"><a-input v-model:value="mq.topic" /></a-form-item>
      <a-form-item label="消费组"><a-input v-model:value="mq.group" /></a-form-item>
      <a-row :gutter="12">
        <a-col :span="12"><a-form-item label="Username"><a-input v-model:value="mq.username" /></a-form-item></a-col>
        <a-col :span="12"><a-form-item label="Password"><a-input-password v-model:value="mq.password" /></a-form-item></a-col>
      </a-row>
      <a-form-item label="轮询周期（秒）">
        <a-input-number v-model:value="mq.poll_interval" :min="10" style="width:100%" />
      </a-form-item>
      <a-form-item label="描述"><a-textarea v-model:value="mq.description" :rows="2" /></a-form-item>
      <a-button type="primary" :loading="saving" @click="saveMq">注册</a-button>
    </a-form>
  </a-drawer>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import {
  Button as AButton, Col as ACol, Drawer as ADrawer, Form as AForm,
  FormItem as AFormItem, Input as AInput, InputNumber as AInputNumber,
  InputPassword as AInputPassword, Row as ARow, Select as ASelect,
  Textarea as ATextarea, Upload as AUpload, message,
} from 'ant-design-vue'
import { UploadOutlined } from '@ant-design/icons-vue'
import {
  uploadDocumentAsset, createOssDocAsset, createDirectoryDocAsset,
  createApiDocAsset, createMqDocAsset,
} from '../../../api/asset'
import type { DocumentSourceType } from '../../../types/asset'

const props = defineProps<{ open: boolean; sourceType: DocumentSourceType }>()
const emit = defineEmits<{
  (e: 'update:open', v: boolean): void
  (e: 'success'): void
}>()

const saving = ref(false)
const form = reactive<{ file: File | null; name: string; description: string; domain: string; tags: string }>({
  file: null, name: '', description: '', domain: '', tags: '',
})
const oss = reactive({ name: '', endpoint: '', bucket: '', access_key: '', secret_key: '', prefix: '', description: '' })
const dir = reactive({ name: '', directory_path: '', file_extensions: '', description: '' })
const api = reactive({ name: '', api_url: '', api_method: 'GET', poll_interval: 60, headers_json: '', api_body: '', description: '' })
const mq = reactive({ name: '', host: '', port: 9092, topic: '', group: 'ontology-consumer', username: '', password: '', poll_interval: 60, description: '' })

const title = computed(() => {
  return ({
    file: '上传文件资产', oss: '对象存储 OSS 资产',
    directory: '本地目录扫描资产', api: 'HTTP API 抓取资产', mq: 'MQ Topic 资产',
  } as Record<DocumentSourceType, string>)[props.sourceType]
})

watch(() => props.open, (v) => {
  if (!v) {
    form.file = null; form.name = ''; form.description = ''; form.domain = ''; form.tags = ''
    Object.assign(oss, { name: '', endpoint: '', bucket: '', access_key: '', secret_key: '', prefix: '', description: '' })
    Object.assign(dir, { name: '', directory_path: '', file_extensions: '', description: '' })
    Object.assign(api, { name: '', api_url: '', api_method: 'GET', poll_interval: 60, headers_json: '', api_body: '', description: '' })
    Object.assign(mq, { name: '', host: '', port: 9092, topic: '', group: 'ontology-consumer', username: '', password: '', poll_interval: 60, description: '' })
  }
})

function handleFileSelect(file: File): boolean {
  form.file = file
  return false
}

async function saveFile() {
  if (!form.file) return
  saving.value = true
  try {
    await uploadDocumentAsset(form.file, {
      name: form.name || undefined,
      description: form.description, domain: form.domain, tags: form.tags,
    })
    message.success('已上传'); emit('success'); emit('update:open', false)
  } catch (e: any) { message.error(e.response?.data?.detail || e.message) }
  finally { saving.value = false }
}

async function saveOss() {
  if (!oss.name || !oss.endpoint || !oss.bucket || !oss.access_key || !oss.secret_key) {
    message.error('请填写必填项'); return
  }
  saving.value = true
  try {
    await createOssDocAsset({ ...oss, prefix: oss.prefix || '' })
    message.success('已注册'); emit('success'); emit('update:open', false)
  } catch (e: any) { message.error(e.response?.data?.detail || e.message) }
  finally { saving.value = false }
}

async function saveDir() {
  if (!dir.name || !dir.directory_path) { message.error('请填写必填项'); return }
  saving.value = true
  try {
    await createDirectoryDocAsset({
      name: dir.name, directory_path: dir.directory_path,
      file_extensions: dir.file_extensions ? dir.file_extensions.split(',').map(s => s.trim()) : [],
      description: dir.description,
    })
    message.success('已注册'); emit('success'); emit('update:open', false)
  } catch (e: any) { message.error(e.response?.data?.detail || e.message) }
  finally { saving.value = false }
}

async function saveApi() {
  if (!api.name || !api.api_url) { message.error('请填写必填项'); return }
  let headers: Record<string, string> | null = null
  if (api.headers_json.trim()) {
    try { headers = JSON.parse(api.headers_json) } catch { message.error('Headers JSON 格式错误'); return }
  }
  saving.value = true
  try {
    await createApiDocAsset({
      name: api.name, api_url: api.api_url, api_method: api.api_method,
      api_headers: headers, api_body: api.api_body || null,
      poll_interval: api.poll_interval, description: api.description,
    })
    message.success('已注册'); emit('success'); emit('update:open', false)
  } catch (e: any) { message.error(e.response?.data?.detail || e.message) }
  finally { saving.value = false }
}

async function saveMq() {
  if (!mq.name || !mq.host || !mq.topic) { message.error('请填写必填项'); return }
  saving.value = true
  try {
    await createMqDocAsset({ ...mq })
    message.success('已注册'); emit('success'); emit('update:open', false)
  } catch (e: any) { message.error(e.response?.data?.detail || e.message) }
  finally { saving.value = false }
}
</script>
