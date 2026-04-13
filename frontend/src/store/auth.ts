import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api/auth'
import type { User, Permission, LoginRequest } from '../types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('token'))

  const isLoggedIn = computed(() => !!token.value)

  function hasPermission(perm: Permission): boolean {
    return user.value?.permissions.includes(perm) ?? false
  }

  async function login(data: LoginRequest) {
    const res = await authApi.login(data)
    token.value = res.token
    user.value = res.user
    localStorage.setItem('token', res.token)
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      user.value = await authApi.me()
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  return { user, token, isLoggedIn, hasPermission, login, fetchUser, logout }
})
