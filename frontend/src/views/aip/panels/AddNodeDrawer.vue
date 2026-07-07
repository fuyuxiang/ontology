<template>
  <transition name="and-drawer">
    <div v-if="open" class="and-wrap" @click.self="$emit('close')">
      <div class="and">
        <!-- Header -->
        <div class="and__head">
          <div class="and__title-row">
            <svg class="and__plus" width="14" height="14" viewBox="0 0 16 16" fill="none">
              <path d="M8 3v10M3 8h10" stroke="#2E5BFF" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
            <span class="and__title">添加节点</span>
            <button class="and__close" @click="$emit('close')" title="关闭">
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                <path d="M3 3l10 10M13 3L3 13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
            </button>
          </div>
          <div class="and__sub">拖入画布或点击添加节点到工作流</div>
          <div class="and__search">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
              <circle cx="7" cy="7" r="5" stroke="#c0c4cc" stroke-width="1.5"/>
              <path d="M11 11l3 3" stroke="#c0c4cc" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
            <input v-model="keyword" placeholder="搜索节点..." />
            <button v-if="keyword" class="and__clear" @click="keyword = ''" title="清空">
              <svg width="10" height="10" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="7" fill="#cbd5e1"/>
                <path d="M5 5l6 6M11 5l-6 6" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- Body -->
        <div class="and__body">
          <div v-for="g in groups" :key="g.label" class="and__group">
            <div class="and__group-label" :style="{ color: g.color, borderLeftColor: g.color }">
              {{ g.label }}
            </div>
            <div class="and__group-nodes">
              <div v-for="n in g.nodes" :key="n.type + '_' + n.label"
                class="and__node"
                draggable="true"
                @dragstart="onDragStart($event, n)"
                @click="onAddClick(n)"
                :style="nodeStyle(g.color)"
                @mouseenter="onHover($event, g.color, true)"
                @mouseleave="onHover($event, g.color, false)">
                <span class="and__node-icon" :style="{ color: g.color }" v-html="iconSvg(n.icon)"></span>
                <div class="and__node-text">
                  <div class="and__node-label">{{ n.label }}</div>
                  <div class="and__node-desc">{{ n.description }}</div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="!groups.length" class="and__empty">
            没有匹配的节点
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAipStore } from '../../../store/aip'

interface NodeItem {
  type: string
  label: string
  description: string
  icon: string
}

defineProps<{ open: boolean }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'pick', n: NodeItem): void
}>()

const store = useAipStore()
const keyword = ref('')

// 分组色 + 节点信息（与原版一致：每个 group 有自身配色）
const RAW_GROUPS: Array<{ label: string; color: string; nodes: NodeItem[] }> = [
  { label: '数据节点', color: '#2E5BFF', nodes: [
    { type: 'ontologyQuery', label: '本体查询', icon: 'database', description: '查询本体对象实例' },
  ] },
  { label: '逻辑节点', color: '#FF8900', nodes: [
    { type: 'llmAgent', label: '模型节点', icon: 'brain', description: 'AI 智能推理' },
  ] },
  { label: '本体组件', color: '#0D9488', nodes: [
    { type: 'functionCall', label: '函数调用', icon: 'tool', description: '调用已发布的本体函数，返回计算结果' },
    { type: 'actionExecute', label: '行动执行', icon: 'send', description: '执行已发布的行动（API调用/通知/写回等）' },
  ] },
  { label: 'Agent 节点', color: '#10B981', nodes: [
    { type: 'agentNode', label: 'Agent 节点', icon: 'robot', description: '挂多个 Skill / Memory / Tool 子节点' },
  ] },
  { label: 'Skill 子节点', color: '#10B981', nodes: [
    { type: 'skillNode', label: 'Skill 节点', icon: 'thunder', description: '关联 Skill 注册表中的 Skill' },
  ] },
  { label: 'Memory 子节点', color: '#7C3AED', nodes: [
    { type: 'memoryNode', label: 'Memory 节点', icon: 'memory', description: 'Working / Episodic / Semantic / Procedural 任一层' },
  ] },
  { label: 'Action 子节点', color: '#0EA5E9', nodes: [
    { type: 'toolNode', label: 'Action 节点', icon: 'tool', description: 'OntologyEngine / MLModel / LLM / KnowledgeGrowth 等 Tool' },
  ] },
  { label: 'Function 节点', color: '#0EA5E9', nodes: [
    { type: 'function', label: '函数计算', icon: 'tool', description: '调用 OntologyFunction（表达式 / SQL / Python 计算）' },
    { type: 'writebackOntology', label: 'Function (写回)', icon: 'save', description: 'Stateless 写回节点（如 ⑤ 结果输出）' },
  ] },
  { label: '动作节点', color: '#059669', nodes: [
    { type: 'writebackOntology', label: '写回本体', icon: 'save', description: '写回本体对象（按字段映射）' },
    { type: 'actionSystem', label: '动作执行', icon: 'send', description: '调用 EntityAction（短信 / 推送 / 工单 / API）' },
  ] },
  { label: '编排节点', color: '#7C3AED', nodes: [
    { type: 'subscene', label: '子场景调用', icon: 'robot', description: '嵌套执行另一个 AIP 场景' },
  ] },
  { label: '控制节点', color: '#64748B', nodes: [
    { type: 'condition', label: '条件分支', icon: 'branch', description: '条件判断分流（==/!=/IN/BETWEEN）' },
  ] },
]

