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
      <button
        class="mapping-next-btn"
        :class="{ active: allMapped }"
        :disabled="!allMapped"
        @click="finishMapping"
      >进入水合演练 →</button>
    </header>

    <div class="mapping-toolbar">
      <div class="mapping-toolbar-row">
        <label>数据范围：</label>
        <a-select
          v-model:value="selectedScope"
          placeholder="选择数据库 / Schema"
          :options="scopeOptions"
          :loading="scopeLoading"
          style="width:280px"
          size="small"
          allow-clear
          @dropdown-visible-change="loadScopes"
        />
        <button class="mapping-auto-btn" :disabled="autoMapping" @click="runAutoMap">
          {{ autoMapping ? '智能映射中...' : '智能映射' }}
        </button>
        <span v-if="!selectedScope" class="mapping-toolbar-hint">选择范围可提高映射准确率，不选则全库扫描</span>
      </div>
      <div v-if="mapCoverage" class="mapping-stats">
        <span class="mapping-stat mapping-stat--high">高置信：{{ mapCoverage.high }}</span>
        <span class="mapping-stat mapping-stat--medium">中置信：{{ mapCoverage.medium }}</span>
        <span class="mapping-stat mapping-stat--low">低置信：{{ mapCoverage.low }}</span>
        <span class="mapping-stat mapping-stat--none">未匹配：{{ mapCoverage.none }}</span>
      </div>
    </div>

    <div class="mapping-body">
      <aside class="mapping-left">
        <div class="mapping-left-head">本体对象 · {{ objects.length }}</div>
        <div class="mapping-obj-list">
          <div
            v-for="o in objects"
            :key="o.id"
            :class="['mapping-obj-item', { active: selectedId === o.id }]"
            @click="selectedId = o.id"
          >
            <span class="mapping-obj-icon" :style="{ background: tierBg(o.tier) }">{{ o.icon || '🔷' }}</span>
            <div class="mapping-obj-meta">
              <div class="mapping-obj-name">{{ o.displayName || o.name }}</div>
              <div class="mapping-obj-sub">{{ objMappedCount(o) }} / {{ o.properties.length }} 已映射</div>
            </div>
            <span :class="['mapping-obj-badge', objFullyMapped(o) ? 'done' : 'pending']">
              {{ objFullyMapped(o) ? '✓' : objMappedCount(o) + '/' + o.properties.length }}
            </span>
          </div>
        </div>
      </aside>

      <main class="mapping-right">
        <div v-if="selected" class="mapping-editor">
          <div class="mapping-editor-head">
            <span class="mapping-editor-title">{{ selected.displayName || selected.name }}</span>
            <span class="mapping-editor-sub">{{ selected.properties.length }} 个属性</span>
          </div>

          <div class="mapping-editor-tables">
            <label class="mapping-editor-tables-label">关联数据表：</label>
            <a-select
              v-model:value="objBoundTables[selected.id]"
              mode="multiple"
              placeholder="搜索并选择数据表..."
              :options="tableOptionsForObj(selected)"
              :filter-option="filterTableOption"
              show-search
              size="small"
              style="flex:1"
              @change="onTableBindChange(selected)"
            />
          </div>

          <div class="mapping-table-wrap">
            <table class="mapping-table">
              <thead>
                <tr>
                  <th>属性名</th>
                  <th>类型</th>
                  <th>映射列</th>
                  <th>置信度</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in selected.properties" :key="p.id">
                  <td class="mapping-td-name">{{ p.name }}</td>
                  <td class="mapping-td-type">{{ p.type || 'string' }}</td>
                  <td>
                    <a-select
                      v-model:value="p.source_column"
                      placeholder="选择列"
                      :options="columnOptionsForObj(selected)"
                      :filter-option="filterColumnOption"
                      show-search
                      size="small"
                      style="width:200px"
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
        <div v-else class="mapping-empty">← 选择一个对象查看属性映射</div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { useBuilderStore } from '../../../store/builder'
import type { BuilderSession } from '../../../types/builder'

const props = defineProps<{ session: BuilderSession }>()
const emit = defineEmits<{ (e: 'prev'): void; (e: 'next'): void }>()

