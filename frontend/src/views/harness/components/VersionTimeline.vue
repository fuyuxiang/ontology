<template>
  <div class="vt">
    <div class="vt__line"></div>
    <div v-for="(item, i) in timeline" :key="i" class="vt__item">
      <div class="vt__dot" :class="{ 'vt__dot--current': item.status === 'current', 'vt__dot--done': item.status === 'done' }">
        <CheckCircleOutlined v-if="item.status === 'done'" :style="{ fontSize: '8px', color: '#52c41a' }" />
        <SyncOutlined v-else-if="item.status === 'current'" spin :style="{ fontSize: '8px', color: '#1677ff' }" />
      </div>
      <div class="vt__head">
        <a-typography-text strong :style="{ fontSize: '14px', color: item.status === 'current' ? '#1677ff' : item.status === 'done' ? '#333' : '#bbb' }">
          {{ item.version }}
        </a-typography-text>
        <a-typography-text type="secondary" style="font-size:11px">{{ item.date }}</a-typography-text>
        <a-tag v-if="item.status === 'current'" color="blue" :style="{ fontSize: '10px', margin: 0 }">当前</a-tag>
      </div>
      <a-typography-text :style="{ fontSize: '12px', color: item.status === 'done' || item.status === 'current' ? '#666' : '#bbb' }">
        {{ item.changes }}
      </a-typography-text>
    </div>
  </div>
</template>

<script setup lang="ts">
import { CheckCircleOutlined, SyncOutlined } from '@ant-design/icons-vue'

defineProps<{
  timeline: Array<{ version: string; date: string; changes: string; status: string }>
}>()
</script>

<style scoped>
.vt { position: relative; padding-left: 24px; }
.vt__line { position: absolute; left: 8px; top: 8px; bottom: 8px; width: 2px; background: #f0f0f0; }
.vt__item { position: relative; margin-bottom: 18px; padding-left: 12px; }
.vt__dot {
  position: absolute; left: -20px; top: 4px;
  width: 14px; height: 14px; border-radius: 50%;
  background: white; border: 2px solid #d9d9d9;
  display: flex; align-items: center; justify-content: center;
}
.vt__dot--done { border-color: #52c41a; }
.vt__dot--current { background: #e6f4ff; border-color: #1677ff; }
.vt__head { display: flex; align-items: center; gap: 8px; }
</style>
