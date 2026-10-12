<template>
  <a-drawer :open="open" :title="text('新建结构化资产')" width="min(640px, 100vw)"
            :closable="!saving" :mask-closable="!saving" :keyboard="!saving"
            @update:open="(v: boolean) => emit('update:open', v)" destroy-on-close>
    <a-alert v-if="optionsError" type="error" show-icon :message="optionsError" style="margin-bottom:16px">
      <template #action><a-button size="small" @click="loadOptions">{{ text("重试") }}</a-button></template>
    </a-alert>
    <a-tabs v-model:active-key="kind">
      <a-tab-pane key="table" :tab="text('表 (table)')" :disabled="saving">
        <a-form layout="vertical">
          <a-form-item :label="text('连接 *')">
            <a-select v-model:value="form.connection_id" :options="connOptions"
                      :loading="loadingOptions" :disabled="saving" show-search option-filter-prop="label"
                      @change="onConnectionChange" />
          </a-form-item>
          <a-form-item :label="text('表名 *')">
            <a-select v-model:value="form.table" :options="tableOptions" allow-clear
                      :loading="loadingTables" :disabled="!form.connection_id || loadingTables || saving" show-search option-filter-prop="label" />
          </a-form-item>
          <a-form-item :label="text('资产名称 *')">
            <a-input v-model:value="form.name" :placeholder="text('如 用户主表')" />
          </a-form-item>
          <a-form-item :label="text('别名（可选，跨模块引用用）')">
            <a-input v-model:value="form.alias" :placeholder="text('如 domain.user_info')" />
          </a-form-item>
          <a-form-item :label="text('领域 (domain)')">
            <a-input v-model:value="form.domain" />
          </a-form-item>
          <a-form-item :label="text('标签')">
            <a-select v-model:value="form.tags" mode="tags" />
          </a-form-item>
          <a-form-item :label="text('缓存 TTL（秒，0 表示不缓存）')">
            <a-input-number v-model:value="form.cache_ttl_seconds" :min="0" style="width:100%" />
          </a-form-item>
          <a-form-item :label="text('描述')">
            <a-textarea v-model:value="form.description" :rows="2" />
          </a-form-item>
          <a-button type="primary" :loading="saving" @click="saveTable" :disabled="!canEdit">{{ text("保存") }}</a-button>
        </a-form>
      </a-tab-pane>

      <a-tab-pane key="sql_view" :tab="text('SQL 视图 (sql_view)')" :disabled="saving">
        <a-form layout="vertical">
          <a-form-item :label="text('基于 table 资产 *')">
            <a-select v-model:value="viewForm.base_asset_id" :options="baseTableOptions"
                      :loading="loadingOptions" :disabled="saving" show-search option-filter-prop="label" />
          </a-form-item>
          <a-form-item :label="text('资产名称 *')">
            <a-input v-model:value="viewForm.name" :placeholder="text('如 用户数量视图')" />
          </a-form-item>
          <a-form-item :label="text('别名')">
            <a-input v-model:value="viewForm.alias" :placeholder="text('对应的 alias')" />
          </a-form-item>
          <a-form-item :label="text('SQL（占位符 :name；用 {{base}} 引用基表）*')">
            <SqlEditor v-model="viewForm.sql"
                       :asset-id="viewForm.base_asset_id || undefined"
                       purpose="sql_view.dry_run"
                       :show-dry-run="!!viewForm.base_asset_id"
                       :rows="10"
                       placeholder="SELECT id, name FROM {{base}} WHERE id = :uid" />
          </a-form-item>
          <a-form-item :label="text('缓存 TTL（秒）')">
            <a-input-number v-model:value="viewForm.cache_ttl_seconds" :min="0" style="width:100%" />
          </a-form-item>
          <a-form-item :label="text('描述')">
            <a-textarea v-model:value="viewForm.description" :rows="2" />
          </a-form-item>
          <a-button type="primary" :loading="saving" @click="saveView" :disabled="!canEdit">{{ text("保存") }}</a-button>
        </a-form>
      </a-tab-pane>
    </a-tabs>
  </a-drawer>
</template>

<script setup lang="ts">
import { useProductText } from "../../../composables/useProductText"
const { text } = useProductText()

