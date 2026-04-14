<template>
  <ModalDialog :visible="visible" title="新建本体对象" width="680px" @close="$emit('close')">
    <!-- 模式切换 -->
    <div class="mode-tabs">
      <button class="mode-tab" :class="{ 'mode-tab--active': mode === 'manual' }" @click="mode = 'manual'">手动创建</button>
      <button class="mode-tab" :class="{ 'mode-tab--active': mode === 'import' }" @click="mode = 'import'">从数据源导入</button>
    </div>

    <!-- 手动创建 -->
    <form v-if="mode === 'manual'" @submit.prevent="handleSubmit" class="entity-form">
      <div class="form-row">
        <label class="form-label">对象名称 (英文)</label>
        <input v-model="form.name" class="form-input" placeholder="如 Customer, FTTRSubscription" required />
      </div>
      <div class="form-row">
        <label class="form-label">中文名称</label>
        <input v-model="form.name_cn" class="form-input" placeholder="如 客户, FTTR订阅" required />
      </div>
      <div class="form-row">
        <label class="form-label">Tier 层级</label>
        <div class="form-radio-group">
          <label v-for="t in [1,2,3]" :key="t" class="form-radio" :class="{ 'form-radio--active': form.tier === t }">
            <input type="radio" :value="t" v-model="form.tier" />
            <span class="tier-dot" :style="{ background: `var(--tier${t}-primary)` }"></span>
            Tier {{ t }} {{ tierNames[t] }}
          </label>
        </div>
      </div>
      <div class="form-row">
        <label class="form-label">描述</label>
        <textarea v-model="form.description" class="form-input form-textarea" placeholder="对象描述..." rows="2" />
      </div>
      <div class="form-section">
        <div class="form-section-header">
          <span class="form-label">属性列表</span>
          <button type="button" class="btn-sm" @click="addAttr">+ 添加属性</button>
        </div>
        <div v-for="(attr, i) in form.attributes" :key="i" class="attr-row">
          <input v-model="attr.name" class="form-input form-input--sm" placeholder="属性名" />
          <select v-model="attr.type" class="form-input form-input--sm">
            <option v-for="t in attrTypes" :key="t" :value="t">{{ t }}</option>
          </select>
          <input v-model="attr.description" class="form-input form-input--sm" placeholder="描述" style="flex:2" />
          <label class="form-checkbox"><input type="checkbox" v-model="attr.required" /> 必填</label>
          <button type="button" class="btn-icon" @click="form.attributes.splice(i, 1)">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </button>
        </div>
      </div>
    </form>

    <!-- 从数据源导入 -->
    <div v-else class="entity-form">
      <!-- Step 1: 选数据源 -->
      <div class="form-row">
        <label class="form-label">选择数据源</label>
        <select v-model="importForm.datasource_id" class="form-input" @change="onDsChange">
          <option value="">请选择数据源...</option>
          <option v-for="ds in datasources" :key="ds.id" :value="ds.id">{{ ds.name }} ({{ ds.type }} · {{ ds.host }})</option>
        </select>
      </div>

      <!-- Step 2: 选表 -->
      <div class="form-row" v-if="importForm.datasource_id">
        <label class="form-label">选择表 <span v-if="loadingTables" class="text-caption">(加载中...)</span></label>
        <select v-model="importForm.table_name" class="form-input" @change="onTableChange" :disabled="loadingTables">
          <option value="">请选择表...</option>
          <option v-for="t in tables" :key="t" :value="t">{{ t }}</option>
        </select>
      </div>

      <!-- Step 3: 预览列 -->
      <div v-if="columns.length > 0" class="form-section">
        <div class="form-section-header">
          <span class="form-label">表结构预览 ({{ columns.length }} 列)</span>
        </div>
        <div class="import-columns">
          <div class="import-col-header">
            <span>列名</span><span>DB类型</span><span>本体类型</span><span>可空</span><span>主键</span>
          </div>
          <div v-for="col in columns" :key="col.name" class="import-col-row" :class="{ 'import-col-row--pk': col.is_pk }">
            <span class="text-code">{{ col.name }}</span>
            <span class="text-caption">{{ col.type }}</span>
            <span class="import-col-mapped">{{ mapType(col.type) }}</span>
            <span>{{ col.nullable ? '✓' : '—' }}</span>
            <span>{{ col.is_pk ? '🔑' : '' }}</span>
          </div>
        </div>
      </div>

      <!-- Step 4: 实体信息 -->
      <div v-if="importForm.table_name" class="import-entity-info">
        <div class="form-row">
          <label class="form-label">中文名称</label>
          <input v-model="importForm.name_cn" class="form-input" placeholder="如 客户表, 订单表" required />
        </div>
        <div class="form-row">
          <label class="form-label">Tier 层级</label>
          <div class="form-radio-group">
            <label v-for="t in [1,2,3]" :key="t" class="form-radio" :class="{ 'form-radio--active': importForm.tier === t }">
              <input type="radio" :value="t" v-model="importForm.tier" />
              <span class="tier-dot" :style="{ background: `var(--tier${t}-primary)` }"></span>
              Tier {{ t }} {{ tierNames[t] }}
            </label>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <button class="btn-secondary" @click="$emit('close')">取消</button>
      <button v-if="mode === 'manual'" class="btn-primary" @click="handleSubmit" :disabled="submitting">
        {{ submitting ? '创建中...' : '创建对象' }}
      </button>
      <button v-else class="btn-primary" @click="handleImport" :disabled="submitting || !importForm.table_name">
        {{ submitting ? '导入中...' : '导入为本体对象' }}
      </button>
    </template>
  </ModalDialog>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import ModalDialog from './ModalDialog.vue'