const store = useBuilderStore()
const objects = computed(() => props.session.ontologyObjects || [])
const selectedId = ref(objects.value[0]?.id || '')
const selected = computed(() => objects.value.find(o => o.id === selectedId.value) || null)

const selectedScope = ref<string | undefined>(props.session.mappingScope || undefined)
const scopeOptions = ref<{ label: string; value: string }[]>([])
const scopeLoading = ref(false)
const autoMapping = ref(false)
const mapCoverage = ref<{ high: number; medium: number; low: number; none: number } | null>(null)

// Per-object: matched tables and their columns. Key = objectId
const objTableMap = ref<Record<string, { asset_id: string; table_name: string; columns: string[] }[]>>({})
// Per-object: user-bound table asset_ids
const objBoundTables = ref<Record<string, string[]>>({})

const totalPropCount = computed(() => objects.value.reduce((s, o) => s + o.properties.length, 0))
const mappedCount = computed(() => objects.value.reduce((s, o) => s + o.properties.filter((p: any) => p.source_column).length, 0))
const progressPct = computed(() => totalPropCount.value ? (mappedCount.value / totalPropCount.value) * 100 : 0)
const allMapped = computed(() => totalPropCount.value > 0 && mappedCount.value === totalPropCount.value)

function objMappedCount(o: any) { return o.properties.filter((p: any) => p.source_column).length }
function objFullyMapped(o: any) { return o.properties.length > 0 && objMappedCount(o) === o.properties.length }
function tierBg(t: number) { return t === 1 ? '#dbeafe' : t === 2 ? '#fef3c7' : '#e0e7ff' }

function confidenceClass(p: any) {
  if (!p.source_column) return 'none'
  const s = p._confidence_score ?? 0
  if (s >= 0.8) return 'high'
  if (s >= 0.5) return 'medium'
  if (s > 0) return 'low'
  return 'manual'
}
function confidenceLabel(p: any) {
  if (!p.source_column) return '未映射'
  const s = p._confidence_score ?? 0
  if (s >= 0.8) return '高'
  if (s >= 0.5) return '中'
  if (s > 0) return '低'
  return '手动'
}

function tableOptionsForObj(obj: any) {
  const tables = objTableMap.value[obj.id] || []
  return tables.map(t => ({ label: t.table_name, value: t.asset_id }))
}

function filterTableOption(input: string, option: any) {
  return option.label.toLowerCase().includes(input.toLowerCase())
}

function onTableBindChange(obj: any) {
  syncStore()
}

function columnOptionsForObj(obj: any) {
  const boundIds = objBoundTables.value[obj.id] || []
  const tables = (objTableMap.value[obj.id] || []).filter(t => boundIds.includes(t.asset_id))
  const opts: { label: string; value: string }[] = []
  for (const t of tables) {
    for (const col of t.columns) {
      opts.push({ label: tables.length > 1 ? `${t.table_name}.${col}` : col, value: `${t.asset_id}::${col}` })
    }
  }
  return opts
}

function filterColumnOption(input: string, option: any) {
  return option.label.toLowerCase().includes(input.toLowerCase())
}

function onColumnChange(p: any, val: string | undefined) {
  if (val) {
    const [assetId, col] = val.split('::')
    p.source_asset_id = assetId
    p.source_column = val
    if (!p._confidence_score) p._confidence_score = 1
  } else {
    p.source_asset_id = undefined
    p.source_column = undefined
    p._confidence_score = 0
  }
  syncStore()
}

function syncStore() {
  store.patchActive({
    ontologyObjects: objects.value,
    mappingScope: selectedScope.value,
  })
}

async function loadScopes(open: boolean) {
  if (!open || scopeOptions.value.length) return
  scopeLoading.value = true
  try {
    const resp = await fetch('/api/v1/assets/scopes')
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const data = await resp.json()
    const items = data.scopes || data || []
    scopeOptions.value = items.map((s: any) => ({
      label: s.display_name || s.name,
      value: s.id || s.name,
    }))
  } catch (e: any) {
    message.error('加载数据范围失败：' + (e.message || e))
  } finally {
    scopeLoading.value = false
  }
}

