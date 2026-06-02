<template>
  <div class="pg-panel">
    <div class="pg-panel__header">Characteristics</div>
    <div class="pg-panel__body" style="display:flex;flex-wrap:wrap;gap:8px">
      <label v-for="ch in allCharacteristics" :key="ch" style="font-size:11px;cursor:pointer;white-space:nowrap">
        <input type="checkbox" :checked="property.characteristics.includes(ch)" @change="toggleChar(ch)" />
        {{ charLabels[ch] }}
      </label>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { OwlObjectProperty, ObjectPropertyCharacteristic } from '../../../../../types/owl'
import { useOwlEditorStore } from '../../../../../store/owlEditor'

const props = defineProps<{ property: OwlObjectProperty }>()
const store = useOwlEditorStore()

const allCharacteristics: ObjectPropertyCharacteristic[] = ['functional', 'inverseFunctional', 'transitive', 'symmetric', 'asymmetric', 'reflexive', 'irreflexive']

const charLabels: Record<ObjectPropertyCharacteristic, string> = {
  functional: 'Functional',
  inverseFunctional: 'Inverse Functional',
  transitive: 'Transitive',
  symmetric: 'Symmetric',
  asymmetric: 'Asymmetric',
  reflexive: 'Reflexive',
  irreflexive: 'Irreflexive',
}

function toggleChar(ch: ObjectPropertyCharacteristic) {
  const current = props.property.characteristics
  const next = current.includes(ch) ? current.filter(c => c !== ch) : [...current, ch]
  store.updateObjectProperty(props.property.id, { characteristics: next })
}
</script>
