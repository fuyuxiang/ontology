import { get, post, put, del } from './client'
import type { DataSource, DataSourceCreate, DataSourceUpdate, TestConnectionResult } from '../types/datasource'

export function listDataSources(params?: { type?: string; status?: string; q?: string }) {
  return get<DataSource[]>('/datasources', { params })
}

export function getDataSource(id: string) {
  return get<DataSource>(`/datasources/${id}`)
}

export function createDataSource(data: DataSourceCreate) {
  return post<DataSource>('/datasources', data)
}

export function updateDataSource(id: string, data: DataSourceUpdate) {
  return put<DataSource>(`/datasources/${id}`, data)
}

export function deleteDataSource(id: string) {
  return del<void>(`/datasources/${id}`)
}

export function testConnection(id: string) {
  return post<TestConnectionResult>(`/datasources/${id}/test`)
}

export function testConnectionInline(data: DataSourceCreate) {
  return post<TestConnectionResult>('/datasources/test', data)
}

export function toggleDataSource(id: string) {
  return post<DataSource>(`/datasources/${id}/toggle`)
}

export function refreshTables(id: string) {
  return post<DataSource>(`/datasources/${id}/refresh-tables`)
}

export function getTableList(id: string) {
  return get<{ tables: string[] }>(`/datasources/${id}/tables`)
}

export function getTablePreview(id: string, tableName: string) {
  return get<{ table: string; columns: string[]; rows: unknown[][] }>(`/datasources/${id}/tables/${encodeURIComponent(tableName)}/preview`)
}
