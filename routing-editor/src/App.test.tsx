import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'
import { specialistChoices } from './specialists'
import type { ConfigResponse } from './types'

const config: ConfigResponse = {
  schema_version: 1, policy_version: '1',
  scopes: { global: { path: '/home/test/.clanker/orchestration-routing.json', revision: 'abc', document: { schema_version: 1 } }, project: { path: '/project/.clanker/orchestration-routing.json', revision: 'project', document: { schema_version: 1 } } },
  bundle: {
    schema_version: 1, policy_version: '1',
    interactions: [
      { id: 'planning', label: 'Planning and design', provider: 'codex', default_model: 'gpt-5.6-sol' },
      { id: 'implementation', label: 'Implementation and testing', provider: 'codex', default_model: 'gpt-5.6-terra' },
      { id: 'native-review', label: 'Native review', provider: 'codex', default_model: 'gpt-5.6-sol' },
      { id: 'visual-review', label: 'Visual review', provider: 'codex', default_model: 'gpt-5.6-sol' },
      { id: 'claude-review', label: 'Claude review', provider: 'claude', default_model: 'claude-opus-5' },
    ],
    roles: [],
    models: [{ id: 'gpt-5.6-terra', label: 'Terra', provider: 'codex', efforts: ['low', 'medium', 'high', 'xhigh', 'max'] }, { id: 'gpt-5.6-luna', label: 'Luna', provider: 'codex', efforts: ['medium', 'high', 'xhigh', 'max'] }, { id: 'claude-opus-5', label: 'Opus', provider: 'claude', efforts: ['low', 'medium', 'high'] }],
    effort_orders: { codex: ['low', 'medium', 'high', 'xhigh', 'max'], claude: ['low', 'medium', 'high'] }, defaults: { schema_version: 1 },
  },
  effective: { interactions: {
    planning: { route: { model: 'gpt-5.6-terra', reasoning: { mode: 'adaptive' } }, provenance: { model: 'bundle.defaults', reasoning: 'bundle.defaults' }, ceiling: 'xhigh', ceiling_source: 'bundle.defaults.adaptive_profiles.codex:gpt-5.6-terra.default_ceiling', specialists: {} },
    implementation: { route: { model: 'gpt-5.6-terra', reasoning: { mode: 'adaptive' } }, provenance: { model: 'bundle.defaults', reasoning: 'bundle.defaults' }, ceiling: 'xhigh', ceiling_source: 'bundle.defaults.adaptive_profiles.codex:gpt-5.6-terra.default_ceiling', specialists: { 'clanker-ui-developer': { route: { model: 'gpt-5.6-terra', reasoning: { mode: 'adaptive' } }, provenance: { model: 'bundle.defaults', reasoning: 'bundle.defaults' }, ceiling: 'xhigh', ceiling_source: 'bundle.defaults.adaptive_profiles.codex:gpt-5.6-terra.default_ceiling' } } },
    'native-review': { ceiling: 'xhigh', ceiling_source: 'bundle.defaults.adaptive_profiles.codex:gpt-5.6-terra.default_ceiling', route: { model: 'gpt-5.6-terra', reasoning: { mode: 'adaptive' } }, provenance: { model: 'bundle.defaults', reasoning: 'bundle.defaults' }, specialists: {} },
    'visual-review': { ceiling: 'xhigh', ceiling_source: 'bundle.defaults.adaptive_profiles.codex:gpt-5.6-terra.default_ceiling', route: { model: 'gpt-5.6-terra', reasoning: { mode: 'adaptive' } }, provenance: { model: 'bundle.defaults', reasoning: 'bundle.defaults' }, specialists: {} },
    'claude-review': { ceiling: 'high', ceiling_source: 'bundle.defaults.adaptive_profiles.claude:claude-opus-5.default_ceiling', route: { model: 'claude-opus-5', reasoning: { mode: 'adaptive' } }, provenance: { model: 'bundle.defaults', reasoning: 'bundle.defaults' }, specialists: {} },
  }, profiles: {} },
}

const catalog = {
  providers: {
    codex: { status: 'live' as const, source: 'codex-cli' as const, cli_version: '0.1', updated_at: '2026-09-21T00:00:00Z', error: null, models: [
      { id: 'gpt-5.6-terra', label: 'Terra local', provider: 'codex' as const, efforts: ['low', 'high', 'unsupported'], default_effort: 'high' },
      { id: 'gpt-5.6-luna', label: 'Luna local', provider: 'codex' as const, efforts: ['medium', 'high'], default_effort: 'high' },
      { id: 'gpt-5.6-sol', label: 'Sol local', provider: 'codex' as const, efforts: ['low', 'high'], default_effort: 'high' },
      { id: 'custom-model-v9', label: 'Profile candidate', provider: 'codex' as const, efforts: ['low', 'high'], default_effort: 'high' },
    ] },
    claude: { status: 'live' as const, source: 'claude-cli' as const, cli_version: '0.1', updated_at: '2026-09-21T00:00:00Z', error: null, models: [{ id: 'claude-opus-5', label: 'Opus local', provider: 'claude' as const, efforts: ['low', 'medium', 'high'], default_effort: 'high' }] },
  },
}

const response = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } })
function deferred<T>() {
  let resolve!: (value: T) => void
  return { promise: new Promise<T>((resolvePromise) => { resolve = resolvePromise }), resolve }
}

async function setInput(input: HTMLInputElement | HTMLSelectElement, value: string) {
  await act(async () => {
    const prototype = input instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype
    Object.getOwnPropertyDescriptor(prototype, 'value')!.set!.call(input, value)
    input.dispatchEvent(new Event(input instanceof HTMLSelectElement ? 'change' : 'input', { bubbles: true }))
  })
}

let root: Root | undefined

function tabButton(name: string) {
  return [...document.querySelectorAll<HTMLButtonElement>('[role="tab"]')].find((button) => button.textContent?.trim().startsWith(name))!
}

async function openTab(name: string) {
  const tab = tabButton(name)
  if (tab.getAttribute('aria-selected') !== 'true') await act(async () => { tab.click() })
}

function activePanel() {
  const tab = document.querySelector<HTMLButtonElement>('[role="tab"][aria-selected="true"]')!
  return document.getElementById(tab.getAttribute('aria-controls')!)!
}

function activityCard(name: string) {
  return [...activePanel().querySelectorAll<HTMLElement>('.activity-default-card')].find((card) => card.querySelector('h2')?.textContent === name)!
}

function activityModel(name: string) {
  return activityCard(name).querySelector<HTMLSelectElement>('.model-picker select')!
}

function actionButton(name: string, container: ParentNode = document) {
  return [...container.querySelectorAll<HTMLButtonElement>('button')].find((button) => button.textContent?.trim() === name)!
}

function profileModelSelect(modelId: string) {
  return [...activePanel().querySelectorAll<HTMLSelectElement>('.profile-addbar select')].find((select) =>
    [...select.options].some((option) => option.value === modelId),
  )!
}

function previewForm() {
  return document.querySelector<HTMLElement>('#panel-preview .preview-form-panel')!
}

function inspector() {
  return activePanel().querySelector<HTMLElement>('.inspector')!
}

async function inspectWorker(label: string) {
  await openTab('Worker routes')
  const button = [...activePanel().querySelectorAll<HTMLButtonElement>('.specialist-select')].find((item) => item.getAttribute('aria-label') === `Inspect ${label}`)!
  await act(async () => { button.click() })
}

