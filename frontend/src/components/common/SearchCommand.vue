<template>
  <Teleport to="body">
    <Transition name="overlay">
      <div v-if="visible" class="search-command-overlay" @click.self="close">
        <div class="search-command-panel" role="dialog" aria-label="全局搜索">
          <!-- 输入区 -->
          <div class="search-command-input">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style="flex-shrink:0;color:var(--neutral-500)">
              <circle cx="7" cy="7" r="4.5" stroke="currentColor" stroke-width="1.5"/>
              <path d="M10.5 10.5l2.5 2.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
            <input
              ref="inputEl"
              v-model="query"
              placeholder="搜索对象、规则、动作..."
              @keydown="handleKeydown"
            />
            <kbd class="search-command-esc">ESC</kbd>
          </div>

          <!-- 结果列表 -->
          <div class="search-command-results" ref="resultsEl">
            <template v-if="results.length > 0">
              <div
                v-for="(item, i) in results"
                :key="item.id"
                class="search-command-item"
                :class="{ 'search-command-item--active': activeIndex === i }"
                @click="select(item)"
                @mouseenter="activeIndex = i"
              >
                <span class="search-command-item__icon" :class="`search-command-item__icon--${item.type}`">
                  {{ typeIcon[item.type] }}
                </span>
                <span class="search-command-item__name">{{ item.name }}</span>
                <span class="search-command-item__meta">{{ item.meta }}</span>
                <span class="search-command-item__type-tag" :class="`search-command-item__type-tag--${item.type}`">
                  {{ typeLabel[item.type] }}
                </span>
              </div>
            </template>
            <div v-else-if="query" class="search-command-empty">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <circle cx="11" cy="11" r="7" stroke="var(--neutral-300)" stroke-width="1.5"/>
                <path d="M16.5 16.5l3 3" stroke="var(--neutral-300)" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
              <span>未找到"{{ query }}"相关结果</span>
            </div>
            <div v-else class="search-command-hint">
              <p class="text-caption-upper" style="margin-bottom:8px;">快速跳转</p>
              <div v-for="s in shortcuts" :key="s.label" class="search-command-shortcut" @click="select(s)">
                <span class="search-command-item__icon" :class="`search-command-item__icon--${s.type}`">{{ typeIcon[s.type] }}</span>
                <span class="search-command-item__name">{{ s.name }}</span>
                <span class="search-command-item__meta">{{ s.meta }}</span>
              </div>
            </div>
          </div>

          <!-- 底部快捷键提示 -->
          <div class="search-command-footer">
            <span><kbd>↑↓</kbd> 导航</span>
            <span><kbd>↵</kbd> 选择</span>
            <span><kbd>ESC</kbd> 关闭</span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

interface SearchItem {
  id: string
  name: string
  meta: string
  type: 'object' | 'rule' | 'action' | 'relation'
  path?: string
}

const visible = ref(false)
const query = ref('')
const activeIndex = ref(0)
const inputEl = ref<HTMLInputElement>()
const resultsEl = ref<HTMLElement>()
const router = useRouter()

const typeLabel: Record<string, string> = {
  object: '对象', rule: '规则', action: '动作', relation: '关系'
}
const typeIcon: Record<string, string> = {
  object: '◈', rule: '⚡', action: '▶', relation: '↔'
}

const allItems: SearchItem[] = [
  { id: '1', name: 'Customer', meta: '核心对象 · Tier 1', type: 'object', path: '/ontology/customer' },
  { id: '2', name: 'FTTRSubscription', meta: '场景对象 · Tier 3', type: 'object', path: '/ontology/fttr-subscription' },
  { id: '3', name: 'CustomerSegment', meta: '领域对象 · Tier 2', type: 'object', path: '/ontology/customer-segment' },
  { id: '4', name: 'Campaign', meta: '领域对象 · Tier 2', type: 'object', path: '/ontology/campaign' },
  { id: '5', name: 'Product', meta: '核心对象 · Tier 1', type: 'object', path: '/ontology/product' },
  { id: '6', name: 'Order', meta: '核心对象 · Tier 1', type: 'object', path: '/ontology/order' },
  { id: '7', name: 'rule_007', meta: '续约风险规则', type: 'rule', path: '/ontology/rule-007' },
  { id: '8', name: 'churn_risk_rule', meta: '流失预警规则', type: 'rule', path: '/ontology/churn-risk' },
  { id: '9', name: 'exclusive_offer', meta: '专属优惠外呼', type: 'action', path: '/ontology/exclusive-offer' },
  { id: '10', name: 'has_subscription', meta: 'Customer → FTTRSubscription', type: 'relation', path: '/ontology/has-subscription' },
]

