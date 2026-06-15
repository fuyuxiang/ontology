<template>
  <div class="manual-root" tabindex="0" @keydown="onShortcut">
    <header class="manual-topbar">
      <div class="manual-topbar-title">
        <span>手工建模</span>
        <small>定义对象、属性、关系</small>
      </div>
      <div class="manual-topbar-stats">
        <span>{{ objects.length }} 对象</span>
        <span>{{ relations.length }} 关系</span>
        <span>{{ totalProps }} 属性</span>
      </div>
      <div class="manual-topbar-actions">
        <button class="btn btn-ghost" @click="undo" :disabled="!canUndo" title="Cmd/Ctrl+Z">↶ 撤销</button>
        <button class="btn btn-ghost" @click="redo" :disabled="!canRedo" title="Cmd/Ctrl+Y">↷ 重做</button>
        <button class="btn btn-ghost" @click="previewOpen = true" :disabled="!objects.length">👁 在图谱中预览</button>
        <button class="btn btn-primary" :disabled="!canSubmit" @click="confirmAll">提交进入走测 →</button>
      </div>
    </header>

    <div class="manual-body">
      <!-- 左：对象列表 -->
      <aside class="manual-col manual-col-left">
        <div class="col-head">
          <span>对象 · {{ objects.length }}</span>
          <div class="col-head-btns">
            <button class="iconbtn" title="批量粘贴 CSV" @click="csvOpen = true">⎘</button>
            <button class="iconbtn iconbtn-primary" title="新建对象 (N)" @click="addObject()">＋</button>
          </div>
        </div>
        <div class="obj-list">
          <div
            v-for="o in objects"
            :key="o.id"
            :class="['obj-item', { active: selectedId === o.id }]"
            @click="selectedId = o.id"
          >
            <span class="obj-icon" :style="{ background: tierBg(o.tier), color: tierColor(o.tier) }">{{ o.icon || '🔷' }}</span>
            <div class="obj-meta">
              <div class="obj-name">{{ o.displayName || '(未命名)' }}</div>
              <div class="obj-en">{{ o.name }} · {{ o.properties.length }} 属性</div>
            </div>
            <button class="iconbtn iconbtn-danger" title="删除 (Del)" @click.stop="removeObject(o.id)">×</button>
          </div>
          <div v-if="!objects.length" class="empty-tip">还没有对象 — 点 ＋ 或按 N 创建</div>
        </div>
      </aside>

      <!-- 中：当前对象详情 -->
      <main class="manual-col manual-col-mid">
        <div v-if="selected" class="detail-card">
          <div class="detail-section">
            <div class="section-title">基本信息</div>
            <div class="form-grid">
              <label>名称（英文，PascalCase）<span class="req">*</span>
                <input v-model="selected.name" :class="{ err: nameErr }" @blur="syncBlur" />
              </label>
              <label>中文名 <span class="req">*</span>
                <input v-model="selected.displayName" @blur="syncBlur" />
              </label>
              <label class="form-grid-full">描述
                <textarea v-model="selected.description" rows="2" @blur="syncBlur"></textarea>
              </label>
            </div>
            <div v-if="nameErr" class="field-err">{{ nameErr }}</div>
          </div>

          <div class="detail-section">
            <div class="section-head">
              <div class="section-title">属性 ({{ selected.properties.length }})</div>
              <button class="btn btn-mini" @click="addProp">＋ 添加属性</button>
            </div>
            <div class="prop-table">
              <div class="prop-row prop-head">
                <div>中文名</div><div>英文名</div><div>类型</div><div></div>
              </div>
              <div v-for="p in selected.properties" :key="p.id" class="prop-row">
                <input v-model="p.displayName" placeholder="例如：客户姓名" @blur="syncBlur" />
                <input v-model="p.name" placeholder="snake_case" @blur="syncBlur" />
                <select v-model="p.type" @change="syncBlur">
                  <option value="string">string</option>
                  <option value="number">number</option>
                  <option value="date">date</option>
                  <option value="boolean">boolean</option>
                  <option value="enum">enum</option>
                </select>
                <button class="iconbtn iconbtn-danger" @click="removeProp(p.id)">×</button>
              </div>
              <div v-if="!selected.properties.length" class="empty-tip">至少需要 1 个属性</div>
            </div>
          </div>

        </div>
        <div v-else class="detail-empty">
          <div>左侧选一个对象进行编辑</div>
          <button class="btn btn-primary" @click="addObject()">＋ 新建对象</button>
        </div>
      </main>

      <!-- 右：关系矩阵 -->
      <aside class="manual-col manual-col-right">
        <div class="col-head">
          <span>关系 · {{ relations.length }}</span>
          <button class="iconbtn iconbtn-primary" title="新建关系 (R)" @click="openRelForm">＋</button>
        </div>
        <div v-if="relForm.open" class="rel-form">
          <label>源对象
            <select v-model="relForm.from">
              <option value="">请选择</option>
              <option v-for="o in objects" :key="o.id" :value="o.id">{{ o.displayName }}（{{ o.name }}）</option>
            </select>
          </label>
          <label>目标对象
            <select v-model="relForm.to">
              <option value="">请选择</option>
              <option v-for="o in objects" :key="o.id" :value="o.id">{{ o.displayName }}（{{ o.name }}）</option>
            </select>
          </label>
          <label>正向关系名
            <input v-model="relForm.label" placeholder="例如：下单、持有、负责" />
          </label>
          <label>反向关系名
            <input v-model="relForm.inverseLabel" placeholder="例如：被下单、归属于、被负责" />
          </label>
          <label>基数
            <select v-model="relForm.cardinality">
              <option value="1:1">一对一</option>
              <option value="1:N">一对多</option>
              <option value="N:N">多对多</option>
            </select>
          </label>
          <label>描述（可选）
            <input v-model="relForm.description" placeholder="补充说明这条关系的业务含义" />
          </label>
          <div class="rel-form-actions">
            <button class="btn btn-ghost" @click="relForm.open = false">取消</button>
            <button class="btn btn-primary" :disabled="!canSaveRel" @click="saveRelation">保存</button>
          </div>
        </div>
        <div class="rel-list">
          <div v-for="r in relations" :key="r.id" class="rel-item">
            <div class="rel-main">
              <span class="rel-from">{{ nameOf(r.source) }}</span>
              <span class="rel-arrow">→</span>
              <span class="rel-to">{{ nameOf(r.target) }}</span>
              <span class="rel-card">{{ r.cardinality }}</span>
              <button class="iconbtn iconbtn-danger" @click="removeRelation(r.id)">×</button>
            </div>
            <div class="rel-labels">
              <span class="rel-label">{{ r.displayName }}</span>
              <span v-if="r.inverseDisplayName" class="rel-label rel-inverse">← {{ r.inverseDisplayName }}</span>
            </div>
          </div>
          <div v-if="!relations.length" class="empty-tip">还没有关系 — 点 ＋ 或按 R 创建</div>
        </div>
      </aside>
    </div>

    <!-- 批量 CSV 弹窗 -->
    <div v-if="csvOpen" class="modal-mask" @click.self="csvOpen = false">
      <div class="modal-card">
        <div class="modal-head">批量粘贴 CSV — name,displayName,tier,description</div>
        <textarea v-model="csvText" rows="10" placeholder="Customer,客户,1,客户主信息&#10;Order,订单,2,客户下的订单"></textarea>
        <div class="modal-actions">
          <button class="btn btn-ghost" @click="csvOpen = false">取消</button>
          <button class="btn btn-primary" @click="commitCsv">导入</button>
        </div>
      </div>
    </div>

    <!-- 只读图谱预览 modal -->
    <div v-if="previewOpen" class="modal-mask" @click.self="previewOpen = false">
      <div class="modal-card modal-card-large">
        <div class="modal-head">
          图谱预览（只读）
          <button class="iconbtn" @click="previewOpen = false">×</button>
        </div>
        <div class="preview-body">
          <SemanticCanvas
            :objects="objects"
            :relations="relations"
            :phase="'graph_done'"
            :editable="false"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useBuilderStore } from '../../../store/builder'
