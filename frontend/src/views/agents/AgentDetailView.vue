<template>
  <div class="harness">
    <div class="harness__topbar">
      <div class="harness__topbar-left">
        <button class="harness__btn harness__btn--ghost" @click="router.push('/agents')" style="padding: 4px 8px">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          返回
        </button>
        <span class="harness__divider"></span>
        <span class="harness__scene-name">{{ form.name || '未命名智能体' }}</span>
        <span class="harness__status-tag" :class="`harness__status-tag--${current?.status}`">
          {{ current?.status === 'published' ? '已发布' : '草稿' }}
        </span>
        <span class="harness__dirty" v-if="isDirty">
          <svg width="6" height="6" viewBox="0 0 6 6"><circle cx="3" cy="3" r="3" fill="#f59e0b"/></svg>
          未保存
        </span>
      </div>
      <div class="harness__topbar-right" v-if="current">
        <button class="harness__btn" @click="saveAgent" :disabled="saving">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M3 2h8l3 3v9H3V2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M6 2v4h5V2M5 9h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          {{ saving ? '保存中...' : '保存' }}
        </button>
        <button class="harness__btn harness__btn--outline" @click="publishAgent" v-if="current.status === 'draft'" :disabled="publishing">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 2l6 4v4l-6 4-6-4V6l6-4z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
          发布
        </button>
        <button class="harness__btn harness__btn--ghost" @click="showSettings = !showSettings">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="2.5" stroke="currentColor" stroke-width="1.5"/><path d="M8 2v1.5M8 12.5V14M2 8h1.5M12.5 8H14M3.5 3.5l1 1M11.5 11.5l1 1M3.5 12.5l1-1M11.5 4.5l1-1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          设置
        </button>
      </div>
    </div>

    <div class="harness__body" v-if="current">
      <div class="harness__left">
        <div class="harness__section harness__section--nodes">
          <div class="harness__section-header">
            <span class="harness__section-title">节点库</span>
            <span class="harness__section-hint">拖入或点击添加</span>
          </div>
          <div class="harness__node-lib">
            <template v-for="group in nodeGroups" :key="group.label">
              <div class="harness__node-group-label">{{ group.label }}</div>
              <div v-for="nt in group.nodes" :key="nt.skillId || nt.type"
                class="harness__node-item"
                draggable="true"
                @dragstart="onDragStart($event, nt.type, nt)"
                @click="addNodeToCenter(nt.type, nt)"
                :title="`点击添加 ${nt.label}`">
                <span class="harness__node-item-icon" :style="{ color: nt.color }" v-html="nt.icon"></span>
                <span class="harness__node-item-label">{{ nt.label }}</span>
                <svg class="harness__node-item-add" width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
              </div>
            </template>
          </div>
        </div>
      </div>

      <div class="harness__canvas-wrap" ref="canvasWrap">
        <VueFlow
          v-model:nodes="flowNodes"
          v-model:edges="flowEdges"
          :node-types="nodeTypes_"
          :default-edge-options="defaultEdgeOptions"
          :snap-to-grid="true"
          :snap-grid="[16, 16]"
          fit-view-on-init
          class="harness__flow"
          @node-click="onNodeClick"
          @pane-click="selectedNodeId = null"
          @drop="onDrop"
          @dragover.prevent>
          <Background variant="lines" pattern-color="#e8edf2" :gap="24" :size="1" />
          <Controls />
          <MiniMap :node-color="miniMapColor" node-stroke-color="transparent" mask-color="rgba(15,23,42,0.6)" />
        </VueFlow>
        <div class="harness__canvas-hint" v-if="flowNodes.length === 0">
          从左侧节点库拖入节点，或点击节点旁的 + 按钮添加
        </div>
      </div>

      <transition name="panel-slide">
        <div class="harness__right" v-if="selectedNodeId && selectedNode">
          <div class="harness__panel-header">
            <div class="harness__panel-header-left">
              <span class="harness__panel-type-dot" :style="{ background: nodeTypeColor(selectedNode.type) }"></span>
              <span>节点配置</span>
            </div>
            <button class="harness__icon-btn" @click="selectedNodeId = null">
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            </button>
          </div>
          <div class="harness__panel-body">
            <div class="harness__panel-type-badge" :style="{ color: nodeTypeColor(selectedNode.type), borderColor: nodeTypeColor(selectedNode.type) + '40', background: nodeTypeColor(selectedNode.type) + '12' }">
              <span v-html="nodeTypeIcon(selectedNode.type)"></span>
              {{ nodeTypeLabel(selectedNode.type) }}
            </div>
            <div class="harness__field">
              <label>节点名称</label>
              <input class="harness__input" v-model="selectedNode.data.label" @input="isDirty = true" placeholder="输入节点名称" />
            </div>
            <div class="harness__field">
              <label>描述</label>
              <textarea class="harness__input harness__input--ta" v-model="selectedNode.data.description" @input="isDirty = true" placeholder="节点说明" rows="2"></textarea>
            </div>
            <div class="harness__field" v-if="selectedNode.type === 'ontology-query'">
              <label>本体对象</label>
              <input class="harness__input" v-model="selectedNode.data.ontology_type" @input="isDirty = true" placeholder="如 InstallOrder" />
            </div>
            <div class="harness__field" v-if="selectedNode.type === 'llm-inference'">
              <label>Prompt 模板</label>
              <textarea class="harness__input harness__input--ta" v-model="selectedNode.data.prompt" @input="isDirty = true" placeholder="输入 Prompt 模板，支持 {变量} 占位符" rows="5"></textarea>
            </div>
            <div class="harness__field" v-if="selectedNode.type === 'datasource'">
              <label>SQL 查询</label>
              <textarea class="harness__input harness__input--ta harness__input--mono" v-model="selectedNode.data.sql" @input="isDirty = true" placeholder="SELECT * FROM table WHERE ..." rows="4"></textarea>
            </div>
            <div class="harness__field" v-if="selectedNode.type === 'condition'">
              <label>判断条件</label>
              <input class="harness__input" v-model="selectedNode.data.condition_expr" @input="isDirty = true" placeholder="如 risk_score > 80" />
            </div>
            <div class="harness__field" v-if="selectedNode.type === 'notification'">
              <label>通知方式</label>
              <select class="harness__input" v-model="selectedNode.data.notify_type" @change="isDirty = true">
                <option value="sms">短信</option>
                <option value="workorder">工单</option>
                <option value="email">邮件</option>
              </select>
            </div>
            <template v-if="selectedNode.type === 'skill'">
              <div class="harness__field">
                <label>选择技能</label>
                <select class="harness__input" v-model="selectedNode.data.skill_id" @change="onSkillSelect(selectedNode)">
                  <option value="">请选择...</option>
                  <option v-for="s in skills" :key="s.id" :value="s.id">{{ s.name }}</option>
                </select>
              </div>
              <div class="harness__field" v-if="selectedNode.data.skill_id">
                <label>技能说明</label>
                <div style="font-size:11px;color:var(--h-text-4);line-height:1.5">{{ getSkillDesc(selectedNode.data.skill_id) }}</div>
              </div>
              <div class="harness__field" v-for="p in getSkillParams(selectedNode.data.skill_id)" :key="p.name">
                <label>{{ p.description || p.name }}</label>
                <input class="harness__input" v-model="selectedNode.data.input_mapping[p.name]" @input="isDirty = true" :placeholder="`如 {question} 或固定值`" />
              </div>
            </template>
            <div class="harness__field" v-if="selectedNode.type === 'intent-recognition'">
              <label>提取字段</label>
              <input class="harness__input" v-model="selectedNode.data.extract_fields" @input="isDirty = true" placeholder="如 churn_id, user_id（逗号分隔）" />
            </div>
            <template v-if="selectedNode.type === 'agent'">
              <div class="harness__field">
                <label>绑定技能</label>
                <select class="harness__input" v-model="selectedNode.data.skill_id" @change="onSkillSelect(selectedNode)">
                  <option value="">请选择...</option>
                  <option v-for="s in skills" :key="s.id" :value="s.id">{{ s.name }}</option>
                </select>
              </div>
              <div class="harness__field" v-if="selectedNode.data.skill_id">
                <label>技能说明</label>
                <div style="font-size:11px;color:var(--h-text-4);line-height:1.5">{{ getSkillDesc(selectedNode.data.skill_id) }}</div>
              </div>
              <div class="harness__field">
                <label>Agent 加工 Prompt</label>
                <textarea class="harness__input harness__input--ta" v-model="selectedNode.data.agent_prompt" @input="isDirty = true" placeholder="可选，用于对技能结果做二次加工。支持 {question} {skill_result}" rows="4"></textarea>
              </div>
            </template>
            <div class="harness__field" v-if="selectedNode.type === 'output'">
              <label>输出格式</label>
              <select class="harness__input" v-model="selectedNode.data.output_format" @change="isDirty = true">
                <option value="text">文本</option>
                <option value="json">JSON</option>
                <option value="markdown">Markdown</option>
              </select>
            </div>
            <div class="harness__panel-actions">
              <button class="harness__btn harness__btn--danger harness__btn--sm" @click="deleteNode(selectedNodeId)">
                <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3 4h10M6 4V2h4v2M5 4v9h6V4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
                删除节点
              </button>
            </div>
          </div>
        </div>
      </transition>

      <transition name="panel-slide">
        <div class="harness__right" v-if="showSettings && !selectedNodeId">
          <div class="harness__panel-header">
            <div class="harness__panel-header-left">
              <span>智能体设置</span>
            </div>
            <button class="harness__icon-btn" @click="showSettings = false">
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            </button>
          </div>
          <div class="harness__panel-body">
            <div class="harness__field">
              <label>名称</label>
              <input class="harness__input" v-model="form.name" @input="isDirty = true" />
            </div>
            <div class="harness__field">
              <label>描述</label>
              <textarea class="harness__input harness__input--ta" v-model="form.description" @input="isDirty = true" rows="3"></textarea>
            </div>
            <div class="harness__field">
              <label>模型</label>
              <select class="harness__input" v-model="form.model_id" @change="isDirty = true">
                <option :value="null">默认模型</option>
                <option v-for="m in models" :key="m.id" :value="m.id">{{ m.name }}</option>
              </select>
            </div>
            <div class="harness__field">
              <label>温度 {{ form.tools_config.temperature }}</label>
              <input type="range" v-model.number="form.tools_config.temperature" min="0" max="2" step="0.1" class="harness__slider" @input="isDirty = true" />
            </div>
            <div class="harness__field">
              <label>系统提示词</label>
              <textarea class="harness__input harness__input--ta harness__input--mono" v-model="form.system_prompt" @input="isDirty = true" rows="8" placeholder="系统提示词..."></textarea>
            </div>
          </div>
        </div>
      </transition>
    </div>

    <div v-else class="harness__canvas-empty" style="flex:1">
      <div class="harness__canvas-empty-icon">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none"><path d="M24 6L42 16v16L24 42 6 32V16L24 6z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
      </div>
      <p class="harness__canvas-empty-title">加载中...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, markRaw } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { VueFlow, MarkerType } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'
