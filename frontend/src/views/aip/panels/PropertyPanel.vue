<template>
  <div v-if="node" class="aip-pp">
    <div class="aip-pp__header" :style="{ background: '#fff' }">
      <div class="aip-pp__icon" :style="{ background: meta?.color || '#94a3b8' }" v-html="iconSvg"></div>
      <div class="aip-pp__title-wrap">
        <div class="aip-pp__title">{{ node.data.label || '节点' }}</div>
        <div class="aip-pp__sub" :style="{ color: meta?.color }">{{ meta?.group }}</div>
      </div>
      <button v-if="store.statusOf(node.id) !== 'idle'" class="aip-pp__btn-ghost" @click="store.bottomDrawerOpen = true; store.bottomTab = 'logs'">查看结果</button>
      <button class="aip-pp__close" @click="store.selectNode(null)">
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
      </button>
    </div>

    <div class="aip-pp__section-label">参数 PARAMETERS</div>

    <div class="aip-pp__body">
      <!-- 通用：节点名称 -->
      <div class="aip-field">
        <label>节点名称</label>
        <input v-model="node.data.label" class="aip-input" @input="touch" />
      </div>
      <div class="aip-field">
        <label>节点类型</label>
        <input :value="node.type" class="aip-input" disabled />
      </div>

      <!-- ontologyQuery -->
      <template v-if="node.type === 'ontologyQuery'">
        <div class="aip-field">
          <label>主对象类型</label>
          <ResourcePicker type="entity" :model-value="node.data.objectType || ''"
            @update:model-value="(v: string) => onPick('objectType', v)" placeholder="选择本体对象" />
        </div>
        <div class="aip-field">
          <label>关联本体（多选，逗号分隔）</label>
          <textarea class="aip-input aip-input--ta" rows="2" :value="(node.data.objectTypes || []).join(',')"
            @input="(e: any) => updateArr('objectTypes', e.target.value)"></textarea>
        </div>
        <div class="aip-field">
          <label>过滤条件 ({{ (node.data.filters || []).length }} 条)</label>
          <div v-for="(f, i) in (node.data.filters || [])" :key="i" class="aip-filter-line">{{ String(f).slice(0, 100) }}</div>
        </div>
        <div class="aip-field">
          <label>结果上限</label>
          <input type="number" v-model.number="node.data.limit" class="aip-input" @input="touch" />
        </div>
      </template>

      <!-- llmAgent -->
      <template v-else-if="node.type === 'llmAgent'">
        <div class="aip-field">
          <label>LLM 模型（模型注册中心）</label>
          <ResourcePicker type="model" :model-value="node.data.model_id || ''"
            @update:model-value="(v: string) => onPick('model_id', v)" placeholder="选择已注册模型" />
        </div>
        <div class="aip-field">
          <label>ML 模型</label>
          <select class="aip-input" v-model="node.data.mlModelRef" @change="touch">
            <option value="">不使用</option>
            <option v-for="m in ML_MODELS" :key="m.value" :value="m.value">{{ m.label }}</option>
          </select>
        </div>
        <div class="aip-field">
          <label>温度 ({{ node.data.temperature ?? 0.3 }})</label>
          <input type="range" min="0" max="1" step="0.05" :value="node.data.temperature ?? 0.3"
            @input="(e: any) => { node.data.temperature = parseFloat(e.target.value); touch() }" class="aip-slider" />
        </div>
        <div class="aip-field">
          <label>最大 Token</label>
          <input type="number" class="aip-input" v-model.number="node.data.maxTokens" @input="touch" placeholder="2048" />
        </div>
        <div class="aip-field">
          <label>Prompt 模板（支持 {question} {upstream} {nodeId.field}）</label>
          <textarea class="aip-input aip-input--ta" rows="6" v-model="node.data.prompt" @input="touch"></textarea>
        </div>
      </template>

      <!-- agentNode -->
      <template v-else-if="node.type === 'agentNode'">
        <div class="aip-field">
          <label>关联 Agent</label>
          <ResourcePicker type="agent" :model-value="node.data.agent_id || ''"
            @update:model-value="(v: string) => onPick('agent_id', v)" placeholder="选择已发布 Agent" />
        </div>
        <div class="aip-field">
          <label>主 Skill</label>
          <ResourcePicker type="skill" :model-value="node.data.skill_id || ''"
            @update:model-value="(v: string) => onPick('skill_id', v)" placeholder="选择 Skill（可选）" />
        </div>
        <div class="aip-field"><label>角色</label>
          <select class="aip-input" v-model="node.data.agentRole" @change="touch">
            <option>reasoning</option><option>generation</option><option>orchestration</option>
          </select>
        </div>
        <div class="aip-field">
          <label>关联本体（逗号分隔）</label>
          <textarea class="aip-input aip-input--ta" rows="2" :value="(node.data.objectTypes || []).join(',')"
            @input="(e: any) => updateArr('objectTypes', e.target.value)"></textarea>
        </div>
      </template>

      <!-- skillNode -->
      <template v-else-if="node.type === 'skillNode'">
        <div class="aip-field">
          <label>绑定 Skill</label>
          <ResourcePicker type="skill" :model-value="node.data.skill_id || ''"
            @update:model-value="(v: string) => onPick('skill_id', v)" placeholder="选择 Skill" />
        </div>
        <div class="aip-field">
          <label>已绑定 Skill ({{ (node.data.skills || []).length }})</label>
          <div v-for="(s, i) in (node.data.skills || [])" :key="i" class="aip-list-item">
            <span class="aip-dot aip-dot--green"></span>
            <span style="flex:1">{{ s.name || s.skillId }}</span>
            <span v-if="s.isPrimary" class="aip-tag aip-tag--gold">主</span>
            <button class="aip-icon-btn" @click="removeAt('skills', i)">×</button>
          </div>
        </div>
      </template>

      <!-- memoryNode -->
      <template v-else-if="node.type === 'memoryNode'">
        <div class="aip-field">
          <label>记忆层 ({{ (node.data.memories || []).length }})</label>
          <div v-for="(m, i) in (node.data.memories || [])" :key="i" class="aip-list-item">
            <span class="aip-dot" :style="{ background: layerColor(m.layer) }"></span>
            <span style="flex:1">{{ m.layer }} · {{ m.impl }}</span>
            <button class="aip-icon-btn" @click="removeAt('memories', i)">×</button>
          </div>
          <button class="aip-add-btn" @click="addMemory">+ 添加记忆层</button>
        </div>
      </template>

      <!-- toolNode -->
      <template v-else-if="node.type === 'toolNode'">
        <div class="aip-field">
          <label>已绑定 Tool ({{ (node.data.tools || []).length }})</label>
          <div v-for="(t, i) in (node.data.tools || [])" :key="i" class="aip-list-item">
            <span class="aip-dot aip-dot--cyan"></span>
            <span style="flex:1">{{ t.name || t.toolId }}</span>
            <button class="aip-icon-btn" @click="removeAt('tools', i)">×</button>
          </div>
        </div>
      </template>

      <!-- ruleEngine -->
      <template v-else-if="node.type === 'ruleEngine'">
        <div class="aip-field">
          <label>关联规则</label>
          <ResourcePicker type="rule" :model-value="node.data.rule_id || ''"
            @update:model-value="(v: string) => onPick('rule_id', v)" placeholder="选择规则" />
        </div>
        <div class="aip-field"><label>表达式字段</label><input class="aip-input" v-model="node.data.expressionField" @input="touch" /></div>
        <div class="aip-field"><label>操作符</label>
          <select class="aip-input" v-model="node.data.operator" @change="touch">
            <option v-for="op in OPERATORS" :key="op">{{ op }}</option>
          </select>
        </div>
        <div class="aip-field"><label>比较值</label><input class="aip-input" v-model="node.data.expressionValue" @input="touch" /></div>
      </template>

      <!-- writebackOntology -->
      <template v-else-if="node.type === 'writebackOntology'">
        <div class="aip-field">
          <label>写回本体对象</label>
          <ResourcePicker type="entity" :model-value="node.data.target_ontology || node.data.targetObjectType || ''"
            @update:model-value="(v: string) => onPick('target_ontology', v)" placeholder="选择写回的本体" />
        </div>
        <div class="aip-field"><label>操作</label>
          <select class="aip-input" v-model="node.data.operation" @change="touch">
            <option value="create">create</option><option value="update">update</option><option value="upsert">upsert</option>
          </select>
        </div>
        <div class="aip-field"><label>字段映射（JSON: 列 → 来源引用）</label>
          <textarea class="aip-input aip-input--ta" rows="4" :value="JSON.stringify(node.data.mapping || {}, null, 2)"
            @input="(e: any) => onJsonChange('mapping', e.target.value)"></textarea>
        </div>
      </template>

      <!-- actionSystem (即 action 节点) -->
      <template v-else-if="node.type === 'actionSystem' || node.type === 'action'">
        <div class="aip-field">
          <label>关联动作</label>
          <ResourcePicker type="action" :model-value="node.data.action_id || ''"
            @update:model-value="(v: string) => onPick('action_id', v)" placeholder="选择动作" />
        </div>
        <div class="aip-field"><label>参数（JSON）</label>
          <textarea class="aip-input aip-input--ta" rows="4" :value="JSON.stringify(node.data.params || {}, null, 2)"
            @input="(e: any) => onJsonChange('params', e.target.value)"></textarea>
        </div>
        <div class="aip-field aip-field--row">
          <input type="checkbox" :checked="!!node.data.dry_run" @change="(e: any) => { node.data.dry_run = e.target.checked; touch() }" />
          <span>Dry-run 模式（仅校验，不真正执行）</span>
        </div>
      </template>

      <!-- function -->
      <template v-else-if="node.type === 'function'">
        <div class="aip-field">
          <label>关联函数</label>
          <ResourcePicker type="function" :model-value="node.data.function_id || ''"
            @update:model-value="(v: string) => onPick('function_id', v)" placeholder="选择函数" />
        </div>
        <div class="aip-field"><label>参数（JSON，支持 {nodeId.field} 模板）</label>
          <textarea class="aip-input aip-input--ta" rows="4" :value="JSON.stringify(node.data.params || {}, null, 2)"
            @input="(e: any) => onJsonChange('params', e.target.value)"></textarea>
        </div>
      </template>

      <!-- subscene -->
      <template v-else-if="node.type === 'subscene'">
        <div class="aip-field">
          <label>子场景</label>
          <input class="aip-input" v-model="node.data.scene_id" @input="touch" placeholder="子场景 ID" />
        </div>
        <div class="aip-field"><label>子场景入参（JSON）</label>
          <textarea class="aip-input aip-input--ta" rows="4" :value="JSON.stringify(node.data.input_params || {}, null, 2)"
            @input="(e: any) => onJsonChange('input_params', e.target.value)"></textarea>
        </div>
      </template>

      <!-- condition -->
      <template v-else-if="node.type === 'condition'">
        <div class="aip-field"><label>条件字段</label><input class="aip-input" :value="node.data.expression?.field || ''" @input="setExpr('field', $event)" /></div>
        <div class="aip-field"><label>操作符</label>
          <select class="aip-input" :value="node.data.expression?.operator || 'switch'" @change="setExpr('operator', $event)">
            <option v-for="op in OPERATORS" :key="op">{{ op }}</option>
          </select>
        </div>
        <div class="aip-field"><label>比较值</label><input class="aip-input" :value="node.data.expression?.value || ''" @input="setExpr('value', $event)" /></div>
        <div class="aip-field">
          <label>分支 ({{ (node.data.branches || []).length }})</label>
          <div v-for="(b, i) in (node.data.branches || [])" :key="i" class="aip-branch">
            <span class="aip-branch__index">{{ i + 1 }}</span>
            <div style="flex:1">
              <div class="aip-branch__label">{{ b.label || b.condition }}</div>
              <div class="aip-branch__action">动作：{{ b.action || '—' }}</div>
            </div>
          </div>
        </div>
      </template>

      <div class="aip-pp__actions">
        <button class="aip-btn aip-btn--danger" @click="onDelete">
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3 4h10M6 4V2h4v2M5 4v9h6V4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          删除节点
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAipStore } from '../../../store/aip'
import { LLM_MODELS, ML_MODELS, OPERATORS, ACTION_TYPES, MEMORY_LAYERS, NODE_TYPES } from '../aipData'
import ResourcePicker from '../../../components/aip/ResourcePicker.vue'

