export type Scope = 'global' | 'project'
export type Reasoning = { mode: 'fixed'; effort: string } | { mode: 'adaptive'; max_effort?: string }

export type Route = {
  model?: string
  reasoning?: Reasoning
  specialists?: Record<string, Route>
}

export type Preferences = {
  schema_version: 1
  agents?: Record<string, AgentRoute>
  interactions?: Record<string, Route>
  adaptive_profiles?: Record<string, AdaptiveProfile>
}

export type AgentRoute = {
  model?: string
  reasoning?: Reasoning
}

export type AdaptiveProfile = {
  tiers: Record<'mechanical' | 'routine' | 'complex' | 'exceptional', string>
  default_ceiling: string
}

export type Interaction = { id: string; label: string; provider: 'codex' | 'claude'; default_model: string }
export type Role = { id: string; label: string }
export type Model = { id: string; label: string; provider: 'codex' | 'claude'; efforts: string[] }

export type ProviderCatalogModel = {
  id: string
  label: string
  provider: 'codex' | 'claude'
  efforts: string[] | null
  default_effort: string | null
}

export type ProviderCatalog = {
  status: 'live' | 'cached' | 'stale' | 'unavailable'
  source: 'codex-cli' | 'claude-cli'
  cli_version: string | null
  updated_at: string | null
  error: string | null
  models: ProviderCatalogModel[]
}

export type ModelCatalogResponse = {
  providers: Record<'codex' | 'claude', ProviderCatalog>
}

export type Bundle = {
  schema_version: 1
  policy_version: string
  interactions: Interaction[]
  roles: Role[]
  models: Model[]
  effort_orders: Record<string, string[]>
  defaults: Preferences
}

export type EffectiveRoute = {
  route?: { model?: string; reasoning?: Reasoning }
  provenance?: { model?: string; reasoning?: string; profile?: string | null }
  ceiling?: string | null
  ceiling_source?: string | null
  specialists?: Record<string, EffectiveRoute>
}

export type ConfigScope = { path: string; revision: string; document: Preferences | null; error?: string }
export type ConfigResponse = {
  wrangler?: { available: boolean; running: boolean; reason?: string }
  schema_version: 1
  policy_version: string
  scopes: { global: ConfigScope; project: ConfigScope | null }
  bundle: Bundle
  effective: { agents?: Record<string, EffectiveRoute>; interactions: Record<string, EffectiveRoute>; profiles: Record<string, AdaptiveProfile> } | null
  error?: string
}

export type Decision = {
  model: string
  reasoning: Reasoning
  effort: string
  proposed_effort: string
  ceiling: string | null
  ceiling_source: string | null
  interaction: string
  role?: string
  tier: string
  reason: string
  limitations: string[]
  provenance: { model: string; reasoning: string; profile: string | null }
  capability_status: string
  dispatch_allowed: boolean
  account_status?: string
}
