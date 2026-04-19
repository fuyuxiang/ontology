<script setup lang="ts">
import { computed } from 'vue'
import GreenCapsule from './GreenCapsule.vue'
import type { EntityListItem } from '../../../types'
import type { RelationData } from '../../../api/relations'

const props = defineProps<{
  entities: EntityListItem[]
  relations: RelationData[]
}>()

const relationLabelMap: Record<string, string> = {
  user_queries_portability: 'Queries',
  user_bindto_contract: 'Binds',
  user_bindto_billing: 'Bills',
  user_bindto_arrears: 'Owes',
  user_has_voice_calls: 'Calls',
  user_receives_retention: 'Retains',
  user_bindto_convergence: 'Converges',
  contract_restricts_portability: 'Restricts',
  arrears_restricts_portability: 'Blocks',
  complaint_influences_retention: 'Influences',
  user_has_complaints: 'Complains',
}

const capsuleSlots: [number, number, number][] = [
  [-2.5, 0.25, -1.5], [-0.8, 0.25, -2], [1.2, 0.25, -1.2],
  [2.8, 0.25, -0.3], [-2, 0.25, 0.8], [0, 0.25, 1.5],
  [2, 0.25, 1], [-1, 0.25, 0], [3, 0.25, -2],
]

const entitySlots: Array<{ pos: [number, number, number]; type: string }> = [
  { pos: [-3.5, 0.35, 0], type: 'factory' },
  { pos: [-1.5, 0.35, -1], type: 'person' },
  { pos: [0.5, 0.35, 0.5], type: 'truck' },
  { pos: [2, 0.35, -1.5], type: 'building' },
  { pos: [3.5, 0.35, 0.8], type: 'person' },
  { pos: [-0.5, 0.35, 2], type: 'building' },
]

const capsuleNodes = computed(() => {
  return props.relations.slice(0, capsuleSlots.length).map((rel, i) => ({
    id: `capsule:${rel.id}`,
    label: relationLabelMap[rel.name] ?? rel.name.replaceAll('_', ' ').slice(0, 12),
    position: capsuleSlots[i],
  }))
})

const entityNodes = computed(() => {
  return props.entities.slice(0, entitySlots.length).map((entity, i) => ({
    id: `entity:${entity.id}`,
    entity,
    ...entitySlots[i],
  }))
})
</script>

<template>
  <TresGroup :position="[0, 2, 0]">
    <TresMesh name="platform:ontology">
      <TresBoxGeometry :args="[10, 0.12, 6]" />
      <TresMeshStandardMaterial color="#ffffff" :metalness="0.05" :roughness="0.9" />
    </TresMesh>

    <TresMesh :position="[0, 0.065, 0]" :rotation-x="-Math.PI / 2">
      <TresPlaneGeometry :args="[9.8, 5.8, 10, 6]" />
      <TresMeshBasicMaterial color="#e5e5e5" wireframe />
    </TresMesh>

    <GreenCapsule
      v-for="cap in capsuleNodes"
      :key="cap.id"
      :id="cap.id"
      :label="cap.label"
      :position="cap.position"
    />

    <TresGroup v-for="node in entityNodes" :key="node.id" :position="node.pos">
      <template v-if="node.type === 'factory'">
        <TresMesh :name="node.id">
          <TresBoxGeometry :args="[0.6, 0.4, 0.4]" />
          <TresMeshStandardMaterial color="#f5f5f5" :metalness="0.05" :roughness="0.9" />
        </TresMesh>
        <TresMesh :position="[0.15, 0.35, 0]">
          <TresCylinderGeometry :args="[0.06, 0.06, 0.3, 8]" />
          <TresMeshStandardMaterial color="#f5f5f5" />
        </TresMesh>
      </template>

      <template v-if="node.type === 'person'">
        <TresMesh :position="[0, 0.15, 0]" :name="node.id">
          <TresSphereGeometry :args="[0.15, 12, 12]" />
          <TresMeshStandardMaterial color="#f5f5f5" />
        </TresMesh>
        <TresMesh :position="[0, -0.05, 0]">
          <TresCylinderGeometry :args="[0.12, 0.15, 0.25, 8]" />
          <TresMeshStandardMaterial color="#f5f5f5" />
        </TresMesh>
      </template>

      <template v-if="node.type === 'truck'">
        <TresMesh :name="node.id">
          <TresBoxGeometry :args="[0.7, 0.25, 0.3]" />
          <TresMeshStandardMaterial color="#f5f5f5" />
        </TresMesh>
        <TresMesh :position="[0.3, 0.05, 0]">
          <TresBoxGeometry :args="[0.2, 0.3, 0.28]" />
          <TresMeshStandardMaterial color="#f5f5f5" />
        </TresMesh>
      </template>

      <template v-if="node.type === 'building'">
        <TresMesh :name="node.id">
          <TresBoxGeometry :args="[0.35, 0.6, 0.35]" />
          <TresMeshStandardMaterial color="#f5f5f5" />
        </TresMesh>
      </template>
    </TresGroup>
  </TresGroup>
</template>