import { entityApi } from '../../api/ontology'
import { listDataSources, getTableList, getTableSchema } from '../../api/datasource'
import { useToast } from '../../composables/useToast'

defineProps<{ visible: boolean }>()
const emit = defineEmits<{ close: []; created: [] }>()
const toast = useToast()

const mode = ref<'manual' | 'import'>('manual')
const tierNames: Record<number, string> = { 1: '核心', 2: '领域', 3: '场景' }
const attrTypes = ['string', 'number', 'boolean', 'date', 'ref', 'computed', 'enum', 'json']
const submitting = ref(false)

// ── 手动创建 ──
const form = reactive({
  name: '', name_cn: '', tier: 1, description: '',
  attributes: [] as { name: string; type: string; description: string; required: boolean }[],
})

function addAttr() {
  form.attributes.push({ name: '', type: 'string', description: '', required: false })
}

async function handleSubmit() {
  if (!form.name || !form.name_cn) return
  submitting.value = true
  try {
    await entityApi.create({ name: form.name, name_cn: form.name_cn, tier: form.tier, description: form.description, attributes: form.attributes.filter(a => a.name) } as never)
    form.name = ''; form.name_cn = ''; form.tier = 1; form.description = ''; form.attributes = []
    toast.success('对象创建成功'); emit('created'); emit('close')
  } catch (e) { toast.error(`创建失败: ${(e as Error).message}`) }
  finally { submitting.value = false }
}

// ── 数据源导入 ──
const datasources = ref<{ id: string; name: string; type: string; host: string }[]>([])
const tables = ref<string[]>([])
const columns = ref<{ name: string; type: string; nullable: boolean; is_pk: boolean; comment: string }[]>([])
const loadingTables = ref(false)

const importForm = reactive({ datasource_id: '', table_name: '', name_cn: '', tier: 3 as number })

const typeMap: Record<string, string> = {
  varchar: 'string', char: 'string', text: 'string', longtext: 'string', nvarchar: 'string',
  int: 'number', integer: 'number', bigint: 'number', smallint: 'number', float: 'number',
  double: 'number', decimal: 'number', numeric: 'number',
  boolean: 'boolean', bool: 'boolean', bit: 'boolean',
  date: 'date', datetime: 'date', timestamp: 'date',
  json: 'json', jsonb: 'json',
}
function mapType(dbType: string) { return typeMap[dbType.toLowerCase().split('(')[0]] || 'string' }

onMounted(async () => {
  try { datasources.value = await listDataSources() } catch { /* ignore */ }
})

async function onDsChange() {
  importForm.table_name = ''; tables.value = []; columns.value = []
  if (!importForm.datasource_id) return
  loadingTables.value = true
  try {
    const res = await getTableList(importForm.datasource_id)
    tables.value = res.tables
  } catch { toast.error('获取表列表失败') }
  finally { loadingTables.value = false }
}

async function onTableChange() {
  columns.value = []
  if (!importForm.table_name) return
  try {
    const res = await getTableSchema(importForm.datasource_id, importForm.table_name)
    columns.value = res.columns
  } catch { toast.error('获取表结构失败') }
}

