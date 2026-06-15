<template>
  <div class="mapping-root">
    <header class="mapping-topbar">
      <button class="mapping-back-btn" @click="$emit('prev')">← 返回</button>
      <div class="mapping-topbar-title">数据映射</div>
      <div class="mapping-topbar-progress">
        <span class="mapping-progress-label">已映射 {{ mappedCount }} / {{ totalPropCount }}</span>
        <div class="mapping-progress-track">
          <div class="mapping-progress-bar" :style="{ width: progressPct + '%' }"></div>
        </div>
        <span class="mapping-progress-pct">{{ Math.round(progressPct) }}%</span>
      </div>
      <button class="mapping-auto-btn secondary" :disabled="autoMapping" @click="runAutoMap">
        {{ autoMapping ? '推荐中...' : '一键推荐' }}
      </button>
      <button
        class="mapping-next-btn"
        :class="{ active: allMapped }"
        :disabled="!allMapped"
        @click="finishMapping"
      >开始数据验证 →</button>
    </header>

    <div class="mapping-body">
      <aside class="mapping-left">
        <div class="mapping-left-head">本体对象 · {{ objects.length }}</div>
        <div class="mapping-obj-list">
          <div
            v-for="o in objects"
            :key="o.id"
            :class="['mapping-obj-item', { active: selectedObjId === o.id }]"
            @click="selectObj(o.id)"
            @dragover.prevent
            @drop="onDropTable($event, o.id)"
          >
            <span class="mapping-obj-icon">{{ o.icon || '🔷' }}</span>
            <div class="mapping-obj-meta">
              <div class="mapping-obj-name">{{ o.displayName || o.name }}</div>
              <div class="mapping-obj-sub">
                <span v-if="objBoundTable(o.id)" class="mapping-obj-bound">📋 {{ objBoundTable(o.id)!.table_name }}</span>
                <span v-else class="mapping-obj-unbound">拖入数据表关联</span>
              </div>
            </div>
            <span :class="['mapping-obj-badge', objFullyMapped(o) ? 'done' : 'pending']">
              {{ objMappedCount(o) }}/{{ o.properties.length }}
            </span>
          </div>
        </div>
      </aside>

      <main class="mapping-center">
        <div v-if="selectedObj" class="mapping-editor">
          <div class="mapping-editor-head">
            <span class="mapping-editor-title">{{ selectedObj.displayName || selectedObj.name }}</span>
            <span v-if="objBoundTable(selectedObjId)" class="mapping-editor-table">
              → {{ objBoundTable(selectedObjId)!.table_name }}
            </span>
            <button v-if="objBoundTable(selectedObjId)" class="mapping-unbind-btn" @click="unbindTable(selectedObjId)">解除关联</button>
          </div>

          <div v-if="!objBoundTable(selectedObjId)" class="mapping-editor-empty">
            从右侧数据资产树中选择一张表拖到左栏对象上，或点击表旁的"关联"按钮
          </div>

          <div v-else class="mapping-table-wrap">
            <div v-if="suggesting" class="mapping-suggesting">正在推荐字段映射...</div>
            <table class="mapping-table">
              <thead>
                <tr>
                  <th>属性名</th>
                  <th>类型</th>
                  <th>映射字段</th>
                  <th>置信度</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in selectedObj.properties" :key="p.id">
                  <td class="mapping-td-name">{{ p.name }}</td>
                  <td class="mapping-td-type">{{ p.type || 'string' }}</td>
                  <td>
                    <a-select
                      v-model:value="p.source_column"
                      placeholder="选择字段"
                      :options="columnOptionsForProp(p)"
                      :filter-option="filterOption"
                      show-search
                      size="small"
                      style="width:220px"
                      allow-clear
                      @change="onColumnChange(p, $event)"
                    />
                  </td>
                  <td>
                    <span :class="['mapping-confidence', confidenceClass(p)]">{{ confidenceLabel(p) }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div v-else class="mapping-empty">← 选择一个对象查看映射详情</div>
      </main>

      <aside class="mapping-right">
        <div class="mapping-right-head">
          <span>数据资产</span>
          <a-input
            v-model:value="treeSearch"
            placeholder="搜索表名或字段..."
            size="small"
            allow-clear
            style="width:160px;margin-left:8px"
          />
        </div>
        <div v-if="treeLoading" class="mapping-tree-loading">加载中...</div>
        <div v-else class="mapping-tree">
          <div v-for="conn in filteredTree" :key="conn.connection_id || '__none__'" class="mapping-tree-conn">
            <div class="mapping-tree-conn-head" @click="toggleConn(conn.connection_id)">
              <span class="mapping-tree-arrow">{{ expandedConns.has(conn.connection_id) ? '▼' : '▶' }}</span>
              <span class="mapping-tree-conn-name">{{ conn.connection_name }}</span>
              <span class="mapping-tree-conn-count">{{ conn.tables.length }} 表</span>
            </div>
            <div v-if="expandedConns.has(conn.connection_id)" class="mapping-tree-tables">
              <div
                v-for="tbl in conn.tables"
                :key="tbl.asset_id"
                class="mapping-tree-table"
                draggable="true"
                @dragstart="onDragStart($event, tbl)"
              >
                <div class="mapping-tree-table-head" @click="toggleTable(tbl.asset_id)">
                  <span class="mapping-tree-arrow">{{ expandedTables.has(tbl.asset_id) ? '▼' : '▶' }}</span>
                  <span class="mapping-tree-table-name">{{ tbl.table_name }}</span>
                  <button
                    v-if="selectedObjId"
                    class="mapping-tree-bind-btn"
                    @click.stop="bindTable(selectedObjId, tbl)"
                  >关联</button>
                </div>
                <div v-if="expandedTables.has(tbl.asset_id)" class="mapping-tree-cols">
                  <div v-for="col in tbl.columns" :key="col.name" class="mapping-tree-col">
                    <span class="mapping-tree-col-name" :class="{ pk: col.is_pk }">{{ col.comment || col.name }}</span>
                    <span class="mapping-tree-col-type">{{ col.type }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { message } from 'ant-design-vue'
import { useBuilderStore } from '../../../store/builder'
import { fetchAssetTree, suggestColumns } from '../../../api/builder'
import type { BuilderSession } from '../../../types/builder'
import type { AssetTreeNode, AssetTreeTable } from '../../../api/builder'

const props = defineProps<{ session: BuilderSession }>()
const emit = defineEmits<{ (e: 'prev'): void; (e: 'next'): void }>()

const store = useBuilderStore()
const objects = computed(() => props.session.ontologyObjects || [])

const selectedObjId = ref(objects.value[0]?.id || '')
const selectedObj = computed(() => objects.value.find(o => o.id === selectedObjId.value) || null)

const assetTree = ref<AssetTreeNode[]>([])
const treeLoading = ref(false)
const treeSearch = ref('')
const expandedConns = reactive(new Set<string | null>())
const expandedTables = reactive(new Set<string>())

const bindings = ref<Record<string, AssetTreeTable>>({})
const suggesting = ref(false)
const autoMapping = ref(false)

const totalPropCount = computed(() => objects.value.reduce((s, o) => s + o.properties.length, 0))
const mappedCount = computed(() => objects.value.reduce((s, o) => s + o.properties.filter((p: any) => p.source_column).length, 0))
const progressPct = computed(() => totalPropCount.value ? (mappedCount.value / totalPropCount.value) * 100 : 0)
const allMapped = computed(() => totalPropCount.value > 0 && mappedCount.value === totalPropCount.value)

function objMappedCount(o: any) { return o.properties.filter((p: any) => p.source_column).length }
function objFullyMapped(o: any) { return o.properties.length > 0 && objMappedCount(o) === o.properties.length }
function objBoundTable(objId: string) { return bindings.value[objId] || null }
function selectObj(id: string) { selectedObjId.value = id }

const filteredTree = computed(() => {
  const q = treeSearch.value.toLowerCase().trim()
  if (!q) return assetTree.value
  return assetTree.value
    .map(conn => ({
      ...conn,
      tables: conn.tables.filter(t =>
        t.table_name.toLowerCase().includes(q) ||
        t.columns.some(c => c.name.toLowerCase().includes(q))
      ),
    }))
    .filter(conn => conn.tables.length > 0)
})

function toggleConn(connId: string | null) {
  if (expandedConns.has(connId)) expandedConns.delete(connId)
  else expandedConns.add(connId)
}
function toggleTable(assetId: string) {
  if (expandedTables.has(assetId)) expandedTables.delete(assetId)
  else expandedTables.add(assetId)
}

function onDragStart(e: DragEvent, tbl: AssetTreeTable) {
  e.dataTransfer?.setData('application/json', JSON.stringify(tbl))
}
function onDropTable(e: DragEvent, objId: string) {
  const raw = e.dataTransfer?.getData('application/json')
  if (!raw) return
  const tbl = JSON.parse(raw) as AssetTreeTable
  bindTable(objId, tbl)
}

async function bindTable(objId: string, tbl: AssetTreeTable) {
  bindings.value[objId] = tbl
  await runSuggestForObj(objId)
  syncStore()
}
function unbindTable(objId: string) {
  delete bindings.value[objId]
  const obj = objects.value.find(o => o.id === objId)
  if (obj) {
    for (const p of obj.properties) {
      ;(p as any).source_column = undefined
      ;(p as any)._confidence_score = 0
      ;(p as any)._candidates = undefined
    }
  }
  syncStore()
}

async function runSuggestForObj(objId: string) {
  const obj = objects.value.find(o => o.id === objId)
  const tbl = bindings.value[objId]
  if (!obj || !tbl) return

  suggesting.value = true
  try {
    const resp = await suggestColumns(
      tbl.asset_id,
      obj.properties.map((p: any) => ({ name: p.name, type: p.type, description: p.description }))
    )
    for (const sug of resp.suggestions) {
      const prop = obj.properties.find((p: any) => p.name === sug.property_name)
      if (prop && sug.candidates.length > 0) {
        ;(prop as any)._candidates = sug.candidates
      }
    }
  } catch {
    message.warning('字段推荐失败，可手动选择')
  } finally {
    suggesting.value = false
  }
}

function columnOptionsForProp(p: any) {
  const tbl = bindings.value[selectedObjId.value]
  if (!tbl) return []
  const candidates = (p._candidates || []) as any[]
  const candidateNames = new Set(candidates.map((c: any) => c.column))

  const opts: { label: string; value: string }[] = []
  for (const c of candidates) {
    const tierTag = c.tier === 'high' ? '★ ' : c.tier === 'medium' ? '☆ ' : ''
    opts.push({ label: `${tierTag}${c.column} (${c.column_type || ''})`, value: `${tbl.asset_id}::${c.column}` })
  }
  for (const col of tbl.columns) {
    if (!candidateNames.has(col.name)) {
      opts.push({ label: `${col.name} (${col.type})`, value: `${tbl.asset_id}::${col.name}` })
    }
  }
  return opts
}

function filterOption(input: string, option: any) {
  return option.label.toLowerCase().includes(input.toLowerCase())
}

function onColumnChange(p: any, val: string | undefined) {
  if (val) {
    const [assetId, col] = val.split('::')
    p.source_asset_id = assetId
    p.source_column = val
    const cand = (p._candidates || []).find((c: any) => c.column === col)
    ;(p as any)._confidence_score = cand ? cand.score : 1
  } else {
    p.source_asset_id = undefined
    p.source_column = undefined
    ;(p as any)._confidence_score = 0
  }
  syncStore()
}

function confidenceClass(p: any) {
  if (!p.source_column) return 'none'
  const s = (p as any)._confidence_score ?? 0
  if (s >= 0.7) return 'high'
  if (s >= 0.4) return 'medium'
  if (s > 0) return 'low'
  return 'manual'
}
function confidenceLabel(p: any) {
  if (!p.source_column) return '未映射'
  const s = (p as any)._confidence_score ?? 0
  if (s >= 0.7) return '高'
  if (s >= 0.4) return '中'
  if (s > 0) return '低'
  return '手动'
}

async function runAutoMap() {
  autoMapping.value = true
  try {
    const resp = await fetch('/api/v1/builder/auto-map', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        objects: objects.value.map(o => ({
          id: o.id, name: o.name, displayName: o.displayName,
          properties: o.properties.map((p: any) => ({ name: p.name, type: p.type, description: p.description })),
        })),
      }),
    })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const data = await resp.json()
    const mappings = data.mappings || {}
    for (const obj of objects.value) {
      const m = mappings[obj.id]
      if (!m) continue
      if (m.matched_tables?.length) {
        const firstTable = m.matched_tables[0]
        const treeTable = assetTree.value
          .flatMap(c => c.tables)
          .find(t => t.asset_id === firstTable.asset_id)
        if (treeTable) bindings.value[obj.id] = treeTable
      }
      if (m.property_mappings) {
        for (const [pName, pm] of Object.entries(m.property_mappings) as any) {
          const prop = obj.properties.find((p: any) => p.name === pName)
          if (prop && pm.column) {
            ;(prop as any).source_column = `${pm.asset_id}::${pm.column}`
            ;(prop as any).source_asset_id = pm.asset_id
            ;(prop as any)._confidence_score = pm.score || 0.5
          }
        }
      }
    }
    message.success('一键推荐完成，请确认映射结果')
  } catch (e: any) {
    message.error('推荐失败：' + (e.message || e))
  } finally {
    autoMapping.value = false
    syncStore()
  }
}

