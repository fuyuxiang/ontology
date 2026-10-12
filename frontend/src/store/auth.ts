import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api/auth'
import { randomUUID } from '../utils/uuid'
import type { User, Permission, LoginRequest } from '../types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  let userRequest: Promise<void> | null = null
  let sessionEpoch = 0

  window.addEventListener('ontology:session', () => {
    token.value = localStorage.getItem('token')
    refreshToken.value = localStorage.getItem('refresh_token')
    if (!token.value) {
      user.value = null
      sessionEpoch++
      userRequest = null
    }
  })

  const isLoggedIn = computed(() => !!token.value)

  function hasPermission(perm: Permission): boolean {
    return user.value?.permissions.includes(perm) ?? false
  }

  async function login(data: LoginRequest) {
    const res = await authApi.login(data)
    acceptLogin(res)
  }

  async function loginWithTicket(code: string) {
    acceptLogin(await authApi.ssoExchange(code))
  }

  function acceptLogin(res: Awaited<ReturnType<typeof authApi.login>>) {
    token.value = res.token
    refreshToken.value = res.refresh_token
    user.value = res.user
    sessionEpoch++
    userRequest = null
    localStorage.setItem('token', res.token)
    localStorage.setItem('refresh_token', res.refresh_token)
    localStorage.setItem('auth_session_id', randomUUID())
    window.dispatchEvent(new Event('ontology:session'))
  }

  function fetchUser(): Promise<void> {
    if (!token.value) return Promise.resolve()
    if (userRequest) return userRequest
    const epoch = sessionEpoch
    const request = authApi
      .me()
      .then((result) => {
        if (sessionEpoch === epoch) user.value = result
      })
      .catch((error: any) => {
        if (error?.response?.status === 401 && sessionEpoch === epoch) clearSession()
        throw error
      })
      .finally(() => {
        if (userRequest === request) userRequest = null
      })
    userRequest = request
    return request
  }

  function setTokens(newToken: string, newRefresh: string) {
    token.value = newToken
    refreshToken.value = newRefresh
    localStorage.setItem('token', newToken)
    localStorage.setItem('refresh_token', newRefresh)
  }

  function clearSession() {
    sessionEpoch++
    userRequest = null
    token.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('auth_session_id')
    window.dispatchEvent(new Event('ontology:session'))
  }

  function logout() {
    const oldToken = token.value
    const revoke = oldToken ? authApi.logout(oldToken) : Promise.resolve()
    clearSession()
    // An offline client still exits locally; the API revokes all account sessions
    // when reachable. Never restore a session after this request completes.
    void revoke.catch(() => undefined)
  }

  return {
    user,
    token,
    refreshToken,
    isLoggedIn,
    hasPermission,
    login,
    loginWithTicket,
    fetchUser,
    setTokens,
    logout,
  }
})
