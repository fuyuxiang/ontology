import { get, post, put } from './client'
import type { LoginRequest, LoginResponse, User } from '../types'

export interface RefreshResponse {
  token: string
  refresh_token: string
}

// ── 用户管理类型 ──

export interface UserListItem {
  id: string
  username: string
  name: string
  email: string | null
  role: string
  is_active: boolean
  last_login_at: string | null
  created_at: string | null
}

export interface UserListResponse {
  items: UserListItem[]
  total: number
  page: number
  page_size: number
}

export interface UserCreateRequest {
  username: string
  password: string
  name: string
  email?: string
  role: string
}

export interface UserUpdateRequest {
  name?: string
  email?: string
  role?: string
  is_active?: boolean
}

export interface RoleOut {
  key: string
  label: string
  description: string
  permissions: string[]
  user_count: number
  is_system: boolean
}

export interface PermissionModule {
  key: string
  label: string
  permissions: string[]
}

export const authApi = {
  login(data: LoginRequest) {
    return post<LoginResponse>('/auth/login', data)
  },

  me() {
    return get<User>('/auth/me')
  },

  refresh(refreshToken: string) {
    return post<RefreshResponse>('/auth/refresh', { refresh_token: refreshToken })
  },

  // ── 用户管理 ──

  listUsers(params?: { page?: number; page_size?: number; keyword?: string; role?: string; is_active?: boolean }) {
    return get<UserListResponse>('/auth/users', { params })
  },

  createUser(data: UserCreateRequest) {
    return post<UserListItem>('/auth/users', data)
  },

  updateUser(id: string, data: UserUpdateRequest) {
    return put<UserListItem>(`/auth/users/${id}`, data)
  },

  toggleUserStatus(id: string) {
    return put<{ id: string; is_active: boolean }>(`/auth/users/${id}/status`)
  },

  resetPassword(id: string, newPassword: string) {
    return post<{ message: string }>(`/auth/users/${id}/reset-password`, { new_password: newPassword })
  },

  // ── 角色管理 ──

  listRoles() {
    return get<RoleOut[]>('/auth/roles')
  },

  listPermissionModules() {
    return get<PermissionModule[]>('/auth/permissions/modules')
  },

  updateRolePerms(roleKey: string, permissions: string[]) {
    return put<{ message: string }>(`/auth/roles/${roleKey}/permissions`, { permissions })
  },
}
