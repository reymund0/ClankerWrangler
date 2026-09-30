import type { ConfigResponse, ModelCatalogResponse, Preferences, Scope } from './types'

export class ApiError extends Error {
  constructor(message: string, readonly status: number) { super(message) }
}

let token = ''

export function bootstrapToken(): void {
  const fragment = new URLSearchParams(window.location.hash.replace(/^#/, ''))
  token = document.querySelector<HTMLMetaElement>('meta[name="clanker-session-token"]')?.content ?? fragment.get('token') ?? window.sessionStorage.getItem('clanker-routing-editor-token') ?? ''
  if (token) window.sessionStorage.setItem('clanker-routing-editor-token', token)
  if (window.location.hash) window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`)
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', 'X-Clanker-Token': token, ...init?.headers },
  })
  const payload = await response.json().catch(() => ({})) as T & { error?: string }
  if (!response.ok) throw new ApiError(payload.error || `Request failed (${response.status})`, response.status)
  return payload
}

export const api = {
  wranglerStatus: () => request<{ available: boolean; running: boolean; reason?: string }>('/api/wrangler'),
  runWrangler: () => request<{ success: boolean; message: string; output: string; truncated: boolean }>('/api/wrangler', { method: 'POST', body: '{}' }),
  config: () => request<ConfigResponse>('/api/config'),
  models: () => request<ModelCatalogResponse>('/api/models'),
  refreshModels: () => request<ModelCatalogResponse>('/api/models/refresh', { method: 'POST', body: '{}' }),
  preview: (scope: Scope, document: Preferences, requestBody?: Record<string, unknown>) =>
    request<{ effective: ConfigResponse['effective']; decision: import('./types').Decision | null }>('/api/preview', {
      method: 'POST', body: JSON.stringify({ scope, document, ...(requestBody ? { request: requestBody } : {}) }),
    }),
  save: (scope: Scope, document: Preferences, revision: string) =>
    request<ConfigResponse>('/api/save', { method: 'POST', body: JSON.stringify({ scope, document, revision }) }),
}
