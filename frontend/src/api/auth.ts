import { get, post } from './client'
import type { LoginRequest, LoginResponse, User } from '../types'

export interface RefreshResponse {
  token: string
  refresh_token: string
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
}