function syncStore() {
  store.patchActive({ ontologyObjects: objects.value })
}

function finishMapping() {
  syncStore()
  emit('next')
}

onMounted(async () => {
  treeLoading.value = true
  try {
    const resp = await fetchAssetTree()
    assetTree.value = resp.tree
    if (resp.tree.length > 0) expandedConns.add(resp.tree[0].connection_id)
  } catch (e: any) {
    message.error('加载数据资产失败：' + (e.message || e))
  } finally {
    treeLoading.value = false
  }
})
</script>

<style scoped>
.mapping-root { display: flex; flex-direction: column; height: 100%; }
.mapping-topbar { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-bottom: 1px solid #e8e8e8; }
.mapping-topbar-title { font-size: 16px; font-weight: 600; }
.mapping-topbar-progress { display: flex; align-items: center; gap: 8px; flex: 1; }
.mapping-progress-track { width: 120px; height: 6px; background: #f0f0f0; border-radius: 3px; }
.mapping-progress-bar { height: 100%; background: #1890ff; border-radius: 3px; transition: width 0.3s; }
.mapping-progress-label { font-size: 12px; color: #666; }
.mapping-progress-pct { font-size: 12px; color: #999; }
.mapping-back-btn, .mapping-next-btn, .mapping-auto-btn { padding: 6px 14px; border-radius: 4px; border: 1px solid #d9d9d9; cursor: pointer; font-size: 13px; background: #fff; }
.mapping-next-btn.active { background: #1890ff; color: #fff; border-color: #1890ff; }
.mapping-next-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.mapping-auto-btn.secondary { background: #fafafa; }

.mapping-body { display: flex; flex: 1; overflow: hidden; }
.mapping-left { width: 240px; border-right: 1px solid #f0f0f0; overflow-y: auto; }
.mapping-center { flex: 1; overflow-y: auto; padding: 16px; }
.mapping-right { width: 280px; border-left: 1px solid #f0f0f0; overflow-y: auto; }

.mapping-left-head, .mapping-right-head { padding: 10px 12px; font-weight: 600; font-size: 13px; border-bottom: 1px solid #f0f0f0; display: flex; align-items: center; }
.mapping-obj-list { padding: 4px 0; }
.mapping-obj-item { display: flex; align-items: center; gap: 8px; padding: 8px 12px; cursor: pointer; border-left: 3px solid transparent; }
.mapping-obj-item:hover { background: #fafafa; }
.mapping-obj-item.active { background: #e6f7ff; border-left-color: #1890ff; }
.mapping-obj-icon { font-size: 16px; }
.mapping-obj-meta { flex: 1; min-width: 0; }
.mapping-obj-name { font-size: 13px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mapping-obj-sub { font-size: 11px; color: #999; }
.mapping-obj-bound { color: #52c41a; }
.mapping-obj-unbound { color: #bbb; font-style: italic; }
.mapping-obj-badge { font-size: 11px; padding: 2px 6px; border-radius: 10px; background: #f5f5f5; }
.mapping-obj-badge.done { background: #f6ffed; color: #52c41a; }

.mapping-editor-head { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.mapping-editor-title { font-size: 15px; font-weight: 600; }
.mapping-editor-table { font-size: 13px; color: #1890ff; }
.mapping-unbind-btn { font-size: 12px; color: #ff4d4f; border: none; background: none; cursor: pointer; margin-left: auto; }
.mapping-editor-empty { padding: 40px; text-align: center; color: #bbb; font-size: 14px; }
.mapping-suggesting { padding: 8px 0; color: #1890ff; font-size: 13px; }

.mapping-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.mapping-table th { text-align: left; padding: 8px; background: #fafafa; border-bottom: 1px solid #f0f0f0; }
.mapping-table td { padding: 8px; border-bottom: 1px solid #f5f5f5; }
.mapping-td-name { font-weight: 500; }
.mapping-td-type { color: #999; font-size: 12px; }
.mapping-confidence { font-size: 12px; padding: 2px 8px; border-radius: 4px; }
.mapping-confidence.high { background: #f6ffed; color: #52c41a; }
.mapping-confidence.medium { background: #fff7e6; color: #fa8c16; }
.mapping-confidence.low { background: #fff1f0; color: #ff4d4f; }
.mapping-confidence.none { color: #bbb; }
.mapping-confidence.manual { background: #e6f7ff; color: #1890ff; }

.mapping-empty { padding: 60px; text-align: center; color: #ccc; font-size: 14px; }

.mapping-tree-loading { padding: 20px; text-align: center; color: #999; }
.mapping-tree { padding: 4px 0; }
.mapping-tree-conn-head { display: flex; align-items: center; gap: 6px; padding: 8px 10px; cursor: pointer; font-weight: 500; font-size: 13px; }
.mapping-tree-conn-head:hover { background: #fafafa; }
.mapping-tree-conn-count { font-size: 11px; color: #999; margin-left: auto; }
.mapping-tree-arrow { font-size: 10px; color: #999; width: 14px; text-align: center; }
.mapping-tree-tables { padding-left: 14px; }
.mapping-tree-table { margin-bottom: 2px; }
.mapping-tree-table-head { display: flex; align-items: center; gap: 6px; padding: 5px 8px; cursor: pointer; font-size: 13px; border-radius: 4px; }
.mapping-tree-table-head:hover { background: #f0f5ff; }
.mapping-tree-table-name { flex: 1; }
.mapping-tree-bind-btn { font-size: 11px; padding: 2px 8px; border: 1px solid #1890ff; color: #1890ff; background: #fff; border-radius: 3px; cursor: pointer; opacity: 0; transition: opacity 0.2s; }
.mapping-tree-table-head:hover .mapping-tree-bind-btn { opacity: 1; }
.mapping-tree-cols { padding-left: 20px; }
.mapping-tree-col { display: flex; gap: 8px; padding: 3px 8px; font-size: 12px; color: #666; }
.mapping-tree-col-name { font-family: monospace; }
.mapping-tree-col-name.pk { font-weight: 600; color: #fa8c16; }
.mapping-tree-col-type { color: #999; }
</style>
