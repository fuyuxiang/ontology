import { defineStore } from 'pinia'
import { ref } from 'vue'
import { platformConfigApi, type PlatformConfig } from '../api/platformConfig'
import { setLocale } from '../i18n'

export const usePlatformConfigStore = defineStore('platform-config', () => {
  const system_name = ref('本体管理平台')
  const language = ref<PlatformConfig['language']>('zh-CN')
  const timezone = ref<PlatformConfig['timezone']>('Asia/Shanghai')
  const loaded = ref(false)
  const loading = ref(false)
  const error = ref('')
  let request = 0

  function applySaved(values: Partial<PlatformConfig>) {
    // Invalidate an earlier startup read before applying a committed save.
    ++request
    if (typeof values.system_name === 'string' && values.system_name.trim()) system_name.value = values.system_name.trim()
    if (values.language === 'zh-CN' || values.language === 'en') {
      language.value = values.language
      setLocale(values.language)
    }
    if (values.timezone === 'Asia/Shanghai' || values.timezone === 'UTC') timezone.value = values.timezone
    loaded.value = true
    loading.value = false
    error.value = ''
  }

  async function load(force = false) {
    if (!force && (loaded.value || loading.value)) return
    const current = ++request
    loading.value = true
    error.value = ''
    try {
      const values = await platformConfigApi.get()
      if (current === request) applySaved(values)
    } catch (exception: any) {
      if (current === request) error.value = exception?.message || 'Platform configuration unavailable'
    } finally {
      if (current === request) loading.value = false
    }
  }

  return { system_name, language, timezone, loaded, loading, error, load, applySaved }
})
