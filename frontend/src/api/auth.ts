import { get, post } from './client'
import type { LoginRequest, LoginResponse, User } from '../types'

export const authApi = {
  login(data: LoginRequest) {
    return post<LoginResponse>('/auth/login', data)
  },

  me() {
    return get<User>('/auth/me')
  },
}