import { useManagementPermission } from '../../../composables/useManagementPermission'
const { canEdit } = useManagementPermission('entity:write')
import { computed, reactive, ref, watch } from 'vue'
import {
  Alert as AAlert, Button as AButton, Drawer as ADrawer, Form as AForm, FormItem as AFormItem,
  Input as AInput, InputNumber as AInputNumber, Select as ASelect,
  TabPane as ATabPane, Tabs as ATabs, Textarea as ATextarea, message,
} from 'ant-design-vue'
import { useAssetStore } from '../../../store/asset'
import { listConnections, listTablesOfConnection } from '../../../api/connection'
import { listAssets } from '../../../api/asset'
import type { Asset } from '../../../types/asset'
import type { Connection } from '../../../types/connection'
import SqlEditor from '../../../components/sql/SqlEditor.vue'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{
  (e: 'update:open', v: boolean): void
  (e: 'success'): void
}>()

const store = useAssetStore()
const kind = ref<'table' | 'sql_view'>('table')
const saving = ref(false)
const loadingTables = ref(false)
const loadingOptions = ref(false)
const optionsError = ref('')
const connections = ref<Connection[]>([])
const baseTables = ref<Asset[]>([])
let tablesRequest = 0
const tableOptions = ref<{ label: string; value: string }[]>([])

const form = reactive({
  connection_id: '', table: '', name: '', alias: '',
  domain: '', tags: [] as string[], cache_ttl_seconds: 0, description: '',
})
const viewForm = reactive({
  base_asset_id: '', name: '', alias: '', sql: '',
  cache_ttl_seconds: 0, description: '',
})

const connOptions = computed(() =>
  connections.value.filter(c => c.category === 'database' && c.enabled).map(c => ({ label: `${c.name} (${c.type})`, value: c.id })))

const baseTableOptions = computed(() =>
  baseTables.value
    .map(a => ({ label: a.name + (a.alias ? ` @${a.alias}` : ''), value: a.id })))

watch(() => props.open, async (v) => {
  if (v) {
    await loadOptions()
  } else {
    ++tablesRequest
    loadingTables.value = false
    Object.assign(form, { connection_id: '', table: '', name: '', alias: '',
      domain: '', tags: [], cache_ttl_seconds: 0, description: '' })
    Object.assign(viewForm, { base_asset_id: '', name: '', alias: '', sql: '',
      cache_ttl_seconds: 0, description: '' })
    tableOptions.value = []
    kind.value = 'table'
  }
})

async function loadOptions() {
  loadingOptions.value = true
  optionsError.value = ''
  try {
    const [loadedConnections, loadedTables] = await Promise.all([listConnections(), listAssets({ kind: 'table' })])
    connections.value = loadedConnections
    baseTables.value = loadedTables
  } catch (e: any) {
    optionsError.value = e.response?.data?.detail || e.message || text("资产选项加载失败，请重试")
  } finally {
    loadingOptions.value = false
  }
}

async function onConnectionChange(value: unknown) {
  const request = ++tablesRequest
  form.table = ''
  tableOptions.value = []
  const connId = value == null ? '' : String(value)
  if (!connId) { loadingTables.value = false; return }
  loadingTables.value = true
  try {
    const tables = await listTablesOfConnection(connId)
    if (request === tablesRequest && props.open) tableOptions.value = tables.map(t => ({ label: t, value: t }))
  } catch (e: any) {
    if (request === tablesRequest && props.open) message.error(e.message)
  } finally {
    if (request === tablesRequest) loadingTables.value = false
  }
}

async function saveTable() {
  if (saving.value) return
  if (!form.connection_id || !form.table || !form.name.trim() || loadingTables.value) {
    message.error(text("请填写连接 / 表 / 名称")); return
  }
  saving.value = true
  try {
    await store.create({
      name: form.name.trim(), alias: form.alias || null,
      kind: 'table', connection_id: form.connection_id,
      locator: { table: form.table },
      domain: form.domain || null, tags: form.tags,
      cache_ttl_seconds: form.cache_ttl_seconds,
      description: form.description || null,
    })
    message.success(text("已创建")); emit('success'); emit('update:open', false)
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  } finally {
    saving.value = false
  }
}

async function saveView() {
  if (saving.value) return
  if (!viewForm.base_asset_id || !viewForm.name.trim() || !viewForm.sql.trim()) {
    message.error(text("请填写基表 / 名称 / SQL")); return
  }
  saving.value = true
  try {
    const base = baseTables.value.find(a => a.id === viewForm.base_asset_id)
    if (!base) { message.error(text("基表资产不存在")); return }
    await store.create({
      name: viewForm.name.trim(), alias: viewForm.alias || null,
      kind: 'sql_view', connection_id: base.connection_id,
      locator: { base_asset_id: viewForm.base_asset_id, sql: viewForm.sql },
      cache_ttl_seconds: viewForm.cache_ttl_seconds,
      description: viewForm.description || null,
    })
    message.success(text("已创建")); emit('success'); emit('update:open', false)
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  } finally {
    saving.value = false
  }
}
</script>
