<template>
  <div class="api-service">
    <div class="api-service__header">
      <h1 class="page-title">本体服务</h1>
      <p class="page-desc">基于本体 Schema 自动生成语义化 API，支持实体查询、关系遍历和规则执行</p>
    </div>

    <div class="api-service__body">
      <!-- 左侧：端点列表 -->
      <div class="api-sidebar">
        <div class="api-sidebar__search">
          <input v-model="searchText" class="search-input" placeholder="搜索端点..." />
        </div>
        <div class="api-sidebar__list">
          <div v-for="group in filteredEndpoints" :key="group.entity" class="endpoint-group">
            <div class="endpoint-group__title" @click="toggleGroup(group.entity)">
              <svg class="endpoint-group__arrow" :class="{ 'endpoint-group__arrow--open': expandedGroups[group.entity] }" width="10" height="10" viewBox="0 0 12 12" fill="none">
                <path d="M4 3l4 3-4 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <span class="endpoint-group__name">{{ group.entityCn }}</span>
              <span class="endpoint-group__count">{{ group.endpoints.length }}</span>
            </div>
            <div v-show="expandedGroups[group.entity]" class="endpoint-group__items">
              <div
                v-for="ep in group.endpoints"
                :key="ep.path"
                class="endpoint-item"
                :class="{ 'endpoint-item--active': selectedEndpoint?.path === ep.path }"
                @click="selectedEndpoint = ep"
              >
                <span class="endpoint-item__method" :class="`endpoint-item__method--${ep.method.toLowerCase()}`">{{ ep.method }}</span>
                <span class="endpoint-item__path">{{ ep.shortPath }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：端点详情 + 调试 -->
      <div class="api-main">
        <template v-if="selectedEndpoint">
          <div class="api-detail">
            <div class="api-detail__header">
              <span class="method-badge" :class="`method-badge--${selectedEndpoint.method.toLowerCase()}`">{{ selectedEndpoint.method }}</span>
              <code class="api-detail__path">{{ selectedEndpoint.path }}</code>
            </div>
            <p class="api-detail__desc">{{ selectedEndpoint.description }}</p>

            <!-- 参数 -->
            <div class="api-detail__section" v-if="selectedEndpoint.params?.length">
              <h3 class="section-title">请求参数</h3>
              <table class="param-table">
                <thead><tr><th>参数名</th><th>类型</th><th>必填</th><th>说明</th></tr></thead>
                <tbody>
                  <tr v-for="p in selectedEndpoint.params" :key="p.name">
                    <td><code>{{ p.name }}</code></td>
                    <td>{{ p.type }}</td>
                    <td>{{ p.required ? '是' : '否' }}</td>
                    <td>{{ p.description }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- 在线调试 -->
            <div class="api-detail__section">
              <h3 class="section-title">在线调试</h3>
              <div class="try-panel">
                <div class="try-panel__params" v-if="selectedEndpoint.params?.length">
                  <div v-for="p in selectedEndpoint.params" :key="p.name" class="try-param">
                    <label>{{ p.name }}</label>
                    <input v-model="tryParams[p.name]" class="try-input" :placeholder="p.type" />
                  </div>
                </div>
                <button class="btn-primary" @click="executeTry" :disabled="trying">
                  {{ trying ? '请求中...' : '发送请求' }}
                </button>
                <div v-if="tryResult !== null" class="try-result">
                  <pre class="try-result__code">{{ tryResult }}</pre>
                </div>
              </div>
            </div>
          </div>
        </template>
        <div v-else class="api-empty">
          <p>选择左侧端点查看详情和调试</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { get, post } from '../../api/client'

interface EndpointParam { name: string; type: string; required: boolean; description: string }
interface Endpoint { method: string; path: string; shortPath: string; description: string; params?: EndpointParam[] }
interface EndpointGroup { entity: string; entityCn: string; endpoints: Endpoint[] }

const searchText = ref('')
const endpointGroups = ref<EndpointGroup[]>([])
const expandedGroups = reactive<Record<string, boolean>>({})
const selectedEndpoint = ref<Endpoint | null>(null)
const tryParams = reactive<Record<string, string>>({})
const trying = ref(false)
const tryResult = ref<string | null>(null)

const filteredEndpoints = computed(() => {
  if (!searchText.value) return endpointGroups.value
  const q = searchText.value.toLowerCase()
  return endpointGroups.value
    .map(g => ({ ...g, endpoints: g.endpoints.filter(e => e.path.toLowerCase().includes(q) || e.description.includes(q)) }))
    .filter(g => g.endpoints.length > 0)
})

function toggleGroup(entity: string) {
  expandedGroups[entity] = !expandedGroups[entity]
}

async function loadEndpoints() {
  try {
    const data = await get<{ groups: EndpointGroup[] }>('/ontology-api/endpoints')
    endpointGroups.value = data.groups
    if (data.groups.length > 0) expandedGroups[data.groups[0].entity] = true
  } catch { /* fallback empty */ }
}

async function executeTry() {
  if (!selectedEndpoint.value) return
  trying.value = true
  tryResult.value = null
  try {
    const ep = selectedEndpoint.value
    let result: any
    if (ep.method === 'GET') {
      const params = new URLSearchParams()
      Object.entries(tryParams).forEach(([k, v]) => { if (v) params.set(k, v) })
      result = await get(`${ep.path}?${params.toString()}`)
    } else {
      const body: Record<string, any> = {}
      Object.entries(tryParams).forEach(([k, v]) => { if (v) body[k] = v })
      result = await post(ep.path, body)
    }
    tryResult.value = JSON.stringify(result, null, 2)
  } catch (e: any) {
    tryResult.value = `Error: ${e?.response?.data?.detail || e.message}`
  } finally {
    trying.value = false
  }
}

onMounted(loadEndpoints)
</script>

<style scoped>
.api-service { display: flex; flex-direction: column; height: 100%; }
.api-service__header { padding: 20px 24px 12px; flex-shrink: 0; }
.page-title { font-size: 18px; font-weight: 700; color: var(--neutral-900); margin: 0 0 4px; }
.page-desc { font-size: 13px; color: var(--neutral-500); margin: 0; }
.api-service__body { display: flex; flex: 1; overflow: hidden; border-top: 1px solid var(--neutral-200); }

.api-sidebar { width: 280px; flex-shrink: 0; border-right: 1px solid var(--neutral-200); display: flex; flex-direction: column; overflow: hidden; }
.api-sidebar__search { padding: 12px; border-bottom: 1px solid var(--neutral-100); }
.search-input { width: 100%; padding: 6px 10px; border: 1px solid var(--neutral-200); border-radius: 6px; font-size: 12px; outline: none; }
.search-input:focus { border-color: var(--semantic-500); }
.api-sidebar__list { flex: 1; overflow-y: auto; padding: 8px; }

.endpoint-group__title { display: flex; align-items: center; gap: 6px; padding: 6px 8px; cursor: pointer; border-radius: 6px; font-size: 12px; font-weight: 600; color: var(--neutral-700); }
.endpoint-group__title:hover { background: var(--neutral-50); }
.endpoint-group__arrow { transition: transform 0.15s; color: var(--neutral-400); }
.endpoint-group__arrow--open { transform: rotate(90deg); }
.endpoint-group__name { flex: 1; }
.endpoint-group__count { font-size: 10px; color: var(--neutral-400); background: var(--neutral-100); padding: 1px 5px; border-radius: 4px; }
.endpoint-group__items { padding-left: 16px; }

.endpoint-item { display: flex; align-items: center; gap: 6px; padding: 5px 8px; border-radius: 5px; cursor: pointer; font-size: 11px; }
.endpoint-item:hover { background: var(--neutral-50); }
.endpoint-item--active { background: var(--semantic-50); }
.endpoint-item__method { font-size: 9px; font-weight: 700; padding: 1px 4px; border-radius: 3px; text-transform: uppercase; }
.endpoint-item__method--get { background: #dbeafe; color: #1d4ed8; }
.endpoint-item__method--post { background: #dcfce7; color: #15803d; }
.endpoint-item__method--put { background: #fef3c7; color: #b45309; }
.endpoint-item__method--delete { background: #fee2e2; color: #dc2626; }
.endpoint-item__path { color: var(--neutral-600); font-family: monospace; font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.api-main { flex: 1; overflow-y: auto; padding: 20px 24px; }
.api-empty { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--neutral-400); font-size: 13px; }

.api-detail__header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.method-badge { font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 4px; }
.method-badge--get { background: #dbeafe; color: #1d4ed8; }
.method-badge--post { background: #dcfce7; color: #15803d; }
.api-detail__path { font-size: 13px; color: var(--neutral-800); }
.api-detail__desc { font-size: 13px; color: var(--neutral-600); margin: 0 0 16px; }

.section-title { font-size: 13px; font-weight: 600; color: var(--neutral-800); margin: 16px 0 8px; }
.param-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.param-table th { text-align: left; padding: 6px 8px; background: var(--neutral-50); border-bottom: 1px solid var(--neutral-200); color: var(--neutral-600); font-weight: 600; }
.param-table td { padding: 6px 8px; border-bottom: 1px solid var(--neutral-100); color: var(--neutral-700); }
.param-table code { background: var(--neutral-100); padding: 1px 4px; border-radius: 3px; font-size: 11px; }

.try-panel { background: var(--neutral-50); border: 1px solid var(--neutral-200); border-radius: 8px; padding: 14px; }
.try-panel__params { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; }
.try-param { display: flex; flex-direction: column; gap: 3px; }
.try-param label { font-size: 11px; font-weight: 600; color: var(--neutral-600); }
.try-input { padding: 5px 8px; border: 1px solid var(--neutral-200); border-radius: 5px; font-size: 12px; width: 160px; }
.btn-primary { padding: 7px 16px; border-radius: 6px; border: none; background: var(--semantic-600); color: #fff; font-size: 12px; font-weight: 500; cursor: pointer; }
.btn-primary:hover:not(:disabled) { background: var(--semantic-700); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.try-result { margin-top: 12px; }
.try-result__code { background: var(--neutral-900); color: #a5f3fc; padding: 12px; border-radius: 6px; font-size: 11px; overflow-x: auto; max-height: 300px; overflow-y: auto; }
</style>
