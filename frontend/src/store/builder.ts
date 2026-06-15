import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  BuilderSession,
  BuildMethod,
  SessionStatus,
  OntologyObjectDraft,
  OntologyRelationDraft,
  UploadRecord,
  OntologyHints,
} from '../types/builder'
import {
  SCENARIO_CLASS_PRESETS,
  SCENARIO_RELATION_PRESETS,
} from '../data/builderPresets'

const SESSIONS_KEY = 'builder-sessions'
const UPLOADS_KEY = 'builder-upload-records'
const ACTIVE_KEY = 'builder-active-session'

function uid(prefix = 'id') {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}

function emptyHints(): OntologyHints {
  return { suggested_rules: [], suggested_actions: [] }
}

function migrateSession(s: any): BuilderSession {
  // 旧 storage 用 ontologyClasses + 'ai'/'upload'，做就地迁移以避免崩溃
  const buildMethod: BuildMethod = (() => {
    const m = s.buildMethod
    if (m === 'ai') return 'chat'
    if (m === 'upload') return 'import'
    if (m === 'manual' || m === 'import' || m === 'extract' || m === 'chat') return m
    return 'manual'
  })()
  const objects: OntologyObjectDraft[] = (s.ontologyObjects || s.ontologyClasses || []).map((c: any) => ({
    id: c.id,
    name: c.name,
    displayName: c.displayName,
    tier: c.tier,
    namespace: c.namespace,
    description: c.description || '',
    primaryKey: c.primaryKey || 'id',
    icon: c.icon || '🔷',
    instanceCount: c.instanceCount || 0,
    properties: c.properties || [],
    derivedProperties: c.derivedProperties || [],
    rules: c.rules || [],
    actions: c.actions || [],
    approved: c.approved ?? false,
  }))
  return {
    ...s,
    buildMethod,
    ontologyObjects: objects,
    ontologyRelations: s.ontologyRelations || [],
    hints: s.hints || emptyHints(),
  } as BuilderSession
}

function loadSessions(): BuilderSession[] {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY)
    if (!raw) return []
    const arr = JSON.parse(raw)
    return Array.isArray(arr) ? arr.map(migrateSession) : []
  } catch { return [] }
}