// PLACEHOLDER_AUTO_MAP
async function runAutoMap() {
  if (autoMapping.value) return
  autoMapping.value = true
  mapCoverage.value = null
  try {
    const resp = await fetch('/api/v1/builder/auto-map', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scope: selectedScope.value || null,
        objects: objects.value.map(o => ({
          id: o.id,
          name: o.name,
          displayName: o.displayName,
          properties: o.properties.map((p: any) => ({
            name: p.name, type: p.type, description: p.description,
          })),
        })),
      }),
    })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `HTTP ${resp.status}`)
    }
    const data = await resp.json()
    const mappings = data.mappings || {}
    let totalHigh = 0, totalMedium = 0, totalLow = 0, totalNone = 0

    for (const obj of objects.value) {
      const objMap = mappings[obj.id]
      if (!objMap) { totalNone += obj.properties.length; continue }

      const tables = objMap.matched_tables || []
      objTableMap.value[obj.id] = tables.map((t: any) => ({
        asset_id: t.asset_id,
        table_name: t.table_name,
        columns: t.columns || [],
      }))
      // Auto-bind the best matching table(s)
      const bestAssetId = objMap.asset_id
      if (bestAssetId) {
        objBoundTables.value[obj.id] = [bestAssetId]
      }

      for (const prop of obj.properties) {
        const pm = objMap.property_mappings?.[prop.name]
        if (pm && pm.score > 0) {
          prop.source_asset_id = pm.asset_id
          prop.source_column = `${pm.asset_id}::${pm.column}`
          prop._confidence_score = pm.score
          if (pm.score >= 0.8) totalHigh++
          else if (pm.score >= 0.5) totalMedium++
          else totalLow++
        } else {
          totalNone++
        }
      }
    }
    mapCoverage.value = { high: totalHigh, medium: totalMedium, low: totalLow, none: totalNone }
    syncStore()
    const mapped = totalHigh + totalMedium + totalLow
    message.success(`智能映射完成：${mapped} 个属性已匹配，${totalNone} 个待手动处理`)
  } catch (e: any) {
    message.error('智能映射失败：' + (e.message || e))
  } finally {
    autoMapping.value = false
  }
}

function finishMapping() {
  if (!allMapped.value) {
    message.warning('请完成所有属性的映射后再进入下一步')
    return
  }
  syncStore()
  emit('next')
}

onMounted(() => {
  if (props.session.mappingScope) {
    selectedScope.value = props.session.mappingScope
  }
})
</script>

