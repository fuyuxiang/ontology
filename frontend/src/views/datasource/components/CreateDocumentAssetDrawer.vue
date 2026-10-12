<template>
  <a-drawer :open="open" :title="title" width="min(560px, 100vw)"
            :closable="!saving" :mask-closable="!saving" :keyboard="!saving"
            @update:open="(v: boolean) => emit('update:open', v)" destroy-on-close>
    <!-- file 上传（不依赖 Connection） -->
    <a-form v-if="sourceType === 'file'" layout="vertical">
      <a-form-item :label="text('文件 *')">
        <a-upload :before-upload="handleFileSelect" :show-upload-list="false"
                  accept=".pdf,.docx,.doc,.xlsx,.xls,.txt,.md,.csv">
          <a-button>
            <UploadOutlined /> {{ text("选择文件") }} </a-button>
        </a-upload>
        <span v-if="form.file" class="selected-file">{{ form.file.name }}（{{ (form.file.size/1024).toFixed(1) }} KB）</span>
      </a-form-item>
      <a-form-item :label="text('资产名称（可选，默认用文件名）')"><a-input v-model:value="form.name" /></a-form-item>
      <a-form-item :label="text('领域')"><a-input v-model:value="form.domain" /></a-form-item>
      <a-form-item :label="text('标签（逗号分隔）')"><a-input v-model:value="form.tags" placeholder="rule,sop,kpi" /></a-form-item>
      <a-form-item :label="text('描述')"><a-textarea v-model:value="form.description" :rows="2" /></a-form-item>
      <a-button type="primary" :loading="saving" :disabled="!canEdit || (!form.file)" @click="saveFile">{{ text("上传并注册") }}</a-button>
    </a-form>

    <!-- directory 本地目录（不依赖 Connection） -->
    <a-form v-else-if="sourceType === 'directory'" layout="vertical">
      <a-form-item :label="text('资产名称 *')"><a-input v-model:value="dir.name" /></a-form-item>
      <a-form-item :label="text('目录路径 *')"><a-input v-model:value="dir.directory_path" placeholder="/data/inbox" /></a-form-item>
      <a-form-item :label="text('文件后缀（逗号分隔）')"><a-input v-model:value="dir.file_extensions" placeholder="pdf,docx" /></a-form-item>
      <a-form-item :label="text('描述')"><a-textarea v-model:value="dir.description" :rows="2" /></a-form-item>
      <a-button type="primary" :loading="saving" @click="saveDir" :disabled="!canEdit">{{ text("注册") }}</a-button>
    </a-form>

    <!-- oss / api / mq 统一走"选 Connection + 填指针" -->
    <a-form v-else layout="vertical">
      <a-alert :message="connectionHint" type="info" show-icon style="margin-bottom:16px" />
      <a-alert v-if="connError" :message="connError" type="error" show-icon style="margin-bottom:16px">
        <template #action><a-button size="small" @click="loadConnections">{{ text("重试") }}</a-button></template>
      </a-alert>
      <a-form-item :label="text('选择数据源连接 *')">
        <a-select v-model:value="conn.connection_id" :options="connectionOptions"
                  :placeholder="text('先在「数据接入」页创建对应类型的数据源')" :loading="connLoading"
                  @change="onConnChange">
          <template #notFoundContent>
            <div style="padding:12px;font-size:12px;color:#9ca3af"> {{ text("暂无") }} {{ requiredCategoryLabel }} {{ text("类型的数据源") }} </div>
          </template>
        </a-select>
      </a-form-item>

      <a-form-item :label="text('资产名称 *')"><a-input v-model:value="conn.name" /></a-form-item>

      <!-- oss/s3 指针字段 -->
      <template v-if="sourceType === 'oss'">
        <a-form-item :label="text('对象 Key *')">
          <a-input-search v-model:value="conn.key" placeholder="path/to/object.csv"
                          :enter-button="text('浏览')" @search="browse" :loading="browsing" />
        </a-form-item>
        <a-form-item v-if="browseList.length > 0" :label="text('可用对象')">
          <a-list size="small" :data-source="browseList" :pagination="false" bordered style="max-height:200px;overflow:auto">
            <template #renderItem="{ item }">
              <a-list-item>
                <button type="button" class="browse-choice" :aria-pressed="conn.key === item.key" @click="conn.key = item.key">{{ item.key }}</button>
                <span style="color:#9ca3af;font-size:11px">{{ formatSize(item.size) }}</span>
              </a-list-item>
            </template>
          </a-list>
        </a-form-item>
      </template>

      <!-- api 指针字段 -->
      <template v-else-if="sourceType === 'api'">
        <a-row :gutter="12">
          <a-col :span="16">
            <a-form-item :label="text('路径 *')">
              <a-input v-model:value="conn.path" :placeholder="text('/users/{id}（相对 base_url）')" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="Method">
              <a-select v-model:value="conn.method" :options="[{value:'GET'},{value:'POST'},{value:'PUT'}]" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item :label="text('轮询周期（秒）')">
          <a-input-number v-model:value="conn.poll_interval" :min="10" style="width:100%" />
        </a-form-item>
      </template>

      <!-- mq 指针字段 -->
      <template v-else-if="sourceType === 'mq'">
        <a-form-item label="Topic *">
          <a-input-search v-model:value="conn.topic" placeholder="orders"
                          :enter-button="text('浏览')" @search="browse" :loading="browsing" />
        </a-form-item>
        <a-form-item v-if="browseTopics.length > 0" :label="text('可用 Topic')">
          <a-list size="small" :data-source="browseTopics" :pagination="false" bordered style="max-height:200px;overflow:auto">
            <template #renderItem="{ item }">
              <a-list-item>
                <button type="button" class="browse-choice" :aria-pressed="conn.topic === item" @click="conn.topic = item">{{ item }}</button>
              </a-list-item>
            </template>
          </a-list>
        </a-form-item>
        <a-form-item :label="text('消费组')"><a-input v-model:value="conn.group" /></a-form-item>
        <a-form-item :label="text('轮询周期（秒）')">
          <a-input-number v-model:value="conn.poll_interval" :min="10" style="width:100%" />
        </a-form-item>
      </template>

      <a-form-item :label="text('描述')"><a-textarea v-model:value="conn.description" :rows="2" /></a-form-item>
      <a-button type="primary" :loading="saving" @click="saveConnAsset" :disabled="!canEdit">{{ text("注册") }}</a-button>
    </a-form>
  </a-drawer>
