<template>
  <div class="pg-panel">
    <div class="pg-panel__header" @click="open = !open">
      <span class="pg-panel__header-icon">{{ open ? '▾' : '▸' }}</span>
      <span>Annotations</span>
    </div>
    <div v-show="open" class="pg-panel__body">
      <table class="pg-table" v-if="entity.annotations.length">
        <thead><tr><th>Property</th><th>Value</th><th>Lang</th><th></th></tr></thead>
        <tbody>
          <tr v-for="a in entity.annotations" :key="a.id">
            <td>
              <select class="pg-input" :value="a.property" @change="updateAnnotation(a.id, 'property', ($event.target as HTMLSelectElement).value)">
                <option value="rdfs:label">rdfs:label</option>
                <option value="rdfs:comment">rdfs:comment</option>
                <option value="rdfs:seeAlso">rdfs:seeAlso</option>
                <option value="rdfs:isDefinedBy">rdfs:isDefinedBy</option>
              </select>
            </td>
            <td><input class="pg-input" :value="a.value" @change="updateAnnotation(a.id, 'value', ($event.target as HTMLInputElement).value)" /></td>
            <td><input class="pg-input" style="width:40px" :value="a.language || ''" @change="updateAnnotation(a.id, 'language', ($event.target as HTMLInputElement).value)" /></td>
            <td><button class="pg-toolbar__btn" @click="removeAnnotation(a.id)">✕</button></td>
          </tr>
        </tbody>
      </table>
      <div v-else class="pg-empty" style="padding:8px">No annotations</div>
      <button class="pg-btn" style="margin-top:4px" @click="addAnnotation">+ Add Annotation</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { OwlAnnotation } from '../../../../../types/owl'
import { uid } from '../../../../../utils/owl/iri'

const props = defineProps<{ entity: { annotations: OwlAnnotation[] } }>()
const emit = defineEmits<{ (e: 'update', annotations: OwlAnnotation[]): void }>()
const open = ref(true)

function addAnnotation() {
  const newAnns = [...props.entity.annotations, { id: uid('ann'), property: 'rdfs:label', value: '', language: '' }]
  emit('update', newAnns)
}

function removeAnnotation(id: string) {
  emit('update', props.entity.annotations.filter(a => a.id !== id))
}

function updateAnnotation(id: string, field: string, value: string) {
  emit('update', props.entity.annotations.map(a => a.id === id ? { ...a, [field]: value } : a))
}
</script>
