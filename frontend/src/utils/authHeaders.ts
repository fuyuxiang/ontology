/**
 * 为原生 fetch 请求提供与 axios client 一致的鉴权头。
 *
 * 用于 SSE/流式等无法走 axios 封装的场景，避免裸 fetch 漏注入 JWT。
 * 注意：仅补 Authorization，调用方自行决定 Content-Type
 *（FormData 上传不要设 Content-Type，让浏览器自动带 boundary）。
 */
export function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const token = localStorage.getItem('token')
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  }
}
