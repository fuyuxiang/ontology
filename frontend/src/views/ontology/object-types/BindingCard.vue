<template>
  <div class="bc">
    <!-- 顶部信息 -->
    <div class="bc-head">
      <div class="bc-asset">
        <a-tag :color="kindColor(asset?.kind)" v-if="asset">{{ kindLabel(asset) }}</a-tag>
        <span class="bc-asset__name">{{ asset?.name || binding.asset_id.slice(0, 8) }}</span>
        <a-tag v-if="asset?.alias" color="purple">@{{ asset.alias }}</a-tag>
        <a-tag v-if="binding.status !== 'active'" :color="binding.status === 'needs_review' ? 'orange' : 'red'">
          {{ binding.status }}
        </a-tag>
      </div>
      <a-space :size="6">
        <a-button size="small" @click="$emit('test', binding.id)">测试解析</a-button>
        <a-button size="small" :type="editing ? 'primary' : 'default'" @click="toggleEdit">
          {{ editing ? '完成编辑' : '编辑映射' }}
        </a-button>
        <a-popconfirm title="确认删除此绑定？" @confirm="$emit('delete', binding.id)">
          <a-button size="small" danger>删除</a-button>
        </a-popconfirm>
      </a-space>
    </div>

    <div v-if="binding.review_reason" class="bc-warn">
      <ExclamationCircleOutlined /> {{ binding.review_reason }}
    </div>

    <!-- 字段映射表 -->
    <a-table size="small" :columns="cols" :data-source="rows" :pagination="false" row-key="attribute_id">
      <template #bodyCell="{ column, record, index }">
        <template v-if="column.key === 'attribute_name'">
          <span class="bc-mono">{{ record.attribute_name }}</span>
          <a-tag size="small" style="margin-left:6px">{{ record.attribute_type }}</a-tag>
        </template>
        <template v-else-if="column.key === 'source_column'">
          <a-select
            v-if="editing"
            v-model:value="rows[index].source_column"
            :options="columnOptions"
            allow-clear
            show-search
            optionFilterProp="label"
            style="width:100%"
            placeholder="选择源列"
          />
          <code v-else class="bc-mono">{{ record.source_column || '—' }}</code>
        </template>
        <template v-else-if="column.key === 'transform'">
          <a-input v-if="editing" v-model:value="rows[index].transform" placeholder="可选：CONCAT(...) 等" />
          <span v-else>{{ record.transform || '—' }}</span>
        </template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="record.source_column ? 'green' : 'default'">
            {{ record.source_column ? '已映射' : '未映射' }}
          </a-tag>
        </template>
      </template>
    </a-table>

    <!-- id_column / filter_expr -->
    <div v-if="editing" class="bc-extra">
      <a-row :gutter="16">
        <a-col :span="12">
          <div class="bc-extra__label">主键列 (id_column)</div>
          <a-select v-model:value="form.id_column" :options="columnOptions" allow-clear />
        </a-col>
        <a-col :span="12">
          <div class="bc-extra__label">过滤表达式 (filter_expr)</div>
          <a-input v-model:value="form.filter_expr" placeholder="可选：限定该对象仅取此 Asset 中满足条件的行" />
        </a-col>
      </a-row>
      <div style="margin-top:12px">
        <a-button type="primary" :loading="saving" @click="save">保存映射</a-button>
        <a-button style="margin-left:8px" @click="cancel">取消</a-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import {
  Button as AButton, Col as ACol, Input as AInput, Popconfirm as APopconfirm,
  Row as ARow, Select as ASelect, Space as ASpace, Table as ATable, Tag as ATag,
} from 'ant-design-vue'
import { ExclamationCircleOutlined } from '@ant-design/icons-vue'
import type { Asset } from '../../../types/asset'
import type { FieldMapping, ObjectBinding } from '../../../types/binding'

const props = defineProps<{
  binding: ObjectBinding
  asset: Asset | undefined
  attributes: { id: string; name: string; type: string }[]
}>()

const emit = defineEmits<{
  (e: 'save', bindingId: string, payload: { field_mappings: FieldMapping[]; id_column?: string | null; filter_expr?: string | null }): void
  (e: 'delete', bindingId: string): void
  (e: 'test', bindingId: string): void
}>()

const editing = ref(false)
const saving = ref(false)
const rows = ref<{ attribute_id: string; attribute_name: string; attribute_type: string; source_column: string | undefined; transform: string | undefined }[]>([])
const form = reactive<{ id_column: string | undefined; filter_expr: string | undefined }>({
  id_column: props.binding.id_column ?? undefined,
  filter_expr: props.binding.filter_expr ?? undefined,
})

const cols = [
  { title: '属性', key: 'attribute_name' },
  { title: '源列', key: 'source_column' },
  { title: '变换', key: 'transform' },
  { title: '状态', key: 'status', width: 90 },
]

const columnOptions = computed(() =>
  (props.asset?.schema_snapshot || []).map(c => ({ label: `${c.name} (${c.type})`, value: c.name })))

watch(() => props.binding, () => syncFromBinding(), { immediate: true })

function syncFromBinding() {
  const fmMap: Record<string, FieldMapping> = {}
  for (const fm of props.binding.field_mappings || []) {
    fmMap[fm.attribute_id] = fm
  }
  rows.value = props.attributes.map(a => ({
    attribute_id: a.id,
    attribute_name: a.name,
    attribute_type: a.type,
    source_column: fmMap[a.id]?.source_column || undefined,
    transform: fmMap[a.id]?.transform || undefined,
  }))
  form.id_column = props.binding.id_column ?? undefined
  form.filter_expr = props.binding.filter_expr ?? undefined
}

function toggleEdit() {
  if (editing.value) syncFromBinding()
  editing.value = !editing.value
}

function cancel() {
  syncFromBinding()
  editing.value = false
}

async function save() {
  saving.value = true
  try {
    const fms: FieldMapping[] = rows.value
      .filter(r => r.source_column)
      .map(r => ({ attribute_id: r.attribute_id, source_column: r.source_column!, transform: r.transform || null }))
    emit('save', props.binding.id, { field_mappings: fms, id_column: form.id_column, filter_expr: form.filter_expr })
    editing.value = false
  } finally {
    saving.value = false
  }
}

function kindColor(k?: string) {
  if (!k) return 'default'
  return ({ table: 'blue', sql_view: 'cyan', document: 'gold' } as Record<string, string>)[k] || 'default'
}
function kindLabel(a: Asset) {
  if (a.kind === 'table') return '表'
  if (a.kind === 'sql_view') return 'SQL 视图'
  return `文档 · ${a.document_source_type}`
}
</script>

<style scoped>
.bc {
  background: #fff; border: 1px solid var(--neutral-100, #e5e7eb);
  border-radius: 8px; padding: 16px; margin-bottom: 12px;
}
.bc-head { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.bc-asset { display: flex; align-items: center; gap: 8px; flex: 1; }
.bc-asset__name { font-weight: 600; }
.bc-warn {
  margin-bottom: 12px; padding: 6px 12px;
  background: #fff8e1; border-radius: 4px;
  font-size: 12px; color: #b45309;
}
.bc-mono { font-family: 'Menlo','Consolas',monospace; font-size: 12px; }
.bc-extra { margin-top: 16px; padding-top: 12px; border-top: 1px dashed #e5e7eb; }
.bc-extra__label { font-size: 12px; color: #6b7280; margin-bottom: 4px; }
</style>
