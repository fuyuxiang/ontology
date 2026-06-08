<template>
  <div class="pg-split">
    <div class="pg-split__left">
      <div class="pg-toolbar">
        <button class="pg-toolbar__btn" title="添加子属性" @click="addSub">⊕</button>
        <button class="pg-toolbar__btn" title="删除属性" :disabled="!store.selectedDataPropertyId" @click="deleteSel">✕</button>
      </div>
      <EntitySearchInput v-model="filter" placeholder="筛选..." />
      <div class="pg-tree">
        <PropertyTreeNode v-for="p in rootProperties" :key="p.id" :node="p" :depth="0" :filter="filter" kind="data" />
      </div>
    </div>
    <div class="pg-split__right">
      <template v-if="store.selectedDataProperty">
        <div class="pg-panel">
          <div class="pg-panel__header">
            <span class="pg-icon-data-prop"></span>
            <span>{{ store.selectedDataProperty.localName }}</span>
          </div>
        </div>
        <AnnotationsPanel :entity="store.selectedDataProperty" @update="a => store.updateDataProperty(store.selectedDataPropertyId!, { annotations: a })" />
        <div class="pg-panel">
          <div class="pg-panel__header">特性</div>
          <div class="pg-panel__body">
            <label style="font-size:11px;cursor:pointer">
              <input type="checkbox" :checked="store.selectedDataProperty.functional" @change="toggleFunctional" /> 函数型
            </label>
          </div>
        </div>
        <DomainRangePanel :property="store.selectedDataProperty" kind="data" />
      </template>
      <div v-else class="pg-empty">选择一个数据属性以查看详情</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useOwlEditorStore } from '../../../../../store/owlEditor'
import EntitySearchInput from '../shared/EntitySearchInput.vue'
import PropertyTreeNode from '../panels/PropertyTreeNode.vue'
import AnnotationsPanel from '../panels/AnnotationsPanel.vue'
import DomainRangePanel from '../panels/DomainRangePanel.vue'

const store = useOwlEditorStore()
const filter = ref('')

const rootProperties = computed(() => {
  const hasParent = new Set<string>()
  for (const p of store.ontology.dataProperties) {
    for (const sup of p.superProperties) hasParent.add(p.iri)
  }
  return store.ontology.dataProperties.filter(p => !hasParent.has(p.iri)).map(p => ({
    id: p.id, iri: p.iri, localName: p.localName,
    children: store.ontology.dataProperties.filter(c => c.superProperties.includes(p.iri)).map(c => ({ id: c.id, iri: c.iri, localName: c.localName, children: [] }))
  }))
})

function addSub() {
  store.addDataProperty(store.selectedDataProperty?.iri)
}
function deleteSel() {
  if (store.selectedDataPropertyId) store.deleteDataProperty(store.selectedDataPropertyId)
}
function toggleFunctional() {
  if (store.selectedDataPropertyId && store.selectedDataProperty) {
    store.updateDataProperty(store.selectedDataPropertyId, { functional: !store.selectedDataProperty.functional })
  }
}
</script>