</template>

<script setup lang="ts">
import { useProductText } from "../../../composables/useProductText"
const { text } = useProductText()

import { useManagementPermission } from '../../../composables/useManagementPermission'
const { canEdit } = useManagementPermission('entity:write')
import { computed, reactive, ref, watch } from 'vue'
import {
  Alert as AAlert, Button as AButton, Col as ACol, Drawer as ADrawer,
  Form as AForm, FormItem as AFormItem, Input as AInput, InputNumber as AInputNumber,
  InputSearch as AInputSearch, List as AList, ListItem as AListItem,
  Row as ARow, Select as ASelect, Textarea as ATextarea, Upload as AUpload, message,
} from 'ant-design-vue'
import { UploadOutlined } from '@ant-design/icons-vue'
import { uploadDocumentAsset, createDirectoryDocAsset, createAsset } from '../../../api/asset'
import { listConnections, listObjects, listTopics } from '../../../api/connection'
import type { DocumentSourceType } from '../../../types/asset'
import type { Connection, ConnectionCategory, ObjectEntry } from '../../../types/connection'

const props = defineProps<{ open: boolean; sourceType: DocumentSourceType }>()
const emit = defineEmits<{
  (e: 'update:open', v: boolean): void
  (e: 'success'): void
}>()

const connections = ref<Connection[]>([])
const saving = ref(false)
const browsing = ref(false)
const connLoading = ref(false)
const connError = ref('')
let browseRequest = 0
const browseList = ref<ObjectEntry[]>([])
const browseTopics = ref<string[]>([])

const form = reactive<{ file: File | null; name: string; description: string; domain: string; tags: string }>({
  file: null, name: '', description: '', domain: '', tags: '',
})
const dir = reactive({ name: '', directory_path: '', file_extensions: '', description: '' })
const conn = reactive({
  connection_id: '' as string,
  name: '',
  key: '',           // oss
  path: '',          // api
  method: 'GET',
  topic: '',         // mq
  group: 'ontology-consumer',
  poll_interval: 60,
  description: '',
})

const title = computed(() => {
  return ({
    file: text("上传文件资产"), oss: text("对象存储资产（依托数据源）"),
    directory: text("本地目录扫描资产"), api: text("HTTP API 资产（依托数据源）"),
    mq: text("消息队列资产（依托数据源）"),
  } as Record<DocumentSourceType, string>)[props.sourceType]
})

const requiredCategory = computed<ConnectionCategory | null>(() => {
  return ({
    oss: 'object_storage', api: 'api', mq: 'message_queue',
  } as Record<string, ConnectionCategory>)[props.sourceType] || null
})

const requiredCategoryLabel = computed(() => {
  return ({
    object_storage: text("对象存储"), api: 'HTTP API', message_queue: text("消息队列"),
  } as Record<string, string>)[requiredCategory.value || ''] || ''
})

const connectionOptions = computed(() => {
  if (!requiredCategory.value) return []
  return connections.value
    .filter(c => c.category === requiredCategory.value && c.enabled)
    .map(c => ({ label: `${c.name} · ${c.type}`, value: c.id }))
})

