import { describe, expect, it } from 'vitest'
import { deriveAgentState } from './routePresentation'
import type { ConfigResponse, Preferences, Reasoning } from './types'

const role = { id: 'clanker-ui-developer', label: 'UI developer' }

function configFixture(): ConfigResponse {
  const interactions = [
    { id: 'planning', label: 'Planning', provider: 'codex' as const, default_model: 'gpt-5.6-terra' },
    { id: 'implementation', label: 'Implementation', provider: 'codex' as const, default_model: 'gpt-5.6-terra' },
    { id: 'native-review', label: 'Native review', provider: 'codex' as const, default_model: 'gpt-5.6-terra' },
    { id: 'visual-review', label: 'Visual review', provider: 'codex' as const, default_model: 'gpt-5.6-terra' },
    { id: 'claude-review', label: 'Claude review', provider: 'claude' as const, default_model: 'claude-opus-5' },
  ]
  const emptyRoute = { route: {}, provenance: {} }
  return {
    schema_version: 1,
    policy_version: '1',
    scopes: {
      global: { path: '/global.json', revision: 'global', document: { schema_version: 1 } },
      project: { path: '/project.json', revision: 'project', document: { schema_version: 1 } },
    },
    bundle: {
      schema_version: 1,
      policy_version: '1',
      interactions,
      roles: [role],
      models: [
        { id: 'gpt-5.6-terra', label: 'Terra', provider: 'codex', efforts: ['low', 'high'] },
        { id: 'gpt-5.6-luna', label: 'Luna', provider: 'codex', efforts: ['low', 'high'] },
        { id: 'gpt-5.6-sol', label: 'Sol', provider: 'codex', efforts: ['low', 'high'] },
        { id: 'claude-opus-5', label: 'Opus', provider: 'claude', efforts: ['low', 'high'] },
      ],
      effort_orders: { codex: ['low', 'high'], claude: ['low', 'high'] },
      defaults: { schema_version: 1 },
    },
    effective: {
      agents: {},
      interactions: Object.fromEntries(interactions.map(({ id }) => [id, structuredClone(emptyRoute)])),
      profiles: {},
    },
  }
}

function setSpecialistRoute(config: ConfigResponse, activity: string, model: string, reasoning: Reasoning, roleId = role.id) {
  config.effective!.interactions[activity].specialists = {
    ...config.effective!.interactions[activity].specialists,
    [roleId]: { route: { model, reasoning }, provenance: { model: 'bundle.defaults', reasoning: 'bundle.defaults' } },
  }
}

describe('agent route presentation', () => {
  it('shows mixed activity values when the effective agent route came from the current scope', () => {
    const config = configFixture()
    config.effective!.agents![role.id] = {
      route: { model: 'gpt-5.6-luna', reasoning: { mode: 'fixed', effort: 'high' } },
      provenance: { model: 'project.agents.clanker-ui-developer.model', reasoning: 'project.agents.clanker-ui-developer.reasoning' },
    }
    setSpecialistRoute(config, 'planning', 'gpt-5.6-terra', { mode: 'adaptive' })
    setSpecialistRoute(config, 'implementation', 'gpt-5.6-luna', { mode: 'fixed', effort: 'high' })

    const state = deriveAgentState(config, { schema_version: 1 }, 'project', role)

    expect(state.baseline?.route).toEqual({})
    expect(state.actualModels).toEqual(['gpt-5.6-terra', 'gpt-5.6-luna'])
    expect(state.modelMixed).toBe(true)
    expect(state.reasoningMixed).toBe(true)
    expect(state.valueModel).toBe('')
    expect(state.valueReasoning).toBeUndefined()
  })

  it('keeps own agent defaults and both project and inherited activity exceptions in the inspector state', () => {
    const config = configFixture()
    config.bundle.roles = [{ id: 'clanker-backend-developer', label: 'Backend developer' }]
    config.scopes.global.document = {
      schema_version: 1,
      interactions: { 'visual-review': { specialists: { 'clanker-backend-developer': { model: 'gpt-5.6-sol' } } } },
    }
    const document: Preferences = {
      schema_version: 1,
      agents: { 'clanker-backend-developer': { model: 'gpt-5.6-terra' } },
      interactions: { implementation: { specialists: { 'clanker-backend-developer': { reasoning: { mode: 'fixed', effort: 'high' } } } } },
    }
    setSpecialistRoute(config, 'implementation', 'gpt-5.6-luna', { mode: 'fixed', effort: 'high' }, 'clanker-backend-developer')
    setSpecialistRoute(config, 'visual-review', 'gpt-5.6-sol', { mode: 'adaptive' }, 'clanker-backend-developer')

    const state = deriveAgentState(config, document, 'project', 'clanker-backend-developer')

    expect(state.valueModel).toBe('gpt-5.6-terra')
    expect(state.own).toEqual({ model: 'gpt-5.6-terra' })
    expect(state.activities.map(({ id }) => id)).toEqual(['planning', 'implementation', 'native-review', 'visual-review'])
    expect(state.exceptionActivities).toEqual(['implementation', 'visual-review'])
    expect(state.activities.some(({ provider }) => provider === 'claude')).toBe(false)
  })
})
