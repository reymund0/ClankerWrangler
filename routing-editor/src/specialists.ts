import type { ConfigResponse, Preferences, Scope } from './types'

// These are editor suggestions, not restrictions on the resolver's supported roles.
const scenarioRoles: Record<string, string[]> = {
  planning: ['clanker-architect', 'clanker-backend-developer', 'clanker-data-engineer', 'clanker-devops-engineer', 'clanker-documentation-writer', 'clanker-performance-engineer', 'clanker-product-engineer', 'clanker-qa-engineer', 'clanker-ui-developer', 'clanker-ux-designer'],
  implementation: ['clanker-backend-developer', 'clanker-data-engineer', 'clanker-devops-engineer', 'clanker-documentation-writer', 'clanker-performance-engineer', 'clanker-test-engineer', 'clanker-ui-developer'],
  'native-review': ['clanker-architect', 'clanker-backend-developer', 'clanker-code-review', 'clanker-data-engineer', 'clanker-devops-engineer', 'clanker-performance-engineer', 'clanker-test-engineer', 'clanker-ui-developer'],
  'visual-review': ['clanker-product-engineer', 'clanker-ui-developer', 'clanker-ui-ux-reviewer', 'clanker-ux-designer'],
}

export function specialistChoices(config: ConfigResponse, document: Preferences, scope: Scope, interaction: string) {
  if (config.bundle.interactions.find((item) => item.id === interaction)?.provider !== 'codex') return []
  const applicable = scenarioRoles[interaction]
  const documents = [config.bundle.defaults, document, ...(scope === 'project' ? [config.scopes.global.document] : [])]
  const configured = new Set(documents.flatMap((item) => Object.keys(item?.interactions?.[interaction]?.specialists ?? {})))
  return config.bundle.roles.filter((role) => !applicable || applicable.includes(role.id) || configured.has(role.id))
    .map((role) => ({ ...role, label: applicable && !applicable.includes(role.id) ? `${role.label} (existing override)` : role.label }))
}
