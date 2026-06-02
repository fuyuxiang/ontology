import type { OwlNamespace } from '../../types/owl'

export const BUILTIN_NAMESPACES: OwlNamespace[] = [
  { prefix: 'owl', iri: 'http://www.w3.org/2002/07/owl#' },
  { prefix: 'rdf', iri: 'http://www.w3.org/1999/02/22-rdf-syntax-ns#' },
  { prefix: 'rdfs', iri: 'http://www.w3.org/2000/01/rdf-schema#' },
  { prefix: 'xsd', iri: 'http://www.w3.org/2001/XMLSchema#' },
  { prefix: 'xml', iri: 'http://www.w3.org/XML/1998/namespace' },
]

export function resolvePrefix(prefixed: string, namespaces: OwlNamespace[]): string {
  const idx = prefixed.indexOf(':')
  if (idx < 0) return prefixed
  const prefix = prefixed.slice(0, idx)
  const local = prefixed.slice(idx + 1)
  const ns = [...BUILTIN_NAMESPACES, ...namespaces].find(n => n.prefix === prefix)
  return ns ? `${ns.iri}${local}` : prefixed
}

export function abbreviate(fullIRI: string, namespaces: OwlNamespace[]): string {
  const all = [...BUILTIN_NAMESPACES, ...namespaces]
  for (const ns of all) {
    if (fullIRI.startsWith(ns.iri)) {
      return `${ns.prefix}:${fullIRI.slice(ns.iri.length)}`
    }
  }
  return fullIRI
}

export function localName(iri: string): string {
  const hashIdx = iri.lastIndexOf('#')
  if (hashIdx >= 0) return iri.slice(hashIdx + 1)
  const slashIdx = iri.lastIndexOf('/')
  if (slashIdx >= 0) return iri.slice(slashIdx + 1)
  return iri
}

export function uid(prefix = 'id'): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}