const store = useAipStore()
const node = computed(() => store.selectedNode)
const meta = computed(() => node.value && NODE_TYPES.find(t => t.type === node.value!.type))

function touch() { store.markDirty() }
function onPick(field: string, value: string) {
  if (!node.value) return
  store.updateNodeData(node.value.id, { [field]: value })
}
function onJsonChange(field: string, raw: string) {
  if (!node.value) return
  try {
    const parsed = raw.trim() ? JSON.parse(raw) : {}
    store.updateNodeData(node.value.id, { [field]: parsed })
  } catch {
    // 暂存原文，等用户改成合法 JSON 再写回
    node.value.data[field + '__raw'] = raw
  }
}
function updateArr(field: string, value: string) {
  if (!node.value) return
  node.value.data[field] = value.split(',').map(s => s.trim()).filter(Boolean)
  touch()
}
function removeAt(field: string, index: number) {
  if (!node.value) return
  const arr = node.value.data[field] || []
  arr.splice(index, 1)
  touch()
}
function addMemory() {
  if (!node.value) return
  if (!node.value.data.memories) node.value.data.memories = []
  node.value.data.memories.push({ layer: 'Working', impl: '默认实现' })
  touch()
}
function layerColor(layer: string) {
  return MEMORY_LAYERS.find(l => l.value === layer)?.color || '#94a3b8'
}
function setExpr(key: string, e: Event) {
  if (!node.value) return
  if (!node.value.data.expression) node.value.data.expression = { field: '', operator: 'switch', value: '' }
  node.value.data.expression[key] = (e.target as HTMLInputElement).value
  touch()
}
function onDelete() {
  if (node.value && confirm('确定删除该节点？')) store.deleteNode(node.value.id)
}