const connectionHint = computed(() => {
  return text('本资产将关联到一个 {type} 类型的数据源连接，凭据由该连接统一管理（不重复填写）。', { type: requiredCategoryLabel.value })
})

watch(() => props.open, async (v) => {
  if (v) {
    if (requiredCategory.value) await loadConnections()
  } else {
    ++browseRequest
    browsing.value = false
    form.file = null; form.name = ''; form.description = ''; form.domain = ''; form.tags = ''
    Object.assign(dir, { name: '', directory_path: '', file_extensions: '', description: '' })
    Object.assign(conn, {
      connection_id: '', name: '', key: '', path: '', method: 'GET',
      topic: '', group: 'ontology-consumer', poll_interval: 60, description: '',
    })
    browseList.value = []
    browseTopics.value = []
  }
})

async function loadConnections() {
  connLoading.value = true
  connError.value = ''
  try { connections.value = await listConnections() }
  catch (e: any) { connError.value = e.response?.data?.detail || e.message || text("数据源选项加载失败，请重试") }
  finally { connLoading.value = false }
}

function handleFileSelect(file: File): boolean {
  form.file = file
  return false
}

function onConnChange() {
  ++browseRequest
  browsing.value = false
  conn.key = ''; conn.path = ''; conn.topic = ''
  browseList.value = []
  browseTopics.value = []
}

async function browse() {
  if (!conn.connection_id) { message.warning(text("请先选择连接")); return }
  browsing.value = true
  const request = ++browseRequest
  const connectionId = conn.connection_id
  try {
    if (props.sourceType === 'oss') {
      const objects = await listObjects(connectionId, conn.key || '', 50)
      if (request === browseRequest && props.open) browseList.value = objects
    } else if (props.sourceType === 'mq') {
      const topics = await listTopics(connectionId)
      if (request === browseRequest && props.open) browseTopics.value = topics
    }
  } catch (e: any) {
    if (request === browseRequest && props.open) message.error(e.response?.data?.detail || e.message)
  } finally {
    if (request === browseRequest) browsing.value = false
  }
}

async function saveFile() {
  if (saving.value || !form.file) return
  saving.value = true
  try {
    await uploadDocumentAsset(form.file, {
      name: form.name || undefined,
      description: form.description, domain: form.domain, tags: form.tags,
    })
    message.success(text("已上传")); emit('success'); emit('update:open', false)
  } catch (e: any) { message.error(e.response?.data?.detail || e.message) }
  finally { saving.value = false }
}

async function saveDir() {
  if (saving.value) return
  if (!dir.name.trim() || !dir.directory_path.trim()) { message.error(text("请填写必填项")); return }
  saving.value = true
  try {
    await createDirectoryDocAsset({
      name: dir.name, directory_path: dir.directory_path,
      file_extensions: dir.file_extensions ? dir.file_extensions.split(',').map(s => s.trim()) : [],
      description: dir.description,
    })
    message.success(text("已注册")); emit('success'); emit('update:open', false)
  } catch (e: any) { message.error(e.response?.data?.detail || e.message) }
  finally { saving.value = false }
}

async function saveConnAsset() {
  if (saving.value) return
  if (!conn.connection_id) { message.error(text("请选择数据源连接")); return }
  if (!conn.name.trim()) { message.error(text("请填写资产名称")); return }
  let locator: Record<string, unknown> = {}
  if (props.sourceType === 'oss') {
    if (!conn.key) { message.error(text("请填写对象 Key")); return }
    locator = { source_type: 's3', key: conn.key }
  } else if (props.sourceType === 'api') {
    if (!conn.path) { message.error(text("请填写路径")); return }
    locator = { source_type: 'api', path: conn.path, method: conn.method, poll_interval: conn.poll_interval }
  } else if (props.sourceType === 'mq') {
    if (!conn.topic) { message.error(text("请填写 Topic")); return }
    locator = {
      source_type: 'mq', topic: conn.topic, group: conn.group, poll_interval: conn.poll_interval,
    }
  }
  saving.value = true
  try {
    await createAsset({
      name: conn.name, kind: 'document',
      connection_id: conn.connection_id,
      locator,
      description: conn.description || undefined,
    } as any)
    message.success(text("已注册")); emit('success'); emit('update:open', false)
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  } finally {
    saving.value = false
  }
}

function formatSize(n: number) {
  if (!n) return ''
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`
}
</script>

<style scoped>
.selected-file { display: block; margin-top: 8px; overflow-wrap: anywhere; color: var(--neutral-700, #374151); }
.browse-choice { min-width: 0; border: 0; padding: 0; background: none; font: inherit; text-align: left; color: var(--neutral-700, #374151); cursor: pointer; overflow-wrap: anywhere; }
.browse-choice[aria-pressed="true"] { color: var(--primary, #2563eb); font-weight: 600; }
.browse-choice:focus-visible { outline: 2px solid var(--primary, #2563eb); outline-offset: 3px; }
</style>