const shortcuts: SearchItem[] = allItems.slice(0, 4)

const results = computed(() => {
  if (!query.value.trim()) return []
  const q = query.value.toLowerCase()
  return allItems.filter(i =>
    i.name.toLowerCase().includes(q) || i.meta.toLowerCase().includes(q)
  ).slice(0, 8)
})

watch(results, () => { activeIndex.value = 0 })

function open() {
  visible.value = true
  query.value = ''
  activeIndex.value = 0
  nextTick(() => inputEl.value?.focus())
}

function close() {
  visible.value = false
}

function select(item: SearchItem) {
  if (item.path) router.push(item.path)
  close()
}

function handleKeydown(e: KeyboardEvent) {
  const list = results.value.length > 0 ? results.value : shortcuts
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    activeIndex.value = Math.min(activeIndex.value + 1, list.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    activeIndex.value = Math.max(activeIndex.value - 1, 0)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    if (list[activeIndex.value]) select(list[activeIndex.value])
  } else if (e.key === 'Escape') {
    close()
  }
}

function onGlobalKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    visible.value ? close() : open()
  }
}

onMounted(() => window.addEventListener('keydown', onGlobalKeydown))
onUnmounted(() => window.removeEventListener('keydown', onGlobalKeydown))

defineExpose({ open, close })
</script>

<style scoped>
.search-command-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 120px;
  z-index: 1000;
}

.search-command-panel {
  width: 560px;
  max-height: 480px;
  background: var(--neutral-0);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.search-command-input {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  height: 48px;
  border-bottom: 1px solid var(--neutral-200);
  flex-shrink: 0;
}
.search-command-input input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 15px;
  color: var(--neutral-900);
  background: transparent;
  font-family: var(--font-sans);
}
.search-command-input input::placeholder { color: var(--neutral-400); }

.search-command-esc {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--neutral-200);
  color: var(--neutral-500);
  background: var(--neutral-50);
  font-family: var(--font-mono);
}

.search-command-results {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.search-command-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background 80ms ease;
}
.search-command-item:hover,
.search-command-item--active {
  background: var(--semantic-50);
}
.search-command-item--active {
  border-left: 2px solid var(--semantic-500);
  padding-left: 10px;
}

.search-command-item__icon {
  width: 24px;
  height: 24px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  flex-shrink: 0;
}
.search-command-item__icon--object { background: var(--tier1-bg); color: var(--tier1-text); }
.search-command-item__icon--rule   { background: var(--kinetic-50); color: var(--kinetic-700); }
.search-command-item__icon--action { background: var(--dynamic-50); color: var(--dynamic-700); }
.search-command-item__icon--relation { background: var(--tier2-bg); color: var(--tier2-text); }

.search-command-item__name {
  font-size: 13px;
  font-weight: 500;
  color: var(--neutral-800);
  flex: 1;
}
.search-command-item__meta {
  font-size: 11px;
  color: var(--neutral-500);
}
.search-command-item__type-tag {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.search-command-item__type-tag--object   { background: var(--tier1-bg); color: var(--tier1-text); }
.search-command-item__type-tag--rule     { background: var(--kinetic-50); color: var(--kinetic-700); }
.search-command-item__type-tag--action   { background: var(--dynamic-50); color: var(--dynamic-700); }
.search-command-item__type-tag--relation { background: var(--tier2-bg); color: var(--tier2-text); }

.search-command-empty,
.search-command-hint {
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--neutral-500);
  font-size: 13px;
}
.search-command-hint {
  align-items: flex-start;
  padding: 12px 8px;
}
.search-command-shortcut {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  width: 100%;
  transition: background 80ms ease;
}
.search-command-shortcut:hover { background: var(--neutral-50); }

.search-command-footer {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 16px;
  border-top: 1px solid var(--neutral-200);
  font-size: 11px;
  color: var(--neutral-500);
  flex-shrink: 0;
}
.search-command-footer kbd {
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  border: 1px solid var(--neutral-200);
  background: var(--neutral-50);
  margin-right: 3px;
}

/* 过渡动画 */
.overlay-enter-active { animation: overlay-in 150ms ease-out; }
.overlay-leave-active { animation: overlay-in 100ms ease-in reverse; }
@keyframes overlay-in {
  from { opacity: 0; }
  to { opacity: 1; }
}
.overlay-enter-active .search-command-panel {
  animation: panel-in 200ms ease-out;
}
.overlay-leave-active .search-command-panel {
  animation: panel-in 150ms ease-in reverse;
}
@keyframes panel-in {
  from { opacity: 0; transform: scale(0.96) translateY(-8px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}
</style>
