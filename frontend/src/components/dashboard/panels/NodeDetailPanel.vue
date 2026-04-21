<template>
  <div class="node-panel-overlay" @click.self="$emit('close')">
    <div class="node-panel">
      <button class="node-panel__close" @click="$emit('close')">&times;</button>

      <!-- 查看模式 -->
      <template v-if="!editing && !creating">
        <div class="node-panel__header">
          <img class="node-panel__icon" :src="node.icon" alt="" />
          <div>
            <div class="node-panel__name">{{ node.label }}</div>
            <div class="node-panel__desc">{{ node.desc }}</div>
          </div>
        </div>

        <div class="node-panel__grid">
          <div class="node-panel__stat">
            <div class="stat-val">{{ node.tier }}</div>
            <div class="stat-lbl">Tier</div>
          </div>
          <div class="node-panel__stat">
            <div class="stat-val" :class="'status--' + node.status">{{ node.status }}</div>
            <div class="stat-lbl">状态</div>
          </div>
          <div class="node-panel__stat">
            <div class="stat-val">{{ node.relationCount }}</div>
            <div class="stat-lbl">关系</div>
          </div>
          <div class="node-panel__stat">
            <div class="stat-val">{{ node.ruleCount }}</div>
            <div class="stat-lbl">规则</div>
          </div>
          <div class="node-panel__stat">
            <div class="stat-val">{{ node.attrCount }}</div>
            <div class="stat-lbl">属性</div>
          </div>
          <div class="node-panel__stat">
            <div class="stat-val">{{ node.actionCount }}</div>
            <div class="stat-lbl">动作</div>
          </div>
        </div>

        <div v-if="relations.length" class="node-panel__section">
          <div class="section-title">关联关系</div>
          <div v-for="r in relations.slice(0, 8)" :key="r.id" class="rel-row">
            <span class="rel-name">{{ r.name.replaceAll('_', ' ') }}</span>
            <span class="rel-card">{{ r.cardinality }}</span>
          </div>
        </div>

        <div class="node-panel__actions">
          <button class="panel-btn" @click="goDetail">查看详情</button>
          <div class="panel-btn-row">
            <button class="panel-btn panel-btn--secondary" @click="startEdit">编辑</button>
            <button class="panel-btn panel-btn--secondary" @click="creating = true">新增节点</button>
            <button class="panel-btn panel-btn--danger" @click="handleDelete" :disabled="deleting">{{ deleting ? '删除中...' : '删除' }}</button>
          </div>
        </div>
      </template>

      <!-- 编辑模式 -->
      <template v-else-if="editing">
        <div class="node-panel__form-title">编辑节点</div>
        <div class="np-field">
          <label>中文名</label>
          <input v-model="editForm.name_cn" class="np-input" />
        </div>
        <div class="np-field">
          <label>英文名</label>
          <input v-model="editForm.name" class="np-input" />
        </div>
        <div class="np-field">
          <label>Tier</label>
          <select v-model.number="editForm.tier" class="np-input">
            <option :value="1">1 — 核心对象</option>
            <option :value="2">2 — 领域对象</option>
            <option :value="3">3 — 场景对象</option>
          </select>
        </div>
        <div class="np-field">
          <label>状态</label>
          <select v-model="editForm.status" class="np-input">
            <option value="active">active</option>
            <option value="inactive">inactive</option>
            <option value="warning">warning</option>
          </select>
        </div>
        <div class="np-field">
          <label>描述</label>
          <textarea v-model="editForm.description" class="np-input np-input--ta" rows="2"></textarea>
        </div>
        <div class="panel-btn-row" style="margin-top:14px">
          <button class="panel-btn panel-btn--secondary" @click="editing = false">取消</button>
          <button class="panel-btn" @click="handleSave" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
        </div>
        <div v-if="errMsg" class="np-err">{{ errMsg }}</div>
      </template>

      <!-- 新增模式 -->
      <template v-else-if="creating">
        <div class="node-panel__form-title">新增节点</div>
        <div class="np-field">
          <label>中文名 <span class="np-req">*</span></label>
          <input v-model="createForm.name_cn" class="np-input" />
        </div>
        <div class="np-field">
          <label>英文名 <span class="np-req">*</span></label>
          <input v-model="createForm.name" class="np-input" placeholder="如：Customer" />
        </div>
        <div class="np-field">
          <label>Tier</label>
          <select v-model.number="createForm.tier" class="np-input">
            <option :value="1">1 — 核心对象</option>
            <option :value="2">2 — 领域对象</option>
            <option :value="3">3 — 场景对象</option>
          </select>
        </div>
        <div class="np-field">
          <label>命名空间</label>
          <input v-model="createForm.namespace" class="np-input" placeholder="可选" />
        </div>
        <div class="np-field">
          <label>描述</label>
          <textarea v-model="createForm.description" class="np-input np-input--ta" rows="2"></textarea>
        </div>
        <div class="panel-btn-row" style="margin-top:14px">
          <button class="panel-btn panel-btn--secondary" @click="creating = false">取消</button>
          <button class="panel-btn" @click="handleCreate" :disabled="saving">{{ saving ? '创建中...' : '创建' }}</button>
        </div>
        <div v-if="errMsg" class="np-err">{{ errMsg }}</div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { entityApi } from '../../../api/ontology'
import type { RelationData } from '../../../api/relations'

const props = defineProps<{
  node: { id: string; label: string; desc: string; icon: string; tier: number; status: string; relationCount: number; ruleCount: number; attrCount: number; actionCount: number }
  relations: RelationData[]
}>()
const emit = defineEmits<{ close: []; updated: []; created: []; deleted: [] }>()

