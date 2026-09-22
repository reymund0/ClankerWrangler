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

async function render(fetchMock: ReturnType<typeof vi.fn>) {
  const mock = fetchMock as unknown as (path: string, init?: RequestInit) => Promise<Response>
  vi.stubGlobal('fetch', (path: string, init?: RequestInit) => path === '/api/models' ? Promise.resolve(response(catalog)) : mock(path, init))
  const element = document.createElement('div'); document.body.append(element)
  root = createRoot(element)
  await act(async () => { root!.render(<App />) })
  await act(async () => { await Promise.resolve() })
}

afterEach(async () => { await act(async () => root?.unmount()); root = undefined; vi.unstubAllGlobals(); vi.useRealTimers() })

describe('routing editor', () => {
  it('filters specialist panels and preview choices by scenario', async () => {
    const loaded = structuredClone(config)
    loaded.bundle.roles = [
      { id: 'clanker-architect', label: 'Architect' },
      { id: 'clanker-backend-developer', label: 'Backend developer' },
      { id: 'clanker-code-review', label: 'Code reviewer' },
      { id: 'clanker-test-engineer', label: 'Test engineer' },
      { id: 'clanker-ui-ux-reviewer', label: 'Visual reviewer' },
    ]
    await render(vi.fn().mockResolvedValue(response(loaded)))
    const activityExpected = [['Planning and design', 'Native review'], ['Planning and design', 'Implementation and testing', 'Native review'], ['Native review'], ['Implementation and testing', 'Native review'], ['Visual review']]
    const expected = [['Architect', 'Backend developer'], ['Backend developer', 'Test engineer'], ['Architect', 'Backend developer', 'Code reviewer', 'Test engineer'], ['Visual reviewer']]
    const cards = [...document.querySelectorAll('.interaction-card')]
    const interaction = document.querySelector('.preview-form select') as HTMLSelectElement
    for (let index = 0; index < expected.length; index++) {
      const toggle = [...cards[index].querySelectorAll('button')].find((button) => button.textContent === 'Customize by activity')!
      await act(async () => toggle.click())
      expect([...cards[index].querySelectorAll('.specialist h4')].map((heading) => heading.textContent)).toEqual(activityExpected[index])
      await setInput(interaction, loaded.bundle.interactions[index].id)
      const roles = document.querySelectorAll('.preview-form select')[1] as HTMLSelectElement
      expect([...roles.options].slice(1).map((option) => option.textContent)).toEqual(expected[index])
    }
    expect(cards[5].textContent).toContain('Claude review')
  })

  it('keeps existing off-scenario overrides editable and removes them from choices after reset', async () => {
    const loaded = structuredClone(config)
    loaded.bundle.roles.push({ id: 'clanker-backend-developer', label: 'Backend developer' })
    loaded.scopes.global.document = { schema_version: 1, interactions: { 'visual-review': { specialists: { 'clanker-backend-developer': { model: 'gpt-5.6-terra' } } } } }
    await render(vi.fn().mockResolvedValue(response(loaded)))
    const card = document.querySelector('.agent-card')!
    await act(async () => [...card.querySelectorAll('button')].find((button) => button.textContent === 'Customize by activity')!.click())
    expect(card.textContent).toContain('Visual review')
    const section = [...card.querySelectorAll('.specialist')].find((item) => item.textContent?.includes('Visual review'))!
    await act(async () => [...section.querySelectorAll('button')].find((button) => button.textContent === 'Reset activity exception')!.click())
    expect(card.textContent).not.toContain('Visual review')
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
    const loaded = structuredClone(config)
    loaded.bundle.roles = [{ id: 'clanker-ui-developer', label: 'UI developer' }]
    await render(vi.fn().mockResolvedValue(response(loaded)))
    expect(document.body.textContent).toContain('Inherited from bundled defaults')
    const toggle = [...document.querySelectorAll('button')].find((button) => button.textContent?.includes('Customize by activity'))!
    await act(async () => { toggle.click() })
    expect(document.body.textContent).toContain('Implementation and testing')
    expect([...document.querySelectorAll('button')].find((button) => button.textContent?.includes('Reset activity exception'))).toBeTruthy()
  })

  it('refreshes the global inherited route from the resolver instead of showing project-effective data', async () => {
    vi.useFakeTimers()
    const loaded = structuredClone(config)
    loaded.effective!.interactions.implementation.route!.model = 'gpt-5.6-luna'
    const globalEffective = structuredClone(config.effective)
    const fetchMock = vi.fn().mockResolvedValueOnce(response(loaded)).mockResolvedValueOnce(response({ effective: globalEffective, decision: null }))
    await render(fetchMock)
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    const implementation = [...document.querySelectorAll('.interaction-card')].find((card) => card.textContent?.includes('Implementation and testing'))!
    expect((implementation.querySelector('.model-picker select') as HTMLInputElement).value).toBe('gpt-5.6-terra')
  })

  it('renders an API-returned Luna ceiling preview as unverified', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(config))
      .mockResolvedValueOnce(response({ effective: config.effective, decision: { model: 'gpt-5.6-luna', reasoning: { mode: 'adaptive' }, effort: 'xhigh', proposed_effort: 'max', ceiling: 'xhigh', ceiling_source: 'global', interaction: 'implementation', tier: 'exceptional', reason: 'Hard integration', limitations: ['Adaptive exceptional effort max is capped at xhigh'], provenance: { model: 'global', reasoning: 'global', profile: 'global' }, capability_status: 'unverified', dispatch_allowed: false } }))
    await render(fetchMock)
    const interaction = document.querySelector('.preview-form select') as HTMLSelectElement
    await act(async () => { interaction.value = 'implementation'; interaction.dispatchEvent(new Event('change', { bubbles: true })) })
    const tier = document.querySelectorAll('.preview-form select')[1] as HTMLSelectElement
    await act(async () => { tier.value = 'exceptional'; tier.dispatchEvent(new Event('change', { bubbles: true })) })
    const previewButton = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Preview route')!
    await act(async () => { previewButton.click(); await Promise.resolve() })
    expect(document.body.textContent).toContain('gpt-5.6-luna')
    expect(document.body.textContent).toContain('unverified')
    expect(document.body.textContent).toContain('max is capped at xhigh')
    expect(JSON.parse(fetchMock.mock.calls[1][1].body).document).toEqual({ schema_version: 1 })
  })

  it('keeps a draft and explains a save conflict', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config)).mockResolvedValueOnce(response({ error: 'Preferences changed since loading.' }, 409))
    await render(fetchMock)
    const model = document.querySelector('.interaction-card .model-picker select') as HTMLInputElement
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
    expect(document.body.textContent).toContain('Model profile default (xhigh)')
    expect(document.body.textContent).toContain('Adaptive ceiling: Model profile default (xhigh) · bundle.defaults.adaptive profiles.codex:gpt-5.6-terra')
    const controls = document.querySelectorAll<HTMLSelectElement>('.interaction-card .route-controls select')
    await act(async () => { controls[2].value = 'high'; controls[2].dispatchEvent(new Event('change', { bubbles: true })) })
    expect(controls[2].options[0].textContent).toBe('Model profile default')
    await act(async () => { controls[1].value = 'fixed'; controls[1].dispatchEvent(new Event('change', { bubbles: true })) })
    const effort = document.querySelectorAll<HTMLSelectElement>('.interaction-card .route-controls select')[2]
    expect(effort.value).toBe('')
    expect(effort.options[0].disabled).toBe(true)
    await act(async () => { effort.value = 'low'; effort.dispatchEvent(new Event('change', { bubbles: true })) })
    const save = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Save global preferences')!
    await act(async () => { save.click(); await Promise.resolve() })
    expect(JSON.parse(fetchMock.mock.calls[2][1].body).document.interactions.planning.reasoning).toEqual({ mode: 'fixed', effort: 'low' })
  })

  it('associates an effective route-root error with its controls and clears it after correction', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config)).mockResolvedValueOnce(response({ error: 'effective.interactions.implementation: Adaptive routing for codex:custom-model-v9 requires a complete profile' }, 400))
    await render(fetchMock)
    const implementation = [...document.querySelectorAll('.interaction-card')].find((card) => card.textContent?.includes('Implementation and testing'))!
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
    const model = document.querySelector('.interaction-card .model-picker select') as HTMLInputElement
    await setInput(model, 'custom-model-v9')
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    expect(document.getElementById('interactions.planning-route-error')).toBeTruthy()
    expect(model.getAttribute('aria-describedby')).toContain('interactions.planning-route-error')
    const advanced = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Show advanced Adaptive profiles')!
    await act(async () => { advanced.click() })
    await setInput(document.querySelectorAll('.add-profile select')[1] as HTMLSelectElement, 'custom-model-v9')
    const add = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Add profile')!
    await act(async () => { add.click() })
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    expect(JSON.parse(fetchMock.mock.calls[2][1].body).document.adaptive_profiles['codex:custom-model-v9']).toBeTruthy()
    expect(document.getElementById('interactions.planning-route-error')).toBeNull()
    expect(model.getAttribute('aria-describedby')).not.toContain('interactions.planning-route-error')
    expect(document.body.textContent).not.toContain('requires a complete profile')
    expect((document.querySelector('.interaction-card .model-picker select') as HTMLSelectElement).value).toBe('custom-model-v9')
  })

  it('invalidates an explicit route error when its missing profile is added', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config))
      .mockResolvedValueOnce(response({ error: 'effective.interactions.planning: requires a complete profile' }, 400))
    await render(fetchMock)
    await setInput(document.querySelector('.interaction-card .model-picker select') as HTMLInputElement, 'custom-model-v9')
    const preview = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Preview route')!
    await act(async () => { preview.click(); await Promise.resolve() })
    expect(document.getElementById('interactions.planning-route-error')).toBeTruthy()
    const advanced = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Show advanced Adaptive profiles')!
    await act(async () => { advanced.click() })
    await setInput(document.querySelectorAll('.add-profile select')[1] as HTMLSelectElement, 'custom-model-v9')
    const add = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Add profile')!
    await act(async () => { add.click() })
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(document.getElementById('interactions.planning-route-error')).toBeNull()
  })

  it('does not clear a save failure when automatic draft validation succeeds', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config))
      .mockResolvedValueOnce(response({ error: 'global.interactions.planning.model: save rejected' }, 400))
      .mockResolvedValueOnce(response({ effective: config.effective, decision: null }))
    await render(fetchMock)
    await setInput(document.querySelector('.interaction-card .model-picker select') as HTMLInputElement, 'gpt-5.6-luna')
    const save = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Save global preferences')!
    await act(async () => { save.click(); await Promise.resolve() })
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    expect(document.getElementById('interactions.planning-model-error')?.textContent).toContain('save rejected')
    expect(document.querySelector('footer')?.textContent).toContain('save rejected')
  })

  it('associates nested reasoning errors with the specialist control and clears them when corrected', async () => {
    const loaded = structuredClone(config)
    loaded.bundle.roles = [{ id: 'clanker-ui-developer', label: 'UI developer' }]
    const fetchMock = vi.fn().mockResolvedValueOnce(response(loaded)).mockResolvedValueOnce(response({ error: 'global.interactions.planning.specialists.clanker-ui-developer.reasoning.max_effort: is not supported by codex' }, 400))
    await render(fetchMock)
    const toggle = [...document.querySelectorAll('button')].find((button) => button.textContent?.includes('Customize by activity'))!
    await act(async () => { toggle.click() })
    const specialistMaximum = document.querySelectorAll<HTMLSelectElement>('.specialist .route-controls select')[2]
    await act(async () => { specialistMaximum.value = 'high'; specialistMaximum.dispatchEvent(new Event('change', { bubbles: true })) })
    const hide = [...document.querySelectorAll('button')].find((button) => button.textContent?.includes('Hide by activity'))!
    await act(async () => { hide.click() })
    const save = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Save global preferences')!
    await act(async () => { save.click(); await Promise.resolve() })
    expect(document.body.textContent).toContain('is not supported by codex')
    expect([...document.querySelectorAll('button')].find((button) => button.textContent?.includes('Hide by activity'))).toBeTruthy()
    const reopenedMaximum = document.querySelectorAll<HTMLSelectElement>('.specialist .route-controls select')[2]
    expect(reopenedMaximum.getAttribute('aria-describedby')).toContain('interactions.planning.specialists.clanker-ui-developer-reasoning-error')
    const reset = [...document.querySelectorAll<HTMLButtonElement>('.specialist button')].find((button) => button.textContent === 'Reset activity exception')!
    await act(async () => { reset.click() })
    expect(document.body.textContent).not.toContain('is not supported by codex')
  })

  it('associates advanced profile errors with the invalid input and clears them when corrected', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config)).mockResolvedValueOnce(response({ error: 'global.adaptive_profiles.codex:custom-model-v9.tiers.routine: is not supported by codex' }, 400))
    await render(fetchMock)
    const advanced = [...document.querySelectorAll('button')].find((button) => button.textContent?.includes('Show advanced Adaptive profiles'))!
    await act(async () => { advanced.click() })
    await setInput(document.querySelectorAll('.add-profile select')[1] as HTMLSelectElement, 'custom-model-v9')
    const addProfile = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Add profile')!
    await act(async () => { addProfile.click() })
    await act(async () => { advanced.click() })
    const save = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Save global preferences')!
    await act(async () => { save.click(); await Promise.resolve() })
    const routine = document.querySelectorAll('.profile select')[1] as HTMLSelectElement
    expect(document.body.textContent).toContain('is not supported by codex')
    expect([...document.querySelectorAll('button')].find((button) => button.textContent?.includes('Hide advanced Adaptive profiles'))).toBeTruthy()
    expect(routine.getAttribute('aria-describedby')).toContain('adaptive_profiles.codex:custom-model-v9.tiers.routine-error')
    await setInput(routine, 'high')
    expect(document.body.textContent).not.toContain('is not supported by codex')
  })

  it('keeps a late save failure global without attaching it to a newer draft', async () => {
    const pending = deferred<Response>()
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config)).mockReturnValueOnce(pending.promise)
    await render(fetchMock)
    const model = document.querySelector('.interaction-card .model-picker select') as HTMLInputElement
    await setInput(model, 'gpt-5.6-luna')
    const save = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Save global preferences')!
    await act(async () => { save.click() })
    await setInput(model, 'gpt-5.6-sol')
    pending.resolve(response({ error: 'global.interactions.planning.model: rejected by the server' }, 400))
    await act(async () => { await Promise.resolve() })
    expect(document.body.textContent).toContain('rejected by the server')
    expect(document.getElementById('interactions.planning-model-error')).toBeNull()
    expect((document.querySelector('.interaction-card .model-picker select') as HTMLSelectElement).value).toBe('gpt-5.6-sol')
  })

  it('clears a field error when resetting the affected route', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config)).mockResolvedValueOnce(response({ error: 'global.interactions.planning.model: rejected by the server' }, 400))
    await render(fetchMock)
    await setInput(document.querySelector('.interaction-card .model-picker select') as HTMLInputElement, 'gpt-5.6-luna')
    const save = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Save global preferences')!
    await act(async () => { save.click(); await Promise.resolve() })
    expect(document.getElementById('interactions.planning-model-error')).toBeTruthy()
    const reset = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Reset route to inherited')!
    await act(async () => { reset.click() })
    expect(document.getElementById('interactions.planning-model-error')).toBeNull()
    expect(document.body.textContent).not.toContain('rejected by the server')
  })

  it('clears only the generic preview error after a successful explicit preview', async () => {
    const decision = { model: 'gpt-5.6-terra', reasoning: { mode: 'adaptive' }, effort: 'high', proposed_effort: 'high', ceiling: 'xhigh', ceiling_source: 'bundle.defaults', interaction: 'implementation', tier: 'routine', reason: 'Resolved', limitations: [], provenance: { model: 'bundle.defaults', reasoning: 'bundle.defaults', profile: 'bundle.defaults' }, capability_status: 'unverified', dispatch_allowed: false }
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config)).mockResolvedValueOnce(response({ error: 'Preview temporarily failed' }, 400)).mockResolvedValueOnce(response({ effective: config.effective, decision }))
    await render(fetchMock)
    const preview = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Preview route')!
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
    await setInput(document.querySelector('.interaction-card .model-picker select') as HTMLInputElement, 'gpt-5.6-luna')
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    await setInput(document.querySelector('.session-fieldset .model-picker select') as HTMLInputElement, 'gpt-5.6-luna')
    const preview = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Preview route')!
    await act(async () => { preview.click(); await Promise.resolve() })
    expect(document.body.textContent).toContain('preview validation failed')
    pending.resolve(response({ effective: config.effective, decision: null }))
    await act(async () => { await Promise.resolve() })
    expect(document.body.textContent).toContain('preview validation failed')
    expect((document.querySelector('.session-fieldset .model-picker select') as HTMLSelectElement).value).toBe('gpt-5.6-luna')
    await setInput(document.querySelector('.session-fieldset .model-picker select') as HTMLInputElement, 'gpt-5.6-sol')
    expect(document.body.textContent).not.toContain('preview validation failed')
  })

  it('ignores an explicit preview response that becomes stale after inputs change', async () => {
    const pending = deferred<Response>()
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config)).mockReturnValueOnce(pending.promise)
    await render(fetchMock)
    const preview = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Preview route')!
    await act(async () => { preview.click() })
    await setInput(document.querySelector('.preview-form input[required]') as HTMLInputElement, 'Changed after preview started')
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
    const model = document.querySelector('.interaction-card .model-picker select') as HTMLInputElement
    await setInput(model, 'gpt-5.6-luna')
    const save = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Save global preferences')!
    await act(async () => { save.click() })
    expect((document.querySelector('.scope-bar select') as HTMLSelectElement).disabled).toBe(true)
    await setInput(model, 'gpt-5.6-sol')
    pending.resolve(response(saved))
    await act(async () => { await Promise.resolve() })
    expect((document.querySelector('.interaction-card .model-picker select') as HTMLSelectElement).value).toBe('gpt-5.6-sol')
    expect(document.body.textContent).toContain('Newer changes remain unsaved.')
  })

  it('does not let a late reload response replace edits made after reload started', async () => {
    const pending = deferred<Response>()
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config)).mockReturnValueOnce(pending.promise)
    await render(fetchMock)
    const reload = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Export draft and reload')!
    await act(async () => { reload.click() })
    const model = document.querySelector('.interaction-card .model-picker select') as HTMLInputElement
    await setInput(model, 'gpt-5.6-luna')
    const save = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Save global preferences')!
    expect(save.disabled).toBe(true)
    pending.resolve(response(config))
    await act(async () => { await Promise.resolve() })
    expect(model.value).toBe('gpt-5.6-luna')
    expect(document.body.textContent).toContain('Unsaved changes')
  })

  it('keeps the original revision when a reload response is discarded after an edit', async () => {
    const pending = deferred<Response>()
    const reloaded = structuredClone(config)
    reloaded.scopes.global.revision = 'revision-b'
    const fetchMock = vi.fn().mockResolvedValueOnce(response(config)).mockReturnValueOnce(pending.promise).mockResolvedValueOnce(response({ error: 'Preferences changed since loading.' }, 409))
    await render(fetchMock)
    const reload = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Export draft and reload')!
    await act(async () => { reload.click() })
    const model = document.querySelector('.interaction-card .model-picker select') as HTMLInputElement
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
    const card = document.querySelector('.agent-card')!
    await setInput(card.querySelector('.model-picker select') as HTMLSelectElement, 'gpt-5.6-luna')
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    expect(document.getElementById('agents.clanker-ui-developer-reasoning-error')?.textContent).toContain('not supported')
    expect(card.querySelector('.adaptive-details')?.hasAttribute('open')).toBe(true)
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
    const scope = document.querySelector('.scope-bar select') as HTMLSelectElement
    await setInput(scope, 'project')
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    const model = document.querySelector('.agent-card .model-picker select') as HTMLSelectElement
    expect(model.value).toBe('gpt-5.6-luna')
    await setInput(scope, 'global')
    expect(model.value).toBe('')
    expect(model.selectedOptions[0].textContent).toContain('Inherited model unresolved')
    await act(async () => { await vi.advanceTimersByTimeAsync(180) })
    expect(model.value).toBe('')
    pending.resolve(response({ effective: loaded.effective, decision: null }))
    await act(async () => { await Promise.resolve() })
    expect(model.value).toBe('gpt-5.6-terra')
  })

  it('keeps Claude and specialist activity controls out of expanded advanced defaults', async () => {
    const loaded = structuredClone(config)
    loaded.bundle.roles = [{ id: 'clanker-ui-developer', label: 'UI developer' }]
    await render(vi.fn().mockResolvedValue(response(loaded)))
    await act(async () => [...document.querySelectorAll('button')].find((button) => button.textContent === 'Customize by activity')!.click())
    await act(async () => [...document.querySelectorAll('button')].find((button) => button.textContent === 'Show advanced activity defaults')!.click())
    const advanced = document.querySelector('.advanced-grid')!
    expect(advanced.textContent).not.toContain('Claude review')
    expect([...advanced.querySelectorAll('button')].some((button) => button.textContent?.includes('specialist overrides'))).toBe(false)
    expect([...document.querySelectorAll('.interaction-card')].filter((card) => card.textContent?.includes('Claude review'))).toHaveLength(1)
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
    const card = document.querySelector('.agent-card')!
    await setInput(card.querySelector('.model-picker select') as HTMLSelectElement, 'gpt-5.6-luna')
    await act(async () => [...document.querySelectorAll('button')].find((button) => button.textContent === 'Save global preferences')!.click())
    const documentBody = JSON.parse(String(fetchMock.mock.calls[1][1].body)).document
    expect(documentBody.agents).toEqual({ 'clanker-ui-developer': { model: 'gpt-5.6-luna' } })
    expect(documentBody.interactions.implementation.specialists['clanker-ui-developer']).toEqual({ model: 'gpt-5.6-terra' })
    expect(card.textContent).toContain('1 activity exception')
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
    const card = document.querySelector('.agent-card')!
    const controls = card.querySelectorAll<HTMLSelectElement>('.route-controls select')
    expect(controls[0].selectedOptions[0].textContent).toContain('Varies by activity')
    await setInput(controls[1], 'fixed')
    const efforts = card.querySelectorAll<HTMLSelectElement>('.route-controls select')[2]
    expect([...efforts.options].filter((option) => !option.disabled).map((option) => option.value)).toEqual(['high'])
    expect(card.textContent).toContain('Activity values differ')
  })
})
