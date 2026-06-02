<template>
  <div>
    <!-- SubClass Of -->
    <div class="pg-panel">
      <div class="pg-panel__header" @click="subOpen = !subOpen">
        <span class="pg-panel__header-icon">{{ subOpen ? '▾' : '▸' }}</span>
        <span>SubClass Of</span>
      </div>
      <div v-show="subOpen" class="pg-panel__body">
        <div v-for="expr in owlClass.superClassExpressions" :key="expr.id" class="pg-tag">
          <span>{{ expressionLabel(expr) }}</span>
          <span class="pg-tag__remove" @click="removeSuperClass(expr.id)">✕</span>
        </div>
        <div v-if="!owlClass.superClassExpressions.length" class="pg-empty" style="padding:4px">—</div>
        <button class="pg-btn" style="margin-top:4px" @click="addSuperClass">+ Add</button>
      </div>
    </div>

    <!-- Equivalent To -->
    <div class="pg-panel">
      <div class="pg-panel__header" @click="eqOpen = !eqOpen">
        <span class="pg-panel__header-icon">{{ eqOpen ? '▾' : '▸' }}</span>
        <span>Equivalent To</span>
      </div>
      <div v-show="eqOpen" class="pg-panel__body">
        <div v-for="expr in owlClass.equivalentClassExpressions" :key="expr.id" class="pg-tag">
          <span>{{ expressionLabel(expr) }}</span>
          <span class="pg-tag__remove" @click="removeEquivalent(expr.id)">✕</span>
        </div>
        <div v-if="!owlClass.equivalentClassExpressions.length" class="pg-empty" style="padding:4px">—</div>
        <button class="pg-btn" style="margin-top:4px" @click="addEquivalent">+ Add</button>
      </div>
    </div>

    <!-- Disjoint With -->
    <div class="pg-panel">
      <div class="pg-panel__header" @click="djOpen = !djOpen">
        <span class="pg-panel__header-icon">{{ djOpen ? '▾' : '▸' }}</span>
        <span>Disjoint With</span>
      </div>
      <div v-show="djOpen" class="pg-panel__body">
        <div v-for="d in owlClass.disjointWith" :key="d" class="pg-tag">
          <span>{{ d.split(/[#/]/).pop() }}</span>
          <span class="pg-tag__remove" @click="removeDisjoint(d)">✕</span>
        </div>
        <div v-if="!owlClass.disjointWith.length" class="pg-empty" style="padding:4px">—</div>
        <button class="pg-btn" style="margin-top:4px" @click="addDisjoint">+ Add</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { OwlClass, OwlClassExpression } from '../../../../../types/owl'
import { uid } from '../../../../../utils/owl/iri'
import { useOwlEditorStore } from '../../../../../store/owlEditor'

const props = defineProps<{ owlClass: OwlClass }>()
const store = useOwlEditorStore()

const subOpen = ref(true)
const eqOpen = ref(true)
const djOpen = ref(true)

function expressionLabel(expr: OwlClassExpression): string {
  if (expr.type === 'namedClass') return expr.classIRI?.split(/[#/]/).pop() || expr.classIRI || ''
  if (expr.type === 'objectSomeValuesFrom') return `${expr.propertyIRI?.split(/[#/]/).pop()} some ${expr.fillerClassIRI?.split(/[#/]/).pop()}`
  if (expr.type === 'objectAllValuesFrom') return `${expr.propertyIRI?.split(/[#/]/).pop()} only ${expr.fillerClassIRI?.split(/[#/]/).pop()}`
  if (expr.type === 'objectMinCardinality') return `${expr.propertyIRI?.split(/[#/]/).pop()} min ${expr.cardinality}`
  if (expr.type === 'objectMaxCardinality') return `${expr.propertyIRI?.split(/[#/]/).pop()} max ${expr.cardinality}`
  if (expr.type === 'objectExactCardinality') return `${expr.propertyIRI?.split(/[#/]/).pop()} exactly ${expr.cardinality}`
  return expr.type
}

function addSuperClass() {
  const className = prompt('Enter superclass IRI or name:')
  if (!className) return
  const base = store.ontology.namespaces[0]?.iri || `${store.ontology.iri}#`
  const iri = className.includes(':') || className.includes('/') ? className : `${base}${className}`
  const expr: OwlClassExpression = { id: uid('expr'), type: 'namedClass', classIRI: iri }
  store.updateClass(props.owlClass.id, { superClassExpressions: [...props.owlClass.superClassExpressions, expr] })
}

function removeSuperClass(exprId: string) {
  store.updateClass(props.owlClass.id, { superClassExpressions: props.owlClass.superClassExpressions.filter(e => e.id !== exprId) })
}

function addEquivalent() {
  const className = prompt('Enter equivalent class IRI or name:')
  if (!className) return
  const base = store.ontology.namespaces[0]?.iri || `${store.ontology.iri}#`
  const iri = className.includes(':') || className.includes('/') ? className : `${base}${className}`
  const expr: OwlClassExpression = { id: uid('expr'), type: 'namedClass', classIRI: iri }
  store.updateClass(props.owlClass.id, { equivalentClassExpressions: [...props.owlClass.equivalentClassExpressions, expr] })
}

function removeEquivalent(exprId: string) {
  store.updateClass(props.owlClass.id, { equivalentClassExpressions: props.owlClass.equivalentClassExpressions.filter(e => e.id !== exprId) })
}

function addDisjoint() {
  const className = prompt('Enter disjoint class IRI or name:')
  if (!className) return
  const base = store.ontology.namespaces[0]?.iri || `${store.ontology.iri}#`
  const iri = className.includes(':') || className.includes('/') ? className : `${base}${className}`
  store.updateClass(props.owlClass.id, { disjointWith: [...props.owlClass.disjointWith, iri] })
}

function removeDisjoint(iri: string) {
  store.updateClass(props.owlClass.id, { disjointWith: props.owlClass.disjointWith.filter(d => d !== iri) })
}
</script>
