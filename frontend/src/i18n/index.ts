import { createI18n } from 'vue-i18n'
import zhCN from './zh-CN.json'
import en from './en.json'

// 从 localStorage 或系统配置读取语言
function getDefaultLocale(): 'zh-CN' | 'en' {
  const saved = localStorage.getItem('language')
  if (saved === 'en' || saved === 'zh-CN') return saved
  // 检测浏览器语言
  const browserLang = navigator.language
  if (browserLang.startsWith('en')) return 'en'
  return 'zh-CN'
}

const i18n = createI18n({
  legacy: false, // 使用 Composition API 模式
  locale: getDefaultLocale(),
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': zhCN,
    'en': en,
  },
})

export default i18n

// 语言切换工具函数
export function setLocale(locale: string) {
  i18n.global.locale.value = locale as 'zh-CN' | 'en'
  localStorage.setItem('language', locale)
  document.documentElement.lang = locale
}

export function getLocale(): string {
  return i18n.global.locale.value
}
