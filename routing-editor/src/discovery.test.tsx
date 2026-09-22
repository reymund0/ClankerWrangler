import { act, StrictMode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'
import type { ConfigResponse, ModelCatalogResponse } from './types'

const fixture: ConfigResponse = {
  schema_version: 1, policy_version: '1', scopes: { global: { path: '/fixture/global.json', revision: 'one', document: { schema_version: 1 } }, project: null },
  bundle: { schema_version: 1, policy_version: '1', roles: [], defaults: { schema_version: 1 },
    interactions: [{ id: 'planning', label: 'Planning', provider: 'codex', default_model: 'gpt-5.6-sol' }, { id: 'implementation', label: 'Implementation', provider: 'codex', default_model: 'gpt-5.6-sol' }, { id: 'claude-review', label: 'Claude review', provider: 'claude', default_model: 'claude-opus-5' }],
    models: [{ id: 'gpt-5.6-sol', label: 'Sol', provider: 'codex', efforts: ['low', 'high'] }, { id: 'claude-opus-5', label: 'Opus', provider: 'claude', efforts: ['low', 'high'] }],
    effort_orders: { codex: ['low', 'medium', 'high', 'xhigh'], claude: ['low', 'medium', 'high', 'max'] } },
  effective: { profiles: {}, interactions: {
    planning: { route: { model: 'gpt-5.6-sol', reasoning: { mode: 'adaptive' } }, provenance: { model: 'bundle.defaults' } },
    implementation: { route: { model: 'gpt-5.6-sol', reasoning: { mode: 'adaptive' } } },
    'claude-review': { route: { model: 'claude-opus-5', reasoning: { mode: 'adaptive' } }, provenance: { model: 'bundle.defaults' } },
  } },
}
const catalog: ModelCatalogResponse = { providers: {
  codex: { status: 'live', source: 'codex-cli', cli_version: 'fixture', updated_at: '2026-09-21T00:00:00Z', error: null, models: [
    { id: 'cli-model', label: 'CLI model', provider: 'codex', efforts: ['high', 'low', 'future'], default_effort: 'high' },
    { id: 'unknown-efforts', label: 'Unknown', provider: 'codex', efforts: null, default_effort: null },
  ] },
  claude: { status: 'live', source: 'claude-cli', cli_version: 'fixture', updated_at: '2026-09-21T00:00:00Z', error: null, models: [
    { id: 'opus[1m]', label: 'Opus alias', provider: 'claude', efforts: ['low', 'high'], default_effort: null },
  ] },
} }
const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status })
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>((done) => { resolve = done }); return { promise, resolve } }
let root: Root | undefined
beforeEach(() => { vi.useFakeTimers() })
afterEach(async () => { await act(async () => root?.unmount()); root = undefined; vi.unstubAllGlobals(); vi.useRealTimers() })
async function render(options: { config?: ConfigResponse; initial?: Promise<Response> | Response | (() => Promise<Response> | Response); strict?: boolean; settleInherited?: boolean; previewError?: string; refresh?: () => Promise<Response> | Response } = {}) {
  const config = options.config ?? fixture
  const fetchMock = vi.fn((path: string, init?: RequestInit) => {
    if (path === '/api/config') return Promise.resolve(response(config))
    if (path === '/api/models') return typeof options.initial === 'function' ? options.initial() : options.initial ?? Promise.resolve(response(catalog))
    if (path === '/api/models/refresh') return options.refresh?.() ?? Promise.resolve(response(catalog))
    if (path === '/api/save') return Promise.resolve(response({ ...config, scopes: { ...config.scopes, global: { ...config.scopes.global, document: JSON.parse(String(init?.body)).document, revision: 'two' } } }))
    if (options.previewError) return Promise.resolve(response({ error: options.previewError }, 400))
    return Promise.resolve(response({ effective: config.effective, decision: null }))
  })
  vi.stubGlobal('fetch', fetchMock)
  const element = document.createElement('div'); document.body.append(element); root = createRoot(element)
  await act(async () => { root!.render(options.strict ? <StrictMode><App /></StrictMode> : <App />) })
  if (options.settleInherited !== false) await act(async () => vi.advanceTimersByTimeAsync(180))
  return fetchMock
}
const route = () => document.querySelector('.interaction-card')!
const modelSelect = () => route().querySelector('.model-picker select') as HTMLSelectElement
const button = (text: string) => [...document.querySelectorAll('button')].find((item) => item.textContent === text)!
async function select(element: HTMLSelectElement, value: string) { await act(async () => { element.value = value; element.dispatchEvent(new Event('change', { bubbles: true })) }) }
const values = (element: HTMLSelectElement) => [...element.options].map((item) => item.value)

