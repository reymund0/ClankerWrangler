import type { AgentRoute, Preferences, Reasoning, Route } from './types'

export const emptyPreferences = (): Preferences => ({ schema_version: 1 })
export const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T

function routeAt(document: Preferences, interaction: string, role?: string, create = false): Route | undefined {
  if (!document.interactions && create) document.interactions = {}
  let route = document.interactions?.[interaction]
  if (!route && create) route = document.interactions![interaction] = {}
  if (!role) return route
  if (!route?.specialists && create) route!.specialists = {}
  let specialist = route?.specialists?.[role]
  if (!specialist && create) specialist = route!.specialists![role] = {}
  return specialist
}

function cleanup(document: Preferences, interaction: string, role?: string): void {
  const interactionRoute = document.interactions?.[interaction]
  if (role && interactionRoute?.specialists && Object.keys(interactionRoute.specialists[role] ?? {}).length === 0) delete interactionRoute.specialists[role]
  if (interactionRoute?.specialists && Object.keys(interactionRoute.specialists).length === 0) delete interactionRoute.specialists
  if (interactionRoute && Object.keys(interactionRoute).length === 0) delete document.interactions![interaction]
  if (document.interactions && Object.keys(document.interactions).length === 0) delete document.interactions
}

function cleanupAgent(document: Preferences, role: string): void {
  if (document.agents?.[role] && Object.keys(document.agents[role]).length === 0) delete document.agents[role]
  if (document.agents && Object.keys(document.agents).length === 0) delete document.agents
}

export function updateRoute(document: Preferences, interaction: string, role: string | undefined, update: Partial<Route>): Preferences {
  const next = clone(document)
  Object.assign(routeAt(next, interaction, role, true)!, update)
  return next
}

export function resetRoute(document: Preferences, interaction: string, role?: string): Preferences {
  const next = clone(document)
  if (role) {
    if (next.interactions?.[interaction]?.specialists) delete next.interactions[interaction].specialists![role]
  } else if (next.interactions) delete next.interactions[interaction]
  cleanup(next, interaction, role)
  return next
}

export function resetField(document: Preferences, interaction: string, role: string | undefined, field: 'model' | 'reasoning'): Preferences {
  const next = clone(document)
  const route = routeAt(next, interaction, role)
  if (route) delete route[field]
  cleanup(next, interaction, role)
  return next
}

export function getOwnRoute(document: Preferences, interaction: string, role?: string): Route | undefined {
  return routeAt(document, interaction, role)
}

export function getOwnAgentRoute(document: Preferences, role: string): AgentRoute | undefined {
  return document.agents?.[role]
}

export function updateAgentRoute(document: Preferences, role: string, update: Partial<AgentRoute>): Preferences {
  const next = clone(document)
  if (!next.agents) next.agents = {}
  Object.assign(next.agents[role] ??= {}, update)
  return next
}

export function resetAgentRoute(document: Preferences, role: string): Preferences {
  const next = clone(document)
  if (next.agents) delete next.agents[role]
  cleanupAgent(next, role)
  return next
}

export function resetAgentField(document: Preferences, role: string, field: 'model' | 'reasoning'): Preferences {
  const next = clone(document)
  if (next.agents?.[role]) delete next.agents[role][field]
  cleanupAgent(next, role)
  return next
}

export function reasoningFor(mode: 'fixed' | 'adaptive', current: Reasoning | undefined, effort?: string): Reasoning {
  if (mode === 'fixed') return { mode, effort: effort || (current?.mode === 'fixed' ? current.effort : '') }
  return { mode, ...(effort ? { max_effort: effort } : {}) }
}