async function render(fetchMock: ReturnType<typeof vi.fn>, initialTab = 'Activity defaults') {
  const mock = fetchMock as unknown as (path: string, init?: RequestInit) => Promise<Response>
  vi.stubGlobal('fetch', (path: string, init?: RequestInit) => path === '/api/models' ? Promise.resolve(response(catalog)) : mock(path, init))
  const element = document.createElement('div'); document.body.append(element)
  root = createRoot(element)
  await act(async () => { root!.render(<App />) })
  await act(async () => { await Promise.resolve() })
  if (document.querySelector('[role="tab"]')) await openTab(initialTab)
}

afterEach(async () => { await act(async () => root?.unmount()); root = undefined; vi.unstubAllGlobals(); vi.useRealTimers() })

describe('routing editor', () => {
  it('filters activity chips and preview choices by scenario', async () => {
    const loaded = structuredClone(config)
    loaded.bundle.roles = [
      { id: 'clanker-architect', label: 'Architect' },
      { id: 'clanker-backend-developer', label: 'Backend developer' },
      { id: 'clanker-code-review', label: 'Code reviewer' },
      { id: 'clanker-test-engineer', label: 'Test engineer' },
      { id: 'clanker-ui-ux-reviewer', label: 'Visual reviewer' },
    ]
    await render(vi.fn().mockResolvedValue(response(loaded)))
    const expected = [['Architect', 'Backend developer'], ['Backend developer', 'Test engineer'], ['Architect', 'Backend developer', 'Code reviewer', 'Test engineer'], ['Visual reviewer']]
    const activities = loaded.bundle.interactions.filter((item) => item.provider === 'codex')
    for (let index = 0; index < expected.length; index++) {
      const card = activityCard(activities[index].label)
      expect([...card.querySelectorAll('.user-chip')].map((chip) => chip.textContent)).toEqual(expected[index])
    }
    await openTab('Preview a route')
    const interaction = previewForm().querySelector('label select') as HTMLSelectElement
    for (let index = 0; index < expected.length; index++) {
      await setInput(interaction, activities[index].id)
      const roles = previewForm().querySelectorAll('label select')[1] as HTMLSelectElement
      expect([...roles.options].slice(1).map((option) => option.textContent)).toEqual(expected[index])
    }
    await openTab('Worker routes')
    expect(activePanel().textContent).toContain('Claude cross-review')
    expect(activePanel().textContent).not.toContain('Claude review</h2>')
  })

  it('keeps existing off-scenario overrides editable and removes them from choices after reset', async () => {
    const loaded = structuredClone(config)
    loaded.bundle.roles.push({ id: 'clanker-backend-developer', label: 'Backend developer' })
    loaded.scopes.global.document = { schema_version: 1, interactions: { 'visual-review': { specialists: { 'clanker-backend-developer': { model: 'gpt-5.6-terra' } } } } }
    await render(vi.fn().mockResolvedValue(response(loaded)))
    await inspectWorker('Backend developer')
    expect(inspector().textContent).toContain('Visual review')
    const section = [...inspector().querySelectorAll<HTMLElement>('.activity-route')].find((item) => item.textContent?.includes('Visual review'))!
    await act(async () => { section.querySelector<HTMLButtonElement>('.activity-route-toggle')!.click() })
    await act(async () => { actionButton('Reset activity exception', section).click() })
    expect(inspector().textContent).not.toContain('Visual review')
  })

  it('preserves inherited off-scenario overrides only in the applicable editing scope', () => {
    const loaded = structuredClone(config)
    loaded.bundle.roles.push({ id: 'clanker-backend-developer', label: 'Backend developer' })
    loaded.scopes.global.document = { schema_version: 1, interactions: { 'visual-review': { specialists: { 'clanker-backend-developer': { model: 'gpt-5.6-terra' } } } } }
    const empty = { schema_version: 1 as const }
    expect(specialistChoices(loaded, empty, 'project', 'visual-review').map((role) => role.label)).toContain('Backend developer (existing override)')
    expect(specialistChoices(loaded, empty, 'global', 'visual-review').map((role) => role.id)).not.toContain('clanker-backend-developer')
    expect(specialistChoices(loaded, empty, 'project', 'claude-review')).toEqual([])
  })

  it('shows inherited values and resets a specialist route without flattening it', async () => {
    vi.useFakeTimers()
    const loaded = structuredClone(config)
    loaded.bundle.roles = [{ id: 'clanker-ui-developer', label: 'UI developer' }]
    await render(vi.fn().mockResolvedValue(response(loaded)), 'Worker routes')
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    expect(document.body.textContent).toContain('Inherited from bundled defaults')
    const section = [...inspector().querySelectorAll<HTMLElement>('.activity-route')].find((item) => item.textContent?.includes('Implementation and testing'))!
    await act(async () => { section.querySelector<HTMLButtonElement>('.activity-route-toggle')!.click() })
    expect(section.textContent).toContain('Implementation and testing')
    expect([...section.querySelectorAll('button')].some((button) => button.textContent === 'Reset activity exception')).toBe(true)
  })

  it('refreshes the global inherited route from the resolver instead of showing project-effective data', async () => {
    vi.useFakeTimers()
    const loaded = structuredClone(config)
    loaded.effective!.interactions.implementation.route!.model = 'gpt-5.6-luna'
    const globalEffective = structuredClone(config.effective)
    const fetchMock = vi.fn().mockResolvedValueOnce(response(loaded)).mockResolvedValueOnce(response({ effective: globalEffective, decision: null }))
    await render(fetchMock)
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    const implementation = activityCard('Implementation and testing')
    expect((implementation.querySelector('.model-picker select') as HTMLInputElement).value).toBe('gpt-5.6-terra')
  })

  it('renders an API-returned Luna ceiling preview as unverified', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(config))
      .mockResolvedValueOnce(response({ effective: config.effective, decision: { model: 'gpt-5.6-luna', reasoning: { mode: 'adaptive' }, effort: 'xhigh', proposed_effort: 'max', ceiling: 'xhigh', ceiling_source: 'global', interaction: 'implementation', tier: 'exceptional', reason: 'Hard integration', limitations: ['Adaptive exceptional effort max is capped at xhigh'], provenance: { model: 'global', reasoning: 'global', profile: 'global' }, capability_status: 'unverified', dispatch_allowed: false } }))
    await render(fetchMock)
    await openTab('Preview a route')
    const form = previewForm()
    const interaction = form.querySelector('label select') as HTMLSelectElement
    await setInput(interaction, 'implementation')
    const tier = form.querySelector('[aria-label="Task tier"]')!
    await act(async () => { actionButton('Exceptional', tier).click() })
    const previewButton = actionButton('Preview route', form)
    await act(async () => { previewButton.click(); await Promise.resolve() })
    expect(document.body.textContent).toContain('gpt-5.6-luna')
    expect(document.body.textContent).toContain('unverified')
    expect(document.body.textContent).toContain('max is capped at xhigh')
    expect(JSON.parse(fetchMock.mock.calls[1][1].body).document).toEqual({ schema_version: 1 })
  })

  it('keeps a draft and explains a save conflict', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config)).mockResolvedValueOnce(response({ error: 'Preferences changed since loading.' }, 409))
    await render(fetchMock)
    const model = activityModel('Planning and design')
    await setInput(model, 'gpt-5.6-luna')
    const save = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Save global preferences')!
    await act(async () => { save.click(); await Promise.resolve() })
    expect(document.body.textContent).toContain('Save conflict: your draft is still available.')
    expect(model.value).toBe('gpt-5.6-luna')
  })

  it('shows resolver-provided Adaptive ceilings and lets users select the first fixed effort', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config)).mockResolvedValueOnce(response({ effective: config.effective, decision: null })).mockResolvedValueOnce(response(config))
    await render(fetchMock)
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    expect(document.body.textContent).toContain('Adaptive ceiling: xhigh')
    expect(document.body.textContent).toContain('Adaptive routes inherit a ceiling of xhigh')
    const planning = activityCard('Planning and design')
    const adaptiveMaximum = planning.querySelector<HTMLSelectElement>('.effort-field select')!
    await setInput(adaptiveMaximum, 'high')
    expect(adaptiveMaximum.options[0].textContent).toBe('Model profile default')
    const mode = planning.querySelector('[role="group"][aria-label="planning reasoning mode"]')!
    await act(async () => { actionButton('Fixed', mode).click() })
    const effort = planning.querySelector<HTMLSelectElement>('.effort-field select')!
    expect(effort.value).toBe('')
    expect(effort.options[0].disabled).toBe(true)
    await setInput(effort, 'low')
    const save = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Save global preferences')!
    await act(async () => { save.click(); await Promise.resolve() })
    expect(JSON.parse(fetchMock.mock.calls[2][1].body).document.interactions.planning.reasoning).toEqual({ mode: 'fixed', effort: 'low' })
  })

  it('associates an effective route-root error with its controls and clears it after correction', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config)).mockResolvedValueOnce(response({ error: 'effective.interactions.implementation: Adaptive routing for codex:custom-model-v9 requires a complete profile' }, 400))
    await render(fetchMock)
    const implementation = activityCard('Implementation and testing')
    const model = implementation.querySelector('.model-picker select') as HTMLInputElement
    await setInput(model, 'custom-model-v9')
    const save = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Save global preferences')!
    await act(async () => { save.click(); await Promise.resolve() })
    expect(document.body.textContent).toContain('requires a complete profile')
    expect(model.getAttribute('aria-describedby')).toContain('interactions.implementation-route-error')
    await setInput(model, 'gpt-5.6-terra')
    expect(document.body.textContent).not.toContain('requires a complete profile')
  })

  it('clears a route validation error after adding its missing Adaptive profile', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config))
      .mockResolvedValueOnce(response({ error: 'effective.interactions.planning: Adaptive routing for codex:custom-model-v9 requires a complete profile' }, 400))
      .mockResolvedValueOnce(response({ effective: config.effective, decision: null }))
    await render(fetchMock)
    const model = activityModel('Planning and design')
    await setInput(model, 'custom-model-v9')
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    expect(document.getElementById('interactions.planning-route-error')).toBeTruthy()
    expect(model.getAttribute('aria-describedby')).toContain('interactions.planning-route-error')
    await openTab('Adaptive profiles')
    await setInput(profileModelSelect('custom-model-v9'), 'custom-model-v9')
    await act(async () => { actionButton('Customize profile', activePanel()).click() })
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    expect(JSON.parse(fetchMock.mock.calls[2][1].body).document.adaptive_profiles['codex:custom-model-v9']).toBeTruthy()
    expect(document.getElementById('interactions.planning-route-error')).toBeNull()
    expect(model.getAttribute('aria-describedby')).not.toContain('interactions.planning-route-error')
    expect(document.body.textContent).not.toContain('requires a complete profile')
    await openTab('Activity defaults')
    expect(activityModel('Planning and design').value).toBe('custom-model-v9')
  })

  it('invalidates an explicit route error when its missing profile is added', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config))
      .mockResolvedValueOnce(response({ error: 'effective.interactions.planning: requires a complete profile' }, 400))
    await render(fetchMock)
    await setInput(activityModel('Planning and design'), 'custom-model-v9')
    await openTab('Preview a route')
    const preview = actionButton('Preview route', previewForm())
    await act(async () => { preview.click(); await Promise.resolve() })
    expect(document.getElementById('interactions.planning-route-error')).toBeTruthy()
    await openTab('Adaptive profiles')
    await setInput(profileModelSelect('custom-model-v9'), 'custom-model-v9')
    await act(async () => { actionButton('Customize profile', activePanel()).click() })
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(document.getElementById('interactions.planning-route-error')).toBeNull()
  })

  it('does not clear a save failure when automatic draft validation succeeds', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config))
      .mockResolvedValueOnce(response({ error: 'global.interactions.planning.model: save rejected' }, 400))
      .mockResolvedValueOnce(response({ effective: config.effective, decision: null }))
    await render(fetchMock)
    await setInput(activityModel('Planning and design'), 'gpt-5.6-luna')
    const save = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Save global preferences')!
    await act(async () => { save.click(); await Promise.resolve() })
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    expect(document.getElementById('interactions.planning-model-error')?.textContent).toContain('save rejected')
    expect(document.querySelector('.alert-stack')?.textContent).toContain('save rejected')
  })

  it('associates nested reasoning errors with the specialist control and clears them when corrected', async () => {
    const loaded = structuredClone(config)
    loaded.bundle.roles = [{ id: 'clanker-ui-developer', label: 'UI developer' }]
    const fetchMock = vi.fn().mockResolvedValueOnce(response(loaded)).mockResolvedValueOnce(response({ error: 'global.interactions.planning.specialists.clanker-ui-developer.reasoning.max_effort: is not supported by codex' }, 400))
    await render(fetchMock)
    await inspectWorker('UI developer')
    const worker = inspector()
    await act(async () => { actionButton('+ Add activity exception', worker).click() })
    await act(async () => { actionButton('Planning and design', worker).click() })
    const planning = [...worker.querySelectorAll<HTMLElement>('.activity-route')].find((item) => item.textContent?.includes('Planning and design'))!
    const specialistMaximum = planning.querySelector<HTMLSelectElement>('.effort-field select')!
    await setInput(specialistMaximum, 'high')
    const save = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Save global preferences')!
    await act(async () => { save.click(); await Promise.resolve() })
    expect(document.body.textContent).toContain('is not supported by codex')
    const reopenedMaximum = planning.querySelector<HTMLSelectElement>('.effort-field select')!
    expect(reopenedMaximum.getAttribute('aria-describedby')).toContain('interactions.planning.specialists.clanker-ui-developer-reasoning-error')
    await act(async () => { actionButton('Reset activity exception', planning).click() })
    expect(document.body.textContent).not.toContain('is not supported by codex')
  })

  it('associates advanced profile errors with the invalid input and clears them when corrected', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config)).mockResolvedValueOnce(response({ error: 'global.adaptive_profiles.codex:custom-model-v9.tiers.routine: is not supported by codex' }, 400))
    await render(fetchMock)
    await openTab('Adaptive profiles')
    await setInput(profileModelSelect('custom-model-v9'), 'custom-model-v9')
    await act(async () => { actionButton('Customize profile', activePanel()).click() })
    const otherFamily = [...activePanel().querySelectorAll<HTMLButtonElement>('[aria-expanded]')].find((button) => button.textContent?.includes('Codex · Other'))!
    expect(otherFamily.getAttribute('aria-expanded')).toBe('true')
    await act(async () => { otherFamily.click() })
    expect(otherFamily.getAttribute('aria-expanded')).toBe('false')
    const save = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Save global preferences')!
    await act(async () => { save.click(); await Promise.resolve() })
    const row = [...activePanel().querySelectorAll<HTMLElement>('.profile-row')].find((item) => item.textContent?.includes('codex:custom-model-v9'))!
    expect(otherFamily.getAttribute('aria-expanded')).toBe('true')
    const routine = row.querySelectorAll<HTMLSelectElement>('select')[1]
    expect(document.body.textContent).toContain('is not supported by codex')
    expect(routine.getAttribute('aria-describedby')).toContain('adaptive_profiles.codex:custom-model-v9.tiers.routine-error')
    await setInput(routine, 'high')
    expect(document.body.textContent).not.toContain('is not supported by codex')
  })

  it('keeps a late save failure global without attaching it to a newer draft', async () => {
    const pending = deferred<Response>()
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config)).mockReturnValueOnce(pending.promise)
    await render(fetchMock)
    const model = activityModel('Planning and design')
    await setInput(model, 'gpt-5.6-luna')
    const save = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Save global preferences')!
    await act(async () => { save.click() })
    await setInput(model, 'gpt-5.6-sol')
    pending.resolve(response({ error: 'global.interactions.planning.model: rejected by the server' }, 400))
    await act(async () => { await Promise.resolve() })
    expect(document.body.textContent).toContain('rejected by the server')
    expect(document.getElementById('interactions.planning-model-error')).toBeNull()
    expect(activityModel('Planning and design').value).toBe('gpt-5.6-sol')
  })

  it('clears a field error when resetting the affected route', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config)).mockResolvedValueOnce(response({ error: 'global.interactions.planning.model: rejected by the server' }, 400))
    await render(fetchMock)
    await setInput(activityModel('Planning and design'), 'gpt-5.6-luna')
    const save = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Save global preferences')!
    await act(async () => { save.click(); await Promise.resolve() })
    expect(document.getElementById('interactions.planning-model-error')).toBeTruthy()
    await act(async () => { actionButton('Reset route to inherited', activityCard('Planning and design')).click() })
    expect(document.getElementById('interactions.planning-model-error')).toBeNull()
    expect(document.body.textContent).not.toContain('rejected by the server')
  })

  it('clears only the generic preview error after a successful explicit preview', async () => {
    const decision = { model: 'gpt-5.6-terra', reasoning: { mode: 'adaptive' }, effort: 'high', proposed_effort: 'high', ceiling: 'xhigh', ceiling_source: 'bundle.defaults', interaction: 'implementation', tier: 'routine', reason: 'Resolved', limitations: [], provenance: { model: 'bundle.defaults', reasoning: 'bundle.defaults', profile: 'bundle.defaults' }, capability_status: 'unverified', dispatch_allowed: false }
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config)).mockResolvedValueOnce(response({ error: 'Preview temporarily failed' }, 400)).mockResolvedValueOnce(response({ effective: config.effective, decision }))
    await render(fetchMock)
    await openTab('Preview a route')
    const preview = actionButton('Preview route', previewForm())
    await act(async () => { preview.click(); await Promise.resolve() })
    expect(document.body.textContent).toContain('Preview temporarily failed')
    await act(async () => { preview.click(); await Promise.resolve() })
    expect(document.body.textContent).not.toContain('Preview temporarily failed')
    expect(document.body.textContent).toContain('Predicted route')
  })

  it('preserves an explicit session-override error when pending automatic validation succeeds', async () => {
    vi.useFakeTimers()
    const pending = deferred<Response>()
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config)).mockReturnValueOnce(pending.promise)
      .mockResolvedValueOnce(response({ error: 'request.session_override.model: preview validation failed' }, 400))
    await render(fetchMock)
    await setInput(activityModel('Planning and design'), 'gpt-5.6-luna')
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    await openTab('Preview a route')
    const session = previewForm().querySelector('.session-fieldset')!
    await act(async () => { (session.querySelector('summary') as HTMLElement).click() })
    await setInput(session.querySelector('.model-picker select') as HTMLSelectElement, 'gpt-5.6-luna')
    const preview = actionButton('Preview route', previewForm())
    await act(async () => { preview.click(); await Promise.resolve() })
    expect(document.body.textContent).toContain('preview validation failed')
    pending.resolve(response({ effective: config.effective, decision: null }))
    await act(async () => { await Promise.resolve() })
    expect(document.body.textContent).toContain('preview validation failed')
    expect((session.querySelector('.model-picker select') as HTMLSelectElement).value).toBe('gpt-5.6-luna')
    await setInput(session.querySelector('.model-picker select') as HTMLSelectElement, 'gpt-5.6-sol')
    expect(document.body.textContent).not.toContain('preview validation failed')
  })

  it('ignores an explicit preview response that becomes stale after inputs change', async () => {
    const pending = deferred<Response>()
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config)).mockReturnValueOnce(pending.promise)
    await render(fetchMock)
    await openTab('Preview a route')
    const preview = actionButton('Preview route', previewForm())
    await act(async () => { preview.click() })
    await setInput(previewForm().querySelector('input[required]') as HTMLInputElement, 'Changed after preview started')
    pending.resolve(response({ effective: config.effective, decision: { model: 'gpt-5.6-terra', reasoning: { mode: 'adaptive' }, effort: 'high', proposed_effort: 'high', ceiling: 'xhigh', ceiling_source: 'bundle.defaults', interaction: 'implementation', tier: 'routine', reason: 'Stale result', limitations: [], provenance: { model: 'bundle.defaults', reasoning: 'bundle.defaults', profile: 'bundle.defaults' }, capability_status: 'unverified', dispatch_allowed: false } }))
    await act(async () => { await Promise.resolve() })
    expect(document.body.textContent).not.toContain('Predicted route')
  })

  it('preserves edits made while a save is pending', async () => {
    const pending = deferred<Response>()
    const saved = structuredClone(config)
    saved.scopes.global.document = { schema_version: 1, interactions: { implementation: { model: 'gpt-5.6-luna' } } }
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config)).mockReturnValueOnce(pending.promise)
    await render(fetchMock)
    const model = activityModel('Planning and design')
    await setInput(model, 'gpt-5.6-luna')
    const save = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Save global preferences')!
    await act(async () => { save.click() })
    expect([...document.querySelector('[aria-label="Scope"]')!.querySelectorAll('button')].every((button) => (button as HTMLButtonElement).disabled)).toBe(true)
    await setInput(model, 'gpt-5.6-sol')
    pending.resolve(response(saved))
    await act(async () => { await Promise.resolve() })
    expect(activityModel('Planning and design').value).toBe('gpt-5.6-sol')
    expect(document.querySelector('[role="status"]')?.textContent).toContain('unsaved change')
  })

  it('does not let a late reload response replace edits made after reload started', async () => {
    const pending = deferred<Response>()
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config)).mockReturnValueOnce(pending.promise)
    await render(fetchMock)
    const reload = actionButton('Export draft & reload')
    await act(async () => { reload.click() })
    const model = activityModel('Planning and design')
    await setInput(model, 'gpt-5.6-luna')
    const save = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Save global preferences')!
    expect(save.disabled).toBe(true)
    pending.resolve(response(config))
    await act(async () => { await Promise.resolve() })
    expect(model.value).toBe('gpt-5.6-luna')
    expect(document.querySelector('[role="status"]')?.textContent).toContain('unsaved change')
  })

  it('keeps the original revision when a reload response is discarded after an edit', async () => {
    const pending = deferred<Response>()
    const reloaded = structuredClone(config)
    reloaded.scopes.global.revision = 'revision-b'
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config)).mockReturnValueOnce(pending.promise).mockResolvedValueOnce(response({ error: 'Preferences changed since loading.' }, 409))
    await render(fetchMock)
    const reload = actionButton('Export draft & reload')
    await act(async () => { reload.click() })
    const model = activityModel('Planning and design')
    await setInput(model, 'gpt-5.6-luna')
    pending.resolve(response(reloaded))
    await act(async () => { await Promise.resolve() })
    const save = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Save global preferences')!
    await act(async () => { save.click(); await Promise.resolve() })
    expect(JSON.parse(fetchMock.mock.calls[2][1].body).revision).toBe('abc')
    expect(document.body.textContent).toContain('Save conflict: your draft is still available.')
  })
  it('reveals an adaptive control when an agent reasoning error is returned', async () => {
    vi.useFakeTimers()
    const loaded = structuredClone(config)
    loaded.bundle.roles = [{ id: 'clanker-ui-developer', label: 'UI developer' }]
    loaded.effective!.agents = { 'clanker-ui-developer': { route: { model: 'gpt-5.6-terra', reasoning: { mode: 'adaptive' } }, provenance: { model: 'global.agents.clanker-ui-developer.model', reasoning: 'global.agents.clanker-ui-developer.reasoning' } } }
    const fetchMock = vi.fn().mockResolvedValueOnce(response(loaded))
      .mockResolvedValueOnce(response({ effective: loaded.effective, decision: null }))
      .mockResolvedValueOnce(response({ error: 'agents.clanker-ui-developer.reasoning.max_effort: not supported' }, 400))
    await render(fetchMock)
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    await inspectWorker('UI developer')
    const card = inspector()
    await setInput(card.querySelector('.model-picker select') as HTMLSelectElement, 'gpt-5.6-luna')
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    expect(document.getElementById('agents.clanker-ui-developer-reasoning-error')?.textContent).toContain('not supported')
    expect([...card.querySelectorAll('label')].some((label) => label.textContent?.includes('Adaptive maximum'))).toBe(true)
    const adaptiveMaximum = [...card.querySelectorAll('label')].find((label) => label.textContent?.startsWith('Adaptive maximum'))?.querySelector('select')
    expect(adaptiveMaximum?.getAttribute('aria-describedby')).toContain('agents.clanker-ui-developer-reasoning-error')
  })

  it('clears project effective agents before a deferred global preview resolves', async () => {
    vi.useFakeTimers()
    const loaded = structuredClone(config)
    loaded.bundle.roles = [{ id: 'clanker-ui-developer', label: 'UI developer' }]
    loaded.scopes.project!.document = { schema_version: 1, agents: { 'clanker-ui-developer': { model: 'gpt-5.6-luna' } } }
    loaded.effective!.agents = { 'clanker-ui-developer': { route: {}, provenance: {} } }
    const projectEffective = structuredClone(loaded.effective)
    projectEffective!.agents!['clanker-ui-developer'] = { route: { model: 'gpt-5.6-luna' }, provenance: { model: 'project.agents.clanker-ui-developer.model' } }
    const pending = deferred<Response>()
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(loaded))
      .mockResolvedValueOnce(response({ effective: loaded.effective, decision: null }))
      .mockResolvedValueOnce(response({ effective: projectEffective, decision: null }))
      .mockReturnValueOnce(pending.promise)
    await render(fetchMock)
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    await openTab('Worker routes')
    const scope = document.querySelector('[aria-label="Scope"]')!
    const projectScope = [...scope.querySelectorAll<HTMLButtonElement>('button')].find((button) => button.textContent?.startsWith('Project ·'))!
    await act(async () => { projectScope.click() })
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    const model = inspector().querySelector('.model-picker select') as HTMLSelectElement
    expect(model.value).toBe('gpt-5.6-luna')
    await act(async () => { actionButton('Global', scope).click() })
    expect(model.value).toBe('')
    expect(model.selectedOptions[0].textContent).toContain('Inherited model unresolved')
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    expect(model.value).toBe('')
    pending.resolve(response({ effective: loaded.effective, decision: null }))
    await act(async () => { await Promise.resolve() })
    expect(model.value).toBe('gpt-5.6-terra')
  })

  it('keeps Claude cross-review in Worker routes and activity defaults limited to Codex', async () => {
    const loaded = structuredClone(config)
    loaded.bundle.roles = [{ id: 'clanker-ui-developer', label: 'UI developer' }]
    await render(vi.fn().mockResolvedValue(response(loaded)))
    expect(activePanel().querySelectorAll('.activity-default-card')).toHaveLength(4)
    expect(activePanel().textContent).not.toContain('Claude review')
    await openTab('Worker routes')
    expect(activePanel().querySelectorAll('.claude-row')).toHaveLength(1)
    await act(async () => { activePanel().querySelector<HTMLButtonElement>('.claude-row .route-cell')!.click() })
    expect(inspector().querySelector('h2')?.textContent).toBe('Claude cross-review')
    const ids = [...document.querySelectorAll('[id]')].map((element) => element.id)
    expect(new Set(ids).size).toBe(ids.length)
  })

})

