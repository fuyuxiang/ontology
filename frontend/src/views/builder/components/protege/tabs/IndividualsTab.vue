<template>
  <div class="pg-split">
    <div class="pg-split__left">
      <div class="pg-toolbar">
        <button class="pg-toolbar__btn" title="Add individual" @click="store.addIndividual()">⊕</button>
        <button class="pg-toolbar__btn" title="Delete" :disabled="!store.selectedIndividualId" @click="deleteSel">✕</button>
      </div>
      <EntitySearchInput v-model="filter" placeholder="Filter..." />
      <div class="pg-tree">
        <div v-for="ind in filteredIndividuals" :key="ind.id"
             class="pg-tree-node" :class="{ 'pg-tree-node--selected': store.selectedIndividualId === ind.id }"
             @click="store.selectedIndividualId = ind.id">
          <span class="pg-tree-node__icon"><span class="pg-icon-individual"></span></span>
          <span class="pg-tree-node__label">{{ ind.localName }}</span>
        </div>
        <div v-if="!filteredIndividuals.length" class="pg-empty">No individuals</div>
      </div>
    </div>
    <div class="pg-split__right">
      <template v-if="store.selectedIndividual">
        <div class="pg-panel">
          <div class="pg-panel__header">
            <span class="pg-icon-individual"></span>
            <span>{{ store.selectedIndividual.localName }}</span>
          </div>
        </div>
        <AnnotationsPanel :entity="store.selectedIndividual" @update="a => store.updateIndividual(store.selectedIndividualId!, { annotations: a })" />
        <!-- Types -->
        <div class="pg-panel">
          <div class="pg-panel__header">Types</div>
          <div class="pg-panel__body">
            <div v-for="t in store.selectedIndividual.types" :key="t" class="pg-tag">
              {{ t.split(/[#/]/).pop() }}
              <span class="pg-tag__remove" @click="removeType(t)">✕</span>
            </div>
            <button class="pg-btn" style="margin-top:4px" @click="addType">+ Add Type</button>
          </div>
        </div>
        <!-- Data Property Assertions -->
        <div class="pg-panel">
          <div class="pg-panel__header">Data Property Assertions</div>
          <div class="pg-panel__body">
            <table class="pg-table" v-if="store.selectedIndividual.dataPropertyAssertions.length">
              <thead><tr><th>Property</th><th>Value</th><th></th></tr></thead>
              <tbody>
                <tr v-for="a in store.selectedIndividual.dataPropertyAssertions" :key="a.id">
                  <td>{{ a.propertyIRI.split(/[#/]/).pop() }}</td>
                  <td>{{ a.value }}</td>
                  <td><button class="pg-toolbar__btn" @click="removeDataAssertion(a.id)">✕</button></td>
                </tr>
              </tbody>
            </table>
            <button class="pg-btn" style="margin-top:4px" @click="addDataAssertion">+ Add</button>
          </div>
        </div>
      </template>
      <div v-else class="pg-empty">Select an individual to view its details</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useOwlEditorStore } from '../../../../../store/owlEditor'
import { uid } from '../../../../../utils/owl/iri'
import EntitySearchInput from '../shared/EntitySearchInput.vue'
import AnnotationsPanel from '../panels/AnnotationsPanel.vue'

const store = useOwlEditorStore()
const filter = ref('')

const filteredIndividuals = computed(() => {
  if (!filter.value) return store.ontology.individuals
  return store.ontology.individuals.filter(i => i.localName.toLowerCase().includes(filter.value.toLowerCase()))
})

function deleteSel() {
  if (store.selectedIndividualId) store.deleteIndividual(store.selectedIndividualId)
}

function addType() {
  const t = prompt('Enter class IRI or name:')
  if (!t || !store.selectedIndividualId || !store.selectedIndividual) return
  const base = store.ontology.namespaces[0]?.iri || `${store.ontology.iri}#`
  const iri = t.includes(':') || t.includes('/') ? t : `${base}${t}`
  store.updateIndividual(store.selectedIndividualId, { types: [...store.selectedIndividual.types, iri] })
}

function removeType(typeIRI: string) {
  if (!store.selectedIndividualId || !store.selectedIndividual) return
  store.updateIndividual(store.selectedIndividualId, { types: store.selectedIndividual.types.filter(t => t !== typeIRI) })
}

function addDataAssertion() {
  const prop = prompt('Data property IRI or name:')
  const val = prompt('Value:')
  if (!prop || !val || !store.selectedIndividualId || !store.selectedIndividual) return
  const base = store.ontology.namespaces[0]?.iri || `${store.ontology.iri}#`
  const propIRI = prop.includes(':') || prop.includes('/') ? prop : `${base}${prop}`
  const assertions = [...store.selectedIndividual.dataPropertyAssertions, { id: uid('dpa'), propertyIRI: propIRI, value: val, datatype: 'xsd:string' }]
  store.updateIndividual(store.selectedIndividualId, { dataPropertyAssertions: assertions })
}

function removeDataAssertion(id: string) {
  if (!store.selectedIndividualId || !store.selectedIndividual) return
  store.updateIndividual(store.selectedIndividualId, { dataPropertyAssertions: store.selectedIndividual.dataPropertyAssertions.filter(a => a.id !== id) })
}
</script>
