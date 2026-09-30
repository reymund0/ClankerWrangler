import { afterEach, expect, it, vi } from 'vitest'
import { api, bootstrapToken } from './api'

afterEach(() => { document.head.innerHTML = ''; sessionStorage.clear(); vi.unstubAllGlobals() })

it('uses the served session instead of stale stored or fragment credentials', async () => {
  sessionStorage.setItem('clanker-routing-editor-token', 'stale')
  document.head.innerHTML = '<meta name="clanker-session-token" content="current-session">'
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) })
  vi.stubGlobal('fetch', fetch)
  bootstrapToken()
  await api.config()
  expect(fetch.mock.calls[0][1].headers['X-Clanker-Token']).toBe('current-session')
  document.querySelector('meta')!.setAttribute('content', 'restarted-session')
  bootstrapToken()
  await api.config()
  expect(fetch.mock.calls[1][1].headers['X-Clanker-Token']).toBe('restarted-session')
})
