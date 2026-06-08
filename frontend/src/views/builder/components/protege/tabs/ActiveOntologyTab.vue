<template>
  <div style="padding: 16px; overflow-y: auto; flex: 1;">
    <!-- Ontology IRI -->
    <div class="pg-panel">
      <div class="pg-panel__header">本体 IRI</div>
      <div class="pg-panel__body">
        <input class="pg-input" :value="store.ontology.iri" @change="store.updateOntologyMeta({ iri: ($event.target as HTMLInputElement).value })" />
      </div>
    </div>

    <!-- Version IRI -->
    <div class="pg-panel">
      <div class="pg-panel__header">版本 IRI</div>
      <div class="pg-panel__body">
        <input class="pg-input" :value="store.ontology.versionIRI || ''" placeholder="（可选）" @change="store.updateOntologyMeta({ versionIRI: ($event.target as HTMLInputElement).value || undefined })" />
      </div>
    </div>

    <!-- Metrics -->
    <div class="pg-panel">
      <div class="pg-panel__header">本体统计</div>
      <div class="pg-panel__body">
        <table class="pg-table">
          <tbody>
            <tr><td>类</td><td>{{ store.metrics.classCount }}</td></tr>
            <tr><td>对象属性</td><td>{{ store.metrics.objectPropertyCount }}</td></tr>
            <tr><td>数据属性</td><td>{{ store.metrics.dataPropertyCount }}</td></tr>
            <tr><td>实例</td><td>{{ store.metrics.individualCount }}</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Namespaces -->
    <div class="pg-panel">
      <div class="pg-panel__header">前缀 / 命名空间</div>
      <div class="pg-panel__body">
        <table class="pg-table">
          <thead><tr><th>前缀</th><th>IRI</th><th></th></tr></thead>
          <tbody>
            <tr v-for="(ns, idx) in store.ontology.namespaces" :key="idx">
              <td><input class="pg-input" :value="ns.prefix" @change="updateNs(idx, 'prefix', ($event.target as HTMLInputElement).value)" /></td>
              <td><input class="pg-input" :value="ns.iri" @change="updateNs(idx, 'iri', ($event.target as HTMLInputElement).value)" /></td>
              <td><button class="pg-toolbar__btn" @click="removeNs(idx)">✕</button></td>
            </tr>
          </tbody>
        </table>
        <button class="pg-btn" style="margin-top:4px" @click="addNs">+ 添加前缀</button>
      </div>
    </div>

    <!-- Annotations -->
    <AnnotationsPanel :entity="store.ontology" @update="a => store.updateOntologyMeta({ annotations: a })" />
  </div>
</template>

<script setup lang="ts">
import { useOwlEditorStore } from '../../../../../store/owlEditor'
import AnnotationsPanel from '../panels/AnnotationsPanel.vue'

const store = useOwlEditorStore()

function updateNs(idx: number, field: 'prefix' | 'iri', value: string) {
  const nsList = [...store.ontology.namespaces]
  nsList[idx] = { ...nsList[idx], [field]: value }
  store.updateOntologyMeta({ namespaces: nsList })
}

function removeNs(idx: number) {
  const nsList = store.ontology.namespaces.filter((_, i) => i !== idx)
  store.updateOntologyMeta({ namespaces: nsList })
}

function addNs() {
  store.updateOntologyMeta({ namespaces: [...store.ontology.namespaces, { prefix: '', iri: '' }] })
}
</script>
