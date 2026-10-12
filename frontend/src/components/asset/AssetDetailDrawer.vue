<template>
  <a-drawer
    v-if="!embedded"
    :open="visible"
    :title="asset?.name || '资产详情'"
    width="720"
    @update:open="(v: boolean) => emit('update:visible', v)"
  >
    <template #extra>
      <a-space v-if="asset">
        <a-tag :color="kindColor(asset.kind)">{{ kindLabel(asset.kind) }}</a-tag>
        <a-tag v-if="asset.document_source_type">{{ asset.document_source_type }}</a-tag>
        <a-tag v-if="asset.alias" color="purple">@{{ asset.alias }}</a-tag>
      </a-space>
    </template>
    <component :is="bodyComp" />
  </a-drawer>

  <component v-else :is="bodyComp" />
</template>

<script setup lang="ts">
import { computed, defineComponent, h, ref, watch, onBeforeUnmount } from 'vue'
import { Drawer as ADrawer, Tag as ATag, Space as ASpace } from 'ant-design-vue'
import { getAsset, getAssetUsage, syncAssetSchema, profileAsset, previewAsset, getAssetQuality } from '../../api/asset'
import type { Asset, AssetWithUsage, PreviewResult } from '../../types/asset'
import type { QualityMetric } from '../../types/quality'
import AssetDetailBody from './AssetDetailBody.vue'

const props = defineProps<{
  assetId: string | null
  visible?: boolean
  embedded?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:visible', v: boolean): void
}>()

const asset = ref<Asset | null>(null)
const usage = ref<AssetWithUsage | null>(null)
const preview = ref<PreviewResult | null>(null)
const metrics = ref<QualityMetric[]>([])
const loading = ref(false)
const syncing = ref(false)
const profiling = ref(false)
const loadError = ref(''), previewError = ref(''), metricsError = ref(''), usageError = ref('')
let request = 0
const describeError = (error: any) => error?.response?.data?.detail || error.message || '资产请求失败'
onBeforeUnmount(() => { ++request })

async function load(id: string) {
  const current = ++request
  loading.value = true
  asset.value = null; usage.value = null; preview.value = null; metrics.value = []
  loadError.value = ''; previewError.value = ''; metricsError.value = ''; usageError.value = ''
  try {
    const result = await getAsset(id)
    if (current !== request || id !== props.assetId) return
    asset.value = result
    const [u, m, p] = await Promise.allSettled([getAssetUsage(id), getAssetQuality(id), previewAsset(id, 20)])
    if (current !== request || id !== props.assetId) return
    if (u.status === 'fulfilled') usage.value = u.value; else usageError.value = describeError(u.reason)
    if (m.status === 'fulfilled') metrics.value = m.value; else metricsError.value = describeError(m.reason)
    if (p.status === 'fulfilled') preview.value = p.value; else previewError.value = describeError(p.reason)
  } catch (exception:any) { if (current === request) loadError.value = describeError(exception)
  } finally {
    if (current === request) loading.value = false
  }
}

watch(
  () => props.assetId,
  (id) => {
    if (id) load(id)
    else { ++request; loading.value = false; asset.value = null; usage.value = null; preview.value = null; metrics.value = []; loadError.value = '' }
  },
  { immediate: true },
)

watch(
  () => props.visible,
  (v) => { if (v && props.assetId && !asset.value) load(props.assetId) },
)

async function doSyncSchema() {
  if (!asset.value || syncing.value || asset.value.kind === 'document') return
  const id = asset.value.id
  syncing.value = true
  try {
    await syncAssetSchema(id)
    if (id === props.assetId) await load(id)
  } catch (exception:any) { if (id === props.assetId) previewError.value = describeError(exception)
  } finally {
    syncing.value = false
  }
}

async function doProfile() {
  if (!asset.value || profiling.value || asset.value.kind === 'document') return
  const id = asset.value.id
  profiling.value = true
  try {
    await profileAsset(id)
    if (id === props.assetId) await load(id)
  } catch (exception:any) { if (id === props.assetId) metricsError.value = describeError(exception)
  } finally {
    profiling.value = false
  }
}

function kindLabel(k: string) {
  return ({ table: '表', sql_view: 'SQL 视图', document: '文档' } as any)[k] || k
}
function kindColor(k: string) {
  return ({ table: 'blue', sql_view: 'cyan', document: 'gold' } as any)[k] || 'default'
}

const bodyProps = computed(() => ({
  asset: asset.value,
  usage: usage.value,
  preview: preview.value,
  metrics: metrics.value,
  loading: loading.value,
  loadError: loadError.value, previewError: previewError.value, metricsError: metricsError.value, usageError: usageError.value,
  onReload: () => { if (props.assetId) void load(props.assetId) },
  syncing: syncing.value,
  profiling: profiling.value,
  onSyncSchema: doSyncSchema,
  onProfile: doProfile,
}))

// 用一个轻量组件包装，避免主模板太长
const bodyComp = defineComponent({
  render() {
    return h(AssetDetailBody, bodyProps.value)
  },
})
</script>
