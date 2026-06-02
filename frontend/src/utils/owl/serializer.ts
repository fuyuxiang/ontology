import type { OwlOntology, OwlClass, OwlObjectProperty, OwlDataProperty, OwlIndividual, OwlClassExpression, OwlAnnotation } from '../../types/owl'
import { BUILTIN_NAMESPACES } from './iri'

function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

function iri(value: string): string {
  if (value.includes(':') && !value.startsWith('http')) {
    return `abbreviatedIRI="${esc(value)}"`
  }
  return `IRI="${esc(value)}"`
}

function serializeAnnotation(a: OwlAnnotation, subjectIRI: string): string {
  const lang = a.language ? ` xml:lang="${esc(a.language)}"` : ''
  const dt = a.datatype ? ` datatypeIRI="${esc(a.datatype)}"` : ''
  return `    <AnnotationAssertion>
        <AnnotationProperty ${iri(a.property)}/>
        <IRI>${esc(subjectIRI)}</IRI>
        <Literal${lang}${dt}>${esc(a.value)}</Literal>
    </AnnotationAssertion>`
}

function serializeClassExpression(expr: OwlClassExpression): string {
  switch (expr.type) {
    case 'namedClass':
      return `<Class ${iri(expr.classIRI || '')}/>`
    case 'objectSomeValuesFrom':
      return `<ObjectSomeValuesFrom>
            <ObjectProperty ${iri(expr.propertyIRI || '')}/>
            <Class ${iri(expr.fillerClassIRI || '')}/>
        </ObjectSomeValuesFrom>`
    case 'objectAllValuesFrom':
      return `<ObjectAllValuesFrom>
            <ObjectProperty ${iri(expr.propertyIRI || '')}/>
            <Class ${iri(expr.fillerClassIRI || '')}/>
        </ObjectAllValuesFrom>`
    case 'objectMinCardinality':
      return `<ObjectMinCardinality cardinality="${expr.cardinality || 0}">
            <ObjectProperty ${iri(expr.propertyIRI || '')}/>
            <Class ${iri(expr.fillerClassIRI || '')}/>
        </ObjectMinCardinality>`
    case 'objectMaxCardinality':
      return `<ObjectMaxCardinality cardinality="${expr.cardinality || 0}">
            <ObjectProperty ${iri(expr.propertyIRI || '')}/>
            <Class ${iri(expr.fillerClassIRI || '')}/>
        </ObjectMaxCardinality>`
    case 'objectExactCardinality':
      return `<ObjectExactCardinality cardinality="${expr.cardinality || 0}">
            <ObjectProperty ${iri(expr.propertyIRI || '')}/>
            <Class ${iri(expr.fillerClassIRI || '')}/>
        </ObjectExactCardinality>`
    case 'objectIntersectionOf':
      return `<ObjectIntersectionOf>
            ${(expr.operands || []).map(serializeClassExpression).join('\n            ')}
        </ObjectIntersectionOf>`
    case 'objectUnionOf':
      return `<ObjectUnionOf>
            ${(expr.operands || []).map(serializeClassExpression).join('\n            ')}
        </ObjectUnionOf>`
    case 'objectComplementOf':
      return `<ObjectComplementOf>
            ${expr.operands?.[0] ? serializeClassExpression(expr.operands[0]) : ''}
        </ObjectComplementOf>`
    case 'objectHasValue':
      return `<ObjectHasValue>
            <ObjectProperty ${iri(expr.propertyIRI || '')}/>
            <NamedIndividual ${iri(expr.individualIRI || '')}/>
        </ObjectHasValue>`
    case 'dataSomeValuesFrom':
      return `<DataSomeValuesFrom>
            <DataProperty ${iri(expr.propertyIRI || '')}/>
            <Datatype ${iri(expr.fillerDatatype || 'xsd:string')}/>
        </DataSomeValuesFrom>`
    case 'dataAllValuesFrom':
      return `<DataAllValuesFrom>
            <DataProperty ${iri(expr.propertyIRI || '')}/>
            <Datatype ${iri(expr.fillerDatatype || 'xsd:string')}/>
        </DataAllValuesFrom>`
    default:
      return `<Class IRI="http://www.w3.org/2002/07/owl#Thing"/>`
  }
}