import WorkflowNode from '../../components/harness/nodes/WorkflowNode.vue'
import { agentsApi, modelsApi } from '../../api/agents'
import { skillsApi, type SkillItem } from '../../api/skills'

const route = useRoute()
const router = useRouter()
const current = ref<any>(null)
const models = ref<any[]>([])
const skills = ref<SkillItem[]>([])
const saving = ref(false)
const publishing = ref(false)
const isDirty = ref(false)
const showSettings = ref(false)
const selectedNodeId = ref<string | null>(null)
const canvasWrap = ref<HTMLElement>()
const flowNodes = ref<any[]>([])
const flowEdges = ref<any[]>([])

const form = ref({
  name: '', description: '', model_id: null as string | null,
  system_prompt: '', kb_ids: [] as string[], entity_ids: [] as string[],
  tags: [] as string[], tools_config: { temperature: 0.7, max_tokens: 2048 }
})

const nodeTypes_: Record<string, any> = {
  'ontology-query': markRaw(WorkflowNode), 'ontology-relation': markRaw(WorkflowNode),
  'rule-evaluate': markRaw(WorkflowNode), 'datasource': markRaw(WorkflowNode),
  'variable-assign': markRaw(WorkflowNode), 'parallel': markRaw(WorkflowNode),
  'llm-inference': markRaw(WorkflowNode), 'ml-model': markRaw(WorkflowNode),
  'voice-audit': markRaw(WorkflowNode), 'condition': markRaw(WorkflowNode),
  'loop': markRaw(WorkflowNode), 'merge': markRaw(WorkflowNode),
  'rule-engine': markRaw(WorkflowNode), 'notification': markRaw(WorkflowNode),
  'human-approval': markRaw(WorkflowNode), 'write-back': markRaw(WorkflowNode),
  'api-response': markRaw(WorkflowNode), 'skill': markRaw(WorkflowNode),
  'intent-recognition': markRaw(WorkflowNode), 'agent': markRaw(WorkflowNode),
  'output': markRaw(WorkflowNode),
}
const defaultEdgeOptions = {
  type: 'smoothstep', markerEnd: MarkerType.ArrowClosed,
  style: { stroke: '#94a3b8', strokeWidth: 1.5 },
}

