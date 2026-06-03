import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api/auth'
import type { User, Permission, LoginRequest } from '../types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))

  const isLoggedIn = computed(() => !!token.value)

  function hasPermission(perm: Permission): boolean {
    return user.value?.permissions.includes(perm) ?? false
  }

  async function login(data: LoginRequest) {
    const res = await authApi.login(data)
    token.value = res.token
    refreshToken.value = res.refresh_token
    user.value = res.user
    localStorage.setItem('token', res.token)
    localStorage.setItem('refresh_token', res.refresh_token)
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      user.value = await authApi.me()
    } catch {
      logout()
    }
  }

  function setTokens(newToken: string, newRefresh: string) {
    token.value = newToken
    refreshToken.value = newRefresh
    localStorage.setItem('token', newToken)
    localStorage.setItem('refresh_token', newRefresh)
  }

  function logout() {
    token.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('refresh_token')
  }

  return { user, token, refreshToken, isLoggedIn, hasPermission, login, fetchUser, setTokens, logout }
})