const groups = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return RAW_GROUPS
  return RAW_GROUPS
    .map(g => ({ ...g, nodes: g.nodes.filter(n =>
      n.label.toLowerCase().includes(kw) ||
      n.description.toLowerCase().includes(kw) ||
      n.type.toLowerCase().includes(kw)
    ) }))
    .filter(g => g.nodes.length > 0)
})

function nodeStyle(color: string) {
  return {
    border: `1px solid ${color}33`,
  }
}

function onHover(e: MouseEvent, color: string, hover: boolean) {
  const el = e.currentTarget as HTMLElement
  if (hover) {
    el.style.boxShadow = `0 2px 8px ${color}40`
    el.style.borderColor = `${color}80`
    el.style.transform = 'translateY(-1px)'
  } else {
    el.style.boxShadow = 'none'
    el.style.borderColor = `${color}33`
    el.style.transform = 'none'
  }
}

function onDragStart(e: DragEvent, n: NodeItem) {
  if (!e.dataTransfer) return
  e.dataTransfer.setData('application/aip-node', n.type)
  e.dataTransfer.setData('application/aip-label', n.label)
  e.dataTransfer.effectAllowed = 'move'
}

function onAddClick(n: NodeItem) {
  const id = `${n.type}_${Date.now()}`
  store.addNode({
    id,
    type: n.type,
    position: { x: 250 + Math.random() * 200, y: 150 + Math.random() * 200 },
    data: { label: n.label, description: n.description, status: 'idle' },
  })
  emit('pick', n)
  emit('close')
}

function iconSvg(name: string) {
  const map: Record<string, string> = {
    database: '<svg width="15" height="15" viewBox="0 0 16 16" fill="none"><ellipse cx="8" cy="3.5" rx="5" ry="1.8" stroke="currentColor" stroke-width="1.4"/><path d="M3 3.5v9c0 1 2.2 1.8 5 1.8s5-.8 5-1.8v-9M3 8c0 1 2.2 1.8 5 1.8s5-.8 5-1.8" stroke="currentColor" stroke-width="1.4"/></svg>',
    filter: '<svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="M2 3h12l-4.5 5v5L7 11.5V8L2 3z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>',
    brain: '<svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="M5 3a2.5 2.5 0 015 0 2.5 2.5 0 012.5 2.5v5A2.5 2.5 0 0110 13a2.5 2.5 0 01-5 0 2.5 2.5 0 01-2.5-2.5v-5A2.5 2.5 0 015 3z" stroke="currentColor" stroke-width="1.3"/><path d="M7.5 5v6M5 7h2.5M7.5 9H10" stroke="currentColor" stroke-width="1.2"/></svg>',
    robot: '<svg width="15" height="15" viewBox="0 0 16 16" fill="none"><rect x="3" y="5" width="10" height="8" rx="1.2" stroke="currentColor" stroke-width="1.4"/><path d="M8 5V2.5M6.5 2.5h3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><circle cx="6" cy="9" r="1" fill="currentColor"/><circle cx="10" cy="9" r="1" fill="currentColor"/></svg>',
    thunder: '<svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="M9 2L3 9h4l-1 6 6-8H8l1-5z" fill="currentColor"/></svg>',
    memory: '<svg width="15" height="15" viewBox="0 0 16 16" fill="none"><rect x="2.5" y="4" width="11" height="8" rx="1" stroke="currentColor" stroke-width="1.4"/><path d="M5 4v8M8 4v8M11 4v8" stroke="currentColor" stroke-width="1"/></svg>',
    tool: '<svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="M11.5 2.5l-2 2 2 2 2-2-2-2zM10 4L4 10l2 2 6-6M3 11l2 2-1.5 1.5L2 13l1-2z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/></svg>',
    save: '<svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="M3 2.5h8l3 3V13a.5.5 0 01-.5.5h-11A.5.5 0 012 13V3a.5.5 0 01.5-.5z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/><path d="M5 2.5v4h6v-4M5 9h6v4.5H5V9z" stroke="currentColor" stroke-width="1.2"/></svg>',
    send: '<svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="M14 2L2 7l5 2 2 5 5-12z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/></svg>',
    branch: '<svg width="15" height="15" viewBox="0 0 16 16" fill="none"><circle cx="4" cy="3" r="1.5" stroke="currentColor" stroke-width="1.3"/><circle cx="4" cy="13" r="1.5" stroke="currentColor" stroke-width="1.3"/><circle cx="12" cy="8" r="1.5" stroke="currentColor" stroke-width="1.3"/><path d="M4 4.5v7M5.5 13c2 0 5-2 5-3.5" stroke="currentColor" stroke-width="1.3" fill="none"/></svg>',
  }
  return map[name] || map.tool
}
</script>