function loadUploads(): UploadRecord[] {
  try {
    const raw = localStorage.getItem(UPLOADS_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* noop */ }
  return []
}

function persist<T>(key: string, val: T) {
  try { localStorage.setItem(key, JSON.stringify(val)) } catch { /* noop */ }
}

export function buildPresetClasses(scenarioId: string): OntologyObjectDraft[] {
  const presets = SCENARIO_CLASS_PRESETS[scenarioId] || []
  return presets.map((p, i) => ({
    id: uid('obj'),
    name: p.name || `Object${i + 1}`,
    displayName: p.displayName || p.name || `对象${i + 1}`,
    tier: (p.tier ?? 1) as 1 | 2 | 3,
    description: p.description || '',
    primaryKey: p.primaryKey || 'id',
    icon: p.icon || '🔷',
    instanceCount: p.instanceCount ?? 0,
    properties: [
      { id: uid('prop'), name: 'name', displayName: '名称', type: 'string', required: true },
      { id: uid('prop'), name: 'updated_at', displayName: '更新时间', type: 'date', required: false },
    ],
    derivedProperties: [],
    rules: [],
    actions: [],
    approved: false,
  }))
}

export function buildPresetRelations(scenarioId: string, objects: OntologyObjectDraft[]): OntologyRelationDraft[] {
  const rels = SCENARIO_RELATION_PRESETS[scenarioId] || []
  const findId = (name: string) => objects.find(o => o.name === name)?.id || ''
  return rels.map((r, i) => ({
    id: uid('rel'),
    name: r.name,
    displayName: r.displayName,
    source: findId(r.source) || r.source,
    target: findId(r.target) || r.target,
    cardinality: r.cardinality,
    description: r.displayName,
    relationType: 'ObjectProperty' as const,
    semanticType: i % 3 === 0 ? 'composition' as const : i % 3 === 1 ? 'event' as const : 'association' as const,
  }))
}

export const useBuilderStore = defineStore('builder', () => {
  const sessions = ref<BuilderSession[]>(loadSessions())
  const activeSessionId = ref<string | null>(localStorage.getItem(ACTIVE_KEY) || null)
  const uploads = ref<UploadRecord[]>(loadUploads())

  const activeSession = computed(() =>
    sessions.value.find(s => s.sessionId === activeSessionId.value) || null,
  )

  const reviewableSessions = computed(() =>
    sessions.value.filter(s => s.status === 'pending_review' || s.status === 'reviewing'),
  )

  function syncSessions() {
    persist(SESSIONS_KEY, sessions.value)
  }

  function syncUploads() {
    persist(UPLOADS_KEY, uploads.value)
  }

  function createSession(payload: {
    ontologyName: string
    buildMethod: BuildMethod
    createdBy?: string
    scenarioId?: string
    scenarioName?: string
  }): BuilderSession {
    const session: BuilderSession = {
      sessionId: uid('sess'),
      ontologyName: payload.ontologyName,
      scenarioId: payload.scenarioId,
      scenarioName: payload.scenarioName,
      buildMethod: payload.buildMethod,
      status: 'drafting',
      createdBy: payload.createdBy || (localStorage.getItem('username') || '当前用户'),
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      ontologyObjects: [],
      ontologyRelations: [],
      hints: emptyHints(),
      selectedAssetIds: [],
      selectedSampleSourceIds: [],
      approvedScenarios: [],
      thresholdChanges: [],
      reviewLog: [],
      businessRules: [],
    }
    sessions.value = [session, ...sessions.value]
    activeSessionId.value = session.sessionId
    localStorage.setItem(ACTIVE_KEY, session.sessionId)
    syncSessions()
    return session
  }

  function updateSession(sessionId: string, patch: Partial<BuilderSession>) {
    sessions.value = sessions.value.map(s =>
      s.sessionId === sessionId
        ? { ...s, ...patch, updatedAt: new Date().toISOString() }
        : s,
    )
    syncSessions()
  }

  function patchActive(patch: Partial<BuilderSession>) {
    if (activeSessionId.value) updateSession(activeSessionId.value, patch)
  }

  function deleteSession(sessionId: string) {
    sessions.value = sessions.value.filter(s => s.sessionId !== sessionId)
    if (activeSessionId.value === sessionId) {
      activeSessionId.value = null
      localStorage.removeItem(ACTIVE_KEY)
    }
    syncSessions()
  }

  function setActiveSession(sessionId: string | null) {
    activeSessionId.value = sessionId
    if (sessionId) localStorage.setItem(ACTIVE_KEY, sessionId)
    else localStorage.removeItem(ACTIVE_KEY)
  }

  function setStatus(status: SessionStatus) {
    if (activeSessionId.value) updateSession(activeSessionId.value, { status })
  }

  // 对象 / 关系操作
  function addObject(obj: OntologyObjectDraft) {
    if (!activeSession.value) return
    const list = [...activeSession.value.ontologyObjects, obj]
    patchActive({ ontologyObjects: list })
  }
  function updateObject(id: string, patch: Partial<OntologyObjectDraft>) {
    if (!activeSession.value) return
    const list = activeSession.value.ontologyObjects.map(c =>
      c.id === id ? { ...c, ...patch } : c,
    )
    patchActive({ ontologyObjects: list })
  }
  function deleteObject(id: string) {
    if (!activeSession.value) return
    const list = activeSession.value.ontologyObjects.filter(c => c.id !== id)
    const rels = activeSession.value.ontologyRelations.filter(r => r.source !== id && r.target !== id)
    patchActive({ ontologyObjects: list, ontologyRelations: rels })
  }
  function addRelation(rel: OntologyRelationDraft) {
    if (!activeSession.value) return
    const list = [...activeSession.value.ontologyRelations, rel]
    patchActive({ ontologyRelations: list })
  }
  function deleteRelation(id: string) {
    if (!activeSession.value) return
    const list = activeSession.value.ontologyRelations.filter(r => r.id !== id)
    patchActive({ ontologyRelations: list })
  }

  function approveObject(id: string) {
    if (!activeSession.value) return
    updateObject(id, { approved: true })
  }
  function approveAllObjects() {
    if (!activeSession.value) return
    const list = activeSession.value.ontologyObjects.map(c => ({ ...c, approved: true }))
    patchActive({ ontologyObjects: list })
  }

  // ── 上传记录 ──
  function addUploadRecord(record: Omit<UploadRecord, 'id' | 'uploadedAt'> & Partial<Pick<UploadRecord, 'id' | 'uploadedAt'>>) {
    const r: UploadRecord = {
      ...record,
      id: record.id || uid('upload'),
      uploadedAt: record.uploadedAt || new Date().toISOString(),
    } as UploadRecord
    uploads.value = [r, ...uploads.value].slice(0, 80)
    syncUploads()
    return r.id
  }
  function updateUploadRecord(id: string, patch: Partial<UploadRecord>) {
    uploads.value = uploads.value.map(u => u.id === id ? { ...u, ...patch } : u)
    syncUploads()
  }
  function deleteUploadRecord(id: string) {
    uploads.value = uploads.value.filter(u => u.id !== id)
    syncUploads()
  }

  return {
    sessions, activeSessionId, uploads,
    activeSession, reviewableSessions,
    createSession, updateSession, deleteSession, setActiveSession, setStatus,
    addObject, updateObject, deleteObject,
    addRelation, deleteRelation,
    approveObject, approveAllObjects,
    addUploadRecord, updateUploadRecord, deleteUploadRecord,
    patchActive,
  }
})
