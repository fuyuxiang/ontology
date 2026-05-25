<template>
  <div class="bt">
    <!-- 顶部统计 + 操作 -->
    <div class="bt-toolbar">
      <a-space>
        <a-statistic title="主绑定" :value="primary ? 1 : 0" />
        <a-statistic title="增强" :value="enrichments.length" />
        <a-statistic title="证据" :value="evidence.length" />
      </a-space>
      <span style="flex:1" />
      <a-button type="primary" @click="openPicker('primary')">
        <template #icon><PlusOutlined /></template>
        绑定数据资产
      </a-button>
    </div>

    <!-- 主绑定 -->
    <div class="bt-section">
      <h3 class="bt-section__title">主绑定 (primary)</h3>
      <a-empty v-if="!primary" description="尚未绑定主数据资产" :image-style="{ height: '40px' }" />
      <BindingCard v-else :binding="primary" :asset="assetMap[primary.asset_id]"
                   :attributes="entityAttrs"
                   @save="onSave" @delete="onDelete" @test="onTestResolve" />
    </div>

    <!-- 增强绑定 -->
    <div v-if="enrichments.length" class="bt-section">
      <h3 class="bt-section__title">增强 (enrichment)</h3>
      <BindingCard v-for="b in enrichments" :key="b.id"
                   :binding="b" :asset="assetMap[b.asset_id]"
                   :attributes="entityAttrs"
                   @save="onSave" @delete="onDelete" @test="onTestResolve" />
    </div>

    <!-- 文档证据 -->
    <div v-if="evidence.length" class="bt-section">
      <h3 class="bt-section__title">文档证据 (document_evidence)</h3>
      <BindingCard v-for="b in evidence" :key="b.id"
                   :binding="b" :asset="assetMap[b.asset_id]"
                   :attributes="entityAttrs"
                   @save="onSave" @delete="onDelete" @test="onTestResolve" />
    </div>

    <!-- AssetPicker 弹窗 -->
    <AssetPicker
      v-model:visible="picker.open"
      :title="`选择资产作为${roleLabel(picker.role)}`"
      :kinds="picker.role === 'document_evidence' ? ['document'] : ['table', 'sql_view']"
      @confirm="onPicked"
    />

    <!-- test-resolve 结果 -->
    <a-modal v-model:open="testResult.open" title="解析样本" :footer="null" width="640">
      <a-empty v-if="!testResult.data" description="无数据" />
      <a-table v-else size="small"
               :columns="testResult.data.columns.map((c: string) => ({ title: c, dataIndex: c, key: c }))"
               :data-source="(testResult.data.rows || []).map((r: any[], i: number) => ({
                 ...Object.fromEntries(testResult.data.columns.map((c: string, j: number) => [c, r[j]])),
                 _idx: i,
               }))"
               row-key="_idx"
               :pagination="false" :scroll="{ x: 'max-content' }" />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  Button as AButton, Empty as AEmpty, Modal as AModal, Space as ASpace,
  Statistic as AStatistic, Table as ATable, message,
} from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import {
  createBinding, deleteBinding, listBindings, testResolveBinding, updateBinding,
} from '../../../api/binding'
import { getAsset } from '../../../api/asset'
import { entityApi } from '../../../api/ontology'
import type { Asset } from '../../../types/asset'
import type { BindingRole, FieldMapping, ObjectBinding } from '../../../types/binding'
import AssetPicker from '../../../components/asset/AssetPicker.vue'
import BindingCard from './BindingCard.vue'

const props = defineProps<{ objectTypeId: string }>()

const bindings = ref<ObjectBinding[]>([])
const assetMap = ref<Record<string, Asset>>({})
const entityAttrs = ref<{ id: string; name: string; type: string }[]>([])

const primary = computed(() => bindings.value.find(b => b.role === 'primary'))
const enrichments = computed(() => bindings.value.filter(b => b.role === 'enrichment'))
const evidence = computed(() => bindings.value.filter(b => b.role === 'document_evidence'))

const picker = reactive<{ open: boolean; role: BindingRole }>({ open: false, role: 'primary' })
const testResult = reactive<{ open: boolean; data: { columns: string[]; rows: any[][] } | null }>({
  open: false, data: null,
})

async function reload() {
  bindings.value = await listBindings({ object_type_id: props.objectTypeId })
  // 加载属性
  try {
    const detail = await entityApi.detail(props.objectTypeId)
    entityAttrs.value = (detail.attributes || []).map((a: any) => ({
      id: a.id, name: a.name, type: a.type,
    }))
  } catch {
    entityAttrs.value = []
  }
  // 加载关联 Asset
  for (const b of bindings.value) {
    if (!assetMap.value[b.asset_id]) {
      try {
        assetMap.value[b.asset_id] = await getAsset(b.asset_id)
      } catch {}
    }
  }
}

watch(() => props.objectTypeId, () => { if (props.objectTypeId) reload() }, { immediate: true })
onMounted(reload)

function openPicker(role: BindingRole) {
  picker.role = role
  picker.open = true
}

function roleLabel(r: BindingRole) {
  return ({ primary: '主绑定', enrichment: '增强绑定', document_evidence: '文档证据' } as any)[r]
}

async function onPicked(selected: Asset[]) {
  if (selected.length === 0) return
  const asset = selected[0]
  // 计算默认 field_mappings：列名相同的属性自动匹配
  const cols = (asset.schema_snapshot || []).map(c => c.name)
  const fms: FieldMapping[] = entityAttrs.value
    .filter(a => cols.includes(a.name))
    .map(a => ({ attribute_id: a.id, source_column: a.name, transform: null }))

  // 主绑定每个 ObjectType 只能 1 个；如果已有，提示错误
  if (picker.role === 'primary' && primary.value) {
    message.warning('已存在主绑定，请先删除或改为增强角色')
    return
  }
  try {
    await createBinding({
      object_type_id: props.objectTypeId,
      asset_id: asset.id,
      role: picker.role,
      field_mappings: fms,
      id_column: asset.primary_key?.[0] || null,
    })
    message.success('已绑定')
    await reload()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '绑定失败')
  }
}

async function onSave(bindingId: string, payload: { field_mappings: FieldMapping[]; id_column?: string | null; filter_expr?: string | null }) {
  try {
    await updateBinding(bindingId, payload)
    message.success('已保存')
    await reload()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '保存失败')
  }
}

async function onDelete(bindingId: string) {
  try {
    await deleteBinding(bindingId)
    message.success('已删除')
    await reload()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '删除失败')
  }
}

async function onTestResolve(bindingId: string) {
  try {
    const r: any = await testResolveBinding(bindingId)
    testResult.data = { columns: r.columns, rows: r.rows }
    testResult.open = true
  } catch (e: any) {
    message.error(e.response?.data?.detail || '取样失败')
  }
}
</script>

<style scoped>
.bt { padding: 16px 0; }
.bt-toolbar { display: flex; align-items: center; gap: 24px; margin-bottom: 16px; }
.bt-section { margin-bottom: 24px; }
.bt-section__title { font-size: 13px; font-weight: 600; color: #374151; margin: 0 0 8px; padding-left: 12px; border-left: 3px solid #3b82f6; }
</style>