<style scoped>
.and-wrap {
  position: absolute; top: 0; right: 0; bottom: 0; left: 0;
  pointer-events: none;
  z-index: 30;
}
.and {
  position: absolute; top: 0; right: 0; bottom: 0;
  width: 380px;
  background: #fff;
  box-shadow: -6px 0 20px rgba(15, 23, 42, .08);
  border-left: 1px solid #f0f0f0;
  display: flex; flex-direction: column;
  pointer-events: auto;
  overflow: hidden;
}
.and-drawer-enter-active, .and-drawer-leave-active { transition: opacity .2s; }
.and-drawer-enter-active .and, .and-drawer-leave-active .and { transition: transform .25s ease; }
.and-drawer-enter-from .and, .and-drawer-leave-to .and { transform: translateX(100%); }
.and-drawer-enter-from, .and-drawer-leave-to { opacity: 0; }

/* ===== Header ===== */
.and__head {
  padding: 18px 22px 14px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}
.and__title-row { display: flex; align-items: center; gap: 8px; }
.and__plus { flex-shrink: 0; }
.and__title { font-size: 15px; font-weight: 700; color: #1a1a2e; flex: 1; }
.and__close {
  width: 22px; height: 22px;
  border: none; background: transparent;
  color: #94a3b8; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  border-radius: 4px;
}
.and__close:hover { background: #f1f5f9; color: #475569; }

.and__sub { font-size: 12px; color: #94a3b8; line-height: 18px; margin-top: 4px; }

.and__search {
  display: flex; align-items: center; gap: 6px;
  margin-top: 12px; padding: 6px 10px;
  background: #f8f9fa; border: 1px solid #e5e7eb; border-radius: 8px;
  transition: border-color .15s;
}
.and__search:focus-within { border-color: #2E5BFF; background: #fff; }
.and__search input {
  flex: 1; border: none; outline: none; background: transparent;
  font-size: 12px; color: #1a1a2e;
}
.and__search input::placeholder { color: #c0c4cc; }
.and__clear { border: none; background: transparent; cursor: pointer; padding: 0; display: flex; }

/* ===== Body ===== */
.and__body {
  flex: 1; overflow-y: auto;
  padding: 8px 12px 16px;
}
.and__group { margin-bottom: 14px; }
.and__group-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 5px 8px;
  border-left: 3px solid;
  margin-bottom: 6px;
}
.and__group-nodes { display: flex; flex-direction: column; gap: 4px; }

.and__node {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  background: #fff;
  cursor: grab;
  transition: box-shadow .2s, border-color .2s, transform .15s;
}
.and__node:active { cursor: grabbing; }
.and__node-icon {
  width: 22px; height: 22px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.and__node-text { flex: 1; min-width: 0; }
.and__node-label {
  font-size: 12px; font-weight: 500; color: #1a1a2e;
  line-height: 18px;
}
.and__node-desc {
  font-size: 10px; color: #94a3b8; line-height: 14px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.and__empty {
  padding: 40px 0; text-align: center;
  color: #cbd5e1; font-size: 12px;
}
</style>
