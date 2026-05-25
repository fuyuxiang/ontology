<template>
  <a-drawer :open="open" :title="`新建结构化资产`" width="640"
            @update:open="(v: boolean) => emit('update:open', v)" destroy-on-close>
    <a-tabs v-model:activeKey="kind">
      <a-tab-pane key="table" tab="表 (table)">
        <a-form layout="vertical">
          <a-form-item label="连接 *">
            <a-select v-model:value="form.connection_id" :options="connOptions"
                      :loading="!connStore.items.length" show-search optionFilterProp="label"
                      @change="onConnectionChange" />
          </a-form-item>
          <a-form-item label="表名 *">
            <a-select v-model:value="form.table" :options="tableOptions" allow-clear
                      :loading="loadingTables" show-search optionFilterProp="label" />
          </a-form-item>
          <a-form-item label="资产名称 *">
            <a-input v-model:value="form.name" placeholder="如 用户主表" />
          </a-form-item>
          <a-form-item label="别名（可选，跨模块引用用）">
            <a-input v-model:value="form.alias" placeholder="如 mnp.user_info" />
          </a-form-item>
          <a-form-item label="领域 (domain)">
            <a-input v-model:value="form.domain" />
          </a-form-item>
          <a-form-item label="标签">
            <a-select v-model:value="form.tags" mode="tags" />
          </a-form-item>
          <a-form-item label="缓存 TTL（秒，0 表示不缓存）">
            <a-input-number v-model:value="form.cache_ttl_seconds" :min="0" style="width:100%" />
          </a-form-item>
          <a-form-item label="描述">
            <a-textarea v-model:value="form.description" :rows="2" />
          </a-form-item>
          <a-button type="primary" :loading="saving" @click="saveTable">保存</a-button>
        </a-form>
      </a-tab-pane>

      <a-tab-pane key="sql_view" tab="SQL 视图 (sql_view)">
        <a-form layout="vertical">
          <a-form-item label="基于 table 资产 *">
            <a-select v-model:value="viewForm.base_asset_id" :options="baseTableOptions"
                      show-search optionFilterProp="label" />
          </a-form-item>
          <a-form-item label="资产名称 *">
            <a-input v-model:value="viewForm.name" placeholder="如 mnp.user_count" />
          </a-form-item>
          <a-form-item label="别名">
            <a-input v-model:value="viewForm.alias" placeholder="对应的 alias" />
          </a-form-item>
          <a-form-item label="SQL（占位符 :name；用 {{base}} 引用基表）*">
            <SqlEditor v-model="viewForm.sql"
                       :asset-id="viewForm.base_asset_id || undefined"
                       purpose="sql_view.dry_run"
                       :show-dry-run="!!viewForm.base_asset_id"
                       :rows="10"
                       placeholder="SELECT id, name FROM {{base}} WHERE id = :uid" />
          </a-form-item>
          <a-form-item label="缓存 TTL（秒）">
            <a-input-number v-model:value="viewForm.cache_ttl_seconds" :min="0" style="width:100%" />
          </a-form-item>
          <a-form-item label="描述">
            <a-textarea v-model:value="viewForm.description" :rows="2" />
          </a-form-item>
          <a-button type="primary" :loading="saving" @click="saveView">保存</a-button>
        </a-form>
      </a-tab-pane>
    </a-tabs>
  </a-drawer>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import {
  Button as AButton, Drawer as ADrawer, Form as AForm, FormItem as AFormItem,
  Input as AInput, InputNumber as AInputNumber, Select as ASelect,
  TabPane as ATabPane, Tabs as ATabs, Textarea as ATextarea, message,
} from 'ant-design-vue'
import { useAssetStore } from '../../../store/asset'
import { useConnectionStore } from '../../../store/connection'
import { listTablesOfConnection } from '../../../api/connection'
import SqlEditor from '../../../components/sql/SqlEditor.vue'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{
  (e: 'update:open', v: boolean): void
  (e: 'success'): void
}>()

const store = useAssetStore()
const connStore = useConnectionStore()
const kind = ref<'table' | 'sql_view'>('table')
const saving = ref(false)
const loadingTables = ref(false)
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
  connStore.items.map(c => ({ label: `${c.name} (${c.type})`, value: c.id })))

const baseTableOptions = computed(() =>
  store.items.filter(a => a.kind === 'table' && a.status === 'active')
    .map(a => ({ label: a.name + (a.alias ? ` @${a.alias}` : ''), value: a.id })))

watch(() => props.open, async (v) => {
  if (v) {
    if (!connStore.items.length) await connStore.fetchList()
    if (!store.items.length) await store.fetchList()
  } else {
    Object.assign(form, { connection_id: '', table: '', name: '', alias: '',
      domain: '', tags: [], cache_ttl_seconds: 0, description: '' })
    Object.assign(viewForm, { base_asset_id: '', name: '', alias: '', sql: '',
      cache_ttl_seconds: 0, description: '' })
    tableOptions.value = []
    kind.value = 'table'
  }
})

async function onConnectionChange(connId: string) {
  if (!connId) return
  loadingTables.value = true
  try {
    const tables = await listTablesOfConnection(connId)
    tableOptions.value = tables.map(t => ({ label: t, value: t }))
  } catch (e: any) {
    message.error(e.message)
  } finally {
    loadingTables.value = false
  }
}

async function saveTable() {
  if (!form.connection_id || !form.table || !form.name) {
    message.error('请填写连接 / 表 / 名称'); return
  }
  saving.value = true
  try {
    await store.create({
      name: form.name, alias: form.alias || null,
      kind: 'table', connection_id: form.connection_id,
      locator: { table: form.table },
      domain: form.domain || null, tags: form.tags,
      cache_ttl_seconds: form.cache_ttl_seconds,
      description: form.description || null,
    })
    message.success('已创建'); emit('success'); emit('update:open', false)
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  } finally {
    saving.value = false
  }
}

async function saveView() {
  if (!viewForm.base_asset_id || !viewForm.name || !viewForm.sql) {
    message.error('请填写基表 / 名称 / SQL'); return
  }
  saving.value = true
  try {
    const base = store.items.find(a => a.id === viewForm.base_asset_id)
    if (!base) { message.error('基表资产不存在'); return }
    await store.create({
      name: viewForm.name, alias: viewForm.alias || null,
      kind: 'sql_view', connection_id: base.connection_id,
      locator: { base_asset_id: viewForm.base_asset_id, sql: viewForm.sql },
      cache_ttl_seconds: viewForm.cache_ttl_seconds,
      description: viewForm.description || null,
    })
    message.success('已创建'); emit('success'); emit('update:open', false)
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  } finally {
    saving.value = false
  }
}
</script>
