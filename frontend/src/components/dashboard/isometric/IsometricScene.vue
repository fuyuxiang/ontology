<template>
  <div class="iso-scene">
    <div class="iso-scene__perspective">
      <!-- Top Layer: Analytics / Workflows / Integrations -->
      <div
        class="iso-layer iso-layer--top"
        :class="{ 'iso-layer--active': activeStage === 'wield', 'iso-layer--dim': activeStage === 'hydrate' }"
      >
        <div class="iso-layer__platform iso-layer__platform--top">
          <div class="iso-layer__label">APPLICATION LAYER</div>
          <div class="iso-layer__modules">
            <button
              v-for="mod in topModules"
              :key="mod.key"
              type="button"
              class="iso-module"
              :class="[
                `iso-module--${mod.tone}`,
                { 'iso-module--selected': selectedKey === mod.key },
              ]"
              @click="$emit('selectTarget', mod.key)"
            >
              <span class="iso-module__icon" v-html="moduleIcon(mod.key)"></span>
              <span class="iso-module__eyebrow">{{ mod.title }}</span>
              <strong class="iso-module__title">{{ mod.label }}</strong>
              <span class="iso-module__metric">{{ mod.metric }} {{ mod.metricLabel }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Flow lines: Middle → Top -->
      <div class="iso-flow iso-flow--upper" :class="{ 'iso-flow--active': activeStage === 'wield' }">
        <svg class="iso-flow__svg" viewBox="0 0 400 60" preserveAspectRatio="none">
          <line v-for="i in 7" :key="`up-${i}`" class="flow-line"
            :x1="30 + (i - 1) * 55" y1="58" :x2="30 + (i - 1) * 55" y2="2" />
        </svg>
        <div v-for="i in 5" :key="`particle-up-${i}`" class="flow-particle flow-particle--up"
          :style="{ left: `${10 + (i - 1) * 20}%`, animationDelay: `${i * 0.35}s` }"></div>
      </div>

      <!-- Middle Layer: Ontology -->
      <div
        class="iso-layer iso-layer--middle"
        :class="{ 'iso-layer--active': activeStage === 'activate', 'iso-layer--glow': activeStage === 'activate' }"
      >
        <div class="iso-layer__platform iso-layer__platform--middle">
          <div class="iso-layer__label">ONTOLOGY</div>
          <div class="iso-layer__ontology-wrap">
            <OntologyNetwork
              :entities="entities"
              :relations="relations"
              :activeStage="activeStage"
              :selectedKey="selectedKey"
              @select="$emit('selectTarget', $event)"
            />
            <AssetDetailCard
              :entity="selectedEntity"
              :visible="activeStage === 'activate' && !!selectedEntity"
            />
          </div>
        </div>
      </div>

      <!-- Flow lines: Bottom → Middle -->
      <div class="iso-flow iso-flow--lower" :class="{ 'iso-flow--active': activeStage === 'hydrate' }">
        <svg class="iso-flow__svg" viewBox="0 0 400 60" preserveAspectRatio="none">
          <line v-for="i in 7" :key="`down-${i}`" class="flow-line"
            :x1="30 + (i - 1) * 55" y1="58" :x2="30 + (i - 1) * 55" y2="2" />
        </svg>
        <div v-for="i in 5" :key="`particle-down-${i}`" class="flow-particle flow-particle--up"
          :style="{ left: `${10 + (i - 1) * 20}%`, animationDelay: `${i * 0.3}s` }"></div>
      </div>

      <!-- Bottom Layer: Data / Models -->
      <div
        class="iso-layer iso-layer--bottom"
        :class="{ 'iso-layer--active': activeStage === 'hydrate', 'iso-layer--dim': activeStage === 'wield' }"
      >
        <div class="iso-layer__platform iso-layer__platform--bottom">
          <div class="iso-layer__label">FOUNDATION LAYER</div>
          <div class="iso-layer__modules iso-layer__modules--bottom">
            <button
              v-for="mod in bottomModules"
              :key="mod.key"
              type="button"
              class="iso-module"
              :class="[
                `iso-module--${mod.tone}`,
                { 'iso-module--selected': selectedKey === mod.key },
              ]"
              @click="$emit('selectTarget', mod.key)"
            >
              <span class="iso-module__icon" v-html="moduleIcon(mod.key)"></span>
              <span class="iso-module__eyebrow">{{ mod.title }}</span>
              <strong class="iso-module__title">{{ mod.label }}</strong>
              <span class="iso-module__metric">{{ mod.metric }} {{ mod.metricLabel }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import OntologyNetwork from './OntologyNetwork.vue'
import AssetDetailCard from './AssetDetailCard.vue'
import type { EntityListItem } from '../../../types'
import type { RelationData } from '../../../api/relations'

type StageId = 'hydrate' | 'activate' | 'wield'

interface ModuleCard {
  key: string
  title: string
  label: string
  metric: string
  metricLabel: string
  tone: string
  placement: 'top' | 'bottom'
  [k: string]: unknown
}

const props = defineProps<{
  entities: EntityListItem[]
  relations: RelationData[]
  activeStage: StageId
  selectedKey: string
  topModules: ModuleCard[]
  bottomModules: ModuleCard[]
}>()

defineEmits<{ selectTarget: [key: string] }>()

const selectedEntity = computed(() => {
  if (!props.selectedKey.startsWith('entity:')) return null
  const id = props.selectedKey.slice(7)
  return props.entities.find(e => e.id === id) ?? null
})

function moduleIcon(key: string): string {
  const icons: Record<string, string> = {
    'module:analytics': '<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><rect x="2" y="10" width="4" height="8" rx="1" stroke="currentColor" stroke-width="1.3"/><rect x="8" y="6" width="4" height="12" rx="1" stroke="currentColor" stroke-width="1.3"/><rect x="14" y="2" width="4" height="16" rx="1" stroke="currentColor" stroke-width="1.3"/></svg>',
    'module:workflows': '<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="4" cy="10" r="2.5" stroke="currentColor" stroke-width="1.3"/><circle cx="16" cy="5" r="2.5" stroke="currentColor" stroke-width="1.3"/><circle cx="16" cy="15" r="2.5" stroke="currentColor" stroke-width="1.3"/><path d="M6.5 9l7-3.5M6.5 11l7 3.5" stroke="currentColor" stroke-width="1.3"/></svg>',
    'module:integrations': '<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><rect x="2" y="2" width="7" height="7" rx="2" stroke="currentColor" stroke-width="1.3"/><rect x="11" y="2" width="7" height="7" rx="2" stroke="currentColor" stroke-width="1.3"/><rect x="2" y="11" width="7" height="7" rx="2" stroke="currentColor" stroke-width="1.3"/><rect x="11" y="11" width="7" height="7" rx="2" stroke="currentColor" stroke-width="1.3"/></svg>',
    'module:data': '<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><ellipse cx="10" cy="5" rx="7" ry="3" stroke="currentColor" stroke-width="1.3"/><path d="M3 5v5c0 1.66 3.13 3 7 3s7-1.34 7-3V5" stroke="currentColor" stroke-width="1.3"/><path d="M3 10v5c0 1.66 3.13 3 7 3s7-1.34 7-3v-5" stroke="currentColor" stroke-width="1.3"/></svg>',
    'module:models': '<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="3" stroke="currentColor" stroke-width="1.3"/><path d="M10 2v4M10 14v4M2 10h4M14 10h4M4.93 4.93l2.83 2.83M12.24 12.24l2.83 2.83M4.93 15.07l2.83-2.83M12.24 7.76l2.83-2.83" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>',
    'module:ontology': '<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="4" r="2.5" stroke="currentColor" stroke-width="1.3"/><circle cx="4" cy="14" r="2.5" stroke="currentColor" stroke-width="1.3"/><circle cx="16" cy="14" r="2.5" stroke="currentColor" stroke-width="1.3"/><path d="M10 6.5v2M8.5 8.5L5.5 12M11.5 8.5l3 3.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>',
  }
  return icons[key] ?? icons['module:ontology']
}
</script>

<style scoped>
.iso-scene {
  position: relative;
  min-height: 700px;
  border-radius: 24px;
  border: 1px solid rgba(15, 17, 23, 0.06);
  background:
    radial-gradient(circle at 30% 20%, rgba(18, 184, 134, 0.06), transparent 40%),
    radial-gradient(circle at 75% 80%, rgba(76, 110, 245, 0.05), transparent 40%),
    linear-gradient(180deg, rgba(248, 249, 250, 0.98), rgba(255, 255, 255, 0.96));
  overflow: hidden;
  padding: 20px;
}

.iso-scene__perspective {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 0;
  perspective: 1200px;
  perspective-origin: 50% 42%;
}

/* ── Layers ── */
.iso-layer {
  position: relative;
  transition: opacity 500ms ease, transform 600ms cubic-bezier(0.22, 1, 0.36, 1);
}

.iso-layer--dim { opacity: 0.4; }
.iso-layer--active { opacity: 1; }

.iso-layer__platform {
  position: relative;
  border-radius: 20px;
  border: 1px solid rgba(15, 17, 23, 0.07);
  background: rgba(255, 255, 255, 0.88);
  padding: 16px 20px;
  transform-style: preserve-3d;
  transition: box-shadow 500ms ease, border-color 500ms ease;
}

.iso-layer__platform--top {
  transform: rotateX(8deg);
  box-shadow: 0 12px 40px rgba(240, 140, 0, 0.06), 0 2px 0 rgba(255, 255, 255, 0.8) inset;
}

.iso-layer__platform--middle {
  transform: rotateX(4deg);
  box-shadow: 0 20px 60px rgba(18, 184, 134, 0.08), 0 2px 0 rgba(255, 255, 255, 0.8) inset;
  min-height: 320px;
}

.iso-layer__platform--bottom {
  transform: rotateX(0deg);
  box-shadow: 0 12px 40px rgba(76, 110, 245, 0.06), 0 2px 0 rgba(255, 255, 255, 0.8) inset;
}

.iso-layer--glow .iso-layer__platform--middle {
  border-color: rgba(18, 184, 134, 0.2);
  box-shadow: 0 20px 60px rgba(18, 184, 134, 0.14), 0 0 80px rgba(18, 184, 134, 0.06);
}

.iso-layer__label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  color: var(--neutral-400);
  text-transform: uppercase;
  margin-bottom: 12px;
}

