<script setup lang="ts">
import { computed } from 'vue'
import { TresCanvas } from '@tresjs/core'
import { OrbitControls } from '@tresjs/cientos'
import TopLayer from './TopLayer.vue'
import MiddleLayer from './MiddleLayer.vue'
import BottomLayer from './BottomLayer.vue'
import FlowLines from './FlowLines.vue'
import AssetDetailCard from './AssetDetailCard.vue'
import { useSceneState } from '../../../composables/useSceneState'
import type { EntityListItem } from '../../../types'
import type { RelationData } from '../../../api/relations'

const props = defineProps<{
  entities: EntityListItem[]
  relations: RelationData[]
}>()

const { selectedId, selectedType } = useSceneState()

const selectedEntity = computed(() => {
  if (selectedType.value === 'entity' && selectedId.value) {
    const id = selectedId.value.replace('entity:', '')
    return props.entities.find(e => e.id === id) ?? null
  }
  return props.entities[0] ?? null
})
</script>

<template>
  <div class="iso-canvas-wrap">
    <TresCanvas clear-color="#f4f4f5" window-size :antialias="true">
      <!-- Isometric orthographic camera -->
      <TresOrthographicCamera
        :position="[12, 10, 12]"
        :zoom="55"
        :near="0.1"
        :far="100"
      />

      <!-- Lighting -->
      <TresAmbientLight :intensity="0.7" color="#ffffff" />
      <TresDirectionalLight
        :position="[8, 15, 10]"
        :intensity="0.8"
        color="#ffffff"
        :cast-shadow="true"
      />
      <TresDirectionalLight
        :position="[-5, 8, -5]"
        :intensity="0.3"
        color="#f0f0ff"
      />

      <!-- Orbit controls (limited rotation) -->
      <OrbitControls
        :enable-zoom="true"
        :enable-pan="true"
        :enable-rotate="true"
        :min-polar-angle="0.4"
        :max-polar-angle="1.2"
        :min-azimuth-angle="-0.8"
        :max-azimuth-angle="0.8"
        :enable-damping="true"
        :damping-factor="0.08"
      />

      <!-- Three layers -->
      <TopLayer />
      <MiddleLayer :entities="entities" :relations="relations" />
      <BottomLayer />

      <!-- Animated flow lines between layers -->
      <FlowLines />
    </TresCanvas>

    <!-- HTML overlay: Asset detail card floating above middle layer -->
    <div class="iso-canvas-wrap__overlay">
      <div class="iso-canvas-wrap__asset-card">
        <AssetDetailCard :entity="selectedEntity" :visible="selectedEntity !== null" />
      </div>

      <!-- Layer labels -->
      <div class="iso-canvas-wrap__labels">
        <div class="layer-label layer-label--top">
          <span class="layer-label__text">ANALYTICS</span>
          <span class="layer-label__text">WORKFLOWS</span>
          <span class="layer-label__text">INTEGRATIONS</span>
        </div>
        <div class="layer-label layer-label--middle">
          <span class="layer-label__text layer-label__text--large">ONTOLOGY</span>
        </div>
        <div class="layer-label layer-label--bottom">
          <span class="layer-label__text">DATA</span>
          <span class="layer-label__text">MODELS</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.iso-canvas-wrap {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.iso-canvas-wrap__overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 10;
}

.iso-canvas-wrap__asset-card {
  position: absolute;
  top: 28%;
  left: 8%;
  pointer-events: auto;
}

.iso-canvas-wrap__labels {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 40px 0;
}

.layer-label {
  display: flex;
  justify-content: center;
  gap: 60px;
}

.layer-label--top { padding-top: 20px; }
.layer-label--middle { padding: 0; }
.layer-label--bottom { padding-bottom: 20px; }

.layer-label__text {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.18em;
  color: #a1a1aa;
  text-transform: uppercase;
  font-family: 'Inter', system-ui, sans-serif;
}

.layer-label__text--large {
  font-size: 14px;
  letter-spacing: 0.25em;
  color: #71717a;
}
</style>
