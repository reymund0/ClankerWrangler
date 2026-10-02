import { act, StrictMode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'
import type { ConfigResponse, ModelCatalogResponse, Preferences } from './types'

const fixture: ConfigResponse = {
  schema_version: 1, policy_version: '4', scopes: { global: { path: '/fixture/global.json', revision: 'one', document: { schema_version: 1 } } },
  bundle: { schema_version: 1, policy_version: '4', roles: [], defaults: { schema_version: 1 },
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
async function render(options: { config?: ConfigResponse; initial?: Promise<Response> | Response | (() => Promise<Response> | Response); strict?: boolean; settleInherited?: boolean; previewError?: string; refresh?: () => Promise<Response> | Response; saveResponse?: (body: { scope?: string; revision?: string; document?: Preferences }) => Response | Promise<Response> } = {}) {
  const config = options.config ?? fixture
  const fetchMock = vi.fn((path: string, init?: RequestInit) => {
    if (path === '/api/config') return Promise.resolve(response(config))
    if (path === '/api/models') return typeof options.initial === 'function' ? options.initial() : options.initial ?? Promise.resolve(response(catalog))
    if (path === '/api/models/refresh') return options.refresh?.() ?? Promise.resolve(response(catalog))
    if (path === '/api/save') {
      const body = JSON.parse(String(init?.body)) as { scope?: string; revision?: string; document?: Preferences }
      return Promise.resolve(options.saveResponse?.(body) ?? response({ ...config, scopes: { ...config.scopes, global: { ...config.scopes.global, document: body.document, revision: 'two' } } }))
    }
    if (options.previewError) return Promise.resolve(response({ error: options.previewError }, 400))
    return Promise.resolve(response({ effective: config.effective, decision: null }))
  })
  vi.stubGlobal('fetch', fetchMock)
  const element = document.createElement('div'); document.body.append(element); root = createRoot(element)
  await act(async () => { root!.render(options.strict ? <StrictMode><App /></StrictMode> : <App />) })
  if (options.settleInherited !== false) await act(async () => vi.advanceTimersByTimeAsync(180))
  await openTab('Activity defaults')
  return fetchMock
}
function tabButton(name: string) { return [...document.querySelectorAll<HTMLButtonElement>('[role="tab"]')].find((item) => item.textContent?.trim().startsWith(name))! }
async function openTab(name: string) { const tab = tabButton(name); if (tab.getAttribute('aria-selected') !== 'true') await act(async () => { tab.click() }) }
function activePanel() { const tab = document.querySelector<HTMLButtonElement>('[role="tab"][aria-selected="true"]')!; return document.getElementById(tab.getAttribute('aria-controls')!)! }
const route = () => activePanel().querySelector('.activity-default-card')!
const modelSelect = () => route().querySelector('.model-picker select') as HTMLSelectElement
const button = (text: string) => [...document.querySelectorAll('button')].find((item) => item.textContent === text)!
const actionButton = (text: string, container: ParentNode = document) => [...container.querySelectorAll<HTMLButtonElement>('button')].find((item) => item.textContent?.trim() === text)!
async function select(element: HTMLSelectElement, value: string) { await act(async () => { element.value = value; element.dispatchEvent(new Event('change', { bubbles: true })) }) }
const values = (element: HTMLSelectElement) => [...element.options].map((item) => item.value)
const profileSelect = () => activePanel().querySelector<HTMLSelectElement>('.profile-addbar select[aria-label="Profile model"]')!
const profileFamilyButton = (family: string) => [...activePanel().querySelectorAll<HTMLButtonElement>('[role="table"] button[aria-expanded]')].find((item) => item.querySelector('strong')?.textContent?.includes(family))!

describe('local discovery controls', () => {
  it('offers all provider models and aliases without changing the inherited selection', async () => {
    await render()
    expect(values(modelSelect())).toEqual(expect.arrayContaining(['gpt-5.6-sol', 'cli-model', 'unknown-efforts']))
    expect(values(modelSelect())).not.toContain('opus[1m]')
    expect(modelSelect().value).toBe('gpt-5.6-sol')
    expect(button('Save global preferences').disabled).toBe(true)
  })
  it('keeps reasoning editable while catalog discovery is pending', async () => {
    const pending = deferred<Response>(); await render({ initial: pending.promise })
    const mode = route().querySelector('[role="group"][aria-label="planning reasoning mode"]')!
    await act(async () => { actionButton('Fixed', mode).click() })
    await act(async () => pending.resolve(response(catalog)))
    expect(actionButton('Fixed', mode).getAttribute('aria-pressed')).toBe('true')
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
  it('groups profile rows into sorted, accessible version family accordions', async () => {
    const configured = structuredClone(fixture)
    const profile = { tiers: { straightforward: 'medium', involved: 'high', demanding: 'xhigh' }, default_ceiling: 'high' }
    configured.effective!.profiles = {
      'codex:gpt-5.6-sol': profile,
      'codex:gpt-6-mini': profile,
      'codex:gpt-6.10-sol': profile,
      'codex:gpt-6.2-sol': profile,
      'codex:gpt-6.1-sol': profile,
      'codex:gpt-5.5-sol': profile,
      'codex:custom-model-v9': profile,
      'claude:opus[1m]': profile,
    }
    configured.scopes.global.document = { schema_version: 1, adaptive_profiles: { 'codex:gpt-6.2-sol': profile } }
    const discovered = structuredClone(catalog)
    discovered.providers.codex.models.push(
      { id: 'gpt-5.6-sol', label: '5.6 Sol', provider: 'codex', efforts: ['high'], default_effort: 'high' },
      { id: 'gpt-6-mini', label: '6 Mini', provider: 'codex', efforts: ['high'], default_effort: 'high' },
      { id: 'gpt-6.10-sol', label: '6.10 Sol', provider: 'codex', efforts: ['high'], default_effort: 'high' },
      { id: 'gpt-6.2-sol', label: '6.2 Sol', provider: 'codex', efforts: ['high'], default_effort: 'high' },
      { id: 'gpt-6.1-sol', label: '6.1 Sol', provider: 'codex', efforts: ['high'], default_effort: 'high' },
    )
    await render({ config: configured, initial: response(discovered) })
    await openTab('Adaptive profiles')
    const table = activePanel().querySelector<HTMLElement>('[role="table"][aria-label="Adaptive model profiles"]')!
    const buttons = [...table.querySelectorAll<HTMLButtonElement>('button[aria-expanded]')]
    const names = buttons.map((item) => item.querySelector('strong')?.textContent?.trim())
    expect(names).toHaveLength(8)
    expect(names).toEqual(['Claude · Models', 'Codex · 6.10', 'Codex · 6.2', 'Codex · 6.1', 'Codex · 6', 'Codex · 5.6', 'Codex · 5.5', 'Codex · Other'])
    const button55 = profileFamilyButton('Codex · 5.5')
    const button62 = profileFamilyButton('Codex · 6.2')
    const claude = profileFamilyButton('Claude · Models')
    expect([...button55.querySelectorAll('span')].map((item) => item.textContent)).toContain('1 models')
    expect([...button62.querySelectorAll('span')].map((item) => item.textContent)).toContain('1 models')
    expect([...button62.querySelectorAll('span')].map((item) => item.textContent)).toContain('· 1 customized here')
    expect(button55.getAttribute('aria-expanded')).toBe('false')
    expect(button62.getAttribute('aria-expanded')).toBe('true')
    expect(claude.getAttribute('aria-expanded')).toBe('false')
    expect([...table.querySelectorAll<HTMLElement>('.profile-row')].every((row) => row.closest('[role="table"]') === table)).toBe(true)
    await act(async () => { button55.click() })
    expect(button55.getAttribute('aria-expanded')).toBe('true')
    expect(table.textContent).toContain('codex:gpt-5.5-sol')
  })
  it('shows exactly three described adaptive tiers and links descriptions to editable controls', async () => {
    const configured = structuredClone(fixture)
    const profile = { tiers: { straightforward: 'medium', involved: 'high', demanding: 'xhigh' }, default_ceiling: 'high' }
    configured.scopes.global.document = { schema_version: 1, adaptive_profiles: { 'codex:cli-model': profile } }
    configured.effective!.profiles = { 'codex:cli-model': profile }
    await render({ config: configured })
    await openTab('Adaptive profiles')
    const table = activePanel().querySelector<HTMLElement>('[role="table"][aria-label="Adaptive model profiles"]')!
    expect(activePanel().querySelector('[aria-label="Adaptive tier definitions"]')?.textContent).toContain('Established approach, limited remaining decisions, and direct acceptance checks.')
    expect(activePanel().querySelector('[aria-label="Adaptive tier definitions"]')?.textContent).toContain('difficult correctness arguments.')
    const headers = [...table.querySelectorAll<HTMLElement>('.profile-heading [role="columnheader"]')]
    expect(headers.map((item) => item.querySelector('span:not(.sr-only)')?.textContent ?? item.textContent?.trim())).toEqual(['Model', 'Straightforward', 'Involved', 'Demanding', 'Default ceiling', 'Actions'])
    expect(headers.slice(1, 4).map((item) => item.getAttribute('aria-label'))).toEqual([
      'Straightforward: Established approach, limited remaining decisions, and direct acceptance checks.',
      'Involved: Meaningful decisions or bounded uncertainty involving related behavior.',
      'Demanding: Substantial unresolved reasoning across interacting constraints or difficult correctness arguments.',
    ])
    const row = [...table.querySelectorAll<HTMLElement>('.profile-row')].find((item) => item.textContent?.includes('codex:cli-model'))!
    const fields = [...row.querySelectorAll<HTMLSelectElement>('select')]
    expect(fields).toHaveLength(4)
    for (const [index, tier] of ['straightforward', 'involved', 'demanding'].entries()) {
      const descriptionId = `tier-definition-${tier}`
      expect(fields[index].getAttribute('aria-describedby')).toContain(descriptionId)
      expect(document.getElementById(descriptionId)?.textContent).toBe(headers[index + 1].getAttribute('aria-label')?.split(': ').slice(1).join(': '))
    }
    expect(table.querySelector('.profile-family-heading [aria-colspan="6"]')).toBeTruthy()
    expect(activePanel().textContent).toContain('An involved task on cli-model maps to high')
  })
  it('defaults route preview to Straightforward while retaining exactly three task tier choices', async () => {
    await render()
    await openTab('Preview a route')
    const group = activePanel().querySelector<HTMLElement>('[role="group"][aria-label="Task tier"]')!
    const choices = [...group.querySelectorAll<HTMLButtonElement>('button')]
    expect(choices.map((choice) => choice.textContent?.trim())).toEqual(['Straightforward', 'Involved', 'Demanding'])
    expect(choices[0].getAttribute('aria-pressed')).toBe('true')
  })
  it('keeps a pending conversion read-only on open and preview until explicit save', async () => {
    const configured = structuredClone(fixture)
    const profile = { tiers: { straightforward: 'medium', involved: 'high', demanding: 'xhigh' }, default_ceiling: 'high' }
    configured.scopes.global = { ...configured.scopes.global!, revision: 'raw-legacy-source-hash', migration_pending: true, document: { schema_version: 1, adaptive_profiles: { 'codex:cli-model': profile } } }
    configured.effective!.profiles = { 'codex:cli-model': profile }
    const fetchMock = await render({ config: configured })
    const migrationNote = document.querySelector('.header-migration-row .migration-save-note')!
    expect(migrationNote.textContent).toContain('Routine → Straightforward')
    expect(migrationNote.textContent).toContain('Mechanical is retired')
    expect(button('Save global preferences').disabled).toBe(false)
    await openTab('Adaptive profiles')
    expect(activePanel().textContent).toContain('Legacy profile conversion is pending.')
    expect(activePanel().textContent).toContain('Mechanical is retired')
    expect(button('Save global preferences').disabled).toBe(false)
    expect(fetchMock.mock.calls.some(([path]) => path === '/api/save')).toBe(false)
    await openTab('Preview a route')
    expect(activePanel().querySelector('[role="group"][aria-label="Task tier"] button[aria-pressed="true"]')?.textContent?.trim()).toBe('Straightforward')
    expect(fetchMock.mock.calls.some(([path]) => path === '/api/save')).toBe(false)
    await act(async () => { button('Export draft & reload').click(); await Promise.resolve() })
    expect(fetchMock.mock.calls.some(([path]) => path === '/api/save')).toBe(false)
  })
  it.each([409, 500])('retains edited draft and pending conversion after save failure (%i)', async (status) => {
    const configured = structuredClone(fixture)
    const profile = { tiers: { straightforward: 'medium', involved: 'high', demanding: 'xhigh' }, default_ceiling: 'high' }
    configured.scopes.global = { ...configured.scopes.global!, migration_pending: true, document: { schema_version: 1, adaptive_profiles: { 'codex:cli-model': profile } } }
    configured.effective!.profiles = { 'codex:cli-model': profile }
    await render({ config: configured, saveResponse: () => response({ error: status === 409 ? 'Preferences changed since loading.' : 'Save rejected for this test.' }, status) })
    await openTab('Adaptive profiles')
    const row = [...activePanel().querySelectorAll<HTMLElement>('.profile-row')].find((item) => item.textContent?.includes('codex:cli-model'))!
    const involved = row.querySelectorAll<HTMLSelectElement>('select')[1]
    await select(involved, 'low')
    await act(async () => { button('Save global preferences').click(); await Promise.resolve() })
    expect(involved.value).toBe('low')
    expect(activePanel().textContent).toContain('Legacy profile conversion is pending.')
    expect(button('Save global preferences').disabled).toBe(false)
    expect(document.body.textContent).toContain(status === 409 ? 'Save conflict: your draft is still available' : 'Save rejected for this test.')
  })
  it('uses the provider switch and a single provider-specific local model selector', async () => {
    await render()
    await openTab('Adaptive profiles')
    const provider = activePanel().querySelector('[aria-label="Profile provider"]')!
    const model = profileSelect()
    expect([...provider.querySelectorAll<HTMLButtonElement>('button')].find((item) => item.textContent === 'Codex')?.getAttribute('aria-pressed')).toBe('true')
    expect(values(model)).toEqual(['', 'cli-model', 'unknown-efforts'])
    await select(model, 'cli-model')
    expect(actionButton('Customize profile', activePanel()).disabled).toBe(false)
    await act(async () => { actionButton('Claude', provider).click() })
    expect(model.value).toBe('')
    expect(values(model)).toEqual(['', 'opus[1m]'])
    expect(actionButton('Customize profile', activePanel()).disabled).toBe(true)
    expect([...model.options].find((option) => option.value === 'opus[1m]')?.textContent).toContain('alias; resolution may change')
    await select(model, 'opus[1m]')
    await act(async () => { actionButton('Customize profile', activePanel()).click() })
    expect([...activePanel().querySelectorAll<HTMLElement>('.profile-row')].some((row) => row.textContent?.includes('claude:opus[1m]'))).toBe(true)
  })
  it('keeps accordion state local to the UI and excludes it from saved preferences', async () => {
    const configured = structuredClone(fixture)
    const inherited = { tiers: { straightforward: 'medium', involved: 'high', demanding: 'xhigh' }, default_ceiling: 'high' }
    configured.effective!.profiles = { 'codex:gpt-5.6-sol': inherited }
    const discovered = structuredClone(catalog)
    discovered.providers.codex.models.push({ id: 'gpt-5.6-sol', label: '5.6 Sol', provider: 'codex', efforts: ['low', 'medium', 'high', 'xhigh'], default_effort: 'high' })
    const fetchMock = await render({ config: configured, initial: response(discovered) })
    await openTab('Adaptive profiles')
    expect([...activePanel().querySelectorAll<HTMLButtonElement>('[role="table"] button[aria-expanded]')].some((item) => item.querySelector('strong')?.textContent?.includes('Codex · Other'))).toBe(false)
    const family = profileFamilyButton('Codex · 5.6')
    expect(family.getAttribute('aria-expanded')).toBe('false')
    expect(button('Save global preferences').disabled).toBe(true)
    await act(async () => { family.click() })
    expect(family.getAttribute('aria-expanded')).toBe('true')
    expect(button('Save global preferences').disabled).toBe(true)
    let row = [...activePanel().querySelectorAll<HTMLElement>('.profile-row')].find((item) => item.textContent?.includes('codex:gpt-5.6-sol'))!
    await act(async () => { actionButton('Customize', row).click() })
    row = [...activePanel().querySelectorAll<HTMLElement>('.profile-row')].find((item) => item.textContent?.includes('codex:gpt-5.6-sol'))!
    const involved = row.querySelectorAll<HTMLSelectElement>('select')[1]
    await select(involved, 'high')
    await act(async () => { actionButton('Save global preferences').click(); await Promise.resolve() })
    const save = fetchMock.mock.calls.find(([path]) => path === '/api/save')!
    expect(JSON.parse(save[1]?.body as string).document).toEqual({ schema_version: 1, adaptive_profiles: { 'codex:gpt-5.6-sol': { ...inherited, tiers: { ...inherited.tiers, involved: 'high' } } } })
  })
  it('keeps the no local models message and disabled empty provider selects', async () => {
    const empty: ModelCatalogResponse = { providers: {
      codex: { ...catalog.providers.codex, models: [] },
      claude: { ...catalog.providers.claude, models: [] },
    } }
    await render({ initial: response(empty) })
    await openTab('Adaptive profiles')
    expect(profileSelect().disabled).toBe(true)
    expect(activePanel().textContent).toContain('No models were reported by the local codex CLI.')
    const provider = activePanel().querySelector('[aria-label="Profile provider"]')!
    await act(async () => { actionButton('Claude', provider).click() })
    expect(profileSelect().disabled).toBe(true)
    expect(activePanel().textContent).toContain('No models were reported by the local claude CLI.')
  })
  it('customizes a locally reported Claude alias through its model-specific selector', async () => {
    await render()
    await openTab('Adaptive profiles')
    const provider = activePanel().querySelector('[aria-label="Profile provider"]')!
    const model = profileSelect()
    const codex = model
    await select(codex, 'cli-model')
    expect(actionButton('Customize profile', activePanel()).disabled).toBe(false)
    await act(async () => { actionButton('Claude', provider).click() })
    expect(codex.value).toBe('')
    await select(model, 'opus[1m]')
    await act(async () => { actionButton('Customize profile', activePanel()).click() })
    expect([...activePanel().querySelectorAll<HTMLElement>('.profile-row')].some((row) => row.textContent?.includes('claude:opus[1m]'))).toBe(true)
  })
  it('renders effort meters from each model choices including a saved unavailable value', async () => {
    const configured = structuredClone(fixture)
    configured.bundle.effort_orders.codex = ['minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra']
    configured.effective!.profiles = {
      'codex:meter-short': { tiers: { straightforward: 'low', involved: 'high', demanding: 'high' }, default_ceiling: 'high' },
      'codex:meter-many': { tiers: { straightforward: 'low', involved: 'high', demanding: 'high' }, default_ceiling: 'ultra' },
      'codex:saved-away': { tiers: { straightforward: 'medium', involved: 'xhigh', demanding: 'high' }, default_ceiling: 'high' },
    }
    const discovered = structuredClone(catalog)
    discovered.providers.codex.models.push(
      { id: 'meter-short', label: 'Short meter', provider: 'codex', efforts: ['low', 'high'], default_effort: 'high' },
      { id: 'meter-many', label: 'Long meter', provider: 'codex', efforts: ['minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra'], default_effort: 'high' },
      { id: 'saved-away', label: 'Saved effort', provider: 'codex', efforts: ['high', 'low', 'future'], default_effort: 'high' },
    )
    configured.scopes.global.document = { schema_version: 1, adaptive_profiles: { 'codex:saved-away': {
      tiers: { straightforward: 'medium', involved: 'xhigh', demanding: 'high' }, default_ceiling: 'high',
    } } }
    await render({ config: configured, initial: response(discovered) })
    await openTab('Adaptive profiles')
    const row = (key: string) => [...activePanel().querySelectorAll<HTMLElement>('.profile-row')].find((item) => item.textContent?.includes(key))!
    // The model is followed by three tier cells, the ceiling, and actions.
    const shortCells = row('codex:meter-short').querySelectorAll<HTMLElement>('[role="cell"]')
    const short = shortCells[2].querySelectorAll<HTMLElement>('.effort-meter i')
    expect([...short].map((bar) => bar.dataset.effort)).toEqual(['low', 'high'])
    expect([...short].map((bar) => bar.className)).toEqual(['filled effort-low', 'filled effort-high'])
    const manyCells = row('codex:meter-many').querySelectorAll<HTMLElement>('[role="cell"]')
    const many = manyCells[1].querySelectorAll<HTMLElement>('.effort-meter i')
    expect([...many].map((bar) => bar.dataset.effort)).toEqual(['minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra'])
    expect([...many].map((bar) => bar.classList.contains('filled'))).toEqual([true, true, true, true, false, false, false])
    expect([...many].slice(0, 4).map((bar) => [...bar.classList].find((name) => name.startsWith('effort-')))).toEqual(['effort-minimal', 'effort-low', 'effort-medium', 'effort-high'])
    const savedCells = row('codex:saved-away').querySelectorAll<HTMLElement>('[role="cell"]')
    const savedStraightforward = savedCells[0].querySelectorAll<HTMLElement>('.effort-meter i')
    expect([...savedStraightforward].map((bar) => bar.dataset.effort)).toEqual(['low', 'medium', 'high'])
    expect([...savedStraightforward].map((bar) => bar.classList.contains('filled'))).toEqual([true, true, false])
    const savedInvolved = savedCells[1].querySelectorAll<HTMLElement>('.effort-meter i')
    expect([...savedInvolved].map((bar) => bar.dataset.effort)).toEqual(['low', 'high', 'xhigh'])
    expect([...savedInvolved].map((bar) => bar.classList.contains('filled'))).toEqual([true, true, true])
    expect([...savedInvolved].map((bar) => bar.dataset.effort)).not.toContain('future')
    expect(row('codex:meter-short').querySelector('.effort-meter')?.getAttribute('aria-hidden')).toBe('true')
    expect(row('codex:saved-away').querySelector('select option[value="xhigh"]')?.textContent).toContain('saved; unavailable for new selection')
  })
  it('uses each profile model CLI efforts for all tiers and the default ceiling', async () => {
    await render()
    await openTab('Adaptive profiles')
    const model = profileSelect()
    await select(model, 'cli-model')
    await act(async () => { actionButton('Customize profile', activePanel()).click() })
    const row = [...activePanel().querySelectorAll<HTMLElement>('.profile-row')].find((item) => item.textContent?.includes('codex:cli-model'))!
    const controls = [...row.querySelectorAll('select')] as HTMLSelectElement[]
    expect(controls).toHaveLength(4)
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
    const effort = route().querySelector<HTMLSelectElement>('.effort-field select')!
    expect(effort.value).toBe('xhigh')
    expect(values(effort).filter((value) => ['low', 'high'].includes(value))).toEqual(['low', 'high'])
    expect([...effort.options].find((item) => item.value === 'future')?.disabled).toBe(true)
    expect([...effort.options].find((item) => item.value === 'xhigh')?.disabled).toBe(false)
    expect(button('Save global preferences').disabled).toBe(true)
  })
  it('shows policy effort choices as unverified when metadata is unknown', async () => {
    await render(); await select(modelSelect(), 'unknown-efforts')
    const effort = route().querySelector<HTMLSelectElement>('.effort-field select')!
    expect(values(effort)).toEqual(expect.arrayContaining(['low', 'medium', 'high', 'xhigh']))
    expect(route().textContent).toContain('unverified')
  })
  it('refreshes provenance without replacing the draft or temporary session model', async () => {
    const refreshed = structuredClone(catalog); refreshed.providers.codex.status = 'stale'; refreshed.providers.codex.error = 'CLI unavailable'
    const fetchMock = await render({ refresh: () => response(refreshed) })
    await select(modelSelect(), 'cli-model')
    await openTab('Preview a route')
    const previewSession = activePanel().querySelector('.session-fieldset')!
    await act(async () => { (previewSession.querySelector('summary') as HTMLElement).click() })
    const session = previewSession.querySelector('.model-picker select') as HTMLSelectElement
    expect(session.value).toBe(''); await select(session, 'unknown-efforts')
    await openTab('Worker routes')
    await act(async () => { actionButton('Refresh models', activePanel()).click() })
    expect(document.body.textContent).toContain('stale'); expect(document.body.textContent).toContain('CLI unavailable')
    expect(button('Save global preferences').disabled).toBe(false)
    const refreshCall = fetchMock.mock.calls.find(([path]) => path === '/api/models/refresh')!
    expect(refreshCall[1]?.body).toBe('{}')
    await openTab('Activity defaults')
    expect(modelSelect().value).toBe('cli-model')
    await openTab('Preview a route')
    expect((activePanel().querySelector('.session-fieldset .model-picker select') as HTMLSelectElement).value).toBe('unknown-efforts')
  })
  it('explains a failed HTTP refresh while retaining the previous choices and draft', async () => {
    await render({ refresh: () => response({ error: 'Discovery temporarily unavailable' }, 503) })
    await select(modelSelect(), 'cli-model'); await openTab('Worker routes'); await act(async () => { actionButton('Refresh models', activePanel()).click() })
    expect(activePanel().querySelector('.catalog-status')?.textContent).toContain('Discovery temporarily unavailable')
    await openTab('Activity defaults')
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
    await openTab('Preview a route')
    const session = activePanel().querySelector('.session-fieldset .model-picker select') as HTMLSelectElement
    await select(session, 'cli-model')
    await act(async () => { actionButton('Reset session model', activePanel()).click() })
    expect(session.value).toBe('')
    expect(button('Save global preferences').disabled).toBe(true)
  })
  it('keeps alias selection exact and exposes existing Adaptive validation', async () => {
    const fetchMock = await render({ previewError: 'interactions.claude-review: Adaptive requires a complete profile for opus[1m]' })
    await openTab('Worker routes')
    await act(async () => { activePanel().querySelector<HTMLButtonElement>('.claude-row .route-cell')!.click() })
    const claude = activePanel().querySelector('.inspector')!
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
    await openTab('Preview a route')
    const activity = activePanel().querySelector('.preview-form-panel label select') as HTMLSelectElement
    await select(activity, 'planning')
    const effort = () => activePanel().querySelector('.session-fieldset label:last-of-type select') as HTMLSelectElement
    expect(values(effort())).toContain('high'); expect(values(effort())).not.toContain('xhigh')
    await select(activePanel().querySelectorAll('.preview-form-panel label select')[1] as HTMLSelectElement, 'clanker-architect')
    expect(values(effort())).toEqual(['', 'medium'])
    await select(activity, 'implementation')
    expect(values(effort())).toContain('xhigh')
    await select(activity, 'planning')
    await openTab('Activity defaults')
    await select(modelSelect(), 'unknown-efforts')
    await openTab('Preview a route')
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

  it('shows unknown CLI profile effort metadata beside every editable profile value', async () => {
    const configured = structuredClone(fixture)
    configured.scopes.global.document = { schema_version: 1, adaptive_profiles: { 'codex:unknown-efforts': {
      tiers: { straightforward: 'high', involved: 'high', demanding: 'xhigh' }, default_ceiling: 'high',
    } } }
    await render({ config: configured })
    await openTab('Adaptive profiles')
    const row = [...activePanel().querySelectorAll<HTMLElement>('.profile-row')].find((item) => item.textContent?.includes('codex:unknown-efforts'))!
    const fields = [...row.querySelectorAll<HTMLSelectElement>('select')]
    expect(fields).toHaveLength(4)
    for (const field of fields) {
      expect(field.getAttribute('aria-describedby')).toContain('-help')
      const helpId = field.getAttribute('aria-describedby')!.split(' ').find((id) => id.endsWith('-help'))!
      expect(document.getElementById(helpId)?.textContent).toContain('Effort metadata is unverified')
      expect(values(field)).toEqual(expect.arrayContaining(['low', 'medium', 'high', 'xhigh']))
    }
  })

  it('compares customized profile values with inherited values and restores them on reset', async () => {
    const configured = structuredClone(fixture)
    const inherited = { tiers: { straightforward: 'medium', involved: 'medium', demanding: 'xhigh' }, default_ceiling: 'high' }
    configured.bundle.defaults.adaptive_profiles = { 'codex:cli-model': inherited }
    configured.effective!.profiles = { 'codex:cli-model': inherited }
    await render({ config: configured })
    await openTab('Adaptive profiles')
    await act(async () => { profileFamilyButton('Codex · Other').click() })
    const profileRow = () => [...activePanel().querySelectorAll<HTMLElement>('.profile-row')].find((item) => item.textContent?.includes('codex:cli-model'))!
    expect(profileRow().classList.contains('is-customized')).toBe(false)
    await act(async () => { actionButton('Customize', profileRow()).click() })
    expect(profileRow().classList.contains('is-customized')).toBe(true)
    const involved = profileRow().querySelectorAll<HTMLSelectElement>('select')[1]
    await select(involved, 'high')
    expect(profileRow().textContent).toContain('Different from inherited medium')
    await act(async () => { actionButton('Reset profile', profileRow()).click() })
    expect(profileRow().classList.contains('is-customized')).toBe(false)
    expect(profileRow().textContent).toContain('medium')
    expect(profileRow().querySelector('select')).toBeNull()
  })

  it('disables profile creation for an already owned model while keeping its row editable', async () => {
    const configured = structuredClone(fixture)
    configured.scopes.global.document = { schema_version: 1, adaptive_profiles: { 'codex:cli-model': {
      tiers: { straightforward: 'medium', involved: 'high', demanding: 'high' }, default_ceiling: 'high',
    } } }
    await render({ config: configured })
    await openTab('Adaptive profiles')
    const addModel = profileSelect()
    expect(values(addModel)).toContain('cli-model')
    await select(addModel, 'cli-model')
    expect(actionButton('Customize profile', activePanel()).disabled).toBe(true)
    const row = [...activePanel().querySelectorAll<HTMLElement>('.profile-row')].find((item) => item.textContent?.includes('codex:cli-model'))!
    const involved = row.querySelectorAll<HTMLSelectElement>('select')[1]
    await select(involved, 'high')
    expect(row.classList.contains('is-customized')).toBe(true)
    expect(involved.value).toBe('high')
  })

  it('keeps a saved profile visible and resettable when its model is no longer reported', async () => {
    const configured = structuredClone(fixture)
    configured.scopes.global.document = { schema_version: 1, adaptive_profiles: { 'codex:retired-model': {
      tiers: { straightforward: 'medium', involved: 'high', demanding: 'xhigh' }, default_ceiling: 'high',
    } } }
    await render({ config: configured })
    await openTab('Adaptive profiles')
    const row = [...activePanel().querySelectorAll<HTMLElement>('.profile-row')].find((item) => item.textContent?.includes('codex:retired-model'))!
    expect(row).toBeTruthy()
    expect(row.querySelector('.state-tag')?.textContent).toBe('Customized here')
    expect(row.textContent).toContain('Effort metadata is unverified')
    await act(async () => { actionButton('Reset profile', row).click() })
    expect([...activePanel().querySelectorAll('.profile-row')].some((item) => item.textContent?.includes('codex:retired-model'))).toBe(false)
  })

})
