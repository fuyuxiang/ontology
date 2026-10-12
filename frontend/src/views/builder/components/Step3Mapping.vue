<template>
  <div class="mapping-root">
    <header class="mapping-topbar">
      <button class="mapping-back-btn" @click="$emit('prev')">{{ text('← 返回') }}</button>
      <div class="mapping-topbar-title">{{ text('数据映射') }}</div>
      <div class="mapping-topbar-progress">
        <span class="mapping-progress-label">{{ text('已映射') }} {{ mappedCount }} / {{ totalPropCount }}</span>
        <div class="mapping-progress-track">
          <div class="mapping-progress-bar" :style="{ width: progressPct + '%' }"></div>
        </div>
        <span class="mapping-progress-pct">{{ Math.round(progressPct) }}%</span>
      </div>
      <button class="mapping-auto-btn secondary" :disabled="autoMapping || suggesting" @click="runAutoMap">
        {{ autoMapping ? text('推荐中...') : text('一键推荐') }}
      </button>
      <button
        class="mapping-next-btn"
        :class="{ active: allMapped }"
        :disabled="!allMapped || autoMapping || suggesting"
        @click="finishMapping"
      >{{ text('进入最终审核 →') }}</button>
    </header>

    <nav class="mapping-mobile-tabs" :aria-label="text('数据映射')">
      <button v-for="tab in mobileTabs" :key="tab.key" :class="{ active: mobilePane === tab.key }" :aria-pressed="mobilePane === tab.key" @click="mobilePane = tab.key">{{ text(tab.label) }}</button>
    </nav>

    <div class="mapping-body" :data-mobile-pane="mobilePane">
      <aside class="mapping-left">
        <div class="mapping-left-head">{{ text('本体对象') }} · {{ objects.length }}</div>
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
                <span v-else class="mapping-obj-unbound">{{ text('拖入数据表关联') }}</span>
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
            <button v-if="objBoundTable(selectedObjId)" class="mapping-unbind-btn" @click="unbindTable(selectedObjId)">{{ text('解除关联') }}</button>
          </div>

          <div v-if="!objBoundTable(selectedObjId)" class="mapping-editor-empty">
            {{ text('从右侧数据资产树中选择一张表拖到左栏对象上，或点击表旁的"关联"按钮') }}
          </div>

          <section v-if="objBoundTable(selectedObjId)" class="mapping-enrichment">
            <label>{{ text("补充资产（明确一对一左关联）") }}<a-select mode="multiple" :value="selectedObj.backing_asset_ids?.slice(1) || []" :options="allTables.filter(table => table.asset_id !== objBoundTable(selectedObjId)?.asset_id).map(table => ({label:table.table_name + ' · ' + table.asset_id.slice(0,8),value:table.asset_id}))" style="width:100%;" :placeholder="text('选择补充资产')" @change="setEnrichments(selectedObj, $event as string[])" /></label>
            <div v-for="extra in enrichmentAssets(selectedObj)" :key="extra.asset_id" class="mapping-relation-row">
              <strong>{{ extra.table_name }}</strong>
              <label>{{ text("主资产关联列") }}<select :value="joinValue(selectedObj,extra.asset_id,'primary_source_column')" @change="setJoin(selectedObj,extra.asset_id,'primary_source_column',($event.target as HTMLSelectElement).value)"><option value="">{{ text("选择主资产物理字段") }}</option><option v-for="column in objBoundTable(selectedObjId)?.columns" :key="column.name" :value="column.name">{{ column.name }}</option></select></label>
              <label>{{ text("补充资产关联列") }}<select :value="joinValue(selectedObj,extra.asset_id,'enrichment_source_column')" @change="setJoin(selectedObj,extra.asset_id,'enrichment_source_column',($event.target as HTMLSelectElement).value)"><option value="">{{ text("选择补充资产物理字段") }}</option><option v-for="column in extra.columns" :key="column.name" :value="column.name">{{ column.name }}</option></select></label>
              <p v-if="!enrichmentReady(selectedObj,extra.asset_id)" role="alert">{{ text("待审核：请明确两侧关联列；没有规则不能进入验证/发布。") }}</p>
              <p v-else>{{ text("按等值一对一 LEFT JOIN；未匹配属性为 null，重复关联键会导致业务失败。") }}</p>
            </div>
          </section>

          <div v-if="objBoundTable(selectedObjId)" class="mapping-table-wrap">
            <div v-if="suggesting" class="mapping-suggesting">{{ text('正在推荐字段映射...') }}</div>
            <table class="mapping-table">
              <thead>
                <tr>
                  <th>{{ text('属性名') }}</th>
                  <th>{{ text('类型') }}</th>
                  <th>{{ text('来源资产') }}</th>
                  <th>{{ text('映射字段') }}</th>
                  <th>{{ text('置信度') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in selectedObj.properties" :key="p.id">
                  <td class="mapping-td-name" :data-label="text('属性名')">{{ p.name }}</td>
                  <td class="mapping-td-type" :data-label="text('类型')">{{ p.type || 'string' }}</td>
                  <td :data-label="text('来源资产')"><select :value="p.source_asset_id || objBoundTable(selectedObjId)?.asset_id" :disabled="autoMapping" @change="onPropertyAssetChange(p, ($event.target as HTMLSelectElement).value)"><option v-for="asset in objectAssets(selectedObj)" :key="asset.asset_id" :value="asset.asset_id">{{ asset.table_name }} · {{ asset.asset_id.slice(0, 8) }}</option></select></td>
                  <td :data-label="text('映射字段')">
                    <a-select
                      v-model:value="p.source_column"
                      :disabled="autoMapping"
                      :placeholder="text('选择字段')"
                      :options="columnOptionsForProp(p)"
                      :filter-option="filterOption"
                      show-search
                      size="small"
                      style="width:220px"
                      allow-clear
                      @change="onColumnChange(p, $event)"
                    />
                  </td>
                  <td :data-label="text('置信度')">
                    <span :class="['mapping-confidence', confidenceClass(p)]">{{ confidenceLabel(p) }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div v-else class="mapping-empty">{{ text('← 选择一个对象查看映射详情') }}</div>
        <section v-if="relations.length" class="mapping-relations">
          <h3>{{ text('关系字段映射') }}</h3>
          <p>{{ text('选择两端真实关联属性，验证时使用其已确认的源字段进行 JOIN。') }}</p>
          <div v-for="relation in relations" :key="relation.id" class="mapping-relation-row">
            <strong>{{ relation.displayName || relation.name }} ({{ relation.cardinality }})</strong>
            <label>{{ objectLabel(relation.source) }}<select v-model="relation.sourceField" @change="syncStore"><option value="">{{ text('选择源关联属性') }}</option><option v-for="property in objectProperties(relation.source)" :key="property.id" :value="property.name">{{ property.name }}</option></select></label>
            <label>{{ objectLabel(relation.target) }}<select v-model="relation.targetField" @change="syncStore"><option value="">{{ text('选择目标关联属性') }}</option><option v-for="property in objectProperties(relation.target)" :key="property.id" :value="property.name">{{ property.name }}</option></select></label>
          </div>
        </section>
      </main>

      <aside class="mapping-right">
        <div class="mapping-right-head">
          <span>{{ text('数据资产') }}</span>
          <a-input
            v-model:value="treeSearch"
            :placeholder="text('搜索表名或字段...')"
            size="small"
            allow-clear
            style="width:160px;margin-left:8px"
          />
        </div>
        <div v-if="treeLoading" class="mapping-tree-loading">{{ text('加载中...') }}</div>
        <div v-else class="mapping-tree">
          <div v-for="conn in filteredTree" :key="conn.connection_id || '__none__'" class="mapping-tree-conn">
            <div class="mapping-tree-conn-head" @click="toggleConn(conn.connection_id)">
              <span class="mapping-tree-arrow">{{ expandedConns.has(conn.connection_id) ? '▼' : '▶' }}</span>
              <span class="mapping-tree-conn-name">{{ conn.connection_name }}</span>
              <span class="mapping-tree-conn-count">{{ conn.tables.length }} {{ text('表') }}</span>
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
                  >{{ text('关联') }}</button>
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
import { authenticatedFetch } from '../../../api/authenticatedFetch'
import { ref, computed, onMounted, onUnmounted, reactive } from 'vue'
import { message } from 'ant-design-vue'
import { useBuilderStore } from '../../../store/builder'
import { authHeaders } from '../../../utils/authHeaders'
import { useProductText } from '../../../composables/useProductText'
const { text } = useProductText()
const mobilePane = ref('mapping')
const mobileTabs = [{ key: 'objects', label: '对象' }, { key: 'mapping', label: '字段映射' }, { key: 'assets', label: '数据资产' }]
import { fetchAssetTree, suggestColumns } from '../../../api/builder'
import type { BuilderSession } from '../../../types/builder'
import type { AssetTreeNode, AssetTreeTable } from '../../../api/builder'

const props = defineProps<{ session: BuilderSession }>()
const emit = defineEmits<{ (e: 'prev'): void; (e: 'next'): void }>()

const store = useBuilderStore()
let mounted = true
const suggestionRequests = new Map<string, number>()
const objects = computed(() => props.session.ontologyObjects || [])
const relations = computed(() => props.session.ontologyRelations || [])
const objectProperties = (id: string) => objects.value.find(object => object.id === id || object.name === id)?.properties || []
const objectLabel = (id: string) => { const object = objects.value.find(item => item.id === id || item.name === id); return object?.displayName || object?.name || id }

const selectedObjId = ref(objects.value[0]?.id || '')
const selectedObj = computed(() => objects.value.find(o => o.id === selectedObjId.value) || null)

const assetTree = ref<AssetTreeNode[]>([])
const treeLoading = ref(false)
const treeSearch = ref('')
const expandedConns = reactive(new Set<string | null>())
const expandedTables = reactive(new Set<string>())

const bindings = ref<Record<string, AssetTreeTable>>({})
const pendingSuggestions = ref(0)
const suggesting = computed(() => pendingSuggestions.value > 0)
const autoMapping = ref(false)

const totalPropCount = computed(() => objects.value.reduce((s, o) => s + o.properties.length, 0))
function isMapped(property: any) { return !!property.source_asset_id && !!property.source_column && assetTree.value.some(connection => connection.tables.some(table => table.asset_id === property.source_asset_id && table.columns.some(column => column.name === property.source_column))) }
const mappedCount = computed(() => objects.value.reduce((s, o) => s + o.properties.filter(isMapped).length, 0))
const progressPct = computed(() => totalPropCount.value ? (mappedCount.value / totalPropCount.value) * 100 : 0)
const allTables = computed(() => assetTree.value.flatMap(connection => connection.tables))
const allMapped = computed(() => totalPropCount.value > 0 && mappedCount.value === totalPropCount.value && objects.value.every(object => (object.backing_asset_ids || []).slice(1).every(assetId => enrichmentReady(object,assetId))) && relations.value.every(relation => !!relation.sourceField && !!relation.targetField))

function objectAssets(object:any):AssetTreeTable[] { return allTables.value.filter(table => (object?.backing_asset_ids || []).includes(table.asset_id)) }
function enrichmentAssets(object:any):AssetTreeTable[] { return objectAssets(object).filter(table => table.asset_id !== object?.backing_asset_ids?.[0]) }
function joinValue(object:any,assetId:string,key:'primary_source_column'|'enrichment_source_column'):string { return object.enrichment_bindings?.find((rule:any) => rule.asset_id === assetId)?.[key] || '' }
function enrichmentReady(object:any,assetId:string) {
  const primary = allTables.value.find(table => table.asset_id === object.backing_asset_ids?.[0]), extra = allTables.value.find(table => table.asset_id === assetId)
  return !!primary?.columns.some(column => column.name === joinValue(object,assetId,'primary_source_column')) && !!extra?.columns.some(column => column.name === joinValue(object,assetId,'enrichment_source_column'))
}
function setJoin(object:any,assetId:string,key:'primary_source_column'|'enrichment_source_column',value:string) {
  const rules = object.enrichment_bindings ||= []
  let rule = rules.find((item:any) => item.asset_id === assetId)
  if (!rule) { rule = {asset_id:assetId}; rules.push(rule) }
  rule[key] = value || null; syncStore()
}
function setEnrichments(object:any, ids:string[]) {
  const primary = bindings.value[object.id]?.asset_id
  if (!primary || autoMapping.value) return
  const assets = [primary,...ids.filter(id => id !== primary)]
  for (const property of object.properties) if (property.source_asset_id && !assets.includes(property.source_asset_id)) { property.source_asset_id = undefined; property.source_column = undefined; property._candidates = undefined }
  object.backing_asset_ids = assets
  object.enrichment_bindings = (object.enrichment_bindings || []).filter((rule:any) => ids.includes(rule.asset_id))
  syncStore()
}
function onPropertyAssetChange(property:any,assetId:string) { property.source_asset_id = assetId || undefined; property.source_column = undefined; property._candidates = undefined; property._confidence_score = 0; syncStore() }

function objMappedCount(o: any) { return o.properties.filter(isMapped).length }
function objFullyMapped(o: any) { return o.properties.length > 0 && objMappedCount(o) === o.properties.length }
function objBoundTable(objId: string) { return bindings.value[objId] || null }
function selectObj(id: string) { selectedObjId.value = id; mobilePane.value = 'mapping' }

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
  mobilePane.value = 'mapping'
  if (autoMapping.value) return
  if (bindings.value[objId]?.asset_id !== tbl.asset_id) unbindTable(objId)
  bindings.value[objId] = tbl
  const obj = objects.value.find(o => o.id === objId)
  if (obj) obj.backing_asset_ids = [tbl.asset_id, ...(obj.backing_asset_ids || []).filter(id => id !== tbl.asset_id)]
  syncStore()
  await runSuggestForObj(objId)
  syncStore()
}
function unbindTable(objId: string) {
  if (autoMapping.value) return
  suggestionRequests.set(objId, (suggestionRequests.get(objId) || 0) + 1)
  delete bindings.value[objId]
  const obj = objects.value.find(o => o.id === objId)
  if (obj) {
    obj.backing_asset_ids = []
    obj.enrichment_bindings = []
    for (const p of obj.properties) {
      p.source_asset_id = undefined
      p.source_column = undefined
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

  const request = (suggestionRequests.get(objId) || 0) + 1
  suggestionRequests.set(objId, request)
  ++pendingSuggestions.value
  try {
    const resp = await suggestColumns(
      tbl.asset_id,
      obj.properties.map((p: any) => ({ name: p.name, type: p.type, description: p.description }))
    )
    if (!mounted || suggestionRequests.get(objId) !== request || bindings.value[objId]?.asset_id !== tbl.asset_id) return
    for (const sug of resp.suggestions) {
      const prop = obj.properties.find((p: any) => p.name === sug.property_name)
      if (prop && sug.candidates.length > 0) {
        ;(prop as any)._candidates = sug.candidates
      }
    }
  } catch {
    if (mounted && suggestionRequests.get(objId) === request) message.warning(text('字段推荐失败，可手动选择'))
  } finally {
    --pendingSuggestions.value
  }
}

function columnOptionsForProp(p: any) {
  const tbl = allTables.value.find(table => table.asset_id === (p.source_asset_id || bindings.value[selectedObjId.value]?.asset_id))
  if (!tbl) return []
  const candidates = (p._candidates || []) as any[]
  const candidateNames = new Set(candidates.map((c: any) => c.column))

  const opts: { label: string; value: string }[] = []
  for (const c of candidates) {
    const tierTag = c.tier === 'high' ? '★ ' : c.tier === 'medium' ? '☆ ' : ''
    opts.push({ label: `${tierTag}${c.column} (${c.column_type || ''})`, value: c.column })
  }
  for (const col of tbl.columns) {
    if (!candidateNames.has(col.name)) {
      opts.push({ label: `${col.name} (${col.type})`, value: col.name })
    }
  }
  return opts
}

function filterOption(input: string, option: any) {
  return option.label.toLowerCase().includes(input.toLowerCase())
}

function onColumnChange(p: any, val: string | undefined) {
  if (val) {
    const col = val
    p.source_asset_id ||= bindings.value[selectedObjId.value]?.asset_id
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
  if (!p.source_column) return text('未映射')
  const s = (p as any)._confidence_score ?? 0
  if (s >= 0.7) return text('高')
  if (s >= 0.4) return text('中')
  if (s > 0) return text('低')
  return text('手动')
}

async function runAutoMap() {
  if (autoMapping.value || suggesting.value || !objects.value.length) return
  autoMapping.value = true
  try {
    const resp = await authenticatedFetch(`${import.meta.env.VITE_API_BASE_URL || "/api/v1"}/builder/auto-map`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({
        objects: objects.value.map(o => ({
          id: o.id, name: o.name, displayName: o.displayName,
          properties: o.properties.map((p: any) => ({ name: p.name, type: p.type, description: p.description })),
        })),
      }),
    })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const data = await resp.json()
    if (!mounted) return
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
      if (m.matched_tables?.length) obj.backing_asset_ids = m.matched_tables.map((table: any) => table.asset_id)
      if (m.property_mappings) {
        for (const [pName, pm] of Object.entries(m.property_mappings) as any) {
          const prop = obj.properties.find((p: any) => p.name === pName)
          if (prop && pm.column) {
            ;(prop as any).source_column = pm.column
            ;(prop as any).source_asset_id = pm.asset_id
            ;(prop as any)._confidence_score = pm.score || 0.5
          }
        }
      }
    }
    message.success(text('一键推荐完成，请确认映射结果'))
  } catch (e: any) {
    message.error('推荐失败：' + (e.message || e))
  } finally {
    autoMapping.value = false
    syncStore()
  }
}

function syncStore() {
  if (mounted) store.updateSession(props.session.sessionId, { ontologyObjects: objects.value, ontologyRelations: relations.value })
}

function finishMapping() {
  if (!allMapped.value || autoMapping.value || suggesting.value) return
  syncStore()
  emit('next')
}

onMounted(async () => {
  treeLoading.value = true
  try {
    const resp = await fetchAssetTree()
    if (!mounted) return
    assetTree.value = resp.tree
    const tables = resp.tree.flatMap(connection => connection.tables)
    for (const obj of objects.value) {
      const assetId = obj.backing_asset_ids?.[0] || obj.properties.find(prop => prop.source_asset_id)?.source_asset_id
      const table = tables.find(item => item.asset_id === assetId)
      if (table) bindings.value[obj.id] = table
      for (const property of obj.properties) {
        const prefix = `${property.source_asset_id}::`
        if (property.source_asset_id && property.source_column?.startsWith(prefix)) property.source_column = property.source_column.slice(prefix.length)
      }
    }
    syncStore()
    if (resp.tree.length > 0) expandedConns.add(resp.tree[0].connection_id)
  } catch (e: any) {
    message.error('加载数据资产失败：' + (e.message || e))
  } finally {
    treeLoading.value = false
  }
})
onUnmounted(() => { mounted = false })
</script>

<style scoped>
.mapping-enrichment {margin:12px;padding:12px;border:1px solid #e2e8f0;border-radius:8px;}.mapping-enrichment select{max-width:100%;padding:6px;}.mapping-enrichment p{margin:4px 0;}
.mapping-root { display: flex; flex-direction: column; height: 100%; }
.mapping-relations { margin: 20px; padding: 16px; border: 1px solid #e2e8f0; border-radius: 8px; }.mapping-relation-row { display:flex;flex-wrap:wrap;gap:12px;margin-top:12px; }.mapping-relation-row label { display:flex;gap:8px;align-items:center; }.mapping-relation-row select { min-width:140px;max-width:100%;padding:6px; }
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
.mapping-mobile-tabs { display: none; }
.mapping-left { width: 240px; border-right: 1px solid #f0f0f0; overflow-y: auto; }
.mapping-center { flex: 1; overflow-y: auto; padding: 16px; }
.mapping-right { width: 280px; border-left: 1px solid #f0f0f0; overflow-y: auto; }
.mapping-center { min-width: 0; }

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
@media (max-width: 1024px) {
  .mapping-left { width: 170px; flex-shrink: 0; }
  .mapping-right { width: 220px; flex-shrink: 0; }
  .mapping-table-wrap { overflow-x: auto; }
}
@media (max-width: 768px) {
  .mapping-topbar { flex-wrap: wrap; gap: 10px; padding: 12px; }
  .mapping-topbar-title { white-space: nowrap; }
  .mapping-topbar-progress { flex-basis: calc(100% - 88px); min-width: 0; flex-wrap: wrap; }
  .mapping-progress-track { flex: 1; min-width: 60px; width: auto; }
  .mapping-auto-btn, .mapping-next-btn { flex: 1; min-height: 44px; white-space: nowrap; }
  .mapping-mobile-tabs { display: flex; padding: 8px; gap: 8px; background: #fff; }
  .mapping-mobile-tabs button { flex: 1; min-height: 44px; border: 1px solid #d9d9d9; border-radius: 6px; background: #fff; }
  .mapping-mobile-tabs button.active { color: #1677ff; border-color: #1677ff; background: #e6f4ff; }
  .mapping-body { display: block; overflow-y: auto; min-height: 240px; }
  .mapping-left, .mapping-center, .mapping-right { display: none; width: 100%; height: 100%; box-sizing: border-box; overflow: auto; border: 0; }
  .mapping-body[data-mobile-pane="objects"] .mapping-left,
  .mapping-body[data-mobile-pane="mapping"] .mapping-center,
  .mapping-body[data-mobile-pane="assets"] .mapping-right { display: block; }
  .mapping-center { padding: 12px; }
  .mapping-editor-head { flex-wrap: wrap; }
  .mapping-enrichment { margin: 10px 0; padding: 10px; }
  .mapping-table-wrap { overflow: visible; }
  .mapping-table, .mapping-table tbody { display: block; width: 100%; }
  .mapping-table thead { display: none; }
  .mapping-table tr { display: block; margin: 12px 0; padding: 8px; border: 1px solid #e2e8f0; border-radius: 8px; }
  .mapping-table td { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; padding: 8px 2px; border: 0; overflow-wrap: anywhere; }
  .mapping-table td::before { content: attr(data-label); flex-basis: 100%; font-size: 12px; color: #64748b; }
  .mapping-table td select { width: 100%; max-width: 100%; min-height: 36px; }
  .mapping-table :deep(.ant-select) { width: 100% !important; }
  .mapping-tree-bind-btn { opacity: 1; min-height: 36px; padding: 6px 12px; }
  .mapping-right-head { flex-wrap: wrap; gap: 8px; }
  .mapping-relations { margin: 12px 0; padding: 12px; }
}
</style>