const nodeTypes = [
  { type: 'ontology-query', label: '本体实体查询', color: '#3b82f6', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="6" r="3" stroke="currentColor" stroke-width="1.5"/><path d="M3 13c0-2.76 2.24-5 5-5s5 2.24 5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'ontology-relation', label: '关系图遍历', color: '#6366f1', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><circle cx="3" cy="8" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="13" cy="4" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="13" cy="12" r="2" stroke="currentColor" stroke-width="1.5"/><path d="M5 8h3l3-4M5 8h3l3 4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>` },
  { type: 'rule-evaluate', label: '规则评估', color: '#f59e0b', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M2 8h8M2 12h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'datasource', label: '数据源连接', color: '#8b5cf6', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><ellipse cx="8" cy="4" rx="5" ry="2" stroke="currentColor" stroke-width="1.5"/><path d="M3 4v4c0 1.1 2.24 2 5 2s5-.9 5-2V4" stroke="currentColor" stroke-width="1.5"/></svg>` },
  { type: 'variable-assign', label: '变量赋值', color: '#64748b', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M4 5h8M4 8h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'parallel', label: '并行分支', color: '#0ea5e9', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M3 8h3M10 5h3M10 11h3M6 8l4-3M6 8l4 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'llm-inference', label: '大模型推理', color: '#10b981', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 2l1.5 3.5L13 7l-3.5 1.5L8 12l-1.5-3.5L3 7l3.5-1.5L8 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>` },
  { type: 'ml-model', label: '预测模型', color: '#06b6d4', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M2 12L6 7l3 3 2-4 3 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>` },
  { type: 'voice-audit', label: '语音质检', color: '#7c3aed', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><rect x="5" y="2" width="6" height="8" rx="3" stroke="currentColor" stroke-width="1.5"/><path d="M3 9a5 5 0 0010 0M8 14v-2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'condition', label: '条件判断', color: '#a855f7', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 2l6 6-6 6-6-6 6-6z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>` },
  { type: 'loop', label: '遍历列表', color: '#0ea5e9', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M3 8a5 5 0 019.9-1M13 8a5 5 0 01-9.9 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'merge', label: '合并分支', color: '#84cc16', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M4 3v4l4 3 4-3V3M8 10v3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>` },
  { type: 'rule-engine', label: '规则引擎', color: '#f59e0b', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M2 8h8M2 12h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'notification', label: '通知触达', color: '#ec4899', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 2a5 5 0 015 5v2l1 2H2l1-2V7a5 5 0 015-5z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>` },
  { type: 'human-approval', label: '人工审批', color: '#f97316', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="5" r="3" stroke="currentColor" stroke-width="1.5"/><path d="M3 14c0-2.76 2.24-5 5-5s5 2.24 5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'write-back', label: '结果写回', color: '#64748b', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 3v8M5 8l3 3 3-3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>` },
  { type: 'api-response', label: 'API 响应', color: '#2e5bff', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M5 4L2 8l3 4M11 4l3 4-3 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M9 3L7 13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'skill', label: '业务技能', color: '#e11d48', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 1l2 4h4l-3 3 1 4-4-2-4 2 1-4-3-3h4l2-4z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/></svg>` },
  { type: 'intent-recognition', label: '意图识别', color: '#0891b2', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 2a6 6 0 100 12A6 6 0 008 2z" stroke="currentColor" stroke-width="1.5"/><path d="M6 7h4M8 5v6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'agent', label: '智能体', color: '#7c3aed', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="5" r="3" stroke="currentColor" stroke-width="1.5"/><path d="M3 14c0-2.76 2.24-5 5-5s5 2.24 5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'output', label: '结果输出', color: '#059669', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M3 8h7M7 5l3 3-3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 3v10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
]

const skillNodeItems = computed(() =>
  skills.value.map(s => ({
    type: 'skill' as const,
    label: s.name,
    color: '#e11d48',
    icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 1l2 4h4l-3 3 1 4-4-2-4 2 1-4-3-3h4l2-4z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/></svg>`,
    skillId: s.id,
    skillName: s.name,
  }))
)