import type {
  BuilderSession,
  OntologyObjectDraft,
  OntologyRelationDraft,
} from '../../../types/builder'
import SemanticCanvas from './graph/SemanticCanvas.vue'

const props = defineProps<{ session: BuilderSession }>()
const emit = defineEmits<{ (e: 'next'): void }>()
const store = useBuilderStore()

const objects = ref<OntologyObjectDraft[]>([...props.session.ontologyObjects])
const relations = ref<OntologyRelationDraft[]>([...props.session.ontologyRelations])
const selectedId = ref<string | null>(objects.value[0]?.id || null)
const selected = computed(() => objects.value.find(o => o.id === selectedId.value))

const csvOpen = ref(false)
const csvText = ref('')
const previewOpen = ref(false)

const relForm = reactive({
  open: false,
  from: '',
  to: '',
  label: '',
  inverseLabel: '',
  description: '',
  cardinality: '1:N' as '1:1' | '1:N' | 'N:N',
  relationType: 'ObjectProperty' as OntologyRelationDraft['relationType'],
  semanticType: 'association' as OntologyRelationDraft['semanticType'],
})

const totalProps = computed(() => objects.value.reduce((s, o) => s + o.properties.length, 0))
const canSaveRel = computed(() =>
  relForm.from && relForm.to && relForm.from !== relForm.to && relForm.label.trim(),
)