const router = useRouter()
const editing = ref(false)
const creating = ref(false)
const saving = ref(false)
const deleting = ref(false)
const errMsg = ref('')

const editForm = ref({ name: '', name_cn: '', tier: 1, status: 'active', description: '' })
const createForm = ref({ name: '', name_cn: '', tier: 2, namespace: '', description: '' })

function goDetail() { router.push(`/ontology/${props.node.id}`) }

function startEdit() {
  const [name, tierStr] = props.node.desc.split(' · Tier ')
  editForm.value = {
    name,
    name_cn: props.node.label,
    tier: props.node.tier,
    status: props.node.status,
    description: '',
  }
  errMsg.value = ''
  editing.value = true
}

async function handleSave() {
  errMsg.value = ''
  saving.value = true
  try {
    await entityApi.update(props.node.id, editForm.value)
    editing.value = false
    emit('updated')
  } catch (e: any) {
    errMsg.value = e.response?.data?.detail || '保存失败'
  } finally {
    saving.value = false
  }
}

async function handleCreate() {
  if (!createForm.value.name || !createForm.value.name_cn) { errMsg.value = '英文名和中文名必填'; return }
  errMsg.value = ''
  saving.value = true
  try {
    await entityApi.create(createForm.value)
    creating.value = false
    emit('created')
    emit('close')
  } catch (e: any) {
    errMsg.value = e.response?.data?.detail || '创建失败'
  } finally {
    saving.value = false
  }
}

async function handleDelete() {
  if (!confirm(`确认删除节点「${props.node.label}」？此操作不可恢复。`)) return
  deleting.value = true
  try {
    await entityApi.remove(props.node.id)
    emit('deleted')
    emit('close')
  } catch (e: any) {
    alert(e.response?.data?.detail || '删除失败')
  } finally {
    deleting.value = false
  }
}
</script>

<style scoped>
.node-panel-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0, 0, 0, 0.5);
  display: flex; align-items: center; justify-content: flex-end;
  padding-right: 24px;
}
.node-panel {
  width: 340px; max-height: 85vh; overflow-y: auto;
  background: rgba(0, 18, 68, 0.95);
  border: 1px solid rgba(0, 80, 234, 0.4);
  border-radius: 12px;
  padding: 24px;
  color: #e8f0ff;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5);
  position: relative;
}
.node-panel__close {
  position: absolute; top: 12px; right: 16px;
  background: none; border: none; color: #94a3b8; font-size: 20px; cursor: pointer;
}
.node-panel__close:hover { color: #e8f0ff; }
.node-panel__header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
.node-panel__icon { width: 48px; height: auto; }
.node-panel__name { font-size: 16px; font-weight: 700; }
.node-panel__desc { font-size: 12px; color: rgba(200, 220, 255, 0.6); margin-top: 2px; }
.node-panel__grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 20px; }
.node-panel__stat { text-align: center; background: rgba(0, 50, 145, 0.2); border: 1px solid rgba(0, 80, 234, 0.15); border-radius: 8px; padding: 10px 4px; }
.stat-val { font-size: 18px; font-weight: 800; color: #5c9aff; }
.stat-lbl { font-size: 10px; color: rgba(200, 220, 255, 0.5); margin-top: 2px; }
.status--active { color: #20c997; }
.status--warning { color: #f59f00; }
.status--error { color: #fa5252; }
.node-panel__section { margin-bottom: 16px; }
.section-title { font-size: 11px; font-weight: 700; color: rgba(200, 220, 255, 0.5); letter-spacing: .08em; text-transform: uppercase; margin-bottom: 8px; }
.rel-row { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; font-size: 12px; }
.rel-name { color: rgba(200, 220, 255, 0.85); }
.rel-card { color: #5c9aff; font-size: 10px; font-weight: 600; }
.node-panel__actions { margin-top: 16px; display: flex; flex-direction: column; gap: 8px; }
.panel-btn-row { display: flex; gap: 8px; }
.panel-btn {
  flex: 1; padding: 9px;
  background: rgba(0, 80, 234, 0.3); border: 1px solid rgba(0, 80, 234, 0.5);
  border-radius: 8px; color: #e8f0ff; font-size: 12px; font-weight: 600;
  cursor: pointer; transition: background .15s;
}
.panel-btn:hover:not(:disabled) { background: rgba(0, 80, 234, 0.5); }
.panel-btn:disabled { opacity: .5; cursor: not-allowed; }
.panel-btn--secondary { background: rgba(255,255,255,0.06); border-color: rgba(255,255,255,0.15); }
.panel-btn--secondary:hover:not(:disabled) { background: rgba(255,255,255,0.12); }
.panel-btn--danger { background: rgba(239,68,68,0.2); border-color: rgba(239,68,68,0.4); color: #fca5a5; }
.panel-btn--danger:hover:not(:disabled) { background: rgba(239,68,68,0.35); }
.node-panel__form-title { font-size: 14px; font-weight: 700; margin-bottom: 16px; color: #e8f0ff; }
.np-field { display: flex; flex-direction: column; gap: 5px; margin-bottom: 12px; }
.np-field label { font-size: 11px; font-weight: 600; color: rgba(200,220,255,0.6); }
.np-input {
  padding: 7px 10px; border-radius: 6px; font-size: 12px;
  border: 1px solid rgba(0,80,234,0.3); background: rgba(0,18,68,0.6);
  color: #e8f0ff; outline: none; width: 100%; box-sizing: border-box; font-family: inherit;
}
.np-input:focus { border-color: rgba(0,80,234,0.7); }
.np-input--ta { resize: vertical; min-height: 56px; }
.np-req { color: #f87171; }
.np-err { margin-top: 8px; font-size: 11px; color: #f87171; }
</style>