const nodeGroups = computed(() => [
  { label: '智能编排', nodes: nodeTypes.filter(n => ['intent-recognition','agent','output'].includes(n.type)) },
  { label: '本体推理', nodes: nodeTypes.filter(n => ['ontology-query','ontology-relation','rule-evaluate'].includes(n.type)) },
  { label: '数据处理', nodes: nodeTypes.filter(n => ['datasource','variable-assign','parallel'].includes(n.type)) },
  { label: 'AI 能力', nodes: nodeTypes.filter(n => ['llm-inference','ml-model','voice-audit'].includes(n.type)) },
  { label: '流程控制', nodes: nodeTypes.filter(n => ['condition','loop','merge','rule-engine'].includes(n.type)) },
  { label: '触达输出', nodes: nodeTypes.filter(n => ['notification','human-approval','write-back','api-response'].includes(n.type)) },
  { label: '业务技能', nodes: skillNodeItems.value.length > 0 ? skillNodeItems.value : [nodeTypes.find(n => n.type === 'skill')!] },
])

const selectedNode = computed(() => flowNodes.value.find(n => n.id === selectedNodeId.value) ?? null)
function nodeTypeColor(type: string) { return nodeTypes.find(n => n.type === type)?.color ?? '#94a3b8' }
function nodeTypeLabel(type: string) { return nodeTypes.find(n => n.type === type)?.label ?? type }
function nodeTypeIcon(type: string) { return nodeTypes.find(n => n.type === type)?.icon ?? '' }
function miniMapColor(node: any) { return nodeTypeColor(node.type) }
function onNodeClick({ node }: any) { selectedNodeId.value = node.id; showSettings.value = false }