<style scoped>
.mapping-root { display: flex; flex-direction: column; height: 100%; }
.mapping-topbar {
  display: flex; align-items: center; gap: 16px;
  padding: 12px 24px; background: #fff; border-bottom: 1px solid #e2e8f0;
}
.mapping-back-btn { background: none; border: none; color: #475569; font-size: 13px; cursor: pointer; padding: 6px 10px; border-radius: 6px; }
.mapping-back-btn:hover { background: #f1f5f9; }
.mapping-topbar-title { font-size: 15px; font-weight: 600; color: #0f172a; }
.mapping-topbar-progress { display: flex; align-items: center; gap: 8px; margin-left: auto; }
.mapping-progress-label { font-size: 12px; color: #64748b; }
.mapping-progress-track { width: 120px; height: 6px; background: #e2e8f0; border-radius: 3px; }
.mapping-progress-bar { height: 100%; background: #4f46e5; border-radius: 3px; transition: width 0.3s; }
.mapping-progress-pct { font-size: 12px; color: #4f46e5; font-weight: 600; }
.mapping-next-btn {
  padding: 8px 16px; border-radius: 8px; border: none;
  background: #e2e8f0; color: #94a3b8; font-size: 13px; cursor: not-allowed;
}
.mapping-next-btn.active { background: #4f46e5; color: #fff; cursor: pointer; }
.mapping-next-btn.active:hover { background: #4338ca; }

.mapping-toolbar { padding: 12px 24px; background: #fafbfc; border-bottom: 1px solid #e2e8f0; }
.mapping-toolbar-row { display: flex; align-items: center; gap: 12px; }
.mapping-toolbar-row label { font-size: 13px; color: #475569; white-space: nowrap; }
.mapping-toolbar-hint { font-size: 12px; color: #94a3b8; }
.mapping-auto-btn {
  padding: 6px 14px; border-radius: 6px; border: 1px solid #4f46e5;
  background: #fff; color: #4f46e5; font-size: 12px; cursor: pointer;
}
.mapping-auto-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.mapping-auto-btn:not(:disabled):hover { background: #4f46e5; color: #fff; }
.mapping-stats { display: flex; gap: 12px; margin-top: 8px; }
.mapping-stat { font-size: 12px; padding: 2px 8px; border-radius: 4px; }
.mapping-stat--high { background: #dcfce7; color: #166534; }
.mapping-stat--medium { background: #fef3c7; color: #92400e; }
.mapping-stat--low { background: #fee2e2; color: #991b1b; }
.mapping-stat--none { background: #f1f5f9; color: #475569; }

.mapping-body { display: flex; flex: 1; overflow: hidden; }
.mapping-left {
  width: 260px; border-right: 1px solid #e2e8f0; background: #fff;
  display: flex; flex-direction: column;
}
.mapping-left-head { padding: 12px 16px; font-size: 13px; font-weight: 600; color: #334155; border-bottom: 1px solid #f1f5f9; }
.mapping-obj-list { flex: 1; overflow-y: auto; }
.mapping-obj-item {
  display: flex; align-items: center; gap: 10px; padding: 10px 16px;
  cursor: pointer; border-bottom: 1px solid #f8fafc; transition: background 0.15s;
}
.mapping-obj-item:hover { background: #f8fafc; }
.mapping-obj-item.active { background: #eff6ff; border-left: 3px solid #4f46e5; }
.mapping-obj-icon { width: 28px; height: 28px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 14px; }
.mapping-obj-meta { flex: 1; min-width: 0; }
.mapping-obj-name { font-size: 13px; font-weight: 500; color: #1e293b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mapping-obj-sub { font-size: 11px; color: #94a3b8; }
.mapping-obj-badge { font-size: 11px; padding: 2px 6px; border-radius: 4px; white-space: nowrap; }
.mapping-obj-badge.done { background: #dcfce7; color: #166534; }
.mapping-obj-badge.pending { background: #f1f5f9; color: #64748b; }

.mapping-right { flex: 1; overflow-y: auto; padding: 20px 24px; background: #f8fafc; }
.mapping-editor { background: #fff; border-radius: 10px; border: 1px solid #e2e8f0; overflow: hidden; }
.mapping-editor-head { display: flex; align-items: center; gap: 12px; padding: 14px 20px; border-bottom: 1px solid #f1f5f9; }
.mapping-editor-title { font-size: 15px; font-weight: 600; color: #0f172a; }
.mapping-editor-sub { font-size: 12px; color: #94a3b8; }
.mapping-editor-table { margin-left: auto; font-size: 12px; color: #4f46e5; background: #eff6ff; padding: 2px 8px; border-radius: 4px; }
.mapping-editor-tables { display: flex; align-items: center; gap: 10px; padding: 10px 20px; background: #f8fafc; border-bottom: 1px solid #f1f5f9; }
.mapping-editor-tables-label { font-size: 12px; color: #475569; white-space: nowrap; }
.mapping-table-wrap { overflow-x: auto; }
.mapping-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.mapping-table th { text-align: left; padding: 10px 16px; background: #f8fafc; color: #64748b; font-weight: 500; border-bottom: 1px solid #e2e8f0; }
.mapping-table td { padding: 10px 16px; border-bottom: 1px solid #f1f5f9; vertical-align: middle; }
.mapping-td-name { font-weight: 500; color: #1e293b; }
.mapping-td-type { color: #64748b; font-family: monospace; font-size: 12px; }
.mapping-confidence { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; }
.mapping-confidence.high { background: #dcfce7; color: #166534; }
.mapping-confidence.medium { background: #fef3c7; color: #92400e; }
.mapping-confidence.low { background: #fee2e2; color: #991b1b; }
.mapping-confidence.none { background: #f1f5f9; color: #94a3b8; }
.mapping-confidence.manual { background: #e0e7ff; color: #3730a3; }
.mapping-empty { display: flex; align-items: center; justify-content: center; height: 100%; color: #94a3b8; font-size: 14px; }
</style>