async function handleImport() {
  if (!importForm.datasource_id || !importForm.table_name || !importForm.name_cn) return
  submitting.value = true
  try {
    await entityApi.createFromDatasource({
      datasource_id: importForm.datasource_id,
      table_name: importForm.table_name,
      name_cn: importForm.name_cn,
      tier: importForm.tier,
    })
    toast.success('从数据源导入成功')
    importForm.datasource_id = ''; importForm.table_name = ''; importForm.name_cn = ''
    tables.value = []; columns.value = []
    emit('created'); emit('close')
  } catch (e) { toast.error(`导入失败: ${(e as Error).message}`) }
  finally { submitting.value = false }
}
</script>

<style scoped>
/* 模式切换 */
.mode-tabs { display: flex; gap: 4px; margin-bottom: 16px; padding: 3px; background: var(--neutral-100); border-radius: 8px; }
.mode-tab {
  flex: 1; padding: 7px 0; border: none; border-radius: 6px; font-size: 13px; font-weight: 500;
  background: transparent; color: var(--neutral-500); cursor: pointer; transition: all 0.15s;
}
.mode-tab--active { background: #fff; color: var(--semantic-600); box-shadow: 0 1px 3px rgba(0,0,0,0.08); }

.entity-form { display: flex; flex-direction: column; gap: 14px; }
.form-row { display: flex; flex-direction: column; gap: 4px; }
.form-label { font-size: 12px; font-weight: 500; color: var(--neutral-600); }
.form-input {
  padding: 8px 12px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md);
  font-size: 13px; color: var(--neutral-800); background: var(--neutral-0); outline: none;
}
.form-input:focus { border-color: var(--semantic-500); }
.form-input--sm { padding: 6px 8px; font-size: 12px; }
.form-textarea { resize: vertical; font-family: inherit; }
.form-radio-group { display: flex; gap: 12px; }
.form-radio {
  display: flex; align-items: center; gap: 6px; padding: 6px 12px;
  border: 1px solid var(--neutral-200); border-radius: var(--radius-md);
  font-size: 12px; cursor: pointer; transition: all var(--transition-fast);
}
.form-radio input { display: none; }
.form-radio--active { border-color: var(--semantic-500); background: var(--semantic-50); }
.tier-dot { width: 8px; height: 8px; border-radius: 50%; }
.form-section { margin-top: 4px; }
.form-section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.attr-row { display: flex; gap: 6px; align-items: center; margin-bottom: 6px; }
.attr-row .form-input { flex: 1; }
.form-checkbox { display: flex; align-items: center; gap: 4px; font-size: 11px; color: var(--neutral-600); white-space: nowrap; }
.btn-sm { padding: 4px 10px; border-radius: var(--radius-md); border: 1px solid var(--semantic-400); background: transparent; color: var(--semantic-600); font-size: 11px; cursor: pointer; }
.btn-sm:hover { background: var(--semantic-50); }
.btn-icon { width: 24px; height: 24px; border: none; background: transparent; color: var(--neutral-400); cursor: pointer; display: flex; align-items: center; justify-content: center; }
.btn-icon:hover { color: var(--status-error); }
.btn-primary { padding: 8px 20px; border-radius: var(--radius-md); border: none; background: var(--semantic-600); color: #fff; font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-primary:hover { background: var(--semantic-700); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-secondary { padding: 8px 16px; border-radius: var(--radius-md); border: 1px solid var(--neutral-300); background: var(--neutral-0); color: var(--neutral-700); font-size: 13px; cursor: pointer; }
.btn-secondary:hover { background: var(--neutral-50); }

/* 导入模式 */
.import-columns { border: 1px solid var(--neutral-200); border-radius: 8px; overflow: hidden; max-height: 240px; overflow-y: auto; }
.import-col-header {
  display: grid; grid-template-columns: 2fr 1fr 1fr 50px 50px; gap: 8px; padding: 8px 12px;
  background: var(--neutral-50); font-size: 11px; font-weight: 600; color: var(--neutral-500); text-transform: uppercase; letter-spacing: 0.3px;
  position: sticky; top: 0;
}
.import-col-row {
  display: grid; grid-template-columns: 2fr 1fr 1fr 50px 50px; gap: 8px; padding: 6px 12px;
  font-size: 12px; border-top: 1px solid var(--neutral-100);
}
.import-col-row--pk { background: var(--semantic-50); }
.import-col-mapped { color: var(--semantic-600); font-weight: 500; }
.import-entity-info { display: flex; flex-direction: column; gap: 12px; margin-top: 8px; padding-top: 12px; border-top: 1px solid var(--neutral-100); }
</style>
