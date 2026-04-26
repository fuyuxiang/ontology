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

      <!-- Modify display name -->
      <div class="ctrl-panel__section">
        <span class="ctrl-panel__label">显示名称</span>
        <input v-model="localLabel" class="ctrl-panel__input" placeholder="输入新名称..." @input="onLabelInput" />
      </div>

      <!-- Modify color -->
      <div class="ctrl-panel__section">
        <span class="ctrl-panel__label">修改颜色</span>
        <div class="ctrl-panel__input-row">
          <input v-model="localColor" type="color" class="ctrl-panel__color" @input="onColorInput" />
          <span class="ctrl-panel__color-hex">{{ localColor }}</span>
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

function onLabelInput() {
  if (localLabel.value) emit('override', 'label', localLabel.value)
}

function onColorInput() {
  emit('override', 'color', localColor.value)
}
</script>

<style scoped>
.ctrl-panel {
  width: 300px;
  height: 100%;
  background: var(--neutral-0);
  border-left: 1px solid var(--neutral-200);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  font-family: var(--font-sans);
}

.ctrl-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ctrl-panel__title {
  font-size: var(--text-body-size);
  font-weight: 700;
  color: var(--neutral-900);
  margin: 0;
}

.ctrl-panel__close {
  width: 28px;
  height: 28px;
  border: 1px solid var(--neutral-200);
  border-radius: 6px;
  background: var(--neutral-50);
  color: var(--neutral-600);
  font-size: var(--text-body-size);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}

.ctrl-panel__close:hover {
  background: var(--neutral-50);
  color: var(--neutral-900);
}

.ctrl-panel__empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--neutral-500);
  font-size: var(--text-body-size);
  padding: 20px;
}

.ctrl-panel__section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ctrl-panel__label {
  font-size: var(--text-caption-upper-size);
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--neutral-500);
}

.ctrl-panel__value {
  font-size: var(--text-body-size);
  font-weight: 600;
  color: var(--neutral-900);
}

.ctrl-panel__value--title {
  font-size: var(--text-h3-size);
}

.ctrl-panel__value--mono {
  font-family: var(--font-mono);
  font-size: var(--text-caption-size);
  color: var(--neutral-600);
}

.ctrl-panel__badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--semantic-50);
  color: var(--semantic-900);
  font-size: var(--text-caption-size);
  font-weight: 600;
  width: fit-content;
}

.ctrl-panel__divider {
  height: 1px;
  background: var(--neutral-50);
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
  border: 1px solid var(--neutral-200);
  border-radius: 6px;
  font-size: var(--text-code-size);
  color: var(--neutral-900);
  background: var(--neutral-50);
  outline: none;
}

.ctrl-panel__input:focus {
  border-color: var(--semantic-600);
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.15);
}

.ctrl-panel__color {
  width: 32px;
  height: 32px;
  border: 1px solid var(--neutral-200);
  border-radius: 6px;
  cursor: pointer;
  padding: 2px;
}

.ctrl-panel__color-hex {
  font-size: var(--text-caption-size);
  color: var(--neutral-600);
  font-family: var(--font-mono);
}
</style>