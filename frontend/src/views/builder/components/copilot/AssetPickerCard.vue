<template>
  <div class="apc">
    <div class="apc-head">
      <span class="apc-title">{{ title || '请勾选' }}</span>
      <span class="apc-count">已选 {{ checked.length }} / {{ items.length }}</span>
    </div>
    <div v-if="!items.length" class="apc-empty">没有匹配项</div>
    <div v-else class="apc-list">
      <label
        v-for="it in items"
        :key="it.id"
        :class="['apc-item', { 'apc-item--on': checked.includes(it.id) }]"
      >
        <input type="checkbox" :value="it.id" v-model="checked" />
        <div class="apc-item-main">
          <div class="apc-item-name">{{ it.name }}</div>
          <div class="apc-item-meta">
            <span v-if="kind === 'datasource' && it.table_count != null">{{ it.table_count }} 表</span>
            <span v-if="kind === 'document' && it.file_type">{{ String(it.file_type).toUpperCase() }}</span>
            <span v-if="it.size_bytes">· {{ Math.round(it.size_bytes / 1024) }} KB</span>
            <span v-if="it.description">· {{ it.description }}</span>
            <span v-if="kind === 'datasource' && it.sample_tables?.length">· 例：{{ it.sample_tables.slice(0,3).join(', ') }}</span>
            <span v-if="kind === 'document' && it.summary">· {{ it.summary.slice(0, 60) }}…</span>
          </div>
        </div>
      </label>
    </div>
    <button class="apc-confirm" :disabled="!checked.length || submitted" @click="submit">
      {{ submitted ? '已提交' : `已选好 (${checked.length})` }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  title?: string
  kind: 'datasource' | 'document'
  items: { id: string; name: string; [k: string]: any }[]
}>()
const emit = defineEmits<{ (e: 'submit', payload: { kind: string; ids: string[]; names: string[] }): void }>()

const checked = ref<string[]>([])
const submitted = ref(false)

function submit() {
  if (!checked.value.length) return
  const ids = [...checked.value]
  const names = props.items.filter(i => ids.includes(i.id)).map(i => i.name)
  submitted.value = true
  emit('submit', { kind: props.kind, ids, names })
}
</script>

<style scoped>
.apc {
  background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
  padding: 12px; display: flex; flex-direction: column; gap: 8px;
}
.apc-head { display: flex; align-items: center; }
.apc-title { font-size: 13px; font-weight: 600; color: #0f172a; flex: 1; }
.apc-count { font-size: 11px; color: #64748b; }
.apc-empty { font-size: 12px; color: #94a3b8; padding: 12px; text-align: center; }
.apc-list { display: flex; flex-direction: column; gap: 4px; max-height: 280px; overflow-y: auto; }
.apc-item {
  display: flex; gap: 8px; align-items: flex-start;
  padding: 8px 10px; border-radius: 8px; cursor: pointer;
  border: 1px solid transparent;
}
.apc-item:hover { background: #f8fafc; }
.apc-item--on { background: rgba(79,70,229,0.06); border-color: #4f46e5; }
.apc-item input { margin-top: 4px; flex-shrink: 0; }
.apc-item-main { flex: 1; min-width: 0; line-height: 1.4; }
.apc-item-name { font-size: 12px; font-weight: 600; color: #0f172a; word-break: break-all; }
.apc-item-meta { font-size: 11px; color: #64748b; margin-top: 2px; }
.apc-confirm {
  align-self: flex-end;
  padding: 6px 14px; border: 0; border-radius: 8px;
  background: linear-gradient(135deg, #4f46e5, #7c3aed); color: #fff;
  font-size: 12px; font-weight: 600; cursor: pointer;
}
.apc-confirm:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
