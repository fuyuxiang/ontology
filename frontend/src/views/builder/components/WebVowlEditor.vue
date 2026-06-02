<template>
  <div class="webvowl-root">
    <div class="webvowl-toolbar">
      <button class="webvowl-btn" @click="resetZoom">Reset View</button>
      <button class="webvowl-btn" @click="toggleLabels">{{ showLabels ? 'Hide Labels' : 'Show Labels' }}</button>
      <div class="webvowl-toolbar__sep"></div>
      <button class="webvowl-btn" @click="addClassNode">+ Class</button>
      <button class="webvowl-btn" @click="addPropertyNode">+ Property</button>
      <button class="webvowl-btn" @click="addRelation">+ Relation</button>
      <button class="webvowl-btn" :disabled="!selectedNode" @click="deleteSelected">Delete</button>
      <div class="webvowl-toolbar__sep"></div>
      <span class="webvowl-info">Classes: {{ classes.length }} | Properties: {{ properties.length }}</span>
      <span style="flex:1"></span>
      <button class="webvowl-btn" @click="store.saveDraft()">Save Draft</button>
      <button class="webvowl-btn webvowl-btn--primary" @click="onImport">Import OWL</button>
      <button class="webvowl-btn" @click="onExport">Export OWL</button>
    </div>
    <div class="webvowl-main">
      <div class="webvowl-canvas" ref="canvasRef"></div>
      <!-- Right sidebar for editing -->
      <div class="webvowl-sidebar" :class="{ 'webvowl-sidebar--open': selectedNode }">
        <template v-if="selectedNode">
          <div class="webvowl-sidebar__header">
            <span class="webvowl-sidebar__icon" :style="{ background: selectedNode.color }"></span>
            <span>{{ selectedNode.label }}</span>
          </div>
          <div class="webvowl-sidebar__section">
            <div class="webvowl-sidebar__label">Name</div>
            <input class="webvowl-input" :value="selectedNode.label" @change="renameSelected(($event.target as HTMLInputElement).value)" />
          </div>
          <div class="webvowl-sidebar__section">
            <div class="webvowl-sidebar__label">IRI</div>
            <div class="webvowl-sidebar__value">{{ selectedNode.iri }}</div>
          </div>
          <div class="webvowl-sidebar__section">
            <div class="webvowl-sidebar__label">Type</div>
            <div class="webvowl-sidebar__value">{{ selectedNode.type }}</div>
          </div>
          <div class="webvowl-sidebar__section" v-if="selectedNode.type === 'class'">
            <div class="webvowl-sidebar__label">Annotations</div>
            <button class="webvowl-btn-sm" @click="addAnnotation">+ Add Label</button>
          </div>
          <div class="webvowl-sidebar__section">
            <button class="webvowl-btn webvowl-btn--danger" @click="deleteSelected">Delete this entity</button>
          </div>
        </template>
        <div v-else class="webvowl-sidebar__empty">Click a node to edit</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, computed } from 'vue'
import * as d3 from 'd3-force'
import { useOwlEditorStore } from '../../../store/owlEditor'
import { uid } from '../../../utils/owl/iri'

const store = useOwlEditorStore()
const canvasRef = ref<HTMLElement | null>(null)
const showLabels = ref(true)
const selectedNode = ref<{ label: string; iri: string; type: string; color: string; description?: string } | null>(null)

interface VNode {
  id: string
  label: string
  iri: string
  type: 'class' | 'objectProperty' | 'dataProperty' | 'datatype'
  x?: number
  y?: number
  fx?: number | null
  fy?: number | null
}

interface VLink {
  source: string
  target: string
  label: string
}

const classes = computed(() => store.ontology.classes)
const properties = computed(() => [...store.ontology.objectProperties, ...store.ontology.dataProperties])

let svg: any = null
let simulation: any = null