.iso-layer__ontology-wrap {
  position: relative;
  min-height: 280px;
}

/* ── Module cards inside layers ── */
.iso-layer__modules {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.iso-layer__modules--bottom {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

/* ── Module card styling ── */
.iso-module {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid rgba(15, 17, 23, 0.07);
  background: rgba(255, 255, 255, 0.9);
  text-align: left;
  cursor: pointer;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast),
    border-color var(--transition-fast);
  box-shadow: 0 8px 20px rgba(15, 17, 23, 0.05);
}

.iso-module::before {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 3px;
  border-radius: 16px 0 0 16px;
}

.iso-module:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(15, 17, 23, 0.08);
}

.iso-module--semantic::before { background: var(--semantic-500); }
.iso-module--dynamic::before { background: var(--dynamic-500); }
.iso-module--kinetic::before { background: var(--kinetic-500); }

.iso-module--selected {
  border-color: rgba(18, 184, 134, 0.22);
  box-shadow: 0 14px 30px rgba(18, 184, 134, 0.12);
}

.iso-module__icon {
  display: flex;
  align-items: center;
  width: 20px;
  height: 20px;
  color: var(--neutral-500);
}

.iso-module__eyebrow {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--neutral-400);
}

.iso-module__title {
  font-size: 14px;
  color: var(--neutral-800);
}