let dragType = ''
let dragSkillMeta: { skillId?: string; skillName?: string } = {}
function onDragStart(e: DragEvent, type: string, extra?: any) {
  dragType = type
  dragSkillMeta = extra?.skillId ? { skillId: extra.skillId, skillName: extra.skillName } : {}
  e.dataTransfer!.effectAllowed = 'move'
}
function onDrop(e: DragEvent) {
  if (!dragType || !canvasWrap.value) return
  const rect = canvasWrap.value.getBoundingClientRect()
  addNode(dragType, { x: e.clientX - rect.left - 80, y: e.clientY - rect.top - 30 }, dragSkillMeta)
  dragType = ''
  dragSkillMeta = {}
}
function addNodeToCenter(type: string, extra?: any) {
  const i = flowNodes.value.length
  addNode(type, { x: 80 + (i % 4) * 220, y: 80 + Math.floor(i / 4) * 120 }, extra)
}
function addNode(type: string, position: { x: number; y: number }, extra?: { skillId?: string; skillName?: string }) {
  const meta = nodeTypes.find(n => n.type === type)
  const nodeData: any = { label: extra?.skillName || meta?.label || type, execState: 'pending' }
  if (type === 'skill' && extra?.skillId) {
    nodeData.skill_id = extra.skillId
    nodeData.skill_name = extra.skillName
    nodeData.input_mapping = {}
  }
  flowNodes.value.push({ id: `node-${Date.now()}`, type, position, data: nodeData })
  isDirty.value = true
}
function deleteNode(id: string) {
  flowNodes.value = flowNodes.value.filter(n => n.id !== id)
  flowEdges.value = flowEdges.value.filter(e => e.source !== id && e.target !== id)
  selectedNodeId.value = null; isDirty.value = true
}
function onSkillSelect(node: any) {
  const s = skills.value.find(sk => sk.id === node.data.skill_id)
  if (s) {
    node.data.skill_name = s.name
    node.data.label = s.name
    node.data.input_mapping = node.data.input_mapping || {}
  }
  isDirty.value = true
}
function getSkillDesc(skillId: string): string {
  return skills.value.find(s => s.id === skillId)?.description || ''
}
function getSkillParams(skillId: string): Array<{ name: string; type: string; description: string }> {
  const s = skills.value.find(sk => sk.id === skillId)
  return (s?.config_json?.params as any[]) || []
}
async function saveAgent() {
  saving.value = true
  try {
    const res = await agentsApi.update(current.value.id, { ...form.value, nodes_json: flowNodes.value, edges_json: flowEdges.value, status: current.value.status })
    current.value = res; isDirty.value = false
  } catch (e) { console.error(e) } finally { saving.value = false }
}
async function publishAgent() {
  publishing.value = true
  try {
    const res = await agentsApi.update(current.value.id, { ...form.value, nodes_json: flowNodes.value, edges_json: flowEdges.value, status: 'published' })
    current.value = res; isDirty.value = false
  } catch (e) { console.error(e) } finally { publishing.value = false }
}
onMounted(async () => {
  const id = route.params.id as string
  const [agentRes, modelRes, skillRes] = await Promise.all([agentsApi.get(id), modelsApi.list(), skillsApi.list()])
  current.value = agentRes; models.value = modelRes; skills.value = skillRes
  form.value = {
    name: agentRes.name || '', description: agentRes.description || '',
    model_id: agentRes.model_id || null, system_prompt: agentRes.system_prompt || '',
    kb_ids: agentRes.kb_ids || [], entity_ids: agentRes.entity_ids || [],
    tags: agentRes.tags || [], tools_config: { temperature: 0.7, max_tokens: 2048, ...(agentRes.tools_config || {}) }
  }
  flowNodes.value = (agentRes.nodes_json || []).map((n: any) => ({ ...n }))
  flowEdges.value = (agentRes.edges_json || []).map((e: any) => ({ ...e }))
})
</script>