function serializeClass(c: OwlClass, ontology: OwlOntology): string {
  const lines: string[] = []
  lines.push(`    <Declaration><Class ${iri(c.iri)}/></Declaration>`)

  for (const sup of c.superClassExpressions) {
    lines.push(`    <SubClassOf>
        <Class ${iri(c.iri)}/>
        ${serializeClassExpression(sup)}
    </SubClassOf>`)
  }
  for (const eq of c.equivalentClassExpressions) {
    lines.push(`    <EquivalentClasses>
        <Class ${iri(c.iri)}/>
        ${serializeClassExpression(eq)}
    </EquivalentClasses>`)
  }
  if (c.disjointWith.length > 0) {
    for (const dj of c.disjointWith) {
      lines.push(`    <DisjointClasses>
        <Class ${iri(c.iri)}/>
        <Class ${iri(dj)}/>
    </DisjointClasses>`)
    }
  }
  for (const a of c.annotations) {
    lines.push(serializeAnnotation(a, c.iri))
  }
  return lines.join('\n')
}

function serializeObjectProperty(p: OwlObjectProperty): string {
  const lines: string[] = []
  lines.push(`    <Declaration><ObjectProperty ${iri(p.iri)}/></Declaration>`)

  for (const sup of p.superProperties) {
    lines.push(`    <SubObjectPropertyOf>
        <ObjectProperty ${iri(p.iri)}/>
        <ObjectProperty ${iri(sup)}/>
    </SubObjectPropertyOf>`)
  }
  for (const d of p.domains) {
    lines.push(`    <ObjectPropertyDomain>
        <ObjectProperty ${iri(p.iri)}/>
        <Class ${iri(d)}/>
    </ObjectPropertyDomain>`)
  }
  for (const r of p.ranges) {
    lines.push(`    <ObjectPropertyRange>
        <ObjectProperty ${iri(p.iri)}/>
        <Class ${iri(r)}/>
    </ObjectPropertyRange>`)
  }
  for (const ch of p.characteristics) {
    const tag = {
      functional: 'FunctionalObjectProperty',
      inverseFunctional: 'InverseFunctionalObjectProperty',
      transitive: 'TransitiveObjectProperty',
      symmetric: 'SymmetricObjectProperty',
      asymmetric: 'AsymmetricObjectProperty',
      reflexive: 'ReflexiveObjectProperty',
      irreflexive: 'IrreflexiveObjectProperty',
    }[ch]
    lines.push(`    <${tag}><ObjectProperty ${iri(p.iri)}/></${tag}>`)
  }
  if (p.inverseOf) {
    lines.push(`    <InverseObjectProperties>
        <ObjectProperty ${iri(p.iri)}/>
        <ObjectProperty ${iri(p.inverseOf)}/>
    </InverseObjectProperties>`)
  }
  for (const a of p.annotations) {
    lines.push(serializeAnnotation(a, p.iri))
  }
  return lines.join('\n')
}

function serializeDataProperty(p: OwlDataProperty): string {
  const lines: string[] = []
  lines.push(`    <Declaration><DataProperty ${iri(p.iri)}/></Declaration>`)

  for (const sup of p.superProperties) {
    lines.push(`    <SubDataPropertyOf>
        <DataProperty ${iri(p.iri)}/>
        <DataProperty ${iri(sup)}/>
    </SubDataPropertyOf>`)
  }
  for (const d of p.domains) {
    lines.push(`    <DataPropertyDomain>
        <DataProperty ${iri(p.iri)}/>
        <Class ${iri(d)}/>
    </DataPropertyDomain>`)
  }
  for (const r of p.ranges) {
    lines.push(`    <DataPropertyRange>
        <DataProperty ${iri(p.iri)}/>
        <Datatype ${iri(r)}/>
    </DataPropertyRange>`)
  }
  if (p.functional) {
    lines.push(`    <FunctionalDataProperty><DataProperty ${iri(p.iri)}/></FunctionalDataProperty>`)
  }
  for (const a of p.annotations) {
    lines.push(serializeAnnotation(a, p.iri))
  }
  return lines.join('\n')
}

