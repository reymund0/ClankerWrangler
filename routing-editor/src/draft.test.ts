import { describe, expect, it } from 'vitest'
import { emptyPreferences, resetAgentField, resetAgentRoute, resetRoute, updateAgentRoute, updateRoute } from './draft'

describe('sparse route drafts', () => {
  it('resets a project specialist override without flattening inherited fields', () => {
    const draft = updateRoute(emptyPreferences(), 'implementation', 'clanker-ui-developer', { model: 'gpt-5.6-luna' })
    const reset = resetRoute(draft, 'implementation', 'clanker-ui-developer')
    expect(reset).toEqual({ schema_version: 1 })
  })

  it('keeps a route reasoning override when only its model is changed', () => {
    const original = updateRoute(emptyPreferences(), 'implementation', undefined, { reasoning: { mode: 'adaptive', max_effort: 'high' } })
    const updated = updateRoute(original, 'implementation', undefined, { model: 'gpt-5.6-luna' })
    expect(updated.interactions?.implementation).toEqual({ model: 'gpt-5.6-luna', reasoning: { mode: 'adaptive', max_effort: 'high' } })
  })
})

  it('updates and resets sparse agent fields without changing activity exceptions', () => {
    const original = updateRoute(emptyPreferences(), 'implementation', 'clanker-ui-developer', { model: 'gpt-5.6-terra' })
    const withAgent = updateAgentRoute(original, 'clanker-ui-developer', { model: 'gpt-5.6-luna', reasoning: { mode: 'fixed', effort: 'high' } })
    expect(resetAgentField(withAgent, 'clanker-ui-developer', 'model')).toEqual({ schema_version: 1, agents: { 'clanker-ui-developer': { reasoning: { mode: 'fixed', effort: 'high' } } }, interactions: original.interactions })
    expect(resetAgentRoute(withAgent, 'clanker-ui-developer').interactions).toEqual(original.interactions)
  })
