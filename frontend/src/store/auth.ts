import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api/auth'
import type { User, Permission, LoginRequest } from '../types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  let userRequest: Promise<void> | null = null

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

  function fetchUser(): Promise<void> {
    if (!token.value) return Promise.resolve()
    if (userRequest) return userRequest
    const sessionToken = token.value
    userRequest = authApi
      .me()
      .then((result) => {
        if (token.value === sessionToken) user.value = result
      })
      .catch((error: any) => {
        if (error?.response?.status === 401 && token.value === sessionToken) logout()
      })
      .finally(() => {
        userRequest = null
      })
    return userRequest
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

  return {
    user,
    token,
    refreshToken,
    isLoggedIn,
    hasPermission,
    login,
    fetchUser,
    setTokens,
    logout,
  }
})
