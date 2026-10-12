<template>
  <div class="login">
    <div class="login__card">
      <div class="login__logo">
        <img src="/images/ontology/logo.png" :alt="platform.system_name" class="login__logo-img" />
        <div class="login__logo-text">
          <span class="login__brand">{{ platform.system_name }}</span>

        </div>
      </div>
      <p class="login__desc">{{ t('login.description') }}</p>
      <form class="login__form" @submit.prevent="handleLogin">
        <div class="login__field">
          <label for="login-username" class="login__label">{{ t('login.username') }}</label>
          <input
            id="login-username"
            v-model="username"
            type="text"
            class="login__input"
            :placeholder="t('login.usernamePlaceholder')"
            autocomplete="username"
            required
            autofocus
            :disabled="loading"
          />
        </div>
        <div class="login__field">
          <label for="login-password" class="login__label">{{ t('login.password') }}</label>
          <input
            id="login-password"
            v-model="password"
            type="password"
            class="login__input"
            :placeholder="t('login.passwordPlaceholder')"
            autocomplete="current-password"
            required
            :disabled="loading"
          />
        </div>
        <p v-if="error" class="login__error" role="alert">{{ error }}</p>
        <button type="submit" class="login__btn" :disabled="loading">
          {{ loading ? t('login.working') : t('login.submit') }}
        </button>
      </form>
      <button v-if="sso.enabled && sso.provider === 'oidc'" type="button" class="login__btn" :disabled="loading" @click="startSSO">{{ t('login.sso', {provider:'OIDC'}) }}</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../store/auth'
import { authApi } from '../../api/auth'
import { useI18n } from 'vue-i18n'
import { usePlatformConfigStore } from '../../store/platformConfig'
import { firstAccessibleRoute } from '../../utils/access'
const { t } = useI18n()
const platform = usePlatformConfigStore()

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const sso = ref({ enabled: false, provider: 'oidc' })

function safeRedirect() {
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
  return redirect.startsWith('/') && !redirect.startsWith('//') && !redirect.includes('\\') &&
    router.resolve(redirect).matched.length && !redirect.startsWith('/login') ? redirect : firstAccessibleRoute(permission => authStore.hasPermission(permission))
}

function startSSO() {
  const base = import.meta.env.VITE_API_BASE_URL || '/api/v1'
  window.location.assign(`${base}/auth/sso/start?redirect=${encodeURIComponent(safeRedirect())}`)
}

onMounted(async () => {
  try { sso.value = await authApi.ssoConfig() } catch { /* local login remains available */ }
  if (typeof route.query.sso_code !== 'string') return
  const code = route.query.sso_code
  const redirect = safeRedirect()
  // Remove the single-use ticket from browser history before exchanging it.
  await router.replace({ path: '/login', query: { redirect } })
  loading.value = true
  try {
    await authStore.loginWithTicket(code)
    await router.replace(redirect)
  } catch (e: any) {
    error.value = typeof e?.response?.data?.detail === 'string' ? e.response.data.detail : t('login.ssoFailed')
  } finally { loading.value = false }
})

async function handleLogin() {
  if (loading.value) return
  error.value = ''
  loading.value = true
  try {
    await authStore.login({ username: username.value.trim(), password: password.value })
    await router.replace(safeRedirect())
  } catch (e: any) {
    error.value =
      e?.response?.status === 401
        ? t('login.invalidCredentials')
        : typeof e?.response?.data?.detail === 'string'
          ? e.response.data.detail
          : t('login.unavailable')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--sidebar-bg);
  padding: 24px;
}
.login__card {
  width: min(420px, 100%);
  padding: 48px 40px;
  background: #0f1117;
  border-radius: 16px;
  border: 1px solid #343a40;
  box-shadow: var(--shadow-lg);
}
.login__logo {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.login__logo-img {
  width: 72px;
  height: auto;
  max-height: 32px;
  object-fit: contain;
}
.login__logo-text {
  display: flex;
  flex-direction: column;
}
.login__brand {
  font-size: var(--text-h2-size);
  font-weight: 700;
  color: #fff;
  line-height: 1.2;
  overflow-wrap: anywhere;
}
.login__brand-sub {
  font-size: var(--text-code-size);
  color: #a8b1bd;
  font-weight: 500;
}
.login__desc {
  font-size: var(--text-body-size);
  color: #a8b1bd;
  margin-bottom: 32px;
}
.login__form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.login__field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.login__label {
  font-size: var(--text-code-size);
  font-weight: 500;
  color: #c1c9d4;
}
.login__input {
  height: 40px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid #49515d;
  background: #171b24;
  color: #fff;
  font-size: var(--text-body-size);
  outline: none;
  transition: border-color 0.15s;
}
.login__input:focus {
  border-color: var(--semantic-600);
}
.login__input::placeholder {
  color: #949dac;
}
.login__error {
  font-size: var(--text-code-size);
  color: var(--status-error);
  margin: -8px 0 0;
}
.login__btn {
  height: 42px;
  border-radius: 8px;
  border: none;
  background: var(--semantic-600);
  color: #fff;
  font-size: var(--text-body-size);
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
  margin-top: 4px;
}
.login__btn:hover:not(:disabled) {
  background: var(--semantic-600);
}
.login__btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
