import { get, post, put, del } from './client'
import type { DataSource, DataSourceCreate, DataSourceUpdate, TestConnectionResult } from '../types/datasource'

export function listDataSources(params?: { type?: string; status?: string; q?: string }) {
  return get<DataSource[]>('/connections', { params })
}

export function getDataSource(id: string) {
  return get<DataSource>(`/connections/${id}`)
}

export function createDataSource(data: DataSourceCreate) {
  return post<DataSource[]>('/connections', data)
}

export function updateDataSource(id: string, data: DataSourceUpdate) {
  return put<DataSource>(`/connections/${id}`, data)
}

export function deleteDataSource(id: string) {
  return del<void>(`/connections/${id}`)
}

export function testConnection(id: string) {
  return post<TestConnectionResult>(`/connections/${id}/test`)
}

export function testConnectionInline(data: DataSourceCreate) {
  return post<TestConnectionResult>('/connections/test', data)
}

export function fetchTablesInline(data: DataSourceCreate) {
  return post<{ tables: string[] }>('/connections/fetch-tables', data)
}

export function toggleDataSource(id: string) {
  return post<DataSource>(`/connections/${id}/toggle`)
}

export function refreshTables(id: string) {
  return post<DataSource>(`/connections/${id}/refresh-tables`)
}

export function previewDatasource(id: string) {
  return get<{ table: string; columns: string[]; rows: unknown[][] }>(`/connections/${id}/preview`)
}

export function getTableList(id: string) {
  return get<{ tables: string[] }>(`/connections/${id}/tables`)
}

export function getTablePreview(id: string, tableName: string) {
  return get<{ table: string; columns: string[]; rows: unknown[][] }>(`/connections/${id}/tables/${encodeURIComponent(tableName)}/preview`)
}

export function getTableSchema(id: string, tableName: string) {
  return get<{ table: string; columns: { name: string; type: string; nullable: boolean; is_pk: boolean; comment: string }[] }>(`/connections/${id}/tables/${encodeURIComponent(tableName)}/schema`)
}
