<template>
  <div class="user-stories-panel">
    <div class="us-header">
      <div class="us-title">📋 已识别 {{ stories.length }} 个用户故事</div>
      <div class="us-count">{{ confirmedCount }}/{{ stories.length }} 已确认</div>
    </div>
    <div class="us-list">
      <div
        v-for="(s, idx) in stories"
        :key="s.id"
        :class="['us-card', { confirmed: s.confirmed }]"
        @click="!readonly && $emit('toggle', s.id)"
      >
        <div class="us-card-top">
          <span class="us-card-num">故事 {{ idx + 1 }}</span>
          <span class="us-check-circle" :style="s.confirmed ? { background: '#10b981', borderColor: '#10b981' } : {}"></span>
        </div>
        <div class="us-card-body">
          <div class="us-line"><span class="us-label">作为</span><span class="us-value">{{ s.asRole }}</span></div>
          <div class="us-line"><span class="us-label">我想要</span><span class="us-value">{{ s.iWant }}</span></div>
          <div class="us-line"><span class="us-label">以便</span><span class="us-value">{{ s.soThat }}</span></div>
        </div>
        <div class="us-keywords">
          <span v-for="k in s.keywords" :key="k" class="us-keyword">{{ k }}</span>
        </div>
      </div>
    </div>
    <button
      v-if="!readonly"
      :class="['us-confirm-all-btn', { ready: allConfirmed }]"
      :disabled="confirmedCount === 0"
      @click="$emit('confirm')"
    >
      {{ allConfirmed ? `确认 ${stories.length} 个故事，开始查找资产 →` : `已确认 ${confirmedCount}/${stories.length}，全部确认后开始查找资产` }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { UserStory } from '../../../../types/builder'

const props = defineProps<{ stories: UserStory[]; readonly?: boolean }>()
defineEmits<{ (e: 'toggle', id: string): void; (e: 'confirm'): void }>()
const confirmedCount = computed(() => props.stories.filter(s => s.confirmed).length)
const allConfirmed = computed(() => props.stories.length > 0 && confirmedCount.value === props.stories.length)
</script>
