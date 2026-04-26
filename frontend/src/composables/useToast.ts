import { ref } from 'vue'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: number
  type: ToastType
  message: string
  duration: number
}

const toasts = ref<Toast[]>([])
let nextId = 0

export function useToast() {
  function show(message: string, type: ToastType = 'info', duration = 3000) {
    const id = ++nextId
    toasts.value.push({ id, type, message, duration })
    setTimeout(() => remove(id), duration)
  }

  function remove(id: number) {
    const idx = toasts.value.findIndex(t => t.id === id)
    if (idx !== -1) toasts.value.splice(idx, 1)
  }

  return {
    toasts,
    show,
    remove,
    success: (msg: string, duration?: number) => show(msg, 'success', duration),
    error:   (msg: string, duration?: number) => show(msg, 'error', duration),
    warning: (msg: string, duration?: number) => show(msg, 'warning', duration),
    info:    (msg: string, duration?: number) => show(msg, 'info', duration),
  }
}
