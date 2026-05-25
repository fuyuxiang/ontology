import { get, post, put, del } from './client'
import type {
  BindingCreate, BindingTestResolveResult, BindingUpdate, ObjectBinding,
} from '../types/binding'

export function listBindings(params?: {
  object_type_id?: string
  asset_id?: string
  role?: string
  status?: string
}) {
  return get<ObjectBinding[]>('/object-bindings', { params })
}

export function getBinding(id: string) {
  return get<ObjectBinding>(`/object-bindings/${id}`)
}

export function createBinding(data: BindingCreate) {
  return post<ObjectBinding>('/object-bindings', data)
}

export function updateBinding(id: string, data: BindingUpdate) {
  return put<ObjectBinding>(`/object-bindings/${id}`, data)
}

export function deleteBinding(id: string) {
  return del<void>(`/object-bindings/${id}`)
}

export function testResolveBinding(id: string) {
  return post<BindingTestResolveResult>(`/object-bindings/${id}/test-resolve`)
}