const iconSvg = computed(() => {
  const m: Record<string, string> = {
    ontologyQuery: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none"><ellipse cx="8" cy="4" rx="5" ry="2" stroke="#fff" stroke-width="1.5"/><path d="M3 4v8c0 1.1 2.24 2 5 2s5-.9 5-2V4" stroke="#fff" stroke-width="1.5"/></svg>',
    llmAgent: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none"><path d="M8 2l1.5 3.5L13 7l-3.5 1.5L8 12l-1.5-3.5L3 7l3.5-1.5L8 2z" stroke="#fff" stroke-width="1.5"/></svg>',
    agentNode: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="5" r="2.5" stroke="#fff" stroke-width="1.5"/><path d="M3 14c0-2.76 2.24-5 5-5s5 2.24 5 5" stroke="#fff" stroke-width="1.5"/></svg>',
    skillNode: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none"><path d="M9 1L3 9h4l-1 6 6-8H8l1-6z" fill="#fff"/></svg>',
    memoryNode: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none"><rect x="2" y="3" width="12" height="10" rx="2" stroke="#fff" stroke-width="1.5"/></svg>',
    toolNode: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none"><path d="M10 2a3 3 0 00-2.83 4L3 10.17V13h2.83L10 8.83A3 3 0 1010 2z" stroke="#fff" stroke-width="1.5"/></svg>',
    ruleEngine: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none"><path d="M3 3h10M3 8h7M3 13h10" stroke="#fff" stroke-width="1.5"/></svg>',
    writebackOntology: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none"><path d="M3 2h7l3 3v9H3V2z" stroke="#fff" stroke-width="1.5"/></svg>',
    actionSystem: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none"><path d="M2 8l11-5-3 12-3-5-5-2z" stroke="#fff" stroke-width="1.5"/></svg>',
    condition: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none"><path d="M8 2l6 6-6 6-6-6 6-6z" stroke="#fff" stroke-width="1.5"/></svg>',
  }
  return node.value ? (m[node.value.type] || '') : ''
})
</script>

