export const XSD_DATATYPES = [
  { iri: 'xsd:string', label: 'string' },
  { iri: 'xsd:integer', label: 'integer' },
  { iri: 'xsd:int', label: 'int' },
  { iri: 'xsd:long', label: 'long' },
  { iri: 'xsd:float', label: 'float' },
  { iri: 'xsd:double', label: 'double' },
  { iri: 'xsd:boolean', label: 'boolean' },
  { iri: 'xsd:dateTime', label: 'dateTime' },
  { iri: 'xsd:date', label: 'date' },
  { iri: 'xsd:time', label: 'time' },
  { iri: 'xsd:decimal', label: 'decimal' },
  { iri: 'xsd:anyURI', label: 'anyURI' },
  { iri: 'xsd:nonNegativeInteger', label: 'nonNegativeInteger' },
] as const

export const XSD_NS = 'http://www.w3.org/2001/XMLSchema#'

export function xsdFull(localName: string): string {
  return `${XSD_NS}${localName}`
}
