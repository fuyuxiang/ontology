/**
 * Build the embedded code-server URL for a workspace folder.
 *
 * The host must be derived in the browser, not on the server: the backend only
 * sees the `Host` header after the dev-server proxy has rewritten it
 * (`changeOrigin: true`), so it always resolves to the backend's own address
 * (e.g. `127.0.0.1`) instead of the address the user actually opened. Deriving
 * it from `window.location` keeps a single build correct on localhost, on a LAN
 * IP, and behind a domain without any per-environment configuration.
 *
 * `publicUrl` is an escape hatch for reverse-proxy setups where code-server is
 * not reachable at `<current host>:<port>` (for example when it is mounted
 * under a path on 443). It is empty unless explicitly configured.
 */
export interface WorkspaceLocation {
  folder: string
  port: number
  public_url?: string
}

export function buildCodeServerUrl(ws: WorkspaceLocation): string {
  const folder = encodeURIComponent(ws.folder)

  const publicUrl = ws.public_url?.trim()
  if (publicUrl) {
    return `${publicUrl.replace(/\/+$/, '')}/?folder=${folder}`
  }

  const { protocol, hostname } = window.location
  return `${protocol}//${hostname}:${ws.port}/?folder=${folder}`
}
