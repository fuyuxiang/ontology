import type { OwlOntology, OwlClass, OwlObjectProperty, OwlDataProperty, OwlIndividual, OwlClassExpression, OwlAnnotation, OwlNamespace, OwlObjectPropertyAssertion, OwlDataPropertyAssertion } from '../../types/owl'
import { uid } from './iri'

function getIRI(el: Element): string {
  return el.getAttribute('IRI') || el.getAttribute('abbreviatedIRI') || ''
}

function parseClassExpression(el: Element): OwlClassExpression | null {
  const tag = el.localName
  const id = uid('expr')

  if (tag === 'Class') {
    return { id, type: 'namedClass', classIRI: getIRI(el) }
  }
  if (tag === 'ObjectSomeValuesFrom') {
    const prop = el.querySelector(':scope > ObjectProperty')
    const filler = el.querySelector(':scope > Class')
    return { id, type: 'objectSomeValuesFrom', propertyIRI: prop ? getIRI(prop) : '', fillerClassIRI: filler ? getIRI(filler) : '' }
  }
  if (tag === 'ObjectAllValuesFrom') {
    const prop = el.querySelector(':scope > ObjectProperty')
    const filler = el.querySelector(':scope > Class')
    return { id, type: 'objectAllValuesFrom', propertyIRI: prop ? getIRI(prop) : '', fillerClassIRI: filler ? getIRI(filler) : '' }
  }
  if (tag === 'ObjectMinCardinality' || tag === 'ObjectMaxCardinality' || tag === 'ObjectExactCardinality') {
    const typeMap: Record<string, OwlClassExpression['type']> = {
      ObjectMinCardinality: 'objectMinCardinality',
      ObjectMaxCardinality: 'objectMaxCardinality',
      ObjectExactCardinality: 'objectExactCardinality',
    }
    const prop = el.querySelector(':scope > ObjectProperty')
    const filler = el.querySelector(':scope > Class')
    return { id, type: typeMap[tag], propertyIRI: prop ? getIRI(prop) : '', fillerClassIRI: filler ? getIRI(filler) : '', cardinality: parseInt(el.getAttribute('cardinality') || '0') }
  }
  if (tag === 'ObjectIntersectionOf' || tag === 'ObjectUnionOf') {
    const operands = Array.from(el.children).map(parseClassExpression).filter(Boolean) as OwlClassExpression[]
    return { id, type: tag === 'ObjectIntersectionOf' ? 'objectIntersectionOf' : 'objectUnionOf', operands }
  }
  if (tag === 'ObjectComplementOf') {
    const child = el.firstElementChild
    const operand = child ? parseClassExpression(child) : null
    return { id, type: 'objectComplementOf', operands: operand ? [operand] : [] }
  }
  if (tag === 'ObjectHasValue') {
    const prop = el.querySelector(':scope > ObjectProperty')
    const ind = el.querySelector(':scope > NamedIndividual')
    return { id, type: 'objectHasValue', propertyIRI: prop ? getIRI(prop) : '', individualIRI: ind ? getIRI(ind) : '' }
  }
  return null
}

