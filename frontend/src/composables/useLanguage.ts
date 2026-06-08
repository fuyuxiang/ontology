import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { setLocale, getLocale } from '../i18n'

export function useLanguage() {
  const { locale, t } = useI18n()
  const currentLocale = ref(getLocale())

  function switchLanguage(lang: string) {
    setLocale(lang)
    currentLocale.value = lang
    locale.value = lang
  }

  // 初始化时同步
  watch(locale, (newVal) => {
    currentLocale.value = newVal
  })

  return {
    currentLocale,
    switchLanguage,
    t,
    locale,
  }
}
