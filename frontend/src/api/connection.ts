import { get, post, put, del } from './client'
import type { Connection, ConnectionCreate, ConnectionUpdate, TestResult } from '../types/connection'
import type { SchemaColumn } from '../types/asset'

export function listConnections(params?: { type?: string; status?: string; q?: string }) {
  return get<Connection[]>('/connections', { params })
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

export function deleteConnection(id: string) {
  return del<void>(`/connections/${id}`)
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