const nameErr = computed(() => {
  if (!selected.value) return ''
  const v = selected.value.name.trim()
  if (!v) return '英文名不能为空'
  if (!/^[A-Z][A-Za-z0-9]*$/.test(v)) return '英文名需 PascalCase（首字母大写、仅字母数字）'
  if (objects.value.some(o => o.id !== selected.value!.id && o.name === v)) return '英文名重复'
  return ''
})

const canSubmit = computed(() => {
  if (!objects.value.length) return false
  for (const o of objects.value) {
    if (!o.name || !o.displayName) return false
    if (!o.properties.length) return false
  }
  return true
})

// session_id 透传给跳转链接，便于回流

function tierBg(t: 1 | 2 | 3) { return t === 1 ? 'rgba(46,91,255,0.12)' : t === 2 ? 'rgba(0,199,177,0.12)' : 'rgba(255,107,53,0.12)' }
function tierColor(t: 1 | 2 | 3) { return t === 1 ? '#2E5BFF' : t === 2 ? '#00C7B1' : '#FF6B35' }
function nameOf(id: string) { return objects.value.find(o => o.id === id)?.displayName || id }

// ── undo/redo ──
const history: string[] = [JSON.stringify({ objects: objects.value, relations: relations.value })]
const future: string[] = []
const canUndo = computed(() => history.length > 1)
const canRedo = computed(() => future.length > 0)
let suppressSnapshot = false
function snapshot() {
  if (suppressSnapshot) return
  history.push(JSON.stringify({ objects: objects.value, relations: relations.value }))
  if (history.length > 50) history.shift()
  future.length = 0
}
function restore(s: string) {
  const d = JSON.parse(s)
  suppressSnapshot = true
  objects.value = d.objects
  relations.value = d.relations
  suppressSnapshot = false
}
function undo() {
  if (history.length <= 1) return
  const cur = history.pop()!
  future.push(cur)
  restore(history[history.length - 1])
  syncStore(true)
}
function redo() {
  const next = future.pop()
  if (!next) return
  history.push(next)
  restore(next)
  syncStore(true)
}

function syncStore(skipSnapshot = false) {
  if (!skipSnapshot) snapshot()
  store.patchActive({
    ontologyObjects: [...objects.value],
    ontologyRelations: [...relations.value],
  })
}
function syncBlur() { syncStore() }

function uid(p: string) { return `${p}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}` }

