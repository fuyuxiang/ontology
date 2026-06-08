<template>
  <div class="vb-root">
    <!-- Top bar -->
    <div class="vb-topbar">
      <div class="vb-topbar__project">
        <span class="vb-topbar__icon">📂</span>
        <span class="vb-topbar__name">{{ store.ontology.iri.split(/[#/]/).pop() || 'Ontology Project' }}</span>
      </div>
      <div class="vb-topbar__actions">
        <button class="vb-btn" @click="store.saveDraft()">保存草稿</button>
        <button class="vb-btn" @click="onImport">导入</button>
        <button class="vb-btn vb-btn--primary" @click="store.exportAndDownload()">导出 OWL</button>
      </div>
    </div>

    <!-- Main nav tabs -->
    <div class="vb-nav">
      <div v-for="tab in navTabs" :key="tab.key" class="vb-nav__item" :class="{ 'vb-nav__item--active': activeNav === tab.key }" @click="activeNav = tab.key">
        <span class="vb-nav__icon">{{ tab.icon }}</span>
        {{ tab.label }}
      </div>
    </div>

    <!-- Body -->
    <div class="vb-body">
      <!-- Left: Tree -->
      <div class="vb-left">
        <div class="vb-left__toolbar">
          <input class="vb-input" v-model="filter" placeholder="搜索..." />
          <button class="vb-btn-sm" title="添加" @click="addEntity">+</button>
          <button class="vb-btn-sm" title="删除" @click="deleteEntity">−</button>
        </div>
        <div class="vb-tree">
          <template v-if="activeNav === 'classes'">
            <VbTreeNode v-for="node in classTree" :key="node.id" :node="node" :depth="0" :selected-id="selectedId" @select="onSelect" />
          </template>
          <template v-else-if="activeNav === 'properties'">
            <div v-for="p in filteredProperties" :key="p.id" class="vb-tree-item" :class="{ 'vb-tree-item--selected': selectedId === p.id }" @click="onSelect(p.id)">
              <span class="vb-tree-item__icon" :style="{ background: '#7b68ee' }"></span>
              {{ p.localName }}
            </div>
          </template>
          <template v-else>
            <div v-for="ind in filteredIndividuals" :key="ind.id" class="vb-tree-item" :class="{ 'vb-tree-item--selected': selectedId === ind.id }" @click="onSelect(ind.id)">
              <span class="vb-tree-item__icon" :style="{ background: '#9370db' }"></span>
              {{ ind.localName }}
            </div>
          </template>
        </div>
      </div>

      <!-- Right: Detail -->
      <div class="vb-right">
        <template v-if="selectedEntity">
          <div class="vb-detail-header">
            <input class="vb-input vb-input--name" :value="selectedEntity.localName" @change="renameEntity(($event.target as HTMLInputElement).value)" />
            <span class="vb-detail-header__iri">{{ selectedEntity.iri }}</span>
          </div>
          <div class="vb-detail-tabs">
            <div v-for="dt in detailTabs" :key="dt" class="vb-detail-tab" :class="{ 'vb-detail-tab--active': activeDetail === dt }" @click="activeDetail = dt">{{ detailTabLabels[dt] || dt }}</div>
          </div>
          <div class="vb-detail-body">
            <!-- Properties tab -->
            <template v-if="activeDetail === 'Properties'">
              <div class="vb-section" v-if="selectedEntity.type === 'class'">
                <div class="vb-section__title">父类 <button class="vb-btn-sm" @click="addSuperClass">+</button></div>
                <div class="vb-section__content">
                  <div v-for="s in (selectedClass?.superClassExpressions || [])" :key="s.id" class="vb-chip">
                    {{ s.classIRI?.split(/[#/]/).pop() || s.type }}
                    <span class="vb-chip__remove" @click="removeSuperClass(s.id)">✕</span>
                  </div>
                  <span v-if="!selectedClass?.superClassExpressions?.length" class="vb-muted">—</span>
                </div>
              </div>
              <div class="vb-section" v-if="selectedEntity.type === 'class'">
                <div class="vb-section__title">互斥类 <button class="vb-btn-sm" @click="addDisjoint">+</button></div>
                <div class="vb-section__content">
                  <div v-for="d in (selectedClass?.disjointWith || [])" :key="d" class="vb-chip">
                    {{ d.split(/[#/]/).pop() }}
                    <span class="vb-chip__remove" @click="removeDisjoint(d)">✕</span>
                  </div>
                  <span v-if="!selectedClass?.disjointWith?.length" class="vb-muted">—</span>
                </div>
              </div>
              <div class="vb-section" v-if="selectedEntity.type === 'property'">
                <div class="vb-section__title">定义域 <button class="vb-btn-sm" @click="addDomain">+</button></div>
                <div class="vb-section__content">
                  <div v-for="d in (selectedProp?.domains || [])" :key="d" class="vb-chip">
                    {{ d.split(/[#/]/).pop() }}
                    <span class="vb-chip__remove" @click="removeDomain(d)">✕</span>
                  </div>
                  <span v-if="!selectedProp?.domains?.length" class="vb-muted">—</span>
                </div>
              </div>
              <div class="vb-section" v-if="selectedEntity.type === 'property'">
                <div class="vb-section__title">值域 <button class="vb-btn-sm" @click="addRange">+</button></div>
                <div class="vb-section__content">
                  <div v-for="r in (selectedProp?.ranges || [])" :key="r" class="vb-chip">
                    {{ r.split(/[#/]/).pop() }}
                    <span class="vb-chip__remove" @click="removeRange(r)">✕</span>
                  </div>
                  <span v-if="!selectedProp?.ranges?.length" class="vb-muted">—</span>
                </div>
              </div>
            </template>
            <!-- Annotations tab -->
            <template v-else-if="activeDetail === 'Annotations'">
              <table class="vb-table" v-if="annotations.length">
                <thead><tr><th>属性</th><th>值</th><th>语言</th><th></th></tr></thead>
                <tbody>
                  <tr v-for="a in annotations" :key="a.id">
                    <td>{{ a.property }}</td>
                    <td>{{ a.value }}</td>
                    <td>{{ a.language || '' }}</td>
                    <td><button class="vb-btn-sm" @click="removeAnnotation(a.id)">✕</button></td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="vb-muted" style="padding:16px">暂无注解</div>
              <button class="vb-btn-sm" style="margin-top:8px" @click="addAnnotation">+ 添加注解</button>
            </template>
            <!-- Other -->
            <template v-else>
              <div class="vb-muted" style="padding:16px">请选择上方标签页</div>
            </template>
          </div>
        </template>
        <div v-else class="vb-empty">
          <span>从左侧树中选择实体以查看详情</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useOwlEditorStore } from '../../../store/owlEditor'
import { uid } from '../../../utils/owl/iri'
import VbTreeNode from './VbTreeNode.vue'

const store = useOwlEditorStore()
const activeNav = ref<'classes' | 'properties' | 'individuals'>('classes')
const activeDetail = ref('Properties')
const filter = ref('')
const selectedId = ref<string | null>(null)

const navTabs = [
  { key: 'classes' as const, label: '类', icon: '◉' },
  { key: 'properties' as const, label: '属性', icon: '◆' },
  { key: 'individuals' as const, label: '实例', icon: '■' },
]

const detailTabs = ['Properties', 'Annotations', 'Lexicalizations']
const detailTabLabels: Record<string, string> = { Properties: '属性', Annotations: '注解', Lexicalizations: '词汇化' }

interface TreeNode { id: string; iri: string; localName: string; children: TreeNode[] }

const classTree = computed<TreeNode[]>(() => {
  const hasParent = new Set<string>()
  const childMap = new Map<string, string[]>()
  for (const c of store.ontology.classes) {
    for (const sup of c.superClassExpressions) {
      if (sup.type === 'namedClass' && sup.classIRI) {
        if (!childMap.has(sup.classIRI)) childMap.set(sup.classIRI, [])
        childMap.get(sup.classIRI)!.push(c.iri)
        hasParent.add(c.iri)
      }
    }
  }
  function build(iri: string): TreeNode {
    const c = store.ontology.classes.find(cl => cl.iri === iri)
    return { id: c?.id || iri, iri, localName: c?.localName || iri.split(/[#/]/).pop() || '', children: (childMap.get(iri) || []).map(build) }
  }
  return store.ontology.classes.filter(c => !hasParent.has(c.iri)).map(c => build(c.iri))
})

const filteredProperties = computed(() => {
  const all = [...store.ontology.objectProperties, ...store.ontology.dataProperties]
  if (!filter.value) return all
  return all.filter(p => p.localName.toLowerCase().includes(filter.value.toLowerCase()))
})

const filteredIndividuals = computed(() => {
  if (!filter.value) return store.ontology.individuals
  return store.ontology.individuals.filter(i => i.localName.toLowerCase().includes(filter.value.toLowerCase()))
})

const selectedEntity = computed(() => {
  if (!selectedId.value) return null
  const c = store.ontology.classes.find(x => x.id === selectedId.value)
  if (c) return { ...c, type: 'class' as const }
  const op = store.ontology.objectProperties.find(x => x.id === selectedId.value)
  if (op) return { ...op, type: 'property' as const }
  const dp = store.ontology.dataProperties.find(x => x.id === selectedId.value)
  if (dp) return { ...dp, type: 'property' as const }
  const ind = store.ontology.individuals.find(x => x.id === selectedId.value)
  if (ind) return { ...ind, type: 'individual' as const }
  return null
})

const selectedClass = computed(() => store.ontology.classes.find(c => c.id === selectedId.value) || null)
const selectedProp = computed(() => [...store.ontology.objectProperties, ...store.ontology.dataProperties].find(p => p.id === selectedId.value) || null)

const annotations = computed(() => selectedEntity.value?.annotations || [])

function onSelect(id: string) { selectedId.value = id }

function addEntity() {
  if (activeNav.value === 'classes') store.addClass()
  else if (activeNav.value === 'properties') store.addObjectProperty()
  else store.addIndividual()
}

function deleteEntity() {
  if (!selectedId.value) return
  if (activeNav.value === 'classes') store.deleteClass(selectedId.value)
  else if (activeNav.value === 'properties') {
    store.deleteObjectProperty(selectedId.value)
    store.deleteDataProperty(selectedId.value)
  } else store.deleteIndividual(selectedId.value)
  selectedId.value = null
}

function onImport() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.owl,.xml,.rdf'
  input.onchange = async () => {
    const file = input.files?.[0]
    if (!file) return
    store.importOwlXml(await file.text())
  }
  input.click()
}

function renameEntity(newName: string) {
  if (!selectedId.value || !newName) return
  const base = store.ontology.namespaces[0]?.iri || `${store.ontology.iri}#`
  const newIRI = `${base}${newName}`
  const cls = store.ontology.classes.find(c => c.id === selectedId.value)
  if (cls) { store.updateClass(cls.id, { localName: newName, iri: newIRI }); return }
  const op = store.ontology.objectProperties.find(p => p.id === selectedId.value)
  if (op) { store.updateObjectProperty(op.id, { localName: newName, iri: newIRI }); return }
  const dp = store.ontology.dataProperties.find(p => p.id === selectedId.value)
  if (dp) { store.updateDataProperty(dp.id, { localName: newName, iri: newIRI }); return }
  const ind = store.ontology.individuals.find(i => i.id === selectedId.value)
  if (ind) { store.updateIndividual(ind.id, { localName: newName, iri: newIRI }); return }
}

function addSuperClass() {
  if (!selectedId.value) return
  const cls = store.ontology.classes.find(c => c.id === selectedId.value)
  if (!cls) return
  const name = prompt('父类名称：')
  if (!name) return
  const base = store.ontology.namespaces[0]?.iri || `${store.ontology.iri}#`
  const iri = name.includes(':') || name.includes('/') ? name : `${base}${name}`
  store.updateClass(cls.id, { superClassExpressions: [...cls.superClassExpressions, { id: uid('expr'), type: 'namedClass', classIRI: iri }] })
}

function removeSuperClass(exprId: string) {
  if (!selectedId.value) return
  const cls = store.ontology.classes.find(c => c.id === selectedId.value)
  if (!cls) return
  store.updateClass(cls.id, { superClassExpressions: cls.superClassExpressions.filter(e => e.id !== exprId) })
}

function addDisjoint() {
  if (!selectedId.value) return
  const cls = store.ontology.classes.find(c => c.id === selectedId.value)
  if (!cls) return
  const name = prompt('互斥类名称：')
  if (!name) return
  const base = store.ontology.namespaces[0]?.iri || `${store.ontology.iri}#`
  const iri = name.includes(':') || name.includes('/') ? name : `${base}${name}`
  store.updateClass(cls.id, { disjointWith: [...cls.disjointWith, iri] })
}

function removeDisjoint(iri: string) {
  if (!selectedId.value) return
  const cls = store.ontology.classes.find(c => c.id === selectedId.value)
  if (!cls) return
  store.updateClass(cls.id, { disjointWith: cls.disjointWith.filter(d => d !== iri) })
}

function addDomain() {
  if (!selectedId.value) return
  const name = prompt('定义域类名：')
  if (!name) return
  const base = store.ontology.namespaces[0]?.iri || `${store.ontology.iri}#`
  const iri = name.includes(':') || name.includes('/') ? name : `${base}${name}`
  const op = store.ontology.objectProperties.find(p => p.id === selectedId.value)
  if (op) { store.updateObjectProperty(op.id, { domains: [...op.domains, iri] }); return }
  const dp = store.ontology.dataProperties.find(p => p.id === selectedId.value)
  if (dp) { store.updateDataProperty(dp.id, { domains: [...dp.domains, iri] }); return }
}

function removeDomain(domainIRI: string) {
  if (!selectedId.value) return
  const op = store.ontology.objectProperties.find(p => p.id === selectedId.value)
  if (op) { store.updateObjectProperty(op.id, { domains: op.domains.filter(d => d !== domainIRI) }); return }
  const dp = store.ontology.dataProperties.find(p => p.id === selectedId.value)
  if (dp) { store.updateDataProperty(dp.id, { domains: dp.domains.filter(d => d !== domainIRI) }); return }
}

function addRange() {
  if (!selectedId.value) return
  const name = prompt('值域（类名或 xsd 类型）：')
  if (!name) return
  const base = store.ontology.namespaces[0]?.iri || `${store.ontology.iri}#`
  const iri = name.includes(':') || name.includes('/') ? name : `${base}${name}`
  const op = store.ontology.objectProperties.find(p => p.id === selectedId.value)
  if (op) { store.updateObjectProperty(op.id, { ranges: [...op.ranges, iri] }); return }
  const dp = store.ontology.dataProperties.find(p => p.id === selectedId.value)
  if (dp) { store.updateDataProperty(dp.id, { ranges: [...dp.ranges, iri] }); return }
}

function removeRange(rangeIRI: string) {
  if (!selectedId.value) return
  const op = store.ontology.objectProperties.find(p => p.id === selectedId.value)
  if (op) { store.updateObjectProperty(op.id, { ranges: op.ranges.filter(r => r !== rangeIRI) }); return }
  const dp = store.ontology.dataProperties.find(p => p.id === selectedId.value)
  if (dp) { store.updateDataProperty(dp.id, { ranges: dp.ranges.filter(r => r !== rangeIRI) }); return }
}

function addAnnotation() {
  if (!selectedId.value) return
  const val = prompt('注解值（rdfs:label）：')
  if (!val) return
  const entity = selectedEntity.value
  if (!entity) return
  const newAnns = [...entity.annotations, { id: uid('ann'), property: 'rdfs:label', value: val }]
  const cls = store.ontology.classes.find(c => c.id === selectedId.value)
  if (cls) { store.updateClass(cls.id, { annotations: newAnns }); return }
  const op = store.ontology.objectProperties.find(p => p.id === selectedId.value)
  if (op) { store.updateObjectProperty(op.id, { annotations: newAnns }); return }
  const dp = store.ontology.dataProperties.find(p => p.id === selectedId.value)
  if (dp) { store.updateDataProperty(dp.id, { annotations: newAnns }); return }
  const ind = store.ontology.individuals.find(i => i.id === selectedId.value)
  if (ind) { store.updateIndividual(ind.id, { annotations: newAnns }); return }
}

function removeAnnotation(annId: string) {
  if (!selectedId.value) return
  const entity = selectedEntity.value
  if (!entity) return
  const newAnns = entity.annotations.filter(a => a.id !== annId)
  const cls = store.ontology.classes.find(c => c.id === selectedId.value)
  if (cls) { store.updateClass(cls.id, { annotations: newAnns }); return }
  const op = store.ontology.objectProperties.find(p => p.id === selectedId.value)
  if (op) { store.updateObjectProperty(op.id, { annotations: newAnns }); return }
  const dp = store.ontology.dataProperties.find(p => p.id === selectedId.value)
  if (dp) { store.updateDataProperty(dp.id, { annotations: newAnns }); return }
  const ind = store.ontology.individuals.find(i => i.id === selectedId.value)
  if (ind) { store.updateIndividual(ind.id, { annotations: newAnns }); return }
}
</script>

<style scoped>
.vb-root { height: 100%; display: flex; flex-direction: column; font-family: 'Roboto', -apple-system, sans-serif; font-size: 13px; color: #333; background: #fafafa; }
.vb-topbar { display: flex; align-items: center; justify-content: space-between; padding: 8px 16px; background: #1565c0; color: #fff; flex-shrink: 0; }
.vb-topbar__project { display: flex; align-items: center; gap: 8px; font-weight: 500; }
.vb-topbar__icon { font-size: 16px; }
.vb-topbar__name { font-size: 14px; }
.vb-topbar__actions { display: flex; gap: 8px; }
.vb-btn { padding: 5px 12px; border: 1px solid rgba(255,255,255,0.3); border-radius: 4px; background: transparent; color: #fff; font-size: 12px; cursor: pointer; }
.vb-btn:hover { background: rgba(255,255,255,0.1); }
.vb-btn--primary { background: rgba(255,255,255,0.2); border-color: rgba(255,255,255,0.5); }

.vb-nav { display: flex; background: #1976d2; padding: 0 16px; flex-shrink: 0; }
.vb-nav__item { padding: 10px 16px; color: rgba(255,255,255,0.7); cursor: pointer; font-size: 12px; font-weight: 500; display: flex; align-items: center; gap: 6px; border-bottom: 3px solid transparent; }
.vb-nav__item:hover { color: #fff; }
.vb-nav__item--active { color: #fff; border-bottom-color: #fff; }
.vb-nav__icon { font-size: 10px; }

.vb-body { flex: 1; display: flex; overflow: hidden; }
.vb-left { width: 300px; min-width: 200px; border-right: 1px solid #e0e0e0; display: flex; flex-direction: column; background: #fff; }
.vb-left__toolbar { display: flex; gap: 4px; padding: 8px; border-bottom: 1px solid #e0e0e0; }
.vb-input { flex: 1; padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 12px; }
.vb-btn-sm { width: 26px; height: 26px; border: 1px solid #ccc; border-radius: 4px; background: #fff; cursor: pointer; font-size: 16px; display: flex; align-items: center; justify-content: center; color: #555; }
.vb-btn-sm:hover { background: #e3f2fd; border-color: #1976d2; color: #1976d2; }
.vb-tree { flex: 1; overflow-y: auto; padding: 4px 0; }
.vb-tree-item { display: flex; align-items: center; gap: 8px; padding: 6px 12px; cursor: pointer; }
.vb-tree-item:hover { background: #e3f2fd; }
.vb-tree-item--selected { background: #1976d2; color: #fff; }
.vb-tree-item__icon { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }

.vb-right { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.vb-detail-header { padding: 12px 16px; border-bottom: 1px solid #e0e0e0; background: #fff; }
.vb-detail-header__name { font-size: 16px; font-weight: 600; display: block; }
.vb-detail-header__iri { font-size: 11px; color: #888; margin-top: 2px; display: block; word-break: break-all; }
.vb-detail-tabs { display: flex; background: #fff; border-bottom: 1px solid #e0e0e0; padding: 0 16px; }
.vb-detail-tab { padding: 8px 14px; font-size: 12px; cursor: pointer; color: #666; border-bottom: 2px solid transparent; }
.vb-detail-tab:hover { color: #1976d2; }
.vb-detail-tab--active { color: #1976d2; border-bottom-color: #1976d2; font-weight: 500; }
.vb-detail-body { flex: 1; overflow-y: auto; padding: 12px 16px; background: #fff; }
.vb-section { margin-bottom: 16px; }
.vb-section__title { font-size: 11px; font-weight: 600; color: #666; text-transform: uppercase; margin-bottom: 6px; }
.vb-section__content { display: flex; flex-wrap: wrap; gap: 6px; }
.vb-chip { padding: 3px 10px; background: #e3f2fd; color: #1565c0; border-radius: 12px; font-size: 12px; display: inline-flex; align-items: center; gap: 4px; }
.vb-chip__remove { cursor: pointer; font-size: 10px; color: #999; }
.vb-chip__remove:hover { color: #d00; }
.vb-input--name { font-size: 16px; font-weight: 600; border: none; border-bottom: 1px solid #e0e0e0; border-radius: 0; padding: 4px 0; width: 100%; }
.vb-input--name:focus { border-bottom-color: #1976d2; outline: none; }
.vb-muted { color: #999; font-size: 12px; }
.vb-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.vb-table th { background: #f5f5f5; border: 1px solid #e0e0e0; padding: 6px 8px; text-align: left; font-weight: 500; }
.vb-table td { border: 1px solid #e0e0e0; padding: 6px 8px; }
.vb-empty { flex: 1; display: flex; align-items: center; justify-content: center; color: #999; }
</style>