function buildGraph() {
  const nodes: VNode[] = []
  const links: VLink[] = []

  for (const c of store.ontology.classes) {
    nodes.push({ id: c.id, label: c.localName, iri: c.iri, type: 'class' })
  }
  for (const p of store.ontology.objectProperties) {
    nodes.push({ id: p.id, label: p.localName, iri: p.iri, type: 'objectProperty' })
    for (const d of p.domains) {
      const domainNode = store.ontology.classes.find(c => c.iri === d)
      if (domainNode) links.push({ source: domainNode.id, target: p.id, label: 'domain' })
    }
    for (const r of p.ranges) {
      const rangeNode = store.ontology.classes.find(c => c.iri === r)
      if (rangeNode) links.push({ source: p.id, target: rangeNode.id, label: 'range' })
    }
  }
  for (const c of store.ontology.classes) {
    for (const sup of c.superClassExpressions) {
      if (sup.type === 'namedClass' && sup.classIRI) {
        const parent = store.ontology.classes.find(cl => cl.iri === sup.classIRI)
        if (parent) links.push({ source: c.id, target: parent.id, label: 'subClassOf' })
      }
    }
  }

  return { nodes, links }
}

function getColor(type: string): string {
  switch (type) {
    case 'class': return '#5b9bd5'
    case 'objectProperty': return '#7b68ee'
    case 'dataProperty': return '#3cb371'
    case 'datatype': return '#ffa500'
    default: return '#999'
  }
}

function getRadius(type: string): number {
  return type === 'class' ? 40 : 28
}

function render() {
  if (!canvasRef.value) return
  const container = canvasRef.value
  container.innerHTML = ''

  const width = container.clientWidth
  const height = container.clientHeight
  const { nodes, links } = buildGraph()

  const svgEl = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
  svgEl.setAttribute('width', '100%')
  svgEl.setAttribute('height', '100%')
  svgEl.setAttribute('viewBox', `0 0 ${width} ${height}`)
  container.appendChild(svgEl)

  const g = document.createElementNS('http://www.w3.org/2000/svg', 'g')
  svgEl.appendChild(g)

  // Zoom
  let currentTransform = { x: 0, y: 0, k: 1 }
  svgEl.addEventListener('wheel', (e) => {
    e.preventDefault()
    const scaleFactor = e.deltaY > 0 ? 0.9 : 1.1
    currentTransform.k *= scaleFactor
    currentTransform.k = Math.max(0.1, Math.min(4, currentTransform.k))
    g.setAttribute('transform', `translate(${currentTransform.x},${currentTransform.y}) scale(${currentTransform.k})`)
  })

  // Links
  const linkEls: SVGLineElement[] = []
  const linkLabelEls: SVGTextElement[] = []
  for (const link of links) {
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line')
    line.setAttribute('stroke', '#999')
    line.setAttribute('stroke-width', '1.5')
    line.setAttribute('stroke-opacity', '0.6')
    g.appendChild(line)
    linkEls.push(line)

    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text')
    text.setAttribute('font-size', '9')
    text.setAttribute('fill', '#666')
    text.setAttribute('text-anchor', 'middle')
    text.textContent = link.label
    g.appendChild(text)
    linkLabelEls.push(text)
  }

  // Nodes
  const nodeEls: SVGGElement[] = []
  for (const node of nodes) {
    const nodeG = document.createElementNS('http://www.w3.org/2000/svg', 'g')
    nodeG.style.cursor = 'pointer'

    const radius = getRadius(node.type)
    const color = getColor(node.type)

    if (node.type === 'class') {
      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle')
      circle.setAttribute('r', String(radius))
      circle.setAttribute('fill', color)
      circle.setAttribute('stroke', '#fff')
      circle.setAttribute('stroke-width', '2')
      circle.setAttribute('opacity', '0.85')
      nodeG.appendChild(circle)
    } else {
      const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect')
      rect.setAttribute('width', String(radius * 2))
      rect.setAttribute('height', String(radius))
      rect.setAttribute('x', String(-radius))
      rect.setAttribute('y', String(-radius / 2))
      rect.setAttribute('rx', '4')
      rect.setAttribute('fill', color)
      rect.setAttribute('stroke', '#fff')
      rect.setAttribute('stroke-width', '2')
      rect.setAttribute('opacity', '0.85')
      nodeG.appendChild(rect)
    }

    const label = document.createElementNS('http://www.w3.org/2000/svg', 'text')
    label.setAttribute('text-anchor', 'middle')
    label.setAttribute('dy', '4')
    label.setAttribute('font-size', '10')
    label.setAttribute('fill', '#fff')
    label.setAttribute('font-weight', '600')
    label.textContent = node.label.length > 12 ? node.label.slice(0, 11) + '…' : node.label
    label.classList.add('vowl-label')
    nodeG.appendChild(label)

    nodeG.addEventListener('click', () => {
      selectedNode.value = { label: node.label, iri: node.iri, type: node.type, color }
    })

    g.appendChild(nodeG)
    nodeEls.push(nodeG)
  }

  // Simulation
  const nodeMap = new Map(nodes.map((n, i) => [n.id, i]))
  const simLinks = links.map(l => ({ source: nodeMap.get(l.source) || 0, target: nodeMap.get(l.target) || 0 }))

  simulation = d3.forceSimulation(nodes as any)
    .force('link', d3.forceLink(simLinks).distance(120))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .on('tick', () => {
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i] as any
        nodeEls[i].setAttribute('transform', `translate(${n.x},${n.y})`)
      }
      for (let i = 0; i < links.length; i++) {
        const s = nodes[simLinks[i].source as number] as any
        const t = nodes[simLinks[i].target as number] as any
        if (s && t) {
          linkEls[i].setAttribute('x1', s.x)
          linkEls[i].setAttribute('y1', s.y)
          linkEls[i].setAttribute('x2', t.x)
          linkEls[i].setAttribute('y2', t.y)
          linkLabelEls[i].setAttribute('x', (s.x + t.x) / 2)
          linkLabelEls[i].setAttribute('y', (s.y + t.y) / 2 - 4)
        }
      }
    })

  svg = svgEl
}

