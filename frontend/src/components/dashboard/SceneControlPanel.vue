<template>
  <div class="ctrl-panel">
    <div class="ctrl-panel__header">
      <h3 class="ctrl-panel__title">属性面板</h3>
      <button v-if="data" class="ctrl-panel__close" @click="$emit('deselect')">✕</button>
    </div>

    <div v-if="!data" class="ctrl-panel__empty">
      <p>点击 3D 场景中的任意元素查看和修改属性</p>
    </div>

    <template v-else>
      <div class="ctrl-panel__section">
        <span class="ctrl-panel__label">选中对象</span>
        <span class="ctrl-panel__value ctrl-panel__value--title">{{ data.label }}</span>
      </div>

      <div class="ctrl-panel__section">
        <span class="ctrl-panel__label">类型</span>
        <span class="ctrl-panel__badge">{{ typeLabel }}</span>
      </div>

      <div class="ctrl-panel__section">
        <span class="ctrl-panel__label">ID</span>
        <span class="ctrl-panel__value ctrl-panel__value--mono">{{ data.id }}</span>
      </div>

      <div class="ctrl-panel__divider"></div>

      <!-- Modify label -->
      <div class="ctrl-panel__section">
        <span class="ctrl-panel__label">修改标签</span>
        <div class="ctrl-panel__input-row">
          <input v-model="localLabel" class="ctrl-panel__input" placeholder="输入新标签..." />
          <button class="ctrl-panel__apply" @click="applyLabel">应用</button>
        </div>
      </div>

      <!-- Modify color -->
      <div class="ctrl-panel__section">
        <span class="ctrl-panel__label">修改颜色</span>
        <div class="ctrl-panel__input-row">
          <input v-model="localColor" type="color" class="ctrl-panel__color" />
          <span class="ctrl-panel__color-hex">{{ localColor }}</span>
          <button class="ctrl-panel__apply" @click="applyColor">应用</button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { SceneSelection } from '../../composables/useSceneInteraction'

const props = defineProps<{
  data: SceneSelection | null
}>()

const emit = defineEmits<{
  deselect: []
  override: [field: string, value: string | number]
}>()

const localLabel = ref('')
const localColor = ref('#ffffff')

const typeMap: Record<string, string> = {
  platform: '平台模块',
  capsule: '关系节点',
  entity: '业务实体',
}

const typeLabel = computed(() => typeMap[props.data?.type ?? ''] ?? props.data?.type ?? '-')

watch(() => props.data, (d) => {
  if (d) {
    localLabel.value = d.label
    localColor.value = d.color
  }
})

function applyLabel() {
  if (localLabel.value) emit('override', 'label', localLabel.value)
}

function applyColor() {
  emit('override', 'color', localColor.value)
}
</script>

<style scoped>
.ctrl-panel {
  width: 300px;
  height: 100%;
  background: #ffffff;
  border-left: 1px solid #e5e5e5;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  font-family: 'Inter', system-ui, sans-serif;
}

.ctrl-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ctrl-panel__title {
  font-size: 14px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0;
}

.ctrl-panel__close {
  width: 28px;
  height: 28px;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  background: #fafafa;
  color: #71717a;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}

.ctrl-panel__close:hover {
  background: #f4f4f5;
  color: #1a1a1a;
}

.ctrl-panel__empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #a1a1aa;
  font-size: 13px;
  padding: 20px;
}

.ctrl-panel__section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ctrl-panel__label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #a1a1aa;
}

.ctrl-panel__value {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
}

.ctrl-panel__value--title {
  font-size: 16px;
}

.ctrl-panel__value--mono {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #71717a;
}

.ctrl-panel__badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 999px;
  background: #f0fdf4;
  color: #166534;
  font-size: 11px;
  font-weight: 600;
  width: fit-content;
}

.ctrl-panel__divider {
  height: 1px;
  background: #f4f4f5;
  margin: 4px 0;
}

.ctrl-panel__input-row {
  display: flex;
  gap: 6px;
  align-items: center;
}

.ctrl-panel__input {
  flex: 1;
  padding: 7px 10px;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  font-size: 12px;
  color: #1a1a1a;
  background: #fafafa;
  outline: none;
}

.ctrl-panel__input:focus {
  border-color: #4ade80;
  box-shadow: 0 0 0 2px rgba(74, 222, 128, 0.15);
}

.ctrl-panel__color {
  width: 32px;
  height: 32px;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  cursor: pointer;
  padding: 2px;
}

.ctrl-panel__color-hex {
  font-size: 11px;
  color: #71717a;
  font-family: 'JetBrains Mono', monospace;
}

.ctrl-panel__apply {
  padding: 7px 12px;
  border: none;
  border-radius: 6px;
  background: #1a1a1a;
  color: #ffffff;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s;
}

.ctrl-panel__apply:hover {
  background: #3f3f46;
}
</style>