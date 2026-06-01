import { get, post, put, del } from './client'
import type {
  Capabilities, Connection, ConnectionCreate, ConnectionUpdate,
  ObjectEntry, PathEntry, TestResult,
} from '../types/connection'
import type { SchemaColumn } from '../types/asset'

export function listConnections(params?: { type?: string; category?: string; status?: string; q?: string }) {
  return get<Connection[]>('/connections', { params })
}

export function getCapabilities() {
  return get<Capabilities>('/connections/_capabilities')
}

export function getConnection(id: string) {
  return get<Connection>(`/connections/${id}`)
}

export function createConnection(data: ConnectionCreate) {
  return post<Connection>('/connections', data)
}

export function updateConnection(id: string, data: ConnectionUpdate) {
  return put<Connection>(`/connections/${id}`, data)
}

export function deleteConnection(id: string, cascade = false) {
  return del<void>(`/connections/${id}`, cascade ? { params: { cascade: true } } : undefined)
}

export function testConnection(id: string) {
  return post<TestResult>(`/connections/${id}/test`)
}

export function toggleConnection(id: string) {
  return post<Connection>(`/connections/${id}/toggle`)
}

export function listDatabases(id: string) {
  return get<string[]>(`/connections/${id}/databases`)
}

export function listTablesOfConnection(id: string, database?: string) {
  return get<string[]>(`/connections/${id}/tables`, { params: database ? { database } : {} })
}

export function getConnectionTableSchema(id: string, tableName: string, database?: string) {
  return get<{ table: string; columns: SchemaColumn[] }>(
    `/connections/${id}/tables/${encodeURIComponent(tableName)}/schema`,
    { params: database ? { database } : {} },
  )
}

export function listObjects(id: string, prefix = '', limit = 200) {
  return get<ObjectEntry[]>(`/connections/${id}/objects`, { params: { prefix, limit } })
}

export function listPaths(id: string, path = '/', limit = 200) {
  return get<PathEntry[]>(`/connections/${id}/paths`, { params: { path, limit } })
}

export function listTopics(id: string) {
  return get<string[]>(`/connections/${id}/topics`)
}
