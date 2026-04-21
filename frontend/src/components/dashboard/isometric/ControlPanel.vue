<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useSceneState } from '../../../composables/useSceneState'
import type { EntityListItem } from '../../../types'
import type { RelationData } from '../../../api/relations'

const props = defineProps<{
  entities: EntityListItem[]
  relations: RelationData[]
}>()

const { selectedId, selectedType, deselect, setOverride, getOverride } = useSceneState()

const localLabel = ref('')
const localColor = ref('#4ade80')

const selectedEntity = computed(() => {
  if (selectedType.value !== 'entity' || !selectedId.value) return null
  const id = selectedId.value.replace('entity:', '')
  return props.entities.find(e => e.id === id) ?? null
})

const selectedRelation = computed(() => {
  if (selectedType.value !== 'capsule' || !selectedId.value) return null
  const id = selectedId.value.replace('capsule:', '')
  return props.relations.find(r => r.id === id) ?? null
})

const platformLabels: Record<string, string> = {
  'platform:analytics': 'ANALYTICS',
  'platform:workflows': 'WORKFLOWS',
  'platform:integrations': 'INTEGRATIONS',
  'platform:data': 'DATA',
  'platform:models': 'MODELS',
  'platform:ontology': 'ONTOLOGY',
  'action:btn': 'ACTION Button',
}

const displayTitle = computed(() => {
  if (selectedEntity.value) return selectedEntity.value.name_cn || selectedEntity.value.name
  if (selectedRelation.value) return selectedRelation.value.name
  if (selectedId.value && platformLabels[selectedId.value]) return platformLabels[selectedId.value]
  return '未选中'
})

const displayType = computed(() => {
  if (!selectedType.value) return '-'
  const map = { platform: '平台模块', capsule: '关系节点', entity: '业务实体' }
  return map[selectedType.value] ?? selectedType.value
})

watch(selectedId, (id) => {
  if (!id) return
  const override = getOverride(id)
  localLabel.value = override.label ?? ''
  localColor.value = override.color ?? '#4ade80'
})

function applyLabel() {
  if (selectedId.value && localLabel.value) {
    setOverride(selectedId.value, { label: localLabel.value })
  }
}

function applyColor() {
  if (selectedId.value) {
    setOverride(selectedId.value, { color: localColor.value })
  }
}
</script>

<template>
  <div class="ctrl-panel">
    <div class="ctrl-panel__header">
      <h3 class="ctrl-panel__title">属性面板</h3>
      <button v-if="selectedId" class="ctrl-panel__close" @click="deselect">✕</button>
    </div>

    <div v-if="!selectedId" class="ctrl-panel__empty">
      <p>点击 3D 场景中的任意元素查看和修改属性</p>
    </div>

    <template v-else>
      <div class="ctrl-panel__section">
        <span class="ctrl-panel__label">选中对象</span>
        <span class="ctrl-panel__value ctrl-panel__value--title">{{ displayTitle }}</span>
      </div>

      <div class="ctrl-panel__section">
        <span class="ctrl-panel__label">类型</span>
        <span class="ctrl-panel__badge">{{ displayType }}</span>
      </div>

      <!-- Entity details -->
      <template v-if="selectedEntity">
        <div class="ctrl-panel__section">
          <span class="ctrl-panel__label">层级</span>
          <span class="ctrl-panel__value">Tier {{ selectedEntity.tier }}</span>
        </div>
        <div class="ctrl-panel__grid">
          <div class="ctrl-panel__stat">
            <span class="ctrl-panel__stat-value">{{ selectedEntity.attr_count }}</span>
            <span class="ctrl-panel__stat-label">属性</span>
          </div>
          <div class="ctrl-panel__stat">
            <span class="ctrl-panel__stat-value">{{ selectedEntity.relation_count }}</span>
            <span class="ctrl-panel__stat-label">关系</span>
          </div>
          <div class="ctrl-panel__stat">
            <span class="ctrl-panel__stat-value">{{ selectedEntity.rule_count }}</span>
            <span class="ctrl-panel__stat-label">规则</span>
          </div>
        </div>
      </template>

      <!-- Relation details -->
      <template v-if="selectedRelation">
        <div class="ctrl-panel__section">
          <span class="ctrl-panel__label">来源</span>
          <span class="ctrl-panel__value">{{ selectedRelation.from_entity_name }}</span>
        </div>
        <div class="ctrl-panel__section">
          <span class="ctrl-panel__label">目标</span>
          <span class="ctrl-panel__value">{{ selectedRelation.to_entity_name }}</span>
        </div>
      </template>

      <!-- Editable fields -->
      <div class="ctrl-panel__divider"></div>
      <div class="ctrl-panel__section">
        <span class="ctrl-panel__label">修改标签</span>
        <div class="ctrl-panel__input-row">
          <input v-model="localLabel" class="ctrl-panel__input" placeholder="输入新标签..." />
          <button class="ctrl-panel__apply" @click="applyLabel">应用</button>
        </div>
      </div>

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
  letter-spacing: 0.02em;
}

.ctrl-panel__close {
  width: 24px;
  height: 24px;
  border: 1px solid var(--neutral-200);
  border-radius: 6px;
  background: var(--neutral-50);
  color: var(--neutral-600);
  font-size: var(--text-code-size);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
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
  line-height: 1.6;
  padding: 40px 20px;
}

.ctrl-panel__section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ctrl-panel__label {
  font-size: var(--text-caption-upper-size);
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--neutral-500);
  text-transform: uppercase;
}

.ctrl-panel__value {
  font-size: var(--text-body-size);
  color: var(--neutral-800);
}

.ctrl-panel__value--title {
  font-size: var(--text-h2-size);
  font-weight: 700;
  color: var(--neutral-900);
}

.ctrl-panel__badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--dynamic-50);
  color: var(--dynamic-900);
  font-size: var(--text-caption-size);
  font-weight: 600;
  width: fit-content;
}

.ctrl-panel__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.ctrl-panel__stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 8px;
  background: var(--neutral-50);
  border: 1px solid var(--neutral-100);
  border-radius: 8px;
}

.ctrl-panel__stat-value {
  font-size: var(--text-h2-size);
  font-weight: 700;
  color: var(--neutral-900);
}

.ctrl-panel__stat-label {
  font-size: var(--text-caption-upper-size);
  color: var(--neutral-500);
  margin-top: 2px;
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
  border-color: var(--dynamic-300);
  box-shadow: 0 0 0 2px rgba(74, 222, 128, 0.15);
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

.ctrl-panel__apply {
  padding: 7px 12px;
  border: none;
  border-radius: 6px;
  background: var(--neutral-950);
  color: var(--neutral-0);
  font-size: var(--text-caption-size);
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s;
}

.ctrl-panel__apply:hover {
  background: var(--neutral-800);
}
</style>
