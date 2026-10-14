import type { ConfigResponse, Interaction, Preferences } from './types'

// Native routes run through the host's own subagent mechanism; only they take specialist routes.
export const isNative = (interaction?: Interaction): boolean => interaction?.execution === 'native'

// These are editor suggestions, not restrictions on the resolver's supported roles.
const scenarioRoles: Record<string, string[]> = {
  planning: ['clanker-architect', 'clanker-backend-developer', 'clanker-data-engineer', 'clanker-devops-engineer', 'clanker-performance-engineer', 'clanker-qa-engineer', 'clanker-ui-developer'],
  implementation: ['clanker-backend-developer', 'clanker-data-engineer', 'clanker-devops-engineer', 'clanker-performance-engineer', 'clanker-test-engineer', 'clanker-ui-developer'],
  'native-review': ['clanker-architect', 'clanker-backend-developer', 'clanker-code-review', 'clanker-data-engineer', 'clanker-devops-engineer', 'clanker-performance-engineer', 'clanker-test-engineer', 'clanker-ui-developer'],
  'visual-review': ['clanker-ui-developer', 'clanker-ui-ux-reviewer'],
}

export function specialistChoices(config: ConfigResponse, document: Preferences, interaction: string) {
  if (!isNative(config.bundle.interactions.find((item) => item.id === interaction))) return []
  const applicable = scenarioRoles[interaction]
  const documents = [config.bundle.defaults, document]
  const configured = new Set(documents.flatMap((item) => Object.keys(item?.interactions?.[interaction]?.specialists ?? {})))
  return config.bundle.roles.filter((role) => !applicable || applicable.includes(role.id) || configured.has(role.id))
    .map((role) => ({ ...role, label: applicable && !applicable.includes(role.id) ? `${role.label} (existing override)` : role.label }))
}
