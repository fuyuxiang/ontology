<template>
  <div class="pg-split">
    <div class="pg-split__left">
      <div class="pg-toolbar">
        <button class="pg-toolbar__btn" title="Add subclass" @click="addSubclass">⊕</button>
        <button class="pg-toolbar__btn" title="Add sibling class" @click="addSibling">⊞</button>
        <button class="pg-toolbar__btn" title="Delete class" :disabled="!store.selectedClassId" @click="deleteSelected">✕</button>
        <div class="pg-toolbar__sep"></div>
      </div>
      <EntitySearchInput v-model="filter" placeholder="Filter..." />
      <div class="pg-tree">
        <ClassTreeNode :node="thingNode" :depth="0" :filter="filter" />
      </div>
    </div>
    <div class="pg-split__right">
      <template v-if="store.selectedClass">
        <div class="pg-panel">
          <div class="pg-panel__header">
            <OwlIcon type="class" />
            <span>{{ store.selectedClass.localName }}</span>
          </div>
          <div class="pg-panel__body">
            <div style="display:flex;gap:6px;align-items:center;margin-bottom:6px">
              <label style="font-size:11px;color:#666;white-space:nowrap">Name:</label>
              <input class="pg-input" :value="store.selectedClass.localName" @change="renameClass(($event.target as HTMLInputElement).value)" />
            </div>
            <div style="font-size:10px;color:#999;word-break:break-all">IRI: {{ store.selectedClass.iri }}</div>
          </div>
        </div>
        <AnnotationsPanel :entity="store.selectedClass" @update="onUpdateAnnotations" />
        <ClassDescriptionPanel :owl-class="store.selectedClass" />
      </template>
      <div v-else class="pg-empty">Select a class to view its details</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useOwlEditorStore } from '../../../../../store/owlEditor'
import EntitySearchInput from '../shared/EntitySearchInput.vue'
import OwlIcon from '../shared/OwlIcon.vue'
import ClassTreeNode from '../panels/ClassTreeNode.vue'
import AnnotationsPanel from '../panels/AnnotationsPanel.vue'
import ClassDescriptionPanel from '../panels/ClassDescriptionPanel.vue'
import type { OwlAnnotation } from '../../../../../types/owl'

const store = useOwlEditorStore()
const filter = ref('')

interface TreeNode {
  id: string
  iri: string
  localName: string
  children: TreeNode[]
}

const thingNode = computed<TreeNode>(() => {
  const classIRIs = new Set(store.ontology.classes.map(c => c.iri))
  const childMap = new Map<string, string[]>()
  const hasParent = new Set<string>()

  for (const c of store.ontology.classes) {
    for (const sup of c.superClassExpressions) {
      if (sup.type === 'namedClass' && sup.classIRI) {
        if (!childMap.has(sup.classIRI)) childMap.set(sup.classIRI, [])
        childMap.get(sup.classIRI)!.push(c.iri)
        hasParent.add(c.iri)
      }
    }
  }

  function buildNode(iri: string): TreeNode {
    const c = store.ontology.classes.find(cl => cl.iri === iri)
    const children = (childMap.get(iri) || []).map(buildNode)
    return { id: c?.id || iri, iri, localName: c?.localName || iri.split(/[#/]/).pop() || '', children }
  }

  const rootChildren = store.ontology.classes
    .filter(c => !hasParent.has(c.iri))
    .map(c => buildNode(c.iri))

  return { id: 'owl-thing', iri: 'owl:Thing', localName: 'Thing', children: rootChildren }
})

function addSubclass() {
  const parentIRI = store.selectedClass?.iri || 'owl:Thing'
  store.addClass(parentIRI)
}

function addSibling() {
  if (!store.selectedClass) { store.addClass(); return }
  const parent = store.selectedClass.superClassExpressions.find(e => e.type === 'namedClass')
  store.addClass(parent?.classIRI || undefined)
}

function deleteSelected() {
  if (store.selectedClassId) store.deleteClass(store.selectedClassId)
}

function onUpdateAnnotations(annotations: OwlAnnotation[]) {
  if (store.selectedClassId) store.updateClass(store.selectedClassId, { annotations })
}

function renameClass(newName: string) {
  if (!store.selectedClassId || !newName) return
  const base = store.ontology.namespaces[0]?.iri || `${store.ontology.iri}#`
  store.updateClass(store.selectedClassId, { localName: newName, iri: `${base}${newName}` })
}
</script>
