<template>
  <div class="protege-editor">
    <ProtegeMenuBar @new="store.newOntology()" @open="onOpen" @save="store.exportAndDownload()" />
    <div class="pg-tabs">
      <div class="pg-tab-strip">
        <div v-for="tab in tabs" :key="tab.key"
             class="pg-tab-item" :class="{ 'pg-tab-item--active': store.selectedTab === tab.key }"
             @click="store.selectedTab = tab.key">
          {{ tab.label }}
        </div>
      </div>
    </div>
    <div class="pg-body">
      <ActiveOntologyTab v-if="store.selectedTab === 'ontology'" />
      <ClassesTab v-else-if="store.selectedTab === 'classes'" />
      <ObjectPropertiesTab v-else-if="store.selectedTab === 'objectProperties'" />
      <DataPropertiesTab v-else-if="store.selectedTab === 'dataProperties'" />
      <IndividualsTab v-else-if="store.selectedTab === 'individuals'" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useOwlEditorStore } from '../../../../store/owlEditor'
import ProtegeMenuBar from './ProtegeMenuBar.vue'
import ActiveOntologyTab from './tabs/ActiveOntologyTab.vue'
import ClassesTab from './tabs/ClassesTab.vue'
import ObjectPropertiesTab from './tabs/ObjectPropertiesTab.vue'
import DataPropertiesTab from './tabs/DataPropertiesTab.vue'
import IndividualsTab from './tabs/IndividualsTab.vue'
import './styles/protege-theme.css'

const store = useOwlEditorStore()

const tabs = [
  { key: 'ontology', label: '活动本体' },
  { key: 'classes', label: '类' },
  { key: 'objectProperties', label: '对象属性' },
  { key: 'dataProperties', label: '数据属性' },
  { key: 'individuals', label: '实例' },
]

function onOpen() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.owl,.xml,.rdf'
  input.onchange = async () => {
    const file = input.files?.[0]
    if (!file) return
    const text = await file.text()
    store.importOwlXml(text)
  }
  input.click()
}

onMounted(() => {
  store.loadDraft()
})
</script>

<style scoped>
.pg-body { flex: 1; overflow: hidden; display: flex; }
.pg-tab-strip {
  display: flex;
  background: var(--pg-toolbar-bg);
  border-bottom: 1px solid var(--pg-border);
  padding: 0 4px;
}
.pg-tab-item {
  padding: 5px 14px;
  font-size: 11px;
  cursor: pointer;
  border: 1px solid transparent;
  border-bottom: none;
  margin-bottom: -1px;
  user-select: none;
  color: var(--pg-text-muted);
}
.pg-tab-item:hover { color: var(--pg-text); }
.pg-tab-item--active {
  background: var(--pg-panel-bg);
  border-color: var(--pg-border);
  border-bottom-color: var(--pg-panel-bg);
  color: var(--pg-text);
  font-weight: 600;
}
</style>
