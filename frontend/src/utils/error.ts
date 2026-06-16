/**
 * 统一的错误消息提取。
 *
 * 优先级：axios 响应体的 detail > 错误对象的 message > String 兜底。
 * 覆盖后端 FastAPI 的 `{ detail: "..." }` 错误格式与普通 Error。
 */
export function getErrorMessage(error: unknown): string {
  if (error && typeof error === 'object') {
    const anyErr = error as Record<string, any>
    const detail = anyErr.response?.data?.detail
    if (typeof detail === 'string' && detail) return detail
    if (typeof anyErr.message === 'string' && anyErr.message) return anyErr.message
  }
  return String(error)
}