function addObject(seed?: Partial<OntologyObjectDraft>) {
  const o: OntologyObjectDraft = {
    id: uid('obj'),
    name: seed?.name || `NewObject${objects.value.length + 1}`,
    displayName: seed?.displayName || '新对象',
    tier: (seed?.tier ?? 3) as 1 | 2 | 3,
    namespace: seed?.namespace,
    description: seed?.description || '',
    primaryKey: 'id',
    icon: seed?.icon || '🔷',
    instanceCount: 0,
    properties: seed?.properties || [{ id: uid('prop'), name: 'name', displayName: '名称', type: 'string', required: true }],
    derivedProperties: [], rules: [], actions: [], approved: false,
  }
  objects.value.push(o)
  selectedId.value = o.id
  syncStore()
}

function removeObject(id: string) {
  objects.value = objects.value.filter(o => o.id !== id)
  relations.value = relations.value.filter(r => r.source !== id && r.target !== id)
  if (selectedId.value === id) selectedId.value = objects.value[0]?.id || null
  syncStore()
}

function addProp() {
  if (!selected.value) return
  selected.value.properties.push({ id: uid('prop'), name: 'newField', displayName: '', type: 'string', required: false })
  syncStore()
}
function removeProp(id: string) {
  if (!selected.value) return
  selected.value.properties = selected.value.properties.filter(p => p.id !== id)
  syncStore()
}

function openRelForm() {
  if (objects.value.length < 2) { message.warning('至少需要 2 个对象才能建关系'); return }
  relForm.open = true
}
function saveRelation() {
  if (!canSaveRel.value) return
  relations.value.push({
    id: uid('rel'),
    name: relForm.label.trim().replace(/\s+/g, '_'),
    displayName: relForm.label.trim(),
    inverseDisplayName: relForm.inverseLabel.trim(),
    source: relForm.from,
    target: relForm.to,
    cardinality: relForm.cardinality,
    description: relForm.description.trim() || relForm.label.trim(),
    relationType: relForm.relationType,
    semanticType: relForm.semanticType,
  })
  Object.assign(relForm, { open: false, from: '', to: '', label: '', inverseLabel: '', description: '', cardinality: '1:N', relationType: 'ObjectProperty', semanticType: 'association' })
  syncStore()
}
function removeRelation(id: string) {
  relations.value = relations.value.filter(r => r.id !== id)
  syncStore()
}

function commitCsv() {
  const lines = csvText.value.split('\n').map(l => l.trim()).filter(Boolean)
  if (!lines.length) { csvOpen.value = false; return }
  let added = 0
  for (const line of lines) {
    const cols = line.split(',').map(c => c.trim())
    const [name, displayName, tier, description] = [cols[0], cols[1] || cols[0], cols[2] || '3', cols[3] || '']
    if (!name) continue
    const t = Math.max(1, Math.min(3, parseInt(tier) || 2)) as 1 | 2 | 3
    addObject({ name, displayName, tier: t, description })
    added++
  }
  csvOpen.value = false
  csvText.value = ''
  message.success(`已批量导入 ${added} 个对象`)
}

function confirmAll() {
  if (!canSubmit.value) {
    message.warning('每个对象至少需要 1 个属性')
    return
  }
  const connectedIds = new Set(relations.value.flatMap(r => [r.source, r.target]))
  const isolated = objects.value.filter(o => !connectedIds.has(o.id))
  if (isolated.length && objects.value.length > 1) {
    message.warning(`以下对象没有任何关系连接：${isolated.map(o => o.displayName).join('、')}`)
  }
  store.patchActive({
    ontologyObjects: [...objects.value],
    ontologyRelations: [...relations.value],
    status: 'pending_review',
  })
  emit('next')
}