.iso-module__metric {
  font-size: 11px;
  color: var(--neutral-500);
}

/* ── Flow lines between layers ── */
.iso-flow {
  position: relative;
  height: 52px;
  margin: 4px 0;
  opacity: 0.18;
  transition: opacity 500ms ease;
  overflow: hidden;
}

.iso-flow--active {
  opacity: 1;
}

.iso-flow__svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.flow-line {
  stroke: var(--neutral-400);
  stroke-width: 1.2;
  stroke-dasharray: 6 5;
  stroke-linecap: round;
}

.iso-flow--active .flow-line {
  stroke: var(--dynamic-400);
  animation: dash-flow 1.2s linear infinite;
}

@keyframes dash-flow {
  to { stroke-dashoffset: -22; }
}

/* ── Flow particles ── */
.flow-particle {
  position: absolute;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--dynamic-500);
  opacity: 0;
  pointer-events: none;
}

.iso-flow--active .flow-particle--up {
  animation: particle-up 1.8s ease-in-out infinite;
}

@keyframes particle-up {
  0% { bottom: 0; opacity: 0; transform: scale(0.5); }
  15% { opacity: 0.9; transform: scale(1); }
  85% { opacity: 0.9; transform: scale(1); }
  100% { bottom: 100%; opacity: 0; transform: scale(0.5); }
}

/* ── Responsive ── */
@media (max-width: 1280px) {
  .iso-scene { min-height: 600px; }
  .iso-layer__platform--middle { min-height: 260px; }
}

@media (max-width: 980px) {
  .iso-scene { min-height: auto; padding: 14px; }
  .iso-layer__modules,
  .iso-layer__modules--bottom {
    grid-template-columns: 1fr;
  }
  .iso-layer__platform--top,
  .iso-layer__platform--middle,
  .iso-layer__platform--bottom {
    transform: none;
  }
  .iso-flow { height: 36px; }
}
</style>