function resetZoom() {
  if (svg) {
    const g = svg.querySelector('g')
    if (g) g.setAttribute('transform', 'translate(0,0) scale(1)')
  }
}

function toggleLabels() {
  showLabels.value = !showLabels.value
  if (svg) {
    const labels = svg.querySelectorAll('.vowl-label')
    labels.forEach((l: SVGElement) => { l.style.display = showLabels.value ? '' : 'none' })
  }
}

function onImport() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.owl,.xml,.rdf'
  input.onchange = async () => {
    const file = input.files?.[0]
    if (!file) return
    const text = await file.text()
    store.importOwlXml(text)
    render()
  }
  input.click()
}

function onExport() {
  store.exportAndDownload()
}

function addClassNode() {
  const name = prompt('Class name:')
  if (!name) return
  const base = store.ontology.namespaces[0]?.iri || `${store.ontology.iri}#`
  store.addClass()
  const c = store.ontology.classes[store.ontology.classes.length - 1]
  if (c) store.updateClass(c.id, { localName: name, iri: `${base}${name}` })
  render()
}

function addPropertyNode() {
  const name = prompt('Object Property name:')
  if (!name) return
  const base = store.ontology.namespaces[0]?.iri || `${store.ontology.iri}#`
  store.addObjectProperty()
  const p = store.ontology.objectProperties[store.ontology.objectProperties.length - 1]
  if (p) store.updateObjectProperty(p.id, { localName: name, iri: `${base}${name}` })
  render()
}

function addRelation() {
  if (store.ontology.classes.length < 2) { alert('Need at least 2 classes to add a relation.'); return }
  const domain = prompt('Domain class name (source):')
  const range = prompt('Range class name (target):')
  const propName = prompt('Property name:')
  if (!domain || !range || !propName) return
  const domainClass = store.ontology.classes.find(c => c.localName === domain)
  const rangeClass = store.ontology.classes.find(c => c.localName === range)
  if (!domainClass || !rangeClass) { alert('Class not found.'); return }
  const base = store.ontology.namespaces[0]?.iri || `${store.ontology.iri}#`
  store.addObjectProperty()
  const p = store.ontology.objectProperties[store.ontology.objectProperties.length - 1]
  if (p) store.updateObjectProperty(p.id, { localName: propName, iri: `${base}${propName}`, domains: [domainClass.iri], ranges: [rangeClass.iri] })
  render()
}

function deleteSelected() {
  if (!selectedNode.value) return
  const cls = store.ontology.classes.find(c => c.iri === selectedNode.value!.iri)
  if (cls) { store.deleteClass(cls.id); selectedNode.value = null; render(); return }
  const op = store.ontology.objectProperties.find(p => p.iri === selectedNode.value!.iri)
  if (op) { store.deleteObjectProperty(op.id); selectedNode.value = null; render(); return }
  const dp = store.ontology.dataProperties.find(p => p.iri === selectedNode.value!.iri)
  if (dp) { store.deleteDataProperty(dp.id); selectedNode.value = null; render(); return }
}

