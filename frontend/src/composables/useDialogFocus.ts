import { nextTick, onBeforeUnmount, watch, type Ref } from 'vue'

const activeDialogs: symbol[] = []

/** Keep keyboard focus inside the topmost custom dialog and restore its trigger. */
export function useDialogFocus(
  visible: () => boolean,
  panel: Ref<HTMLElement | null>,
  close: () => void,
) {
  const id = Symbol('dialog')
  let previousFocus: HTMLElement | null = null
  const focusable = () =>
    Array.from(
      panel.value?.querySelectorAll<HTMLElement>(
        'button, input, select, textarea, a[href], [tabindex]',
      ) || [],
    ).filter(
      (el) =>
        !el.matches(':disabled, [tabindex="-1"]') &&
        el.getClientRects().length > 0 &&
        !el.closest('[inert], [aria-hidden="true"]'),
    )

  function keydown(event: KeyboardEvent) {
    if (activeDialogs.at(-1) !== id) return
    if (event.key === 'Escape') {
      event.preventDefault()
      event.stopPropagation()
      close()
    } else if (event.key === 'Tab') {
      const items = focusable()
      const first = items[0]
      const last = items.at(-1)
      if (!first || !last) {
        event.preventDefault()
        panel.value?.focus()
        return
      }
      if (
        !panel.value?.contains(document.activeElement) ||
        (event.shiftKey && document.activeElement === first) ||
        (!event.shiftKey && document.activeElement === last)
      ) {
        event.preventDefault()
        ;(event.shiftKey ? last : first).focus()
      }
    }
  }

  function release() {
    document.removeEventListener('keydown', keydown, true)
    const index = activeDialogs.indexOf(id)
    if (index < 0) return
    const wasTop = activeDialogs.at(-1) === id
    activeDialogs.splice(index, 1)
    if (wasTop && previousFocus?.isConnected) previousFocus.focus()
  }

  watch(
    visible,
    async (open) => {
      if (!open) {
        release()
        return
      }
      previousFocus = document.activeElement as HTMLElement | null
      activeDialogs.push(id)
      document.addEventListener('keydown', keydown, true)
      await nextTick()
      if (visible() && activeDialogs.at(-1) === id) (focusable()[0] || panel.value)?.focus()
    },
    { immediate: true },
  )
  onBeforeUnmount(release)
}
