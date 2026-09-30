import { emptyPreferences, getOwnAgentRoute, getOwnRoute } from './draft'
import { specialistChoices } from './specialists'
import type { AgentRoute, ConfigResponse, EffectiveRoute, Interaction, Preferences, Reasoning, Role, Scope } from './types'

function uniform<T>(values: T[]): T | undefined {
  if (values.length === 0) return undefined
  const serialized = JSON.stringify(values[0])
  return values.every((value) => JSON.stringify(value) === serialized) ? values[0] : undefined
}

export function deriveAgentState(config: ConfigResponse, document: Preferences, scope: Scope, role: Role | string) {
  const roleId = typeof role === 'string' ? role : role.id
  const own = getOwnAgentRoute(document, roleId)
  const activities = config.bundle.interactions.filter((interaction) =>
    interaction.provider === 'codex' && specialistChoices(config, document, scope, interaction.id).some((candidate) => candidate.id === roleId))
  const rawBaseline = config.effective?.agents?.[roleId]
  const baseline: EffectiveRoute | undefined = rawBaseline ? { ...rawBaseline, route: {
    ...(rawBaseline.route?.model && !(rawBaseline.provenance?.model?.startsWith(`${scope}.agents.`) && !own?.model) ? { model: rawBaseline.route.model } : {}),
    ...(rawBaseline.route?.reasoning && !(rawBaseline.provenance?.reasoning?.startsWith(`${scope}.agents.`) && !own?.reasoning) ? { reasoning: rawBaseline.route.reasoning } : {}),
  } } : undefined
  const actual = activities
    .map((interaction) => ({ interaction, route: config.effective?.interactions[interaction.id]?.specialists?.[roleId] }))
    .filter((item): item is { interaction: Interaction; route: EffectiveRoute } => Boolean(item.route))
  const actualModels = actual.map((item) => item.route.route?.model).filter((value): value is string => Boolean(value))
  const actualReasoning = actual.map((item) => item.route.route?.reasoning).filter((value): value is Reasoning => Boolean(value))
  const inheritedModel = baseline?.route?.model ?? uniform(actualModels)
  const inheritedReasoning = baseline?.route?.reasoning ?? uniform(actualReasoning)
  const modelMixed = !own?.model && !baseline?.route?.model && actualModels.length > 1 && !uniform(actualModels)
  const reasoningMixed = !own?.reasoning && !baseline?.route?.reasoning && actualReasoning.length > 1 && !uniform(actualReasoning)
  const valueModel = own?.model ?? inheritedModel ?? ''
  const valueReasoning = own?.reasoning ?? inheritedReasoning
  const globalDocument = scope === 'project' ? config.scopes.global.document ?? emptyPreferences() : emptyPreferences()
  const exceptionActivities = activities
    .filter((interaction) => Boolean(getOwnRoute(document, interaction.id, roleId) || getOwnRoute(globalDocument, interaction.id, roleId)))
    .map((interaction) => interaction.id)
  const actualDiffers = actual.some(({ route }) =>
    (baseline?.route?.model !== undefined && route.route?.model !== baseline.route.model) ||
    (baseline?.route?.reasoning !== undefined && JSON.stringify(route.route?.reasoning) !== JSON.stringify(baseline.route.reasoning)))

  return {
    roleId,
    activities,
    own,
    baseline,
    actual,
    actualModels,
    actualReasoning,
    inheritedModel,
    inheritedReasoning,
    modelMixed,
    reasoningMixed,
    valueModel,
    valueReasoning,
    exceptionActivities,
    actualDiffers,
    hasDifferences: modelMixed || reasoningMixed || actualDiffers,
  }
}