function onShortcut(e: KeyboardEvent) {
  const tag = (e.target as HTMLElement)?.tagName?.toLowerCase()
  if (tag === 'input' || tag === 'textarea' || tag === 'select') {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 's') { e.preventDefault(); syncStore(); message.success('已保存草稿') }
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'z') { e.preventDefault(); undo() }
    if ((e.metaKey || e.ctrlKey) && (e.key.toLowerCase() === 'y' || (e.shiftKey && e.key.toLowerCase() === 'z'))) { e.preventDefault(); redo() }
    return
  }
  if (e.key === 'n' || e.key === 'N') { e.preventDefault(); addObject() }
  else if (e.key === 'r' || e.key === 'R') { e.preventDefault(); openRelForm() }
  else if ((e.key === 'Delete' || e.key === 'Backspace') && selectedId.value) { e.preventDefault(); removeObject(selectedId.value) }
  else if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 's') { e.preventDefault(); syncStore(); message.success('已保存草稿') }
  else if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'z') { e.preventDefault(); undo() }
  else if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'y') { e.preventDefault(); redo() }
}

onMounted(() => {
  // 焦点放到根容器以便快捷键
  const root = document.querySelector<HTMLElement>('.manual-root')
  root?.focus()
})

// session 切换：重新初始化
watch(() => props.session.sessionId, () => {
  objects.value = [...props.session.ontologyObjects]
  relations.value = [...props.session.ontologyRelations]
  selectedId.value = objects.value[0]?.id || null
})
</script>