<style scoped>
.harness {
  --h-bg:#f8fafc;--h-bg-2:#fff;--h-bg-3:#f1f5f9;--h-border:#e2e8f0;--h-border-2:#cbd5e1;
  --h-text:#0f172a;--h-text-2:#334155;--h-text-3:#64748b;--h-text-4:#94a3b8;
  --h-input-bg:#fff;--h-accent:#4f46e5;--h-canvas-bg:#ffffff;
  display:flex;flex-direction:column;height:100vh;background:var(--h-bg);color:var(--h-text);
}
.harness__topbar{display:flex;align-items:center;justify-content:space-between;height:48px;padding:0 16px;flex-shrink:0;background:var(--h-bg);border-bottom:1px solid var(--h-border);gap:8px;}
.harness__topbar-left{display:flex;align-items:center;gap:8px;}
.harness__topbar-right{display:flex;align-items:center;gap:6px;}
.harness__divider{width:1px;height:14px;background:var(--h-border-2);}
.harness__scene-name{font-size:13px;color:var(--h-text-2);}
.harness__dirty{display:flex;align-items:center;gap:4px;font-size:11px;color:#f59e0b;}
.harness__status-tag{font-size:11px;padding:2px 7px;border-radius:10px;font-weight:600;background:var(--h-bg-2);color:var(--h-text-3);}
.harness__status-tag--draft{background:#fef3c7;color:#d97706;}
.harness__status-tag--published{background:#d1fae5;color:#059669;}
.harness__btn{display:inline-flex;align-items:center;gap:5px;padding:5px 11px;border-radius:6px;font-size:12px;font-weight:500;border:1px solid var(--h-border-2);background:var(--h-bg-2);color:var(--h-text-2);cursor:pointer;transition:all .15s;white-space:nowrap;}
.harness__btn:hover:not(:disabled){color:var(--h-text);}
.harness__btn:disabled{opacity:.4;cursor:not-allowed;}
.harness__btn--primary{background:#4f46e5;border-color:#4f46e5;color:#fff;}
.harness__btn--primary:hover:not(:disabled){background:#4338ca;}
.harness__btn--outline{border-color:#4f46e5;color:#6366f1;background:transparent;}
.harness__btn--outline:hover:not(:disabled){background:#eef2ff;}
.harness__btn--ghost{border-color:transparent;background:transparent;color:var(--h-text-3);}
.harness__btn--ghost:hover:not(:disabled){background:var(--h-bg-2);color:var(--h-text-2);}
.harness__btn--danger{border-color:#fca5a5;background:#fff1f2;color:#ef4444;}
.harness__btn--sm{padding:3px 8px;font-size:11px;}
.harness__body{flex:1;display:flex;overflow:hidden;}
.harness__left{width:200px;min-width:200px;background:var(--h-bg-2);border-right:1px solid var(--h-border);display:flex;flex-direction:column;overflow:hidden;}
.harness__section{display:flex;flex-direction:column;overflow:hidden;flex:1;}
.harness__section-header{display:flex;align-items:center;justify-content:space-between;padding:10px 12px 6px;flex-shrink:0;}
.harness__section-title{font-size:11px;font-weight:600;color:var(--h-text-3);text-transform:uppercase;letter-spacing:0.5px;}
.harness__section-hint{font-size:10px;color:var(--h-text-4);}
.harness__node-lib{overflow-y:auto;padding:0 8px 8px;}
.harness__node-group-label{font-size:10px;color:var(--h-text-4);padding:6px 4px 2px;text-transform:uppercase;letter-spacing:0.3px;}
.harness__node-item{display:flex;align-items:center;gap:7px;padding:5px 8px;border-radius:5px;cursor:pointer;color:var(--h-text-2);font-size:12px;transition:background 0.12s;}
.harness__node-item:hover{background:var(--h-bg-3);}
.harness__node-item-icon{width:13px;height:13px;flex-shrink:0;display:flex;align-items:center;justify-content:center;}
.harness__node-item-label{flex:1;}
.harness__node-item-add{color:var(--h-text-4);flex-shrink:0;opacity:0;transition:opacity 0.12s;}
.harness__node-item:hover .harness__node-item-add{opacity:1;}
.harness__canvas-wrap{flex:1;position:relative;overflow:hidden;}
.harness__flow{width:100%;height:100%;}
.harness__canvas-hint{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:13px;color:var(--h-text-4);pointer-events:none;}
.harness__canvas-empty{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;color:var(--h-text-4);}
.harness__canvas-empty-icon{opacity:0.3;}
.harness__canvas-empty-title{font-size:14px;color:var(--h-text-3);margin:0;}
.harness__right{width:260px;min-width:260px;background:var(--h-bg-2);border-left:1px solid var(--h-border);display:flex;flex-direction:column;overflow:hidden;}
.harness__panel-header{display:flex;align-items:center;justify-content:space-between;padding:12px 14px;border-bottom:1px solid var(--h-border);flex-shrink:0;font-size:12px;font-weight:600;color:var(--h-text-2);}
.harness__panel-header-left{display:flex;align-items:center;gap:8px;}
.harness__panel-type-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;}
.harness__icon-btn{background:none;border:none;cursor:pointer;color:var(--h-text-4);padding:3px;border-radius:4px;display:flex;align-items:center;}
.harness__icon-btn:hover{background:var(--h-bg-3);color:var(--h-text-2);}
.harness__panel-body{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:12px;}
.harness__panel-type-badge{display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:600;padding:3px 8px;border-radius:5px;border:1px solid;width:fit-content;}
.harness__field{display:flex;flex-direction:column;gap:5px;}
.harness__field label{font-size:11px;font-weight:500;color:var(--h-text-3);}
.harness__input{padding:6px 9px;background:var(--h-input-bg);border:1px solid var(--h-border);border-radius:6px;font-size:12px;color:var(--h-text);outline:none;width:100%;box-sizing:border-box;transition:border-color 0.15s;}
.harness__input:focus{border-color:var(--h-accent);}
.harness__input--ta{resize:vertical;font-family:inherit;}
.harness__input--mono{font-family:'Consolas','Monaco',monospace;}
.harness__slider{width:100%;accent-color:var(--h-accent);}
.harness__panel-actions{margin-top:4px;}
.panel-slide-enter-active,.panel-slide-leave-active{transition:all .2s ease;}
.panel-slide-enter-from,.panel-slide-leave-to{transform:translateX(20px);opacity:0;}
:deep(.vue-flow__background){background:var(--h-canvas-bg);}
:deep(.vue-flow__controls){background:var(--h-bg-2);border:1px solid var(--h-border-2);border-radius:8px;overflow:hidden;}
:deep(.vue-flow__controls-button){background:var(--h-bg-2);border-color:var(--h-border-2);color:var(--h-text-3);}
:deep(.vue-flow__controls-button:hover){background:var(--h-bg-3);color:var(--h-text-2);}
:deep(.vue-flow__minimap){background:var(--h-bg-3);border:1px solid var(--h-border);border-radius:8px;}
</style>
