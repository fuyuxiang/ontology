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
import { computed, defineComponent, h, ref, watch } from 'vue'
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
  (e: 'navigate-to-binding', assetId: string): void
}>()

const asset = ref<Asset | null>(null)
const usage = ref<AssetWithUsage | null>(null)
const preview = ref<PreviewResult | null>(null)
const metrics = ref<QualityMetric[]>([])
const loading = ref(false)
const syncing = ref(false)
const profiling = ref(false)

async function load(id: string) {
  loading.value = true
  try {
    asset.value = await getAsset(id)
    const [u, m] = await Promise.all([
      getAssetUsage(id),
      getAssetQuality(id).catch(() => []),
    ])
    usage.value = u
    metrics.value = m
    try {
      preview.value = await previewAsset(id, 20)
    } catch {
      preview.value = null
    }
  } finally {
    loading.value = false
  }
}

watch(
  () => props.assetId,
  (id) => {
    if (id) load(id)
    else { asset.value = null; usage.value = null; preview.value = null; metrics.value = [] }
  },
  { immediate: true },
)

watch(
  () => props.visible,
  (v) => { if (v && props.assetId && !asset.value) load(props.assetId) },
)

async function doSyncSchema() {
  if (!asset.value || asset.value.kind === 'document') return
  syncing.value = true
  try {
    await syncAssetSchema(asset.value.id)
    await load(asset.value.id)
  } finally {
    syncing.value = false
  }
}

async function doProfile() {
  if (!asset.value || asset.value.kind === 'document') return
  profiling.value = true
  try {
    await profileAsset(asset.value.id)
    await load(asset.value.id)
  } finally {
    profiling.value = false
  }
}

function navigateToBinding() {
  if (asset.value) emit('navigate-to-binding', asset.value.id)
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
  syncing: syncing.value,
  profiling: profiling.value,
  onSyncSchema: doSyncSchema,
  onProfile: doProfile,
  onNavigateToBinding: navigateToBinding,
}))

// 用一个轻量组件包装，避免主模板太长
const bodyComp = defineComponent({
  render() {
    return h(AssetDetailBody, bodyProps.value)
  },
})
</script>
