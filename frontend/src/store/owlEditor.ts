import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { OwlOntology, OwlClass, OwlObjectProperty, OwlDataProperty, OwlIndividual } from '../types/owl'
import { uid } from '../utils/owl/iri'
import { serializeToOwlXml, downloadOwlFile } from '../utils/owl/serializer'
import { parseOwlXml } from '../utils/owl/parser'

const STORAGE_KEY = 'owl-editor-draft'

function createEmptyOntology(): OwlOntology {
  return {
    id: uid('ont'),
    iri: 'http://example.org/ontology',
    annotations: [],
    namespaces: [{ prefix: 'ex', iri: 'http://example.org/ontology#' }],
    classes: [],
    objectProperties: [],
    dataProperties: [],
    individuals: [],
  }
}

export const useOwlEditorStore = defineStore('owlEditor', () => {
  const ontology = ref<OwlOntology>(createEmptyOntology())
  const selectedTab = ref<string>('classes')
  const selectedClassId = ref<string | null>(null)
  const selectedObjectPropertyId = ref<string | null>(null)
  const selectedDataPropertyId = ref<string | null>(null)
  const selectedIndividualId = ref<string | null>(null)
  const isDirty = ref(false)

  const undoStack = ref<string[]>([])
  const redoStack = ref<string[]>([])
  const MAX_UNDO = 50

  function snapshot() {
    undoStack.value.push(JSON.stringify(ontology.value))
    if (undoStack.value.length > MAX_UNDO) undoStack.value.shift()
    redoStack.value = []
    isDirty.value = true
  }

  function undo() {
    const prev = undoStack.value.pop()
    if (!prev) return
    redoStack.value.push(JSON.stringify(ontology.value))
    ontology.value = JSON.parse(prev)
  }

  function redo() {
    const next = redoStack.value.pop()
    if (!next) return
    undoStack.value.push(JSON.stringify(ontology.value))
    ontology.value = JSON.parse(next)
  }

  // Computed
  const selectedClass = computed(() => ontology.value.classes.find(c => c.id === selectedClassId.value) || null)
  const selectedObjectProperty = computed(() => ontology.value.objectProperties.find(p => p.id === selectedObjectPropertyId.value) || null)
  const selectedDataProperty = computed(() => ontology.value.dataProperties.find(p => p.id === selectedDataPropertyId.value) || null)
  const selectedIndividual = computed(() => ontology.value.individuals.find(i => i.id === selectedIndividualId.value) || null)

  const metrics = computed(() => ({
    classCount: ontology.value.classes.length,
    objectPropertyCount: ontology.value.objectProperties.length,
    dataPropertyCount: ontology.value.dataProperties.length,
    individualCount: ontology.value.individuals.length,
  }))

  // Class CRUD
  function addClass(parentIRI?: string): OwlClass {
    snapshot()
    const base = ontology.value.namespaces[0]?.iri || `${ontology.value.iri}#`
    const localName = `NewClass${ontology.value.classes.length + 1}`
    const c: OwlClass = {
      id: uid('cls'),
      iri: `${base}${localName}`,
      localName,
      annotations: [],
      superClassExpressions: parentIRI ? [{ id: uid('expr'), type: 'namedClass', classIRI: parentIRI }] : [],
      equivalentClassExpressions: [],
      disjointWith: [],
    }
    ontology.value.classes.push(c)
    selectedClassId.value = c.id
    return c
  }

  function deleteClass(id: string) {
    snapshot()
    ontology.value.classes = ontology.value.classes.filter(c => c.id !== id)
    if (selectedClassId.value === id) selectedClassId.value = null
  }

  function updateClass(id: string, patch: Partial<OwlClass>) {
    snapshot()
    const idx = ontology.value.classes.findIndex(c => c.id === id)
    if (idx >= 0) ontology.value.classes[idx] = { ...ontology.value.classes[idx], ...patch }
  }

  // Object Property CRUD
  function addObjectProperty(parentIRI?: string): OwlObjectProperty {
    snapshot()
    const base = ontology.value.namespaces[0]?.iri || `${ontology.value.iri}#`
    const localName = `newObjectProperty${ontology.value.objectProperties.length + 1}`
    const p: OwlObjectProperty = {
      id: uid('op'),
      iri: `${base}${localName}`,
      localName,
      annotations: [],
      superProperties: parentIRI ? [parentIRI] : [],
      domains: [],
      ranges: [],
      characteristics: [],
      inverseOf: null,
    }
    ontology.value.objectProperties.push(p)
    selectedObjectPropertyId.value = p.id
    return p
  }

  function deleteObjectProperty(id: string) {
    snapshot()
    ontology.value.objectProperties = ontology.value.objectProperties.filter(p => p.id !== id)
    if (selectedObjectPropertyId.value === id) selectedObjectPropertyId.value = null
  }

  function updateObjectProperty(id: string, patch: Partial<OwlObjectProperty>) {
    snapshot()
    const idx = ontology.value.objectProperties.findIndex(p => p.id === id)
    if (idx >= 0) ontology.value.objectProperties[idx] = { ...ontology.value.objectProperties[idx], ...patch }
  }

  // Data Property CRUD
  function addDataProperty(parentIRI?: string): OwlDataProperty {
    snapshot()
    const base = ontology.value.namespaces[0]?.iri || `${ontology.value.iri}#`
    const localName = `newDataProperty${ontology.value.dataProperties.length + 1}`
    const p: OwlDataProperty = {
      id: uid('dp'),
      iri: `${base}${localName}`,
      localName,
      annotations: [],
      superProperties: parentIRI ? [parentIRI] : [],
      domains: [],
      ranges: [],
      functional: false,
    }
    ontology.value.dataProperties.push(p)
    selectedDataPropertyId.value = p.id
    return p
  }

  function deleteDataProperty(id: string) {
    snapshot()
    ontology.value.dataProperties = ontology.value.dataProperties.filter(p => p.id !== id)
    if (selectedDataPropertyId.value === id) selectedDataPropertyId.value = null
  }

  function updateDataProperty(id: string, patch: Partial<OwlDataProperty>) {
    snapshot()
    const idx = ontology.value.dataProperties.findIndex(p => p.id === id)
    if (idx >= 0) ontology.value.dataProperties[idx] = { ...ontology.value.dataProperties[idx], ...patch }
  }

  // Individual CRUD
  function addIndividual(): OwlIndividual {
    snapshot()
    const base = ontology.value.namespaces[0]?.iri || `${ontology.value.iri}#`
    const localName = `individual${ontology.value.individuals.length + 1}`
    const ind: OwlIndividual = {
      id: uid('ind'),
      iri: `${base}${localName}`,
      localName,
      annotations: [],
      types: [],
      objectPropertyAssertions: [],
      dataPropertyAssertions: [],
      sameAs: [],
      differentFrom: [],
    }
    ontology.value.individuals.push(ind)
    selectedIndividualId.value = ind.id
    return ind
  }

  function deleteIndividual(id: string) {
    snapshot()
    ontology.value.individuals = ontology.value.individuals.filter(i => i.id !== id)
    if (selectedIndividualId.value === id) selectedIndividualId.value = null
  }

  function updateIndividual(id: string, patch: Partial<OwlIndividual>) {
    snapshot()
    const idx = ontology.value.individuals.findIndex(i => i.id === id)
    if (idx >= 0) ontology.value.individuals[idx] = { ...ontology.value.individuals[idx], ...patch }
  }

  // Ontology meta
  function updateOntologyMeta(patch: Partial<Pick<OwlOntology, 'iri' | 'versionIRI' | 'annotations' | 'namespaces'>>) {
    snapshot()
    Object.assign(ontology.value, patch)
  }

  // Serialization
  function exportOwlXml(): string {
    return serializeToOwlXml(ontology.value)
  }

  function exportAndDownload(filename?: string) {
    downloadOwlFile(ontology.value, filename)
  }

  function importOwlXml(xmlString: string) {
    snapshot()
    ontology.value = parseOwlXml(xmlString)
    selectedClassId.value = null
    selectedObjectPropertyId.value = null
    selectedDataPropertyId.value = null
    selectedIndividualId.value = null
  }

  function newOntology(iri?: string) {
    snapshot()
    ontology.value = createEmptyOntology()
    if (iri) ontology.value.iri = iri
    selectedClassId.value = null
    selectedObjectPropertyId.value = null
    selectedDataPropertyId.value = null
    selectedIndividualId.value = null
    isDirty.value = false
  }

  // Persistence
  function saveDraft() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(ontology.value)) } catch { /* noop */ }
    isDirty.value = false
  }

  function loadDraft(): boolean {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) { ontology.value = JSON.parse(raw); return true }
    } catch { /* noop */ }
    return false
  }

  return {
    ontology, selectedTab, selectedClassId, selectedObjectPropertyId, selectedDataPropertyId, selectedIndividualId, isDirty,
    selectedClass, selectedObjectProperty, selectedDataProperty, selectedIndividual, metrics,
    snapshot, undo, redo,
    addClass, deleteClass, updateClass,
    addObjectProperty, deleteObjectProperty, updateObjectProperty,
    addDataProperty, deleteDataProperty, updateDataProperty,
    addIndividual, deleteIndividual, updateIndividual,
    updateOntologyMeta, exportOwlXml, exportAndDownload, importOwlXml, newOntology,
    saveDraft, loadDraft,
  }
})
