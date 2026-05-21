<template>
  <div
    :class="['draggable-asset-card', 'asset-card', { subscribed: asset.subscribed }]"
    draggable="true"
    @dragstart="onDragStart"
    @click="$emit('toggle', asset.id)"
    style="cursor:pointer"
  >
    <div class="asset-card-header">
      <div class="asset-card-name" @click.stop>
        <span class="drag-handle" style="color:#cbd5e1;margin-right:4px;cursor:grab">⠿</span>
        <span style="font-size:14px;margin-right:4px">{{ typeIcon(asset.type) }}</span>
        <span>{{ asset.name }}</span>
      </div>
      <span v-if="asset.subscribed" style="color:#10b981;font-size:14px">✓</span>
    </div>

    <div class="asset-card-tags">
      <span class="ant-tag" style="background:#e6f4ff;color:#1677ff;border:1px solid #91caff;font-size:10px;padding:0 6px;border-radius:4px">{{ asset.type }}</span>
      <span class="ant-tag" style="font-size:10px;color:#64748b;background:#f1f5f9;border:none;padding:0 6px;border-radius:4px">{{ asset.domain }}</span>
    </div>

    <div v-if="asset.category === 'unstructured' && (asset.fileType || asset.fileSize)" class="asset-card-id" style="font-size:10px;color:#94a3b8;margin-top:2px">
      <span v-if="asset.fileType">类型：{{ asset.fileType?.toUpperCase() }}</span>
      <span v-if="asset.fileType && asset.fileSize"> · </span>
      <span v-if="asset.fileSize">大小：{{ asset.fileSize }}</span>
    </div>

    <div v-if="asset.description" class="asset-card-desc" style="font-size:11px;color:#64748b;margin-top:6px;line-height:1.5">
      {{ asset.description }}
    </div>

    <div v-if="asset.rating" class="asset-card-footer">
      <span style="font-size:11px;color:#fadb14">{{ '★'.repeat(Math.round(asset.rating)) + '☆'.repeat(Math.max(0, 5 - Math.round(asset.rating))) }}</span>
    </div>

    <div v-if="asset.fields?.length" class="asset-fields">
      <span v-for="f in asset.fields" :key="f.name" class="field-tag">
        <code class="field-tag-en">{{ f.en || f.name }}</code>
        <span class="field-tag-cn">{{ f.name }}</span>
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DataAsset } from '../../../../types/builder'

const props = defineProps<{ asset: DataAsset }>()
defineEmits<{ (e: 'toggle', id: string): void }>()

function typeIcon(t?: string) {
  if (!t) return '📦'
  if (/数据模型|数据表|宽表|主表|结构化/.test(t)) return '🗃️'
  if (/标签|tag/i.test(t)) return '🏷️'
  if (/指标|KPI|kpi/i.test(t)) return '📊'
  if (/规则/.test(t)) return '📐'
  if (/文档|FAQ|SOP/.test(t)) return '📄'
  if (/录音|外呼|语音/.test(t)) return '🎙️'
  if (/图谱/.test(t)) return '🕸️'
  return '📦'
}

function onDragStart(e: DragEvent) {
  if (!e.dataTransfer) return
  e.dataTransfer.setData('assetId', props.asset.id)
  e.dataTransfer.effectAllowed = 'copy'
}
</script>