export function parseOwlXml(xml: string): OwlOntology {
  const parser = new DOMParser()
  const doc = parser.parseFromString(xml, 'application/xml')
  const root = doc.documentElement

  const ontologyIRI = root.getAttribute('ontologyIRI') || 'http://example.org/ontology'
  const versionIRI = root.getAttribute('versionIRI') || undefined

  const namespaces: OwlNamespace[] = []
  const prefixEls = root.querySelectorAll(':scope > Prefix')
  prefixEls.forEach(el => {
    const prefix = el.getAttribute('name') || ''
    const iri = el.getAttribute('IRI') || ''
    if (prefix && iri) namespaces.push({ prefix, iri })
  })

  const classes: OwlClass[] = []
  const objectProperties: OwlObjectProperty[] = []
  const dataProperties: OwlDataProperty[] = []
  const individuals: OwlIndividual[] = []
  const annotations: OwlAnnotation[] = []

  const classMap = new Map<string, OwlClass>()
  const opMap = new Map<string, OwlObjectProperty>()
  const dpMap = new Map<string, OwlDataProperty>()
  const indMap = new Map<string, OwlIndividual>()

  function getOrCreateClass(classIRI: string): OwlClass {
    if (!classMap.has(classIRI)) {
      const c: OwlClass = { id: uid('cls'), iri: classIRI, localName: classIRI.split(/[#/]/).pop() || '', annotations: [], superClassExpressions: [], equivalentClassExpressions: [], disjointWith: [] }
      classMap.set(classIRI, c)
      classes.push(c)
    }
    return classMap.get(classIRI)!
  }

  function getOrCreateOP(propIRI: string): OwlObjectProperty {
    if (!opMap.has(propIRI)) {
      const p: OwlObjectProperty = { id: uid('op'), iri: propIRI, localName: propIRI.split(/[#/]/).pop() || '', annotations: [], superProperties: [], domains: [], ranges: [], characteristics: [], inverseOf: null }
      opMap.set(propIRI, p)
      objectProperties.push(p)
    }
    return opMap.get(propIRI)!
  }

  function getOrCreateDP(propIRI: string): OwlDataProperty {
    if (!dpMap.has(propIRI)) {
      const p: OwlDataProperty = { id: uid('dp'), iri: propIRI, localName: propIRI.split(/[#/]/).pop() || '', annotations: [], superProperties: [], domains: [], ranges: [], functional: false }
      dpMap.set(propIRI, p)
      dataProperties.push(p)
    }
    return dpMap.get(propIRI)!
  }

  function getOrCreateInd(indIRI: string): OwlIndividual {
    if (!indMap.has(indIRI)) {
      const ind: OwlIndividual = { id: uid('ind'), iri: indIRI, localName: indIRI.split(/[#/]/).pop() || '', annotations: [], types: [], objectPropertyAssertions: [], dataPropertyAssertions: [], sameAs: [], differentFrom: [] }
      indMap.set(indIRI, ind)
      individuals.push(ind)
    }
    return indMap.get(indIRI)!
  }

  for (const el of Array.from(root.children)) {
    const tag = el.localName

    if (tag === 'Declaration') {
      const child = el.firstElementChild
      if (!child) continue
      const childTag = child.localName
      const childIRI = getIRI(child)
      if (childTag === 'Class') getOrCreateClass(childIRI)
      else if (childTag === 'ObjectProperty') getOrCreateOP(childIRI)
      else if (childTag === 'DataProperty') getOrCreateDP(childIRI)
      else if (childTag === 'NamedIndividual') getOrCreateInd(childIRI)
    }

    else if (tag === 'SubClassOf') {
      const children = Array.from(el.children)
      if (children.length >= 2) {
        const subClassIRI = getIRI(children[0])
        const superExpr = parseClassExpression(children[1])
        if (subClassIRI && superExpr) {
          getOrCreateClass(subClassIRI).superClassExpressions.push(superExpr)
        }
      }
    }

    else if (tag === 'EquivalentClasses') {
      const children = Array.from(el.children)
      if (children.length >= 2) {
        const classIRI = getIRI(children[0])
        const expr = parseClassExpression(children[1])
        if (classIRI && expr) {
          getOrCreateClass(classIRI).equivalentClassExpressions.push(expr)
        }
      }
    }

    else if (tag === 'DisjointClasses') {
      const children = Array.from(el.children)
      if (children.length >= 2) {
        const iri1 = getIRI(children[0])
        const iri2 = getIRI(children[1])
        if (iri1 && iri2) {
          getOrCreateClass(iri1).disjointWith.push(iri2)
        }
      }
    }

    else if (tag === 'SubObjectPropertyOf') {
      const props = el.querySelectorAll(':scope > ObjectProperty')
      if (props.length >= 2) {
        getOrCreateOP(getIRI(props[0])).superProperties.push(getIRI(props[1]))
      }
    }

    else if (tag === 'ObjectPropertyDomain') {
      const prop = el.querySelector(':scope > ObjectProperty')
      const cls = el.querySelector(':scope > Class')
      if (prop && cls) getOrCreateOP(getIRI(prop)).domains.push(getIRI(cls))
    }

    else if (tag === 'ObjectPropertyRange') {
      const prop = el.querySelector(':scope > ObjectProperty')
      const cls = el.querySelector(':scope > Class')
      if (prop && cls) getOrCreateOP(getIRI(prop)).ranges.push(getIRI(cls))
    }

    else if (tag === 'InverseObjectProperties') {
      const props = el.querySelectorAll(':scope > ObjectProperty')
      if (props.length >= 2) {
        getOrCreateOP(getIRI(props[0])).inverseOf = getIRI(props[1])
      }
    }

    else if (tag.endsWith('ObjectProperty') && tag !== 'ObjectProperty') {
      const prop = el.querySelector(':scope > ObjectProperty')
      if (prop) {
        const charMap: Record<string, string> = {
          FunctionalObjectProperty: 'functional',
          InverseFunctionalObjectProperty: 'inverseFunctional',
          TransitiveObjectProperty: 'transitive',
          SymmetricObjectProperty: 'symmetric',
          AsymmetricObjectProperty: 'asymmetric',
          ReflexiveObjectProperty: 'reflexive',
          IrreflexiveObjectProperty: 'irreflexive',
        }
        const ch = charMap[tag]
        if (ch) getOrCreateOP(getIRI(prop)).characteristics.push(ch as any)
      }
    }

    else if (tag === 'SubDataPropertyOf') {
      const props = el.querySelectorAll(':scope > DataProperty')
      if (props.length >= 2) {
        getOrCreateDP(getIRI(props[0])).superProperties.push(getIRI(props[1]))
      }
    }

    else if (tag === 'DataPropertyDomain') {
      const prop = el.querySelector(':scope > DataProperty')
      const cls = el.querySelector(':scope > Class')
      if (prop && cls) getOrCreateDP(getIRI(prop)).domains.push(getIRI(cls))
    }

    else if (tag === 'DataPropertyRange') {
      const prop = el.querySelector(':scope > DataProperty')
      const dt = el.querySelector(':scope > Datatype')
      if (prop && dt) getOrCreateDP(getIRI(prop)).ranges.push(getIRI(dt))
    }

    else if (tag === 'FunctionalDataProperty') {
      const prop = el.querySelector(':scope > DataProperty')
      if (prop) getOrCreateDP(getIRI(prop)).functional = true
    }

    else if (tag === 'ClassAssertion') {
      const cls = el.querySelector(':scope > Class')
      const ind = el.querySelector(':scope > NamedIndividual')
      if (cls && ind) getOrCreateInd(getIRI(ind)).types.push(getIRI(cls))
    }

    else if (tag === 'ObjectPropertyAssertion') {
      const prop = el.querySelector(':scope > ObjectProperty')
      const inds = el.querySelectorAll(':scope > NamedIndividual')
      if (prop && inds.length >= 2) {
        const assertion: OwlObjectPropertyAssertion = { id: uid('opa'), propertyIRI: getIRI(prop), targetIndividualIRI: getIRI(inds[1]) }
        getOrCreateInd(getIRI(inds[0])).objectPropertyAssertions.push(assertion)
      }
    }

    else if (tag === 'DataPropertyAssertion') {
      const prop = el.querySelector(':scope > DataProperty')
      const ind = el.querySelector(':scope > NamedIndividual')
      const lit = el.querySelector(':scope > Literal')
      if (prop && ind && lit) {
        const assertion: OwlDataPropertyAssertion = { id: uid('dpa'), propertyIRI: getIRI(prop), value: lit.textContent || '', datatype: lit.getAttribute('datatypeIRI') || 'xsd:string' }
        getOrCreateInd(getIRI(ind)).dataPropertyAssertions.push(assertion)
      }
    }

    else if (tag === 'AnnotationAssertion') {
      const apEl = el.querySelector(':scope > AnnotationProperty')
      const iriEl = el.querySelector(':scope > IRI')
      const litEl = el.querySelector(':scope > Literal')
      if (apEl && litEl) {
        const subjectIRI = iriEl?.textContent || ontologyIRI
        const ann: OwlAnnotation = { id: uid('ann'), property: getIRI(apEl), value: litEl.textContent || '', language: litEl.getAttribute('xml:lang') || undefined }
        const target = classMap.get(subjectIRI) || opMap.get(subjectIRI) || dpMap.get(subjectIRI) || indMap.get(subjectIRI)
        if (target) target.annotations.push(ann)
        else annotations.push(ann)
      }
    }
  }

  return { id: uid('ont'), iri: ontologyIRI, versionIRI, annotations, namespaces, classes, objectProperties, dataProperties, individuals }
}