describe('agent-first cards', () => {
  it('saves a sparse agent model without flattening an activity exception', async () => {
    const loaded = structuredClone(config)
    loaded.bundle.roles = [{ id: 'clanker-ui-developer', label: 'UI developer' }]
    loaded.scopes.global.document = { schema_version: 1, interactions: { implementation: { specialists: { 'clanker-ui-developer': { model: 'gpt-5.6-terra' } } } } }
    loaded.effective!.agents = { 'clanker-ui-developer': { route: {}, provenance: {} } }
    const saved = structuredClone(loaded)
    const fetchMock = vi.fn().mockResolvedValueOnce(response(loaded)).mockResolvedValueOnce(response(saved))
    await render(fetchMock)
    await inspectWorker('UI developer')
    const card = inspector()
    await setInput(card.querySelector('.model-picker select') as HTMLSelectElement, 'gpt-5.6-luna')
    await act(async () => [...document.querySelectorAll('button')].find((button) => button.textContent === 'Save global preferences')!.click())
    const documentBody = JSON.parse(String(fetchMock.mock.calls[1][1].body)).document
    expect(documentBody.agents).toEqual({ 'clanker-ui-developer': { model: 'gpt-5.6-luna' } })
    expect(documentBody.interactions.implementation.specialists['clanker-ui-developer']).toEqual({ model: 'gpt-5.6-terra' })
    expect(card.textContent).toContain('1 exception')
  })

  it('shows mixed applicable activity values and intersects fixed effort choices', async () => {
    vi.useFakeTimers()
    const loaded = structuredClone(config)
    loaded.bundle.roles = [{ id: 'clanker-ui-developer', label: 'UI developer' }]
    loaded.effective!.agents = { 'clanker-ui-developer': { route: {}, provenance: {} } }
    loaded.effective!.interactions.planning.specialists = { 'clanker-ui-developer': { route: { model: 'gpt-5.6-terra', reasoning: { mode: 'adaptive' } }, provenance: { model: 'bundle.defaults', reasoning: 'bundle.defaults' } } }
    loaded.effective!.interactions.implementation.specialists = { 'clanker-ui-developer': { route: { model: 'gpt-5.6-luna', reasoning: { mode: 'adaptive' } }, provenance: { model: 'bundle.defaults', reasoning: 'bundle.defaults' } } }
    const fetchMock = vi.fn().mockResolvedValueOnce(response(loaded)).mockResolvedValueOnce(response({ effective: loaded.effective, decision: null }))
    await render(fetchMock)
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    await inspectWorker('UI developer')
    const card = inspector()
    const defaultCell = activePanel().querySelector<HTMLButtonElement>('.route-cell[aria-label^="UI developer, agent default"]')!
    expect(defaultCell.getAttribute('aria-label')).toContain('Varies by activity')
    const mode = card.querySelector('[role="group"][aria-label="UI developer reasoning mode"]')!
    await act(async () => { actionButton('Fixed', mode).click() })
    const effort = [...card.querySelectorAll<HTMLSelectElement>('.agent-fields label select')].find((item) => item.parentElement?.textContent?.trim().startsWith('Effort'))!
    expect([...effort.options].filter((option) => !option.disabled && option.value).map((option) => option.value)).toEqual(['high'])
    expect(card.textContent).toContain('Varies by activity')
  })

  it('counts distinct changed leaves and returns to zero when a draft is reverted', async () => {
    const loaded = structuredClone(config)
    loaded.scopes.global.document = { schema_version: 1, interactions: { planning: { model: 'gpt-5.6-terra', reasoning: { mode: 'fixed', effort: 'low' } } } }
    await render(vi.fn().mockResolvedValue(response(loaded)))
    const card = activityCard('Planning and design')
    const model = () => card.querySelector<HTMLSelectElement>('.model-picker select')!
    const effort = () => card.querySelector<HTMLSelectElement>('.effort-field select')!
    const status = document.querySelector('[role="status"]')!

    await setInput(model(), 'gpt-5.6-sol')
    await setInput(effort(), 'high')
    expect(status.textContent).toContain('2 unsaved changes')

    await setInput(model(), 'gpt-5.6-terra')
    await setInput(effort(), 'low')
    expect(status.textContent).toContain('0 unsaved changes')
  })

  it('resets only activity defaults and preserves specialist exceptions', async () => {
    const loaded = structuredClone(config)
    loaded.bundle.roles = [{ id: 'clanker-ui-developer', label: 'UI developer' }]
    loaded.scopes.global.document = { schema_version: 1, interactions: { implementation: {
      model: 'gpt-5.6-luna', reasoning: { mode: 'fixed', effort: 'high' },
      specialists: { 'clanker-ui-developer': { model: 'gpt-5.6-sol' } },
    } } }
    const fetchMock = vi.fn().mockResolvedValueOnce(response(loaded)).mockResolvedValueOnce(response(loaded))
    await render(fetchMock)
    const card = activityCard('Implementation and testing')
    expect(card.textContent).toContain('Set here')
    await act(async () => { actionButton('Reset route to inherited', card).click() })
    expect(card.textContent).toContain('Inherited')
    expect(actionButton('Reset route to inherited', card).disabled).toBe(true)
    expect(document.querySelector('[role="status"]')?.textContent).toContain('3 unsaved changes')

    await act(async () => { actionButton('Save global preferences').click(); await Promise.resolve() })
    const savedDocument = JSON.parse(String(fetchMock.mock.calls[1][1].body)).document
    expect(savedDocument.interactions.implementation).toEqual({ specialists: { 'clanker-ui-developer': { model: 'gpt-5.6-sol' } } })
  })

  it('keeps scope confirmation and draft state when a scope switch is canceled', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValueOnce(true)
    try {
      await render(vi.fn().mockResolvedValue(response(config)))
      await setInput(activityModel('Planning and design'), 'gpt-5.6-luna')
      const scope = document.querySelector('[aria-label="Scope"]')!
      const project = [...scope.querySelectorAll<HTMLButtonElement>('button')].find((button) => button.textContent?.startsWith('Project ·'))!
      await act(async () => { project.click() })
      expect(project.getAttribute('aria-pressed')).toBe('false')
      expect(activityModel('Planning and design').value).toBe('gpt-5.6-luna')

      await act(async () => { project.click() })
      expect(project.getAttribute('aria-pressed')).toBe('true')
      expect(actionButton('Save project preferences').disabled).toBe(true)
      expect(document.querySelector('[role="status"]')?.textContent).toContain('All changes saved')
      expect(confirm).toHaveBeenCalledTimes(2)
    } finally {
      confirm.mockRestore()
    }
  })

  it('routes Claude save errors to Worker routes and keeps them discoverable across tabs', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(config))
      .mockResolvedValueOnce(response({ error: 'global.interactions.claude-review.model: unavailable route' }, 400))
    await render(fetchMock)
    await openTab('Worker routes')
    await act(async () => { activePanel().querySelector<HTMLButtonElement>('.claude-row .route-cell')!.click() })
    const mode = inspector().querySelector('[aria-label="claude-review reasoning mode"]')!
    await act(async () => { actionButton('Fixed', mode).click() })
    await act(async () => { actionButton('Save global preferences').click(); await Promise.resolve() })

    expect(tabButton('Worker routes').querySelector('.tab-error-dot')).toBeTruthy()
    await openTab('Activity defaults')
    expect(tabButton('Activity defaults').querySelector('.tab-error-dot')).toBeNull()
    await openTab('Worker routes')
    expect(document.getElementById('interactions.claude-review-model-error')?.textContent).toContain('unavailable route')
  })

  it('keeps hidden specialist errors marked in the worker matrix', async () => {
    vi.useFakeTimers()
    const loaded = structuredClone(config)
    loaded.bundle.roles = [
      { id: 'clanker-ui-developer', label: 'UI developer' },
      { id: 'clanker-backend-developer', label: 'Backend developer' },
    ]
    loaded.effective!.agents = { 'clanker-ui-developer': { route: { model: 'gpt-5.6-terra', reasoning: { mode: 'adaptive' } }, provenance: { model: 'bundle.defaults', reasoning: 'bundle.defaults' } } }
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(loaded))
      .mockResolvedValueOnce(response({ effective: loaded.effective, decision: null }))
      .mockResolvedValueOnce(response({ error: 'global.agents.clanker-ui-developer.reasoning.max_effort: unsupported' }, 400))
    await render(fetchMock)
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    await inspectWorker('UI developer')
    const maximum = [...inspector().querySelectorAll('label')].find((label) => label.textContent?.startsWith('Adaptive maximum'))!.querySelector('select')!
    await setInput(maximum, 'high')
    await act(async () => { actionButton('Save global preferences').click(); await Promise.resolve() })
    await inspectWorker('Backend developer')

    const uiRow = [...activePanel().querySelectorAll<HTMLTableRowElement>('.matrix-row')].find((row) => row.textContent?.includes('clanker-ui-developer'))!
    expect(uiRow.classList.contains('has-error')).toBe(true)
    expect(uiRow.querySelector('.row-error-label')?.textContent).toBe('Field error')
    expect(tabButton('Worker routes').querySelector('.tab-error-dot')).toBeTruthy()
  })

  it('prefills and preserves a worker preview while tracing split winners and global scope', async () => {
    vi.useFakeTimers()
    const loaded = structuredClone(config)
    const role = { id: 'clanker-ui-developer', label: 'UI developer' }
    loaded.bundle.roles = [role]
    loaded.bundle.defaults.interactions = { implementation: { model: 'gpt-5.6-terra', reasoning: { mode: 'adaptive' } } }
    loaded.scopes.global.document = {
      schema_version: 1,
      interactions: { implementation: { model: 'gpt-5.6-luna' } },
      agents: { [role.id]: { model: 'gpt-5.6-sol' } },
    }
    loaded.scopes.project!.document = { schema_version: 1, interactions: { implementation: { model: 'project-only-model' } } }
    const decision = {
      model: 'gpt-5.6-sol', reasoning: { mode: 'fixed', effort: 'high' } as const,
      effort: 'high', proposed_effort: 'max', ceiling: 'high', ceiling_source: 'global profile',
      interaction: 'implementation', role: role.id, tier: 'exceptional', reason: 'Risk raised the tier', limitations: [],
      provenance: { model: 'global.agents.clanker-ui-developer.model', reasoning: 'session_override.reasoning', profile: null },
      capability_status: 'available', dispatch_allowed: false,
    }
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(loaded))
      .mockResolvedValueOnce(response({ effective: loaded.effective, decision }))
    await render(fetchMock)
    await inspectWorker('UI developer')
    const implementationCell = [...activePanel().querySelectorAll<HTMLButtonElement>('.route-cell')].find((button) => button.getAttribute('aria-label')?.startsWith('UI developer, Implementation and testing:'))!
    await act(async () => { implementationCell.click() })
    await act(async () => { actionButton('Preview a decision for this agent', inspector()).click() })
    const form = previewForm()
    expect((form.querySelector('label select') as HTMLSelectElement).value).toBe('implementation')
    expect((form.querySelectorAll('label select')[1] as HTMLSelectElement).value).toBe(role.id)
    await act(async () => { actionButton('security', form).click() })
    const session = form.querySelector('.session-fieldset')!
    await act(async () => { (session.querySelector('summary') as HTMLElement).click() })
    await act(async () => { actionButton('Fixed', session.querySelector('[aria-label="Session override mode"]')!).click() })
    await setInput(session.querySelector('label:last-of-type select') as HTMLSelectElement, 'high')
    await act(async () => { actionButton('Preview route', form).click(); await Promise.resolve() })

    const table = document.querySelector('[aria-label="Eight routing precedence layers"]')!
    expect(table.querySelectorAll('[role="row"]')).toHaveLength(9)
    const row = (label: string) => [...table.querySelectorAll<HTMLElement>('[role="row"]')].find((item) => item.querySelector('[role="rowheader"]')?.textContent?.includes(label))!
    expect(row('Global agent default').querySelector('[role="cell"]')?.textContent).toContain('gpt-5.6-sol')
    expect(row('Global agent default').querySelector('[role="cell"]')?.textContent).toContain('WINS')
    expect(row('Session override').querySelectorAll('[role="cell"]')[1].textContent).toContain('Fixed · high')
    expect(row('Session override').querySelectorAll('[role="cell"]')[1].textContent).toContain('WINS')
    expect(row('Project activity').querySelectorAll('[role="cell"]')[0].textContent).toBe('—')
    expect(document.body.textContent).toContain('raised from routine by security')

    const previewCall = fetchMock.mock.calls.find(([path]) => path === '/api/preview')
    const payload = JSON.parse(String(previewCall?.[1]?.body))
    expect(payload.scope).toBe('global')
    expect(payload.request).toMatchObject({ interaction: 'implementation', role: role.id, risk_flags: ['security'], session_override: { reasoning: { mode: 'fixed', effort: 'high' } } })
    expect(payload.document.interactions.implementation.model).toBe('gpt-5.6-luna')
    expect(payload.document.interactions.implementation.model).not.toBe('project-only-model')

    await openTab('Worker routes')
    await openTab('Preview a route')
    expect(document.querySelector('.decision-hero')).toBeTruthy()
    expect((previewForm().querySelector('label select') as HTMLSelectElement).value).toBe('implementation')
    expect((previewForm().querySelectorAll('label select')[1] as HTMLSelectElement).value).toBe(role.id)
  })

  it('switches theme and restores system theme without losing the saved preference', async () => {
    await render(vi.fn().mockResolvedValue(response(config)))
    const theme = document.querySelector<HTMLSelectElement>('[aria-label="Theme"]')!
    await setInput(theme, 'dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(localStorage.getItem('routing-editor-theme')).toBe('dark')
    await setInput(theme, 'system')
    expect(document.documentElement.hasAttribute('data-theme')).toBe(false)
    expect(localStorage.getItem('routing-editor-theme')).toBe('system')
  })

  it('keeps Retry load available after dismissing the initial configuration failure', async () => {
    const fetchMock = vi.fn().mockRejectedValueOnce(new Error('Configuration service is offline')).mockResolvedValueOnce(response(config))
    await render(fetchMock)
    expect(document.querySelector('[role="alert"]')?.textContent).toContain('Configuration service is offline')
    await act(async () => { document.querySelector<HTMLButtonElement>('[aria-label="Dismiss load message"]')!.click() })
    expect(document.body.textContent).toContain('Routing preferences are unavailable.')
    await act(async () => { actionButton('Retry load').click(); await Promise.resolve(); await Promise.resolve() })
    await openTab('Activity defaults')
    expect(activePanel().querySelectorAll('.activity-default-card')).toHaveLength(4)
  })

  it('keeps an intentionally opened activity expanded through draft validation', async () => {
    vi.useFakeTimers()
    const loaded = structuredClone(config)
    loaded.bundle.roles = [{ id: 'clanker-ui-developer', label: 'UI developer' }]
    loaded.effective!.agents = { 'clanker-ui-developer': { route: { model: 'gpt-5.6-terra', reasoning: { mode: 'adaptive' } }, provenance: { model: 'bundle.defaults', reasoning: 'bundle.defaults' } } }
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(loaded))
      .mockResolvedValue(response({ effective: loaded.effective, decision: null }))
    await render(fetchMock)
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    await inspectWorker('UI developer')
    const implementation = [...activePanel().querySelectorAll<HTMLButtonElement>('.route-cell')].find((button) => button.getAttribute('aria-label')?.startsWith('UI developer, Implementation and testing:'))!
    await act(async () => { implementation.click() })
    const planning = [...inspector().querySelectorAll<HTMLElement>('.activity-route')].find((item) => item.querySelector('.activity-route-toggle')?.textContent?.includes('Planning and design'))!
    await act(async () => { planning.querySelector<HTMLButtonElement>('.activity-route-toggle')!.click() })
    const planningModel = planning.querySelector<HTMLSelectElement>('.activity-route-editor .model-picker select')!
    await setInput(planningModel, 'gpt-5.6-luna')
    expect(planning.querySelector('.activity-route-editor')).toBeTruthy()
    expect(planning.querySelector('.activity-route-toggle')?.getAttribute('aria-expanded')).toBe('true')
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    expect(planning.querySelector('.activity-route-editor')).toBeTruthy()
    expect(planning.querySelector('.activity-route-toggle')?.getAttribute('aria-expanded')).toBe('true')
  })

  it('shows an inherited Claude alias warning in both the matrix and inspector', async () => {
    vi.useFakeTimers()
    const loaded = structuredClone(config)
    loaded.effective!.interactions['claude-review'].route!.model = 'opus'
    loaded.scopes.global.document = { schema_version: 1 }
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(loaded))
      .mockResolvedValue(response({ effective: loaded.effective, decision: null }))
    await render(fetchMock)
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    await openTab('Worker routes')
    const aliasCell = activePanel().querySelector<HTMLButtonElement>('.claude-row .route-cell')!
    expect(aliasCell.textContent).toContain('Alias · resolution may change')
    await act(async () => { aliasCell.click() })
    expect(inspector().querySelector('.alias-note')?.textContent).toContain('Alias · resolution may change')
  })

  it('shows an unknown profile source and does not strike matching local trace values', async () => {
    vi.useFakeTimers()
    const loaded = structuredClone(config)
    loaded.bundle.defaults.interactions = { implementation: { model: 'gpt-5.6-terra', reasoning: { mode: 'adaptive' } } }
    const profileSource = 'global.adaptive_profiles.codex:gpt-5.6-terra'
    const decision = {
      model: 'gpt-5.6-terra', reasoning: { mode: 'adaptive' } as const,
      effort: 'high', proposed_effort: 'high', ceiling: 'xhigh', ceiling_source: 'bundle profile',
      interaction: 'implementation', tier: 'complex', reason: 'Matched saved routing', limitations: [],
      provenance: { model: 'resolver-v2:model', reasoning: 'resolver-v2:reasoning', profile: profileSource },
      capability_status: 'available', dispatch_allowed: false,
    }
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(loaded))
      .mockResolvedValueOnce(response({ effective: loaded.effective, decision }))
    await render(fetchMock)
    await openTab('Preview a route')
    await act(async () => { actionButton('Preview route', previewForm()).click(); await Promise.resolve() })

    const table = document.querySelector('[aria-label="Eight routing precedence layers"]')!
    const bundled = [...table.querySelectorAll<HTMLElement>('[role="row"]')].find((row) => row.querySelector('[role="rowheader"]')?.textContent?.includes('Bundled defaults'))!
    const model = bundled.querySelectorAll<HTMLElement>('[role="cell"]')[0]
    const reasoning = bundled.querySelectorAll<HTMLElement>('[role="cell"]')[1]
    expect(model.textContent).toContain('gpt-5.6-terra')
    expect(model.querySelector('.is-overridden')).toBeNull()
    expect(reasoning.textContent).toContain('Adaptive')
    expect(reasoning.querySelector('.is-overridden')).toBeNull()
    expect(document.querySelector('.effort-section')?.textContent).toContain(`Profile source: ${profileSource.replaceAll('_', ' ')}`)
  })

  it('reopens Wrangler completion details and Escape restores focus to its button', async () => {
    const loaded = structuredClone(config)
    loaded.wrangler = { available: true, running: false }
    const completion = deferred<Response>()
    const fetchStarted = deferred<void>()
    const fetchMock = vi.fn((path: string) => {
      if (path === '/api/config') return Promise.resolve(response(loaded))
      if (path === '/api/wrangler') { fetchStarted.resolve(undefined); return completion.promise }
      return Promise.resolve(response({ effective: loaded.effective, decision: null }))
    })
    await render(fetchMock)
    const run = actionButton('Run Wrangler')
    await act(async () => { run.click() })
    await fetchStarted.promise
    const details = document.querySelector<HTMLDetailsElement>('.wrangler-details')!
    expect(details.open).toBe(true)
    const fastResult = {
      ok: true,
      status: 200,
      json: () => Promise.resolve({ success: false, message: 'Wrangler failed safely', output: 'permission denied', truncated: false }),
    } as unknown as Response
    await act(async () => {
      (details.querySelector('summary') as HTMLElement).click()
      completion.resolve(fastResult)
      await Promise.resolve()
      await Promise.resolve()
      await Promise.resolve()
    })
    expect(run.disabled).toBe(false)
    expect(details.open).toBe(true)
    expect(details.querySelector('[role="alert"]')?.textContent).toContain('Wrangler failed safely')
    const summary = details.querySelector('summary') as HTMLElement
    summary.focus()
    await act(async () => { summary.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })) })
    expect(details.open).toBe(false)
    expect(document.activeElement).toBe(run)
  })

  it('reopens an activity when its matrix cell is selected a second time', async () => {
    const loaded = structuredClone(config)
    loaded.bundle.roles = [{ id: 'clanker-ui-developer', label: 'UI developer' }]
    await render(vi.fn().mockResolvedValue(response(loaded)))
    await inspectWorker('UI developer')
    const implementation = [...activePanel().querySelectorAll<HTMLButtonElement>('.route-cell')].find((button) => button.getAttribute('aria-label')?.startsWith('UI developer, Implementation and testing:'))!
    const route = () => [...inspector().querySelectorAll<HTMLElement>('.activity-route')].find((item) => item.querySelector('.activity-route-toggle')?.textContent?.includes('Implementation and testing'))!

    await act(async () => { implementation.click() })
    expect(route().querySelector('.activity-route-toggle')?.getAttribute('aria-expanded')).toBe('true')
    await act(async () => { route().querySelector<HTMLButtonElement>('.activity-route-toggle')!.click() })
    expect(route().querySelector('.activity-route-toggle')?.getAttribute('aria-expanded')).toBe('false')
    await act(async () => { implementation.click() })
    expect(route().querySelector('.activity-route-toggle')?.getAttribute('aria-expanded')).toBe('true')
  })

  it('keeps the expanded activity when a new error is added and that activity also has an error', async () => {
    vi.useFakeTimers()
    const loaded = structuredClone(config)
    loaded.bundle.roles = [{ id: 'clanker-ui-developer', label: 'UI developer' }]
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(loaded))
      .mockResolvedValueOnce(response({ effective: loaded.effective, decision: null }))
      .mockResolvedValueOnce(response({ error: 'global.interactions.planning.specialists.clanker-ui-developer.model: save rejected' }, 400))
      .mockResolvedValueOnce(response({ error: 'interactions.implementation.specialists.clanker-ui-developer.model: resolver rejected route' }, 400))
    await render(fetchMock)
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    await inspectWorker('UI developer')
    const activity = (label: string) => [...inspector().querySelectorAll<HTMLElement>('.activity-route')].find((item) => item.querySelector('.activity-route-toggle')?.textContent?.includes(label))!
    const planningCell = [...activePanel().querySelectorAll<HTMLButtonElement>('.route-cell')].find((button) => button.getAttribute('aria-label')?.startsWith('UI developer, Planning and design:'))!
    await act(async () => { planningCell.click() })
    const planning = activity('Planning and design')
    await setInput(planning.querySelector<HTMLSelectElement>('.activity-route-editor .model-picker select')!, 'gpt-5.6-luna')
    await act(async () => { actionButton('Save global preferences').click(); await Promise.resolve() })
    expect(document.body.textContent).toContain('save rejected')

    const implementation = activity('Implementation and testing')
    await act(async () => { implementation.querySelector<HTMLButtonElement>('.activity-route-toggle')!.click() })
    await setInput(implementation.querySelector<HTMLSelectElement>('.activity-route-editor .model-picker select')!, 'gpt-5.6-luna')
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })

    expect(document.body.textContent).toContain('resolver rejected route')
    expect(implementation.querySelector('.activity-route-editor')).toBeTruthy()
    expect(implementation.querySelector('.activity-route-toggle')?.getAttribute('aria-expanded')).toBe('true')
  })

  it('labels an adaptive decision with no profile provenance as unavailable from the resolver', async () => {
    vi.useFakeTimers()
    const loaded = structuredClone(config)
    const decision = {
      model: 'gpt-5.6-terra', reasoning: { mode: 'adaptive' } as const,
      effort: 'high', proposed_effort: 'high', ceiling: 'xhigh', ceiling_source: 'bundle profile',
      interaction: 'implementation', tier: 'complex', reason: 'No profile source returned', limitations: [],
      provenance: { model: 'bundle.defaults', reasoning: 'bundle.defaults', profile: null },
      capability_status: 'available', dispatch_allowed: false,
    }
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(loaded))
      .mockResolvedValueOnce(response({ effective: loaded.effective, decision }))
    await render(fetchMock)
    await openTab('Preview a route')
    await act(async () => { actionButton('Preview route', previewForm()).click(); await Promise.resolve() })
    expect(document.querySelector('.effort-section')?.textContent).toContain('Profile source: unavailable from resolver')
  })

  it('includes the effective reasoning effort in a worker activity cell accessible name', async () => {
    vi.useFakeTimers()
    const loaded = structuredClone(config)
    loaded.bundle.roles = [{ id: 'clanker-ui-developer', label: 'UI developer' }]
    loaded.effective!.interactions.implementation.specialists!['clanker-ui-developer'] = {
      route: { model: 'gpt-5.6-terra', reasoning: { mode: 'fixed', effort: 'high' } },
      provenance: { model: 'bundle.defaults', reasoning: 'bundle.defaults' },
    }
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(loaded))
      .mockResolvedValue(response({ effective: loaded.effective, decision: null }))
    await render(fetchMock)
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    await inspectWorker('UI developer')
    const implementation = [...activePanel().querySelectorAll<HTMLButtonElement>('.route-cell')].find((button) => button.getAttribute('aria-label')?.startsWith('UI developer, Implementation and testing:'))!
    expect(implementation.getAttribute('aria-label')).toContain('fixed · high')
  })
})
