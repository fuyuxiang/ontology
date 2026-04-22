<template>
  <div class="canvas-toolbar">
    <div class="canvas-toolbar__search-group">
      <label class="toolbar-search">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" class="toolbar-search__icon">
          <circle cx="6" cy="6" r="4" stroke="currentColor" stroke-width="1.5"/>
          <path d="M9 9l2.5 2.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        <input
          :value="searchQuery"
          type="text"
          placeholder="搜索实体..."
          class="toolbar-search__input"
          @input="$emit('update:searchQuery', ($event.target as HTMLInputElement).value)"
        />
      </label>

      <div class="toolbar-tier-group">
        <button
          type="button"
          class="toolbar-tier-btn"
          :class="{ 'toolbar-tier-btn--active': activeTier === null }"
          @click="$emit('tierFilter', null)"
        >
          全部
        </button>
        <button
          v-for="item in tierCards"
          :key="item.tier"
          type="button"
          class="toolbar-tier-btn"
          :class="[
            `toolbar-tier-btn--tier${item.tier}`,
            { 'toolbar-tier-btn--active': activeTier === item.tier },
          ]"
          @click="$emit('tierFilter', item.tier)"
        >
          T{{ item.tier }}
          <span class="toolbar-tier-btn__count">{{ item.count }}</span>
        </button>
      </div>
    </div>

    <div class="canvas-toolbar__controls">
      <button class="toolbar-btn" title="重新计算布局" @click="$emit('layout')">
        <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
          <rect x="1.25" y="1.25" width="5.5" height="5.5" rx="1.1" stroke="currentColor" stroke-width="1.4"/>
          <rect x="9.25" y="1.25" width="5.5" height="5.5" rx="1.1" stroke="currentColor" stroke-width="1.4"/>
          <rect x="5.25" y="9.25" width="5.5" height="5.5" rx="1.1" stroke="currentColor" stroke-width="1.4"/>
          <path d="M4 6.75v1.8a1 1 0 001 1h2.4m4.6-2.8v1.8a1 1 0 01-1 1H8.6" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
        </svg>
        重排
      </button>

      <button class="toolbar-btn" title="适应画布" @click="$emit('fit')">
        <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
          <path d="M1.5 5V2.4a.9.9 0 01.9-.9H5M11 1.5h2.6a.9.9 0 01.9.9V5M14.5 11v2.6a.9.9 0 01-.9.9H11M5 14.5H2.4a.9.9 0 01-.9-.9V11" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
        </svg>
        适应
      </button>

      <div class="toolbar-segment">
        <button class="toolbar-segment__btn" :class="{ 'toolbar-segment__btn--active': direction === 'LR' }" @click="$emit('direction', 'LR')">横向</button>
        <button class="toolbar-segment__btn" :class="{ 'toolbar-segment__btn--active': direction === 'TB' }" @click="$emit('direction', 'TB')">纵向</button>
      </div>
    </div>

    <div class="canvas-toolbar__stats">
      <span class="toolbar-pill">{{ nodeCount }} 对象</span>
      <span class="toolbar-pill">{{ edgeCount }} 关系</span>
      <button v-if="hasFilters" class="toolbar-clear" @click="$emit('clear')">清空筛选</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Tier } from '../../types'

defineProps<{
  direction: 'LR' | 'TB'
  nodeCount: number
  edgeCount: number
  totalNodeCount: number
  hasFilters?: boolean
  searchQuery: string
  activeTier: Tier | null
  tierCards: { tier: Tier; count: number }[]
}>()

defineEmits<{
  layout: []
  fit: []
  direction: [d: 'LR' | 'TB']
  clear: []
  'update:searchQuery': [value: string]
  tierFilter: [tier: Tier | null]
}>()
</script>

<style scoped>
.canvas-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border: 1px solid rgba(208, 217, 229, 0.86);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 8px 24px -16px rgba(33, 53, 88, 0.18);
  backdrop-filter: blur(16px);
  flex-shrink: 0;
  flex-wrap: wrap;
}

.canvas-toolbar__search-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.toolbar-search {
  position: relative;
  display: block;
  min-width: 140px;
  max-width: 220px;
}

.toolbar-search__icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--neutral-500);
}

.toolbar-search__input {
  width: 100%;
  padding: 7px 10px 7px 30px;
  border-radius: 10px;
  border: 1px solid rgba(212, 220, 232, 0.92);
  background: rgba(247, 249, 252, 0.92);
  font-size: 12px;
  color: var(--neutral-800);
  outline: none;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.toolbar-search__input:focus {
  border-color: rgba(76, 110, 245, 0.45);
  background: #fff;
  box-shadow: 0 0 0 3px rgba(76, 110, 245, 0.08);
}

.toolbar-tier-group {
  display: flex;
  align-items: center;
  gap: 4px;
}

.toolbar-tier-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(216, 223, 234, 0.9);
  background: #fff;
  color: var(--neutral-600);
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.toolbar-tier-btn:hover {
  border-color: rgba(181, 192, 210, 0.92);
  background: rgba(247, 249, 252, 0.95);
}

.toolbar-tier-btn--active {
  background: var(--neutral-800);
  color: #fff;
  border-color: var(--neutral-800);
}

.toolbar-tier-btn--tier1.toolbar-tier-btn--active {
  background: #4c6ef5;
  border-color: #4c6ef5;
}

.toolbar-tier-btn--tier2.toolbar-tier-btn--active {
  background: #7950f2;
  border-color: #7950f2;
}

.toolbar-tier-btn--tier3.toolbar-tier-btn--active {
  background: #20c997;
  border-color: #20c997;
}

.toolbar-tier-btn__count {
  font-size: 10px;
  opacity: 0.75;
}

.canvas-toolbar__controls {
  display: flex;
  align-items: center;
  gap: 6px;
}

.toolbar-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 7px 10px;
  border-radius: 10px;
  border: 1px solid rgba(216, 223, 234, 0.92);
  background: rgba(247, 249, 252, 0.92);
  color: var(--neutral-700);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast), border-color var(--transition-fast);
}

.toolbar-btn:hover {
  transform: translateY(-1px);
  border-color: rgba(181, 192, 210, 0.92);
  box-shadow: var(--shadow-sm);
}

.toolbar-segment {
  display: inline-flex;
  align-items: center;
  padding: 2px;
  border-radius: 999px;
  background: rgba(243, 246, 250, 0.95);
  border: 1px solid rgba(216, 223, 234, 0.92);
}

.toolbar-segment__btn {
  padding: 6px 10px;
  border: none;
  background: transparent;
  color: var(--neutral-600);
  font-size: 11px;
  font-weight: 700;
  border-radius: 999px;
  cursor: pointer;
}

.toolbar-segment__btn--active {
  background: #fff;
  color: var(--semantic-700);
  box-shadow: 0 2px 8px -4px rgba(33, 53, 88, 0.25);
}

.canvas-toolbar__stats {
  display: flex;
  align-items: center;
  gap: 6px;
}

.toolbar-pill {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(247, 249, 252, 0.92);
  border: 1px solid rgba(221, 228, 237, 0.94);
  color: var(--neutral-600);
  font-size: 11px;
  font-weight: 700;
}

.toolbar-clear {
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(76, 110, 245, 0.24);
  background: rgba(238, 242, 255, 0.92);
  color: var(--semantic-700);
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

@media (max-width: 900px) {
  .canvas-toolbar {
    gap: 8px;
  }

  .canvas-toolbar__search-group {
    flex-basis: 100%;
  }
}
</style>