describe('local discovery controls', () => {
  it('offers all provider models and aliases without changing the inherited selection', async () => {
    await render()
    expect(values(modelSelect())).toEqual(expect.arrayContaining(['gpt-5.6-sol', 'cli-model', 'unknown-efforts']))
    expect(values(modelSelect())).not.toContain('opus[1m]')
    expect(modelSelect().value).toBe('gpt-5.6-sol')
    expect(document.body.textContent).toContain('alias; resolution may change')
    expect(button('Save global preferences').disabled).toBe(true)
  })
  it('keeps reasoning editable while catalog discovery is pending', async () => {
    const pending = deferred<Response>(); await render({ initial: pending.promise })
    await select(route().querySelectorAll('select')[1] as HTMLSelectElement, 'fixed')
    await act(async () => pending.resolve(response(catalog)))
    expect((route().querySelectorAll('select')[1] as HTMLSelectElement).value).toBe('fixed')
    expect(button('Save global preferences').disabled).toBe(false)
  })
  it('explains discovery failure without offering manual or bundled alternatives', async () => {
    const configured = structuredClone(fixture)
    configured.bundle.models.push({ id: 'bundle-only', label: 'Bundle only', provider: 'codex', efforts: ['high'] })
    await render({ config: configured, initial: response({ error: 'Unknown endpoint' }, 404) })
    expect(document.body.textContent).toContain('Model discovery is unavailable')
    expect(values(modelSelect())).not.toContain('bundle-only')
    expect(document.querySelector('input[aria-label="Custom model ID"]')).toBeNull()
    expect(document.body.textContent).not.toContain('Enter custom model ID')
  })
  it('offers only CLI models for profile creation and clears selection on provider change', async () => {
    await render()
    expect(document.querySelector('#preview-title')?.textContent).toBe('Preview model and reasoning')
    await act(async () => button('Show advanced Adaptive profiles').click())
    const controls = document.querySelectorAll('.add-profile select')
    const provider = controls[0] as HTMLSelectElement, model = controls[1] as HTMLSelectElement
    expect(values(model)).toEqual(['', 'cli-model', 'unknown-efforts'])
    expect(document.querySelector('.add-profile input')).toBeNull()
    await select(model, 'cli-model')
    expect(button('Add profile').disabled).toBe(false)
    await select(provider, 'claude')
    expect(model.value).toBe('')
    expect(button('Add profile').disabled).toBe(true)
    expect(values(model)).toEqual(['', 'opus[1m]'])
    await select(model, 'opus[1m]')
    await act(async () => button('Add profile').click())
    expect(document.querySelector('.profile h3')?.textContent).toBe('claude:opus[1m]')
  })
  it('uses each profile model CLI efforts for all tiers and the default ceiling', async () => {
    await render()
    await act(async () => button('Show advanced Adaptive profiles').click())
    const model = document.querySelectorAll('.add-profile select')[1] as HTMLSelectElement
    await select(model, 'cli-model')
    await act(async () => button('Add profile').click())
    const controls = [...document.querySelectorAll('.profile select')] as HTMLSelectElement[]
    expect(controls).toHaveLength(5)
    expect(document.querySelector('.profile input')).toBeNull()
    for (const control of controls) {
      expect([...control.options].filter((option) => !option.disabled && ['low', 'high'].includes(option.value)).map((option) => option.value)).toEqual(['low', 'high'])
      expect([...control.options].find((option) => option.value === 'future')?.disabled).toBe(true)
    }
    await select(controls[1], 'high')
    expect(controls[1].value).toBe('high')
  })
  it('intersects effort metadata with policy order and preserves a saved unsupported effort', async () => {
    const configured = structuredClone(fixture)
    configured.scopes.global.document = { schema_version: 1, interactions: { planning: { model: 'cli-model', reasoning: { mode: 'fixed', effort: 'xhigh' } } } }
    await render({ config: configured })
    const effort = route().querySelectorAll('select')[2] as HTMLSelectElement
    expect(effort.value).toBe('xhigh')
    expect(values(effort).filter((value) => ['low', 'high'].includes(value))).toEqual(['low', 'high'])
    expect([...effort.options].find((item) => item.value === 'future')?.disabled).toBe(true)
    expect([...effort.options].find((item) => item.value === 'xhigh')?.disabled).toBe(false)
    expect(button('Save global preferences').disabled).toBe(true)
  })
  it('shows policy effort choices as unverified when metadata is unknown', async () => {
    await render(); await select(modelSelect(), 'unknown-efforts')
    const effort = route().querySelectorAll('select')[2] as HTMLSelectElement
    expect(values(effort)).toEqual(expect.arrayContaining(['low', 'medium', 'high', 'xhigh']))
    expect(route().textContent).toContain('unverified')
  })
  it('refreshes provenance without replacing the draft or temporary session model', async () => {
    const refreshed = structuredClone(catalog); refreshed.providers.codex.status = 'stale'; refreshed.providers.codex.error = 'CLI unavailable'
    const fetchMock = await render({ refresh: () => response(refreshed) })
    await select(modelSelect(), 'cli-model')
    const session = document.querySelector('.session-fieldset .model-picker select') as HTMLSelectElement
    expect(session.value).toBe(''); await select(session, 'unknown-efforts')
    await act(async () => button('Refresh models').click())
    expect(modelSelect().value).toBe('cli-model'); expect(session.value).toBe('unknown-efforts')
    expect(document.body.textContent).toContain('stale'); expect(document.body.textContent).toContain('CLI unavailable')
    expect(button('Save global preferences').disabled).toBe(false)
    const refreshCall = fetchMock.mock.calls.find(([path]) => path === '/api/models/refresh')!
    expect(refreshCall[1]?.body).toBe('{}')
  })
  it('explains a failed HTTP refresh while retaining the previous choices and draft', async () => {
    await render({ refresh: () => response({ error: 'Discovery temporarily unavailable' }, 503) })
    await select(modelSelect(), 'cli-model'); await act(async () => button('Refresh models').click())
    expect(document.querySelector('.catalog-status')?.textContent).toContain('Discovery temporarily unavailable')
    expect(values(modelSelect())).toContain('unknown-efforts'); expect(modelSelect().value).toBe('cli-model')
  })
  it('ignores an older catalog response after a newer request has completed', async () => {
    const first = deferred<Response>(), second = deferred<Response>()
    let calls = 0
    await render({ strict: true, initial: () => ++calls === 1 ? first.promise : second.promise })
    expect(calls).toBe(2)
    const newer = structuredClone(catalog); newer.providers.codex.models[0].id = 'newer-model'
    await act(async () => second.resolve(response(newer)))
    expect(values(modelSelect())).toContain('newer-model')
    await act(async () => first.resolve(response(catalog)))
    expect(values(modelSelect())).toContain('newer-model')
    expect(values(modelSelect())).not.toContain('cli-model')
  })
  it('resets a temporary session model without writing a route override', async () => {
    await render()
    const session = document.querySelector('.session-fieldset .model-picker select') as HTMLSelectElement
    await select(session, 'cli-model')
    await act(async () => button('Reset session model').click())
    expect(session.value).toBe('')
    expect(button('Save global preferences').disabled).toBe(true)
  })
  it('keeps alias selection exact and exposes existing Adaptive validation', async () => {
    const fetchMock = await render({ previewError: 'interactions.claude-review: Adaptive requires a complete profile for opus[1m]' })
    const claude = [...document.querySelectorAll('.interaction-card')].find((item) => item.textContent?.includes('Claude review'))!
    await select(claude.querySelector('.model-picker select') as HTMLSelectElement, 'opus[1m]')
    await act(async () => vi.advanceTimersByTimeAsync(180))
    expect(claude.textContent).toContain('Adaptive requires a complete profile for opus[1m]')
    const call = fetchMock.mock.calls.filter(([path]) => path === '/api/preview').at(-1)!
    expect(JSON.parse(String(call[1]?.body)).document.interactions['claude-review'].model).toBe('opus[1m]')
  })

  it('uses the draft interaction and specialist model for session effort metadata without a model override', async () => {
    const configured = structuredClone(fixture), models = structuredClone(catalog)
    configured.bundle.roles = [{ id: 'clanker-architect', label: 'Architect' }]
    configured.scopes.global.document = { schema_version: 1, interactions: { planning: { model: 'cli-model', specialists: { 'clanker-architect': { model: 'specialist-model' } } } } }
    models.providers.codex.models.push({ id: 'specialist-model', label: 'Specialist', provider: 'codex', efforts: ['medium'], default_effort: 'medium' })
    await render({ config: configured, initial: response(models) })
    await select(document.querySelector('.preview-form select') as HTMLSelectElement, 'planning')
    const effort = () => document.querySelectorAll('.session-fieldset select')[2] as HTMLSelectElement
    expect(values(effort())).toContain('high'); expect(values(effort())).not.toContain('xhigh')
    await select(document.querySelectorAll('.preview-form > label select')[1] as HTMLSelectElement, 'clanker-architect')
    expect(values(effort())).toEqual(['', 'medium'])
    await select(document.querySelector('.preview-form select') as HTMLSelectElement, 'implementation')
    expect(values(effort())).toContain('xhigh')
    await select(document.querySelector('.preview-form select') as HTMLSelectElement, 'planning')
    await act(async () => button('Show advanced activity defaults').click())
    await select(document.querySelector('.advanced-grid .model-picker select') as HTMLSelectElement, 'unknown-efforts')
    expect(values(effort())).toContain('xhigh')
  })
  it('does not display the first real model while inherited resolution is pending or invalid', async () => {
    const configured = structuredClone(fixture)
    configured.bundle.models.unshift({ id: 'gpt-6-astra', label: 'Astra', provider: 'codex', efforts: ['high'] })
    await render({ config: configured, settleInherited: false, previewError: 'Invalid inherited preferences' })
    expect(modelSelect().value).toBe('')
    expect(modelSelect().selectedOptions[0].disabled).toBe(true)
    expect(modelSelect().selectedOptions[0].textContent).toContain('Inherited model unresolved')
    await act(async () => vi.advanceTimersByTimeAsync(180))
    expect(modelSelect().value).toBe('')
    await select(modelSelect(), 'cli-model')
    expect(modelSelect().value).toBe('cli-model')
    expect(button('Save global preferences').disabled).toBe(false)
  })

})
