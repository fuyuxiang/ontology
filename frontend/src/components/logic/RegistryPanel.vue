<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { registryApi } from '../../api/registry'
import type { RegistryItem, RegistryGroup } from '../../api/registry'

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'add', item: RegistryItem): void
}>()

const search = ref('')
const typeFilter = ref<'all' | 'rule' | 'function'>('all')
const groups = ref<RegistryGroup[]>([])
const loading = ref(false)

async function fetchGroups() {
  loading.value = true
  try {
    groups.value = await registryApi.listGrouped(search.value || undefined)
  } finally {
    loading.value = false
  }
}

onMounted(fetchGroups)

let debounceTimer: ReturnType<typeof setTimeout> | undefined
function onSearchInput() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(fetchGroups, 300)
}

const filteredGroups = computed(() => {
  if (typeFilter.value === 'all') return groups.value
  return groups.value.map(g => ({
    ...g,
    items: g.items.filter(i => i.type === typeFilter.value),
  })).filter(g => g.items.length > 0)
})

function iconFor(type: 'rule' | 'function') {
  return type === 'rule' ? '⚡' : 'ƒ'
}
</script>

<template>
  <div class="registry-panel">
    <div class="drawer-panel__header">
      <h2>注册表</h2>
      <button class="btn-sm-edit" @click="emit('close')">✕</button>
    </div>

    <div style="padding:16px 24px 0;">
      <input class="logic-search" style="width:100%;box-sizing:border-box;" v-model="search"
        placeholder="搜索名称或描述…" @input="onSearchInput" />
      <div class="logic-filter-tags" style="margin-top:10px;">
        <button class="filter-tag" :class="{ 'filter-tag--active': typeFilter === 'all' }" @click="typeFilter = 'all'">全部</button>
        <button class="filter-tag" :class="{ 'filter-tag--active': typeFilter === 'rule' }" @click="typeFilter = 'rule'">⚡ 规则</button>
        <button class="filter-tag" :class="{ 'filter-tag--active': typeFilter === 'function' }" @click="typeFilter = 'function'">ƒ 函数</button>
      </div>
    </div>

    <div style="flex:1;overflow-y:auto;padding:16px 24px;">
      <div v-if="loading" class="logic-empty">加载中…</div>
      <div v-else-if="!filteredGroups.length" class="logic-empty">暂无结果</div>

      <template v-for="group in filteredGroups" :key="group.entity_id ?? '__global__'">
        <div style="font-size:12px;font-weight:600;color:var(--neutral-500,#888);margin:12px 0 6px;text-transform:uppercase;letter-spacing:.04em;">
          {{ group.entity_name || '全局' }}
        </div>

        <div v-for="item in group.items" :key="item.id" class="rule-card" style="cursor:default;">
          <div class="rule-card__header">
            <span style="font-size:16px;flex-shrink:0;">{{ iconFor(item.type) }}</span>
            <div style="flex:1;min-width:0;">
              <div style="font-weight:500;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                {{ item.name }}
                <code style="font-size:11px;color:var(--neutral-400,#aaa);font-weight:400;margin-left:4px;">{{ item.callable_name }}</code>
              </div>
              <div v-if="item.description" style="font-size:12px;color:var(--neutral-500,#888);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                {{ item.description }}
              </div>
            </div>
            <button class="btn-sm-exec" style="flex-shrink:0;" @click="emit('add', item)">+ 添加</button>
          </div>

          <div v-if="item.input_params?.length || item.output_info" class="rule-card__detail" style="margin-top:8px;padding-top:8px;">
            <div v-if="item.input_params?.length" class="rule-detail-row">
              <span class="rule-detail-label">输入</span>
              <span style="font-size:12px;">
                {{ item.input_params.map((p: any) => p.name ?? p).join(', ') }}
              </span>
            </div>
            <div v-if="item.output_info" class="rule-detail-row">
              <span class="rule-detail-label">输出</span>
              <span style="font-size:12px;">{{ item.output_info }}</span>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
