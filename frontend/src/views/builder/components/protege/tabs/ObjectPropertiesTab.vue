<template>
  <div class="pg-split">
    <div class="pg-split__left">
      <div class="pg-toolbar">
        <button class="pg-toolbar__btn" title="添加子属性" @click="addSub">⊕</button>
        <button class="pg-toolbar__btn" title="删除属性" :disabled="!store.selectedObjectPropertyId" @click="deleteSel">✕</button>
      </div>
      <EntitySearchInput v-model="filter" placeholder="筛选..." />
      <div class="pg-tree">
        <PropertyTreeNode v-for="p in rootProperties" :key="p.id" :node="p" :depth="0" :filter="filter" kind="object" />
      </div>
    </div>
    <div class="pg-split__right">
      <template v-if="store.selectedObjectProperty">
        <div class="pg-panel">
          <div class="pg-panel__header">
            <span class="pg-icon-obj-prop"></span>
            <span>{{ store.selectedObjectProperty.localName }}</span>
          </div>
        </div>
        <AnnotationsPanel :entity="store.selectedObjectProperty" @update="a => store.updateObjectProperty(store.selectedObjectPropertyId!, { annotations: a })" />
        <PropertyCharacteristics :property="store.selectedObjectProperty" />
        <DomainRangePanel :property="store.selectedObjectProperty" kind="object" />
      </template>
      <div v-else class="pg-empty">选择一个对象属性以查看详情</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useOwlEditorStore } from '../../../../../store/owlEditor'
import EntitySearchInput from '../shared/EntitySearchInput.vue'
import PropertyTreeNode from '../panels/PropertyTreeNode.vue'
import AnnotationsPanel from '../panels/AnnotationsPanel.vue'
import PropertyCharacteristics from '../panels/PropertyCharacteristics.vue'
import DomainRangePanel from '../panels/DomainRangePanel.vue'

const store = useOwlEditorStore()
const filter = ref('')

const rootProperties = computed(() => {
  const hasParent = new Set<string>()
  for (const p of store.ontology.objectProperties) {
    if (p.superProperties.length > 0) hasParent.add(p.iri)
  }
  return store.ontology.objectProperties.filter(p => !hasParent.has(p.iri)).map(p => ({
    id: p.id, iri: p.iri, localName: p.localName,
    children: store.ontology.objectProperties.filter(c => c.superProperties.includes(p.iri)).map(c => ({ id: c.id, iri: c.iri, localName: c.localName, children: [] }))
  }))
})

function addSub() {
  store.addObjectProperty(store.selectedObjectProperty?.iri)
}
function deleteSel() {
  if (store.selectedObjectPropertyId) store.deleteObjectProperty(store.selectedObjectPropertyId)
}
</script>
