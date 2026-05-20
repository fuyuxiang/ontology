import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  BuilderSession,
  BuildMethod,
  SessionStatus,
  OntologyClassDraft,
  OntologyRelationDraft,
  UploadRecord,
} from '../types/builder'
import {
  SCENARIO_PRESETS,
  SCENARIO_CLASS_PRESETS,
  SCENARIO_RELATION_PRESETS,
  DEMO_UPLOAD_RECORDS,
} from '../data/builderPresets'

const SESSIONS_KEY = 'builder-sessions'
const UPLOADS_KEY = 'builder-upload-records'
const ACTIVE_KEY = 'builder-active-session'

function uid(prefix = 'id') {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}

function loadSessions(): BuilderSession[] {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY)
    return raw ? JSON.parse(raw) : []
  } catch { return [] }
}

function loadUploads(): UploadRecord[] {
  try {
    const raw = localStorage.getItem(UPLOADS_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* noop */ }
  return [...DEMO_UPLOAD_RECORDS]
}

function persist<T>(key: string, val: T) {
  try { localStorage.setItem(key, JSON.stringify(val)) } catch { /* noop */ }
}

export function buildPresetClasses(scenarioId: string): OntologyClassDraft[] {
  const presets = SCENARIO_CLASS_PRESETS[scenarioId] || []
  return presets.map((p, i) => ({
    id: uid('cls'),
    name: p.name || `Class${i + 1}`,
    displayName: p.displayName || p.name || `对象${i + 1}`,
    tier: (p.tier ?? 1) as 1 | 2 | 3,
    description: p.description || '',
    primaryKey: p.primaryKey || 'id',
    icon: p.icon || '🔷',
    instanceCount: p.instanceCount ?? 0,
    properties: [
      { id: uid('prop'), name: p.primaryKey || 'id', displayName: '主键', type: 'string', required: true },
      { id: uid('prop'), name: 'name', displayName: '名称', type: 'string', required: true },
      { id: uid('prop'), name: 'updated_at', displayName: '更新时间', type: 'date', required: false },
    ],
    rules: [],
    actions: [],
    approved: false,
  }))
}

export function buildPresetRelations(scenarioId: string, classes: OntologyClassDraft[]): OntologyRelationDraft[] {
  const rels = SCENARIO_RELATION_PRESETS[scenarioId] || []
  const findId = (name: string) => classes.find(c => c.name === name)?.id || ''
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
    scenarioId: string
    scenarioName?: string
    buildMethod: BuildMethod
    createdBy?: string
  }): BuilderSession {
    const scenario = SCENARIO_PRESETS.find(s => s.id === payload.scenarioId)
    const classes = buildPresetClasses(payload.scenarioId)
    const relations = buildPresetRelations(payload.scenarioId, classes)
    const session: BuilderSession = {
      sessionId: uid('sess'),
      ontologyName: payload.ontologyName,
      scenarioId: payload.scenarioId,
      scenarioName: payload.scenarioName || scenario?.title || payload.scenarioId,
      buildMethod: payload.buildMethod,
      status: 'drafting',
      createdBy: payload.createdBy || (localStorage.getItem('username') || '当前用户'),
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      ontologyClasses: payload.buildMethod === 'ai' ? [] : classes,
      ontologyRelations: payload.buildMethod === 'ai' ? [] : relations,
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

  // 类与关系操作
  function addClass(cls: OntologyClassDraft) {
    if (!activeSession.value) return
    const list = [...activeSession.value.ontologyClasses, cls]
    patchActive({ ontologyClasses: list })
  }
  function updateClass(id: string, patch: Partial<OntologyClassDraft>) {
    if (!activeSession.value) return
    const list = activeSession.value.ontologyClasses.map(c =>
      c.id === id ? { ...c, ...patch } : c,
    )
    patchActive({ ontologyClasses: list })
  }
  function deleteClass(id: string) {
    if (!activeSession.value) return
    const list = activeSession.value.ontologyClasses.filter(c => c.id !== id)
    const rels = activeSession.value.ontologyRelations.filter(r => r.source !== id && r.target !== id)
    patchActive({ ontologyClasses: list, ontologyRelations: rels })
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

  function approveClass(id: string) {
    if (!activeSession.value) return
    updateClass(id, { approved: true })
  }
  function approveAllClasses() {
    if (!activeSession.value) return
    const list = activeSession.value.ontologyClasses.map(c => ({ ...c, approved: true }))
    patchActive({ ontologyClasses: list })
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
    addClass, updateClass, deleteClass,
    addRelation, deleteRelation,
    approveClass, approveAllClasses,
    addUploadRecord, updateUploadRecord, deleteUploadRecord,
    patchActive,
  }
})