<style scoped>
.manual-root {
  height: calc(100vh - 64px - 56px - 76px);
  display: flex; flex-direction: column;
  background: #f8fafc; outline: none;
}
.manual-topbar {
  display: flex; align-items: center; gap: 18px;
  padding: 12px 20px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
}
.manual-topbar-title { display: flex; flex-direction: column; line-height: 1.3; }
.manual-topbar-title span { font-size: 15px; font-weight: 600; color: #0f172a; }
.manual-topbar-title small { font-size: 11px; color: #94a3b8; }
.manual-topbar-stats { display: flex; gap: 12px; font-size: 12px; color: #64748b; flex: 1; margin-left: 16px; }
.manual-topbar-stats span { padding: 2px 8px; background: #f1f5f9; border-radius: 999px; }
.manual-topbar-actions { display: flex; gap: 8px; }
.btn { padding: 6px 14px; border-radius: 8px; font-size: 12px; cursor: pointer; border: 1px solid transparent; }
.btn-ghost { background: #fff; color: #475569; border-color: #e2e8f0; }
.btn-ghost:hover:not(:disabled) { border-color: #4f46e5; color: #4f46e5; }
.btn-ghost:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-primary { background: linear-gradient(135deg, #4f46e5, #7c3aed); color: #fff; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-mini { padding: 3px 10px; border-radius: 6px; font-size: 11px; background: transparent; color: #4f46e5; border: 1px solid #e0e7ff; cursor: pointer; }
.btn-mini:hover { background: #eef2ff; }

.manual-body {
  flex: 1; overflow: hidden;
  display: grid;
  grid-template-columns: 280px 1fr 360px;
  gap: 12px;
  padding: 12px;
}
.manual-col { background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; display: flex; flex-direction: column; }
.col-head { display: flex; align-items: center; padding: 12px 14px; border-bottom: 1px solid #f1f5f9; font-size: 13px; font-weight: 600; color: #0f172a; }
.col-head > span { flex: 1; }
.col-head-btns { display: flex; gap: 4px; }
.iconbtn {
  width: 24px; height: 24px; border-radius: 6px; border: 1px solid #e2e8f0;
  background: #fff; color: #64748b; cursor: pointer; font-size: 14px; line-height: 1;
}
.iconbtn:hover { color: #4f46e5; border-color: #4f46e5; }
.iconbtn-primary { background: #4f46e5; color: #fff; border-color: #4f46e5; }
.iconbtn-primary:hover { background: #4338ca; color: #fff; }
.iconbtn-danger { color: #ef4444; border-color: transparent; background: transparent; }
.iconbtn-danger:hover { background: #fee2e2; border-color: transparent; color: #ef4444; }

.obj-list { flex: 1; overflow-y: auto; padding: 6px; }
.obj-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px; border-radius: 8px; cursor: pointer; margin-bottom: 4px;
}
.obj-item:hover { background: #f8fafc; }
.obj-item.active { background: rgba(79,70,229,0.08); }
.obj-icon { width: 28px; height: 28px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0; }
.obj-meta { flex: 1; min-width: 0; line-height: 1.3; }
.obj-name { font-size: 12px; font-weight: 600; color: #0f172a; }
.obj-en { font-size: 10px; color: #94a3b8; }

.empty-tip { padding: 16px; text-align: center; color: #94a3b8; font-size: 12px; }

.manual-col-mid { padding: 0; overflow-y: auto; }
.detail-card { padding: 16px 20px; }
.detail-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; height: 100%; color: #94a3b8; font-size: 13px; padding: 40px; }
.detail-section { margin-bottom: 18px; }
.section-head { display: flex; align-items: center; margin-bottom: 8px; }
.section-head .section-title { flex: 1; }
.section-title { font-size: 12px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 12px; }
.form-grid label { display: flex; flex-direction: column; gap: 4px; font-size: 11px; color: #64748b; }
.form-grid-full { grid-column: 1 / -1; }
.form-grid input, .form-grid select, .form-grid textarea, .prop-row input, .prop-row select, .rel-form input, .rel-form select, .modal-card textarea {
  padding: 6px 10px; font-size: 13px; border: 1px solid #e2e8f0; border-radius: 6px; background: #fff; color: #0f172a; outline: none;
}
.form-grid input:focus, .form-grid select:focus, .form-grid textarea:focus, .prop-row input:focus, .prop-row select:focus, .rel-form input:focus, .rel-form select:focus { border-color: #4f46e5; box-shadow: 0 0 0 2px rgba(79,70,229,.12); }
.form-grid input.err { border-color: #ef4444; }
.field-err { font-size: 11px; color: #ef4444; margin-top: 4px; }
.req { color: #ef4444; }

.prop-table { display: flex; flex-direction: column; gap: 4px; }
.prop-row {
  display: grid; grid-template-columns: 1fr 1fr 120px 28px;
  gap: 6px; align-items: center;
}
.prop-row.prop-head { font-size: 10px; color: #94a3b8; text-transform: uppercase; padding: 0 4px; }
.prop-row.prop-head > div { padding: 0 4px; }

.link { font-size: 11px; color: #4f46e5; text-decoration: none; }
.link:hover { text-decoration: underline; }

.rel-form {
  padding: 10px 14px; background: #f8fafc; border-bottom: 1px solid #e2e8f0;
  display: flex; flex-direction: column; gap: 8px;
}
.rel-form label { display: flex; flex-direction: column; gap: 3px; font-size: 11px; color: #64748b; }
.rel-form-actions { display: flex; gap: 8px; justify-content: flex-end; }

.rel-list { flex: 1; overflow-y: auto; padding: 6px; }
.rel-item {
  display: flex; flex-direction: column; gap: 4px;
  padding: 8px 10px; border-radius: 8px;
  font-size: 11px; margin-bottom: 6px; background: #f8fafc;
}
.rel-main {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
}
.rel-labels {
  display: flex; gap: 8px; font-size: 10px; color: #64748b; padding-left: 2px;
}
.rel-from, .rel-to { color: #1e293b; font-weight: 500; }
.rel-arrow { color: #94a3b8; text-align: center; }
.rel-label { color: #4f46e5; font-family: monospace; }
.rel-card { color: #94a3b8; font-family: monospace; font-size: 10px; }

.modal-mask {
  position: fixed; inset: 0; background: rgba(15,23,42,0.5);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal-card { background: #fff; border-radius: 14px; padding: 18px 20px; width: 480px; max-width: 90vw; }
.modal-card-large { width: 1100px; max-width: 95vw; height: 80vh; display: flex; flex-direction: column; }
.modal-head { font-size: 14px; font-weight: 600; color: #0f172a; margin-bottom: 12px; display: flex; align-items: center; }
.modal-head > .iconbtn { margin-left: auto; }
.modal-card textarea { width: 100%; resize: vertical; font-family: monospace; font-size: 12px; }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 12px; }
.preview-body { flex: 1; min-height: 0; display: flex; flex-direction: column; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; }
</style>