function renameSelected(newName: string) {
  if (!selectedNode.value || !newName) return
  const base = store.ontology.namespaces[0]?.iri || `${store.ontology.iri}#`
  const cls = store.ontology.classes.find(c => c.iri === selectedNode.value!.iri)
  if (cls) { store.updateClass(cls.id, { localName: newName, iri: `${base}${newName}` }); selectedNode.value = { ...selectedNode.value, label: newName, iri: `${base}${newName}` }; render(); return }
  const op = store.ontology.objectProperties.find(p => p.iri === selectedNode.value!.iri)
  if (op) { store.updateObjectProperty(op.id, { localName: newName, iri: `${base}${newName}` }); selectedNode.value = { ...selectedNode.value, label: newName, iri: `${base}${newName}` }; render(); return }
}

function addAnnotation() {
  if (!selectedNode.value) return
  const cls = store.ontology.classes.find(c => c.iri === selectedNode.value!.iri)
  if (!cls) return
  const val = prompt('Label value:')
  if (!val) return
  store.updateClass(cls.id, { annotations: [...cls.annotations, { id: uid('ann'), property: 'rdfs:label', value: val }] })
}

onMounted(() => {
  render()
})

watch(() => [store.ontology.classes.length, store.ontology.objectProperties.length, store.ontology.dataProperties.length], () => {
  render()
})

onBeforeUnmount(() => {
  if (simulation) simulation.stop()
})
</script>

<style scoped>
.webvowl-root {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #1a1a2e;
  color: #e0e0e0;
  font-family: -apple-system, 'Segoe UI', sans-serif;
  font-size: 12px;
  position: relative;
}
.webvowl-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #16213e;
  border-bottom: 1px solid #2a2a4a;
  flex-shrink: 0;
}
.webvowl-btn {
  padding: 4px 10px;
  border: 1px solid #3a3a5a;
  border-radius: 4px;
  background: #2a2a4a;
  color: #e0e0e0;
  font-size: 11px;
  cursor: pointer;
}
.webvowl-btn:hover { background: #3a3a5a; }
.webvowl-btn:disabled { opacity: 0.4; cursor: default; }
.webvowl-btn--primary { background: #4a6fa5; border-color: #5a8fd4; }
.webvowl-btn--primary:hover { background: #5a8fd4; }
.webvowl-btn--danger { background: #8b2020; border-color: #a03030; }
.webvowl-btn--danger:hover { background: #a03030; }
.webvowl-btn-sm { padding: 3px 8px; border: 1px solid #3a3a5a; border-radius: 3px; background: #2a2a4a; color: #e0e0e0; font-size: 11px; cursor: pointer; }
.webvowl-toolbar__sep { width: 1px; height: 18px; background: #3a3a5a; }
.webvowl-info { font-size: 11px; color: #888; }
.webvowl-main { flex: 1; display: flex; overflow: hidden; position: relative; }
.webvowl-canvas {
  flex: 1;
  overflow: hidden;
  background: radial-gradient(ellipse at center, #1a1a2e 0%, #0f0f1a 100%);
}
.webvowl-sidebar {
  width: 280px;
  background: #16213e;
  border-left: 1px solid #2a2a4a;
  padding: 12px;
  overflow-y: auto;
  flex-shrink: 0;
}
.webvowl-sidebar__empty { color: #666; text-align: center; padding: 32px 12px; }
.webvowl-input {
  width: 100%;
  padding: 4px 8px;
  border: 1px solid #3a3a5a;
  border-radius: 3px;
  background: #0f0f1a;
  color: #e0e0e0;
  font-size: 12px;
}
.webvowl-sidebar__header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
}
.webvowl-sidebar__icon {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}
.webvowl-sidebar__section {
  margin-bottom: 10px;
}
.webvowl-sidebar__label {
  font-size: 10px;
  color: #888;
  text-transform: uppercase;
  margin-bottom: 2px;
}
.webvowl-sidebar__value {
  font-size: 12px;
  word-break: break-all;
}
</style>