<style scoped>
.aip-pp { display: flex; flex-direction: column; height: 100%; background: #fff; }
.aip-pp__header {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 16px 10px; border-bottom: 1px solid #f0f0f0;
}
.aip-pp__icon {
  width: 36px; height: 36px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.aip-pp__title-wrap { flex: 1; min-width: 0; }
.aip-pp__title { font-weight: 600; font-size: 14px; color: #1e293b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.aip-pp__sub { font-size: 11px; margin-top: 2px; }
.aip-pp__btn-ghost {
  font-size: 11px; padding: 4px 10px;
  border: 1px solid #2E5BFF; background: #fff; color: #2E5BFF;
  border-radius: 4px; cursor: pointer;
}
.aip-pp__close {
  width: 24px; height: 24px; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  border: none; background: transparent; cursor: pointer; color: #94a3b8;
}
.aip-pp__close:hover { background: #f1f5f9; color: #1e293b; }
.aip-pp__section-label {
  font-size: 10px; color: #94a3b8; letter-spacing: 0.8px;
  font-weight: 700; padding: 12px 16px 6px;
}
.aip-pp__body { flex: 1; overflow-y: auto; padding: 0 16px 16px; display: flex; flex-direction: column; gap: 12px; }

.aip-field { display: flex; flex-direction: column; gap: 4px; }
.aip-field > label { font-size: 11px; color: #475569; font-weight: 500; }
.aip-input {
  width: 100%; padding: 6px 10px;
  border: 1px solid #e2e8f0; border-radius: 4px;
  font-size: 12px; color: #1e293b; background: #fff; outline: none;
}
.aip-input:focus { border-color: #2E5BFF; box-shadow: 0 0 0 2px rgba(46,91,255,.15); }
.aip-input--ta { resize: vertical; min-height: 60px; font-family: ui-monospace, monospace; font-size: 11px; }
.aip-slider { width: 100%; accent-color: #2E5BFF; }

.aip-filter-line {
  font-size: 10px; color: #475569;
  background: #f8fafc; border: 1px solid #e2e8f0;
  border-radius: 4px; padding: 4px 8px;
  margin-bottom: 4px;
  font-family: ui-monospace, monospace;
  word-break: break-all;
}
.aip-list-item {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 10px;
  background: #f8fafc; border: 1px solid #e2e8f0;
  border-radius: 4px; font-size: 12px;
  margin-bottom: 4px;
}
.aip-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.aip-dot--green { background: #10b981; }
.aip-dot--cyan { background: #0ea5e9; }
.aip-tag { font-size: 10px; padding: 1px 6px; border-radius: 3px; }
.aip-tag--gold { background: #fef3c7; color: #b45309; }
.aip-icon-btn { border: none; background: transparent; cursor: pointer; color: #94a3b8; font-size: 14px; }
.aip-icon-btn:hover { color: #ef4444; }
.aip-add-btn {
  margin-top: 6px; padding: 6px 10px;
  border: 1px dashed #cbd5e1; background: #fff; color: #475569;
  border-radius: 4px; cursor: pointer; font-size: 11px; width: 100%;
}
.aip-add-btn:hover { border-color: #2E5BFF; color: #2E5BFF; }

.aip-branch {
  display: flex; gap: 8px; padding: 8px 10px;
  background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px;
  margin-bottom: 6px;
}
.aip-branch__index {
  width: 18px; height: 18px; border-radius: 50%;
  background: #2E5BFF; color: #fff; font-size: 10px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.aip-branch__label { font-size: 12px; font-weight: 500; color: #1e293b; }
.aip-branch__action { font-size: 10px; color: #64748b; margin-top: 2px; }

.aip-pp__actions { padding-top: 12px; border-top: 1px solid #f0f0f0; }
.aip-btn {
  padding: 6px 12px; border-radius: 4px; cursor: pointer;
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 12px; border: 1px solid;
}
.aip-btn--danger { background: #fff; color: #ef4444; border-color: #fecaca; }
.aip-btn--danger:hover { background: #fef2f2; }
</style>
