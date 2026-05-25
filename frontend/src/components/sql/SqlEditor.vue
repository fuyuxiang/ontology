<template>
  <div class="se">
    <textarea
      class="se-input"
      :value="modelValue"
      :placeholder="placeholder"
      :rows="rows"
      @input="onInput"
    />
    <div class="se-toolbar">
      <a-space>
        <a-button v-if="showDryRun" size="small" :loading="running" @click="runDry">
          Dry-run 预览
        </a-button>
        <span v-if="placeholders.length" class="se-hint">
          占位符：<code v-for="p in placeholders" :key="p">:{{ p }}</code>
        </span>
      </a-space>
    </div>
    <div v-if="dryResult" class="se-result">
      <div class="se-result__title">编译后 SQL</div>
      <pre class="se-pre">{{ dryResult.compiled_sql }}</pre>
      <div class="se-result__meta">
        引用表：{{ dryResult.referenced_tables.join(', ') || '—' }} ·
        参数：{{ dryResult.placeholders.join(', ') || '—' }} ·
        类型：{{ dryResult.is_select ? 'SELECT' : (dryResult.is_dml ? 'DML' : '?') }}
      </div>
    </div>
    <a-alert v-if="dryError" type="error" :message="dryError" show-icon class="se-error" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Alert as AAlert, Button as AButton, Space as ASpace } from 'ant-design-vue'
import { dryRun } from '../../api/execute'
import type { DryRunResult } from '../../types/execution'

const props = withDefaults(defineProps<{
  modelValue: string
  placeholder?: string
  rows?: number
  showDryRun?: boolean
  // dry-run 上下文
  assetId?: string
  params?: Record<string, unknown>
  purpose?: string
}>(), {
  rows: 10,
  showDryRun: true,
  placeholder: 'SELECT * FROM <asset> WHERE id = :uid LIMIT :lim',
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void
}>()

const running = ref(false)
const dryResult = ref<DryRunResult | null>(null)
const dryError = ref<string | null>(null)

function onInput(ev: Event) {
  emit('update:modelValue', (ev.target as HTMLTextAreaElement).value)
}

const placeholders = computed(() => {
  const set = new Set<string>()
  const re = /(?<!:):([A-Za-z_][A-Za-z0-9_]*)/g
  for (const m of (props.modelValue || '').matchAll(re)) set.add(m[1])
  return Array.from(set)
})

async function runDry() {
  if (!props.assetId) {
    dryError.value = '需要 asset_id 才能 dry-run'
    return
  }
  running.value = true
  dryError.value = null
  try {
    dryResult.value = await dryRun({
      asset_id: props.assetId,
      sql: props.modelValue,
      params: props.params || Object.fromEntries(placeholders.value.map(p => [p, null])),
      purpose: props.purpose || 'sql.dry_run',
    })
  } catch (e: any) {
    dryError.value = e.response?.data?.detail?.detail
      || e.response?.data?.detail?.reason
      || e.message
      || 'dry-run 失败'
    dryResult.value = null
  } finally {
    running.value = false
  }
}

watch(() => props.modelValue, () => {
  dryResult.value = null
  dryError.value = null
})
</script>

<style scoped>
.se { display: flex; flex-direction: column; gap: 8px; }
.se-input {
  width: 100%; padding: 12px;
  font-family: var(--font-mono, 'Menlo', 'Consolas', monospace);
  font-size: 12px; line-height: 1.6;
  border: 1px solid var(--neutral-200, #e5e7eb);
  border-radius: 6px; resize: vertical; outline: none;
  background: #fafafa;
}
.se-input:focus { background: #fff; border-color: #3b82f6; }
.se-toolbar { display: flex; align-items: center; }
.se-hint { font-size: 12px; color: var(--neutral-500, #6b7280); }
.se-hint code { padding: 1px 4px; background: var(--neutral-100, #f3f4f6); border-radius: 3px; margin-right: 4px; font-size: 11px; }
.se-result {
  padding: 8px 12px; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px;
}
.se-result__title { font-size: 11px; color: #065f46; margin-bottom: 4px; }
.se-pre {
  font-family: var(--font-mono, 'Menlo', 'Consolas', monospace);
  font-size: 11px; white-space: pre-wrap; margin: 0; padding: 4px 0;
}
.se-result__meta { font-size: 11px; color: #047857; margin-top: 4px; }
.se-error { margin-top: 8px; }
</style>
