<template>
  <div class="user-stories-panel">
    <div class="usp-head">
      <div class="usp-title">📋 拆解的用户故事 <span class="usp-count">{{ confirmedCount }}/{{ stories.length }} 已确认</span></div>
    </div>
    <div class="usp-list">
      <div
        v-for="(s, idx) in stories"
        :key="s.id"
        class="us-card"
        :class="{ 'us-card--confirmed': s.confirmed, 'us-card--readonly': readonly }"
        @click="!readonly && $emit('toggle', s.id)"
      >
        <div class="us-no">故事 {{ idx + 1 }}</div>
        <div class="us-check">
          <svg v-if="s.confirmed" width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M3 7l3 3 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <div class="us-body">
          <div class="us-row"><span class="us-label">作为</span> {{ s.asRole }}</div>
          <div class="us-row"><span class="us-label">我想要</span> {{ s.iWant }}</div>
          <div class="us-row"><span class="us-label">以便</span> {{ s.soThat }}</div>
        </div>
        <div class="us-keywords">
          <span v-for="k in s.keywords" :key="k" class="us-keyword">{{ k }}</span>
        </div>
      </div>
    </div>
    <button
      v-if="!readonly"
      class="usp-confirm"
      :disabled="confirmedCount === 0"
      @click="$emit('confirm')"
    >
      确认 {{ confirmedCount }} 个故事，开始查找资产 →
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { UserStory } from '../../../../types/builder'

const props = defineProps<{ stories: UserStory[]; readonly?: boolean }>()
defineEmits<{ (e: 'toggle', id: string): void; (e: 'confirm'): void }>()
const confirmedCount = computed(() => props.stories.filter(s => s.confirmed).length)
</script>

<style scoped>
.user-stories-panel {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.05), rgba(139, 92, 246, 0.05));
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 12px;
  padding: 14px;
  margin-top: 4px;
}
.usp-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.usp-title { font-size: 13px; font-weight: 600; color: #1e293b; }
.usp-count { color: #4f46e5; font-weight: 500; margin-left: 6px; font-size: 12px; }

.usp-list { display: grid; gap: 10px; margin-bottom: 12px; }
.us-card {
  position: relative;
  padding: 12px 14px;
  border-radius: 10px;
  background: #fff;
  border: 1.5px solid #e2e8f0;
  cursor: pointer;
  transition: all 150ms ease;
}
.us-card:hover { border-color: #c7d2fe; }
.us-card--confirmed { border-color: #4f46e5; background: rgba(79, 70, 229, 0.04); }
.us-card--readonly { cursor: default; }
.us-no {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(99, 102, 241, 0.12);
  color: #4f46e5;
  font-size: 10px; font-weight: 600;
  margin-bottom: 6px;
}
.us-check {
  position: absolute; top: 12px; right: 12px;
  width: 20px; height: 20px; border-radius: 50%;
  border: 1.5px solid #cbd5e1;
  display: flex; align-items: center; justify-content: center;
  color: transparent;
  transition: all 150ms ease;
}
.us-card--confirmed .us-check {
  background: #4f46e5; border-color: #4f46e5; color: #fff;
}
.us-row { font-size: 12px; color: #334155; line-height: 1.7; }
.us-label {
  display: inline-block; min-width: 38px;
  color: #94a3b8; font-weight: 500; margin-right: 6px;
}
.us-keywords { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
.us-keyword {
  padding: 2px 8px; border-radius: 4px;
  background: #f1f5f9; color: #64748b;
  font-size: 10px;
}
.usp-confirm {
  width: 100%;
  padding: 10px;
  border: 0; border-radius: 10px;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  color: #fff;
  font-size: 13px; font-weight: 600;
  cursor: pointer;
  transition: all 150ms ease;
}
.usp-confirm:disabled { opacity: 0.5; cursor: not-allowed; }
.usp-confirm:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 16px -4px rgba(79, 70, 229, 0.4); }
</style>
