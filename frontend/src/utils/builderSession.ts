import type { BuilderSession } from '../types/builder'

/** Approval metadata does not change the business draft; mappings and executable references do. */
export function builderContentSignature(session: Partial<BuilderSession>): string {
  return JSON.stringify({
    ontologyId: session.ontologyId || null,
    kind: session.builderKind || session.buildMethod,
    objects: (session.ontologyObjects || []).map(({ approved: _approved, ...object }) => object),
    relations: session.ontologyRelations || [],
    actions: session.importedActions || [],
    assets: session.selectedAssetIds || [],
    rules: session.businessRules || [],
    input: session.builderState ? {
      businessDesc: session.builderState.businessDesc,
      selectedTables: session.builderState.selectedTables,
      selectedDocs: session.builderState.selectedDocs,
      sessionId: session.builderState.sessionId,
      extractionResult: session.builderState.extractionResult,
      mappedResult: session.builderState.mappedResult,
    } : null,
  })
}

export function matchesBuilderSession(session: BuilderSession, kind: string, ontologyId?: string, ownerId?: string): boolean {
  return (session.builderKind || session.buildMethod) === kind &&
    (session.ontologyId || undefined) === ontologyId &&
    !!ownerId && session.ownerId === ownerId
}
