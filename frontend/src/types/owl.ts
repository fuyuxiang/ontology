export interface OwlNamespace {
  prefix: string
  iri: string
}

export interface OwlAnnotation {
  id: string
  property: string
  value: string
  language?: string
  datatype?: string
}

export type OwlClassExpressionType =
  | 'namedClass'
  | 'objectSomeValuesFrom'
  | 'objectAllValuesFrom'
  | 'objectMinCardinality'
  | 'objectMaxCardinality'
  | 'objectExactCardinality'
  | 'dataSomeValuesFrom'
  | 'dataAllValuesFrom'
  | 'objectIntersectionOf'
  | 'objectUnionOf'
  | 'objectComplementOf'
  | 'objectHasValue'

export interface OwlClassExpression {
  id: string
  type: OwlClassExpressionType
  classIRI?: string
  propertyIRI?: string
  fillerClassIRI?: string
  fillerDatatype?: string
  cardinality?: number
  operands?: OwlClassExpression[]
  individualIRI?: string
  literalValue?: string
}

export interface OwlClass {
  id: string
  iri: string
  localName: string
  annotations: OwlAnnotation[]
  superClassExpressions: OwlClassExpression[]
  equivalentClassExpressions: OwlClassExpression[]
  disjointWith: string[]
}

export type ObjectPropertyCharacteristic =
  | 'functional'
  | 'inverseFunctional'
  | 'transitive'
  | 'symmetric'
  | 'asymmetric'
  | 'reflexive'
  | 'irreflexive'

export interface OwlObjectProperty {
  id: string
  iri: string
  localName: string
  annotations: OwlAnnotation[]
  superProperties: string[]
  domains: string[]
  ranges: string[]
  characteristics: ObjectPropertyCharacteristic[]
  inverseOf: string | null
}

export interface OwlDataProperty {
  id: string
  iri: string
  localName: string
  annotations: OwlAnnotation[]
  superProperties: string[]
  domains: string[]
  ranges: string[]
  functional: boolean
}

export interface OwlObjectPropertyAssertion {
  id: string
  propertyIRI: string
  targetIndividualIRI: string
}

export interface OwlDataPropertyAssertion {
  id: string
  propertyIRI: string
  value: string
  datatype: string
}

export interface OwlIndividual {
  id: string
  iri: string
  localName: string
  annotations: OwlAnnotation[]
  types: string[]
  objectPropertyAssertions: OwlObjectPropertyAssertion[]
  dataPropertyAssertions: OwlDataPropertyAssertion[]
  sameAs: string[]
  differentFrom: string[]
}

export interface OwlOntology {
  id: string
  iri: string
  versionIRI?: string
  annotations: OwlAnnotation[]
  namespaces: OwlNamespace[]
  classes: OwlClass[]
  objectProperties: OwlObjectProperty[]
  dataProperties: OwlDataProperty[]
  individuals: OwlIndividual[]
}
