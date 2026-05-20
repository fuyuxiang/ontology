<template>
  <div class="threebox">
    <!-- 三盒 Tab -->
    <div class="threebox__head">
      <div class="threebox__tabs">
        <button
          v-for="t in tabs"
          :key="t.value"
          class="threebox__tab"
          :class="{ 'threebox__tab--active': activeTab === t.value, [`threebox__tab--${t.value}-active`]: activeTab === t.value }"
          @click="activeTab = t.value"
        >
          {{ t.label }}
        </button>
      </div>
      <span class="threebox__owl-hint">OWL 三盒架构</span>
    </div>

    <!-- T-Box -->
    <section v-if="activeTab === 'tbox'" class="threebox__panel">
      <div class="threebox__notice threebox__notice--tbox">
        <strong>T-box (Terminology Box)</strong> 定义本体 Schema 结构：
        {{ objects.length }} 个对象类型、{{ relations.length }} 条关系类型、
        {{ totalProps }} 个属性定义
      </div>

      <!-- 对象类型表 -->
      <table class="threebox__table">
        <thead>
          <tr>
            <th>对象类型</th>
            <th style="width:80px">层级</th>
            <th style="width:80px">属性数</th>
            <th style="width:80px">关系数</th>
            <th style="width:70px">规则</th>
            <th style="width:90px">场景</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="obj in objects" :key="obj.apiName">
            <tr class="threebox__row" @click="toggleExpand(obj.apiName)">
              <td>
                <div class="threebox__obj-cell">
                  <div class="threebox__obj-icon" :style="{ background: tierColor[obj.tier] + '18', color: tierColor[obj.tier] }">
                    {{ obj.displayName.charAt(0) }}
                  </div>
                  <div>
                    <div class="threebox__obj-name">{{ obj.displayName }}</div>
                    <div class="threebox__obj-en">{{ obj.apiName }}</div>
                  </div>
                </div>
              </td>
              <td><span class="threebox__tier" :style="{ background: tierColor[obj.tier] + '15', color: tierColor[obj.tier] }">T{{ obj.tier }} {{ tierName[obj.tier] }}</span></td>
              <td><span class="threebox__count threebox__count--blue">{{ obj.properties.length }}</span></td>
              <td><span class="threebox__count threebox__count--cyan">{{ relCount[obj.apiName] || 0 }}</span></td>
              <td>
                <span v-if="obj.ruleCount > 0" class="threebox__count threebox__count--orange">{{ obj.ruleCount }}</span>
                <span v-else class="threebox__none">—</span>
              </td>
              <td><code class="threebox__scenario">{{ obj.scenarioCode }}</code></td>
            </tr>
            <tr v-if="expanded === obj.apiName" class="threebox__row-detail">
              <td colspan="6">
                <div class="threebox__props">
                  <div class="threebox__props-title">属性定义 ({{ obj.properties.length }})</div>
                  <table class="threebox__sub-table">
                    <thead>
                      <tr>
                        <th>属性名</th>
                        <th style="width:100px">类型</th>
                        <th style="width:60px">必填</th>
                        <th style="width:200px">物理字段</th>
                        <th>说明</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="p in obj.properties" :key="p.apiName">
                        <td>
                          <strong>{{ p.displayName }}</strong>
                          <code class="threebox__prop-en">{{ p.apiName }}</code>
                        </td>
                        <td><span class="threebox__prop-type">{{ p.dataType }}</span></td>
                        <td><span v-if="p.required" class="threebox__check">✓</span><span v-else class="threebox__none">—</span></td>
                        <td>
                          <code v-if="p.sourceColumn" class="threebox__prop-field">{{ p.sourceColumn || p.physicalName }}</code>
                          <span v-else class="threebox__none">未映射</span>
                        </td>
                        <td class="threebox__prop-desc">{{ p.description || '—' }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>

      <!-- 关系类型表 -->
      <h3 class="threebox__sub-title">关系类型 Link Types ({{ relations.length }})</h3>
      <table class="threebox__table">
        <thead>
          <tr>
            <th>关系名</th>
            <th style="width:140px">源</th>
            <th style="width:140px">目标</th>
            <th style="width:70px">基数</th>
            <th>说明</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in relations" :key="r.apiName">
            <td>
              <strong>{{ r.displayName }}</strong>
              <code class="threebox__prop-en">{{ r.apiName }}</code>
            </td>
            <td><span class="threebox__link-end">{{ r.source }}</span></td>
            <td><span class="threebox__link-end">{{ r.target }}</span></td>
            <td><span class="threebox__count threebox__count--blue">{{ r.cardinality }}</span></td>
            <td class="threebox__prop-desc">{{ r.description || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- A-Box -->
    <section v-else-if="activeTab === 'abox'" class="threebox__panel">
      <div class="threebox__notice threebox__notice--abox">
        <strong>A-box (Assertion Box)</strong> 展示本体实例化状态：
        实例数据待后端集成 POC 数据流后注入
      </div>

      <table class="threebox__table">
        <thead>
          <tr>
            <th>对象类型</th>
            <th style="width:100px">实例数</th>
            <th style="width:100px">水合状态</th>
            <th style="width:180px">属性覆盖率</th>
            <th>数据源</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="obj in objects" :key="obj.apiName">
            <td>
              <div class="threebox__obj-cell">
                <div class="threebox__obj-icon" :style="{ background: tierColor[obj.tier] + '18', color: tierColor[obj.tier] }">
                  {{ obj.displayName.charAt(0) }}
                </div>
                <div>
                  <div class="threebox__obj-name">{{ obj.displayName }}</div>
                  <div class="threebox__obj-en">{{ obj.apiName }}</div>
                </div>
              </div>
            </td>
            <td><strong>{{ (hydration[obj.apiName]?.instanceCount ?? 0).toLocaleString() }}</strong></td>
            <td>
              <span class="threebox__hydration" :class="`threebox__hydration--${hydration[obj.apiName]?.level ?? 'none'}`">
                {{ hydrationLabel[hydration[obj.apiName]?.level ?? 'none'] }}
              </span>
            </td>
            <td>
              <div class="threebox__progress">
                <div
                  class="threebox__progress-bar"
                  :style="{ width: ((hydration[obj.apiName]?.propertyCompleteness.coverage ?? 0) * 100) + '%' }"
                ></div>
              </div>
              <span class="threebox__progress-text">
                {{ Math.round((hydration[obj.apiName]?.propertyCompleteness.coverage ?? 0) * 100) }}%
              </span>
            </td>
            <td><code v-if="hydration[obj.apiName]?.backingSource" class="threebox__prop-field">{{ hydration[obj.apiName]?.backingSource }}</code><span v-else class="threebox__none">—</span></td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- R-Box -->
    <section v-else class="threebox__panel">
      <div class="threebox__notice threebox__notice--rbox">
        <strong>R-box (Rule Box)</strong> 管理本体的业务规则和约束条件：
        {{ rules.length }} 条业务规则
      </div>

      <table class="threebox__table">
        <thead>
          <tr>
            <th style="width:120px">规则 ID</th>
            <th>规则名称</th>
            <th style="width:100px">类别</th>
            <th style="width:80px">优先级</th>
            <th>动作说明</th>
            <th style="width:140px">适用对象</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rules" :key="r.rule_id">
            <td><code class="threebox__prop-field">{{ r.rule_id.slice(0, 8) }}</code></td>
            <td><strong>{{ r.display_name }}</strong></td>
            <td><span class="threebox__count threebox__count--orange">{{ r.category }}</span></td>
            <td><span class="threebox__count threebox__count--blue">{{ r.priority }}</span></td>
            <td class="threebox__prop-desc">{{ r.action.reason }}</td>
            <td>
              <span v-for="o in r.applicable_objects" :key="o" class="threebox__link-end">{{ o }}</span>
              <span v-if="r.applicable_objects.length === 0" class="threebox__none">—</span>
            </td>
          </tr>
          <tr v-if="rules.length === 0">
            <td colspan="6" class="threebox__empty">暂无业务规则</td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { StudioObjectType, StudioLinkType, StudioRule, StudioHydration } from '../../api/studio'

const props = defineProps<{
  objects: StudioObjectType[]
  relations: StudioLinkType[]
  rules: StudioRule[]
  hydration: Record<string, StudioHydration>
}>()

defineEmits<{
  (e: 'select', obj: StudioObjectType): void
}>()

const tabs = [
  { value: 'tbox' as const, label: 'T-box 术语层' },
  { value: 'abox' as const, label: 'A-box 断言层' },
  { value: 'rbox' as const, label: 'R-box 规则层' },
]
const activeTab = ref<'tbox' | 'abox' | 'rbox'>('tbox')
const expanded = ref<string | null>(null)

const tierColor: Record<1 | 2 | 3, string> = { 1: '#2E5BFF', 2: '#00C7B1', 3: '#FF6B35' }
const tierName: Record<1 | 2 | 3, string> = { 1: '核心', 2: '领域', 3: '场景' }
const hydrationLabel: Record<StudioHydration['level'], string> = {
  full: '完全', partial: '部分', mapping: '映射中', none: '未水合',
}

const totalProps = computed(() => props.objects.reduce((acc, o) => acc + o.properties.length, 0))

const relCount = computed(() => {
  const m: Record<string, number> = {}
  for (const o of props.objects) m[o.apiName] = 0
  for (const r of props.relations) {
    if (m[r.source] !== undefined) m[r.source]++
    if (m[r.target] !== undefined) m[r.target]++
  }
  return m
})

function toggleExpand(name: string) {
  expanded.value = expanded.value === name ? null : name
}
</script>

<style scoped>
.threebox {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.threebox__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.threebox__tabs {
  display: inline-flex;
  background: #f1f5f9;
  border-radius: 6px;
  padding: 2px;
  gap: 2px;
}
.threebox__tab {
  padding: 6px 14px;
  font-size: 12px;
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: #475569;
  font-weight: 500;
}
.threebox__tab:hover { background: rgba(255,255,255,0.5); }
.threebox__tab--active { background: #fff; color: #1e293b; font-weight: 600; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
.threebox__owl-hint {
  font-size: 11px;
  color: #94a3b8;
  background: #f1f5f9;
  padding: 4px 10px;
  border-radius: 4px;
}

.threebox__panel { display: flex; flex-direction: column; gap: 14px; }

.threebox__notice {
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.6;
}
.threebox__notice--tbox { background: #eff6ff; border: 1px solid #bfdbfe; color: #1d4ed8; }
.threebox__notice--abox { background: #f0fdf4; border: 1px solid #bbf7d0; color: #15803d; }
.threebox__notice--rbox { background: #fff7ed; border: 1px solid #fed7aa; color: #c2410c; }

.threebox__table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e5e7eb;
  font-size: 12px;
}
.threebox__table th {
  background: #f8fafc;
  text-align: left;
  padding: 10px 12px;
  font-size: 11px;
  font-weight: 600;
  color: #475569;
  border-bottom: 1px solid #e5e7eb;
}
.threebox__table td {
  padding: 10px 12px;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}
.threebox__table tbody tr:last-child td { border-bottom: none; }
.threebox__row { cursor: pointer; transition: background 0.1s; }
.threebox__row:hover { background: #f8fafc; }
.threebox__row-detail { background: #f8fafc; }
.threebox__row-detail td { padding: 12px 16px 16px 16px; }

.threebox__obj-cell { display: flex; align-items: center; gap: 10px; }
.threebox__obj-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}
.threebox__obj-name { font-size: 13px; font-weight: 500; color: #1e293b; }
.threebox__obj-en { font-size: 10px; color: #94a3b8; font-family: monospace; }

.threebox__tier {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}
.threebox__count {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  min-width: 24px;
  text-align: center;
}
.threebox__count--blue { background: #dbeafe; color: #1d4ed8; }
.threebox__count--cyan { background: #cffafe; color: #0e7490; }
.threebox__count--orange { background: #fed7aa; color: #c2410c; }
.threebox__none { color: #cbd5e1; font-size: 11px; }
.threebox__check { color: #22c55e; font-size: 14px; font-weight: 700; }
.threebox__scenario {
  font-size: 10px;
  background: #f1f5f9;
  color: #475569;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: monospace;
}

.threebox__sub-title {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  margin: 8px 0 0;
}
.threebox__props { padding: 0 4px; }
.threebox__props-title {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 8px;
}
.threebox__sub-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  background: #fff;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
  font-size: 11px;
}
.threebox__sub-table th {
  background: #f1f5f9;
  text-align: left;
  padding: 6px 10px;
  font-size: 10px;
  font-weight: 600;
  color: #64748b;
}
.threebox__sub-table td {
  padding: 6px 10px;
  border-top: 1px solid #f1f5f9;
}
.threebox__prop-en {
  font-size: 10px;
  background: #f1f5f9;
  color: #64748b;
  padding: 1px 5px;
  border-radius: 3px;
  font-family: monospace;
  margin-left: 6px;
}
.threebox__prop-type {
  font-size: 10px;
  background: #f1f5f9;
  color: #475569;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 500;
}
.threebox__prop-field {
  font-size: 10px;
  font-family: monospace;
  background: #f8fafc;
  color: #475569;
  padding: 1px 5px;
  border-radius: 3px;
}
.threebox__prop-desc {
  font-size: 11px;
  color: #64748b;
}
.threebox__link-end {
  display: inline-block;
  font-size: 10px;
  background: #f1f5f9;
  color: #1e293b;
  padding: 2px 8px;
  border-radius: 4px;
  font-family: monospace;
  margin-right: 4px;
}

.threebox__hydration {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid transparent;
}
.threebox__hydration--full { background: #f0fdf4; color: #16a34a; border-color: #bbf7d0; }
.threebox__hydration--partial { background: #eff6ff; color: #2563eb; border-color: #bfdbfe; }
.threebox__hydration--mapping { background: #fef3c7; color: #b45309; border-color: #fde68a; }
.threebox__hydration--none {
  background: transparent;
  color: #94a3b8;
  border-color: #cbd5e1;
  border-style: dashed;
}

.threebox__progress {
  display: inline-block;
  width: 120px;
  height: 6px;
  background: #f1f5f9;
  border-radius: 3px;
  overflow: hidden;
  vertical-align: middle;
}
.threebox__progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #06b6d4);
  border-radius: 3px;
  transition: width 0.3s;
}
.threebox__progress-text {
  font-size: 11px;
  color: #64748b;
  margin-left: 8px;
}

.threebox__empty {
  text-align: center;
  padding: 32px;
  color: #94a3b8;
  font-size: 12px;
}
</style>
