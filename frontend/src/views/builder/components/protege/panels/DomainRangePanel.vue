<template>
  <div>
    <!-- Domains -->
    <div class="pg-panel">
      <div class="pg-panel__header">Domains</div>
      <div class="pg-panel__body">
        <div v-for="d in domains" :key="d" class="pg-tag">
          {{ d.split(/[#/]/).pop() }}
          <span class="pg-tag__remove" @click="removeDomain(d)">✕</span>
        </div>
        <button class="pg-btn" style="margin-top:4px" @click="addDomain">+ Add Domain</button>
      </div>
    </div>
    <!-- Ranges -->
    <div class="pg-panel">
      <div class="pg-panel__header">Ranges</div>
      <div class="pg-panel__body">
        <div v-for="r in ranges" :key="r" class="pg-tag">
          {{ r.split(/[#/]/).pop() }}
          <span class="pg-tag__remove" @click="removeRange(r)">✕</span>
        </div>
        <button class="pg-btn" style="margin-top:4px" @click="addRange">+ Add Range</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { OwlObjectProperty, OwlDataProperty } from '../../../../../types/owl'
import { useOwlEditorStore } from '../../../../../store/owlEditor'

const props = defineProps<{ property: OwlObjectProperty | OwlDataProperty; kind: 'object' | 'data' }>()
const store = useOwlEditorStore()

const domains = computed(() => props.property.domains)
const ranges = computed(() => props.property.ranges)

function addDomain() {
  const val = prompt('Enter class IRI or name:')
  if (!val) return
  const base = store.ontology.namespaces[0]?.iri || `${store.ontology.iri}#`
  const iri = val.includes(':') || val.includes('/') ? val : `${base}${val}`
  const newDomains = [...props.property.domains, iri]
  if (props.kind === 'object') store.updateObjectProperty(props.property.id, { domains: newDomains })
  else store.updateDataProperty(props.property.id, { domains: newDomains })
}

function removeDomain(d: string) {
  const newDomains = props.property.domains.filter(x => x !== d)
  if (props.kind === 'object') store.updateObjectProperty(props.property.id, { domains: newDomains })
  else store.updateDataProperty(props.property.id, { domains: newDomains })
}

function addRange() {
  const val = prompt(props.kind === 'data' ? 'Enter XSD datatype (e.g. xsd:string):' : 'Enter class IRI or name:')
  if (!val) return
  const base = store.ontology.namespaces[0]?.iri || `${store.ontology.iri}#`
  const iri = val.includes(':') || val.includes('/') ? val : `${base}${val}`
  const newRanges = [...props.property.ranges, iri]
  if (props.kind === 'object') store.updateObjectProperty(props.property.id, { ranges: newRanges })
  else store.updateDataProperty(props.property.id, { ranges: newRanges })
}

function removeRange(r: string) {
  const newRanges = props.property.ranges.filter(x => x !== r)
  if (props.kind === 'object') store.updateObjectProperty(props.property.id, { ranges: newRanges })
  else store.updateDataProperty(props.property.id, { ranges: newRanges })
}
</script>