function serializeIndividual(ind: OwlIndividual): string {
  const lines: string[] = []
  lines.push(`    <Declaration><NamedIndividual ${iri(ind.iri)}/></Declaration>`)

  for (const t of ind.types) {
    lines.push(`    <ClassAssertion>
        <Class ${iri(t)}/>
        <NamedIndividual ${iri(ind.iri)}/>
    </ClassAssertion>`)
  }
  for (const opa of ind.objectPropertyAssertions) {
    lines.push(`    <ObjectPropertyAssertion>
        <ObjectProperty ${iri(opa.propertyIRI)}/>
        <NamedIndividual ${iri(ind.iri)}/>
        <NamedIndividual ${iri(opa.targetIndividualIRI)}/>
    </ObjectPropertyAssertion>`)
  }
  for (const dpa of ind.dataPropertyAssertions) {
    lines.push(`    <DataPropertyAssertion>
        <DataProperty ${iri(dpa.propertyIRI)}/>
        <NamedIndividual ${iri(ind.iri)}/>
        <Literal datatypeIRI="${esc(dpa.datatype)}">${esc(dpa.value)}</Literal>
    </DataPropertyAssertion>`)
  }
  for (const s of ind.sameAs) {
    lines.push(`    <SameIndividual>
        <NamedIndividual ${iri(ind.iri)}/>
        <NamedIndividual ${iri(s)}/>
    </SameIndividual>`)
  }
  for (const d of ind.differentFrom) {
    lines.push(`    <DifferentIndividuals>
        <NamedIndividual ${iri(ind.iri)}/>
        <NamedIndividual ${iri(d)}/>
    </DifferentIndividuals>`)
  }
  for (const a of ind.annotations) {
    lines.push(serializeAnnotation(a, ind.iri))
  }
  return lines.join('\n')
}

export function serializeToOwlXml(ontology: OwlOntology): string {
  const allNs = [...BUILTIN_NAMESPACES, ...ontology.namespaces]
  const nsAttrs = allNs.map(ns => `    xmlns:${ns.prefix}="${ns.iri}"`).join('\n')

  const prefixes = allNs.map(ns => `    <Prefix name="${ns.prefix}" IRI="${ns.iri}"/>`).join('\n')

  const body: string[] = []
  for (const c of ontology.classes) body.push(serializeClass(c, ontology))
  for (const p of ontology.objectProperties) body.push(serializeObjectProperty(p))
  for (const p of ontology.dataProperties) body.push(serializeDataProperty(p))
  for (const ind of ontology.individuals) body.push(serializeIndividual(ind))

  for (const a of ontology.annotations) {
    body.push(serializeAnnotation(a, ontology.iri))
  }

  return `<?xml version="1.0"?>
<Ontology xmlns="http://www.w3.org/2002/07/owl#"
${nsAttrs}
    xml:base="${esc(ontology.iri)}"
    ontologyIRI="${esc(ontology.iri)}"${ontology.versionIRI ? `\n    versionIRI="${esc(ontology.versionIRI)}"` : ''}>

${prefixes}

${body.join('\n\n')}

</Ontology>`
}

export function downloadOwlFile(ontology: OwlOntology, filename?: string) {
  const xml = serializeToOwlXml(ontology)
  const blob = new Blob([xml], { type: 'application/owl+xml' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename || `${ontology.iri.split(/[#/]/).pop() || 'ontology'}.owl`
  a.click()
  URL.revokeObjectURL(url)
}