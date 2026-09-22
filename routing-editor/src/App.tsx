import { WranglerPanel } from './WranglerPanel'
import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { api, ApiError } from './api'
import { specialistChoices } from './specialists'
import { clone, emptyPreferences, getOwnAgentRoute, getOwnRoute, reasoningFor, resetAgentField, resetAgentRoute, resetField, resetRoute, updateAgentRoute, updateRoute } from './draft'
import type { AdaptiveProfile, ConfigResponse, Decision, EffectiveRoute, ModelCatalogResponse, Preferences, Reasoning, Route, Scope } from './types'

const tiers = ['mechanical', 'routine', 'complex', 'exceptional'] as const
const risks = ['security', 'data-integrity', 'recovery', 'cross-layer', 'uncertainty', 'performance']

function effectiveRoute(config: ConfigResponse, interaction: string, role?: string): EffectiveRoute {
  const route = config.effective?.interactions[interaction] ?? {}
  return role ? route.specialists?.[role] ?? route : route
}

function sourceLabel(source?: string | null): string {
  if (!source) return 'Inherited from bundled defaults'
  if (source === 'bundle.defaults') return 'Inherited from bundled defaults'
  return source.replaceAll('_', ' ')
}

function documentFor(scope: Scope, config: ConfigResponse): Preferences {
  return clone(config.scopes[scope]?.document ?? emptyPreferences())
}

function errorsFor(error: unknown, fallback: string): Record<string, string> {
  const message = error instanceof Error ? error.message : 'The request could not be completed'
  const field = message.match(/((?:agents|interactions|adaptive_profiles)(?:\.[^.\s]+)+)(?=:\s|$)/)?.[1]
  return { [field ?? fallback]: message }
}

function errorFor(errors: Record<string, string>, path: string): string | undefined {
  return errors[path] ?? Object.entries(errors).find(([field]) => field.startsWith(`${path}.`))?.[1]
}

function FieldError({ error, id }: { error?: string; id: string }) {
  return error ? <p id={id} className="field-error" role="alert">{error}</p> : null
}
type Provider = 'codex' | 'claude'
type Choice = { id: string; label: string }

function isClaudeAlias(id: string): boolean {
  return /^(default|opus|sonnet|haiku)(?:$|[.:/_\[-])/.test(id)
}

function modelChoices(catalog: ModelCatalogResponse | null, provider: Provider): Choice[] {
  const choices = new Map<string, Choice>()
  for (const model of catalog?.providers[provider]?.models ?? []) {
    choices.set(model.id, { id: model.id, label: model.label })
  }
  return [...choices.values()]
}

function choiceLabel(choice: Choice, provider: Provider): string {
  const alias = provider === 'claude' && isClaudeAlias(choice.id) ? ' · alias; resolution may change' : ''
  return `${choice.label} (${choice.id}) · local CLI${alias}`
}

function effortChoices(config: ConfigResponse, catalog: ModelCatalogResponse | null, provider: Provider, model: string, selected: string) {
  const policy = config.bundle.effort_orders[provider] ?? []
  const discovered = catalog?.providers[provider]?.models.find((item) => item.id === model)
  const reported = discovered?.efforts ?? null
  const unknown = reported === null
  const allowed = unknown ? policy : policy.filter((effort) => reported.includes(effort))
  const options = allowed.map((value) => ({ value, label: value, disabled: false }))
  if (!unknown) for (const value of reported.filter((item) => !policy.includes(item) && item !== selected)) options.push({ value, label: `${value} (unavailable by routing policy)`, disabled: true })
  if (selected && !allowed.includes(selected)) options.push({ value: selected, label: `${selected} (saved; unavailable for new selection)`, disabled: false })
  return { options, note: unknown ? 'Effort metadata is unverified; policy choices are shown.' : null, empty: false }
}

function ModelPicker({ catalog, provider, value, onChange, describedBy, allowEmpty = false, emptyLabel = 'Inherited model unresolved' }: {
  catalog: ModelCatalogResponse | null
  provider: Provider
  value: string
  onChange: (value: string) => void
  describedBy?: string
  allowEmpty?: boolean
  emptyLabel?: string
}) {
  const choices = modelChoices(catalog, provider)
  const currentUnavailable = Boolean(value) && !choices.some((choice) => choice.id === value)
  const emptyMessage = catalog ? `No models were reported by the local ${provider} CLI.` : 'Local CLI catalog is loading or unavailable.'
  return <span className="model-picker">
    <select aria-label="Model" aria-describedby={describedBy} value={value} onChange={(event) => onChange(event.target.value)}>
      {allowEmpty && <option value="">No override</option>}
      {currentUnavailable && <option value={value} disabled>{value} (unavailable — not reported by local {provider} CLI)</option>}
      {!allowEmpty && !value && <option value="" disabled>{emptyLabel}</option>}
      {choices.map((choice) => <option key={choice.id} value={choice.id}>{choiceLabel(choice, provider)}</option>)}
    </select>
    {choices.length === 0 && <span className="field-help">{emptyMessage}</span>}
  </span>
}


type RouteEditorProps = {
  config: ConfigResponse
  catalog: ModelCatalogResponse | null
  scope: Scope
  document: Preferences
  interaction: string
  role?: string
  errors: Record<string, string>
  onChange: (next: Preferences, changedPaths?: string[]) => void
}

function RouteEditor({ config, catalog, scope, document, interaction, role, errors, onChange }: RouteEditorProps) {
  const own = getOwnRoute(document, interaction, role)
  const effective = effectiveRoute(config, interaction, role)
  const route = effective.route ?? {}
  const provider = config.bundle.interactions.find((item) => item.id === interaction)?.provider ?? 'codex'
  const valueModel = own?.model ?? route.model ?? ''
  const valueReasoning: Reasoning = own?.reasoning ?? route.reasoning ?? { mode: 'adaptive' }
  const path = `interactions.${interaction}${role ? `.specialists.${role}` : ''}`
  const routeError = errors[path]
  const modelError = errorFor(errors, `${path}.model`)
  const reasoningError = errorFor(errors, `${path}.reasoning`)
  const adaptiveCeiling = valueReasoning.mode === 'adaptive' ? valueReasoning.max_effort ?? `Model profile default${effective.ceiling ? ` (${effective.ceiling})` : ''}` : null
  const selectedEffort = valueReasoning.mode === 'fixed' ? valueReasoning.effort : valueReasoning.max_effort ?? ''
  const effort = effortChoices(config, catalog, provider, valueModel, selectedEffort)
  const reset = (field: 'model' | 'reasoning') => onChange(resetField(document, interaction, role, field), [`${path}.${field}`])

  return <fieldset className="route-controls">
    <legend className="sr-only">{role ? `${role} override` : 'Route settings'}</legend>
    <label>
      Model
      <ModelPicker catalog={catalog} provider={provider} value={valueModel}
        describedBy={`${path}-model-help ${path}-model-error${routeError ? ` ${path}-route-error` : ''}`}

        onChange={(model) => onChange(updateRoute(document, interaction, role, { model }), [`${path}.model`])} />
      <span id={`${path}-model-help`} className="field-help">{sourceLabel(own?.model ? 'this scope' : effective.provenance?.model)}</span>
      <FieldError id={`${path}-model-error`} error={modelError} />
      <FieldError id={`${path}-route-error`} error={routeError} />
    </label>
    <button type="button" className="text-button" onClick={() => reset('model')} disabled={!own?.model}>Reset model</button>
    <label>
      Reasoning mode
      <select value={valueReasoning.mode} aria-describedby={`${path}-reasoning-error${routeError ? ` ${path}-route-error` : ''}`} onChange={(event) => onChange(updateRoute(document, interaction, role, { reasoning: reasoningFor(event.target.value as 'fixed' | 'adaptive', valueReasoning) }), [`${path}.reasoning`])}>
        <option value="adaptive">Adaptive</option>
        <option value="fixed">Fixed</option>
      </select>
      <span className="field-help">{sourceLabel(own?.reasoning ? 'this scope' : effective.provenance?.reasoning)}</span>
    </label>
    <label>
      {valueReasoning.mode === 'fixed' ? 'Effort' : 'Adaptive maximum'}
      <select value={selectedEffort}
        aria-describedby={`${path}-reasoning-error${routeError ? ` ${path}-route-error` : ''}`}
        onChange={(event) => onChange(updateRoute(document, interaction, role, { reasoning: reasoningFor(valueReasoning.mode, valueReasoning, event.target.value) }), [`${path}.reasoning`])}>
        {valueReasoning.mode === 'adaptive' ? <option value="">{valueReasoning.mode === 'adaptive' && valueReasoning.max_effort ? 'Model profile default' : adaptiveCeiling}</option> : <option value="" disabled>Choose effort</option>}
        {effort.options.map((item) => <option value={item.value} key={item.value} disabled={item.disabled}>{item.label}</option>)}
      </select>
      {effort.note && <span className="field-help">{effort.note}</span>}
      {adaptiveCeiling && <span className="field-help">Adaptive ceiling: {adaptiveCeiling} · {sourceLabel(effective.ceiling_source)}</span>}
      <FieldError id={`${path}-reasoning-error`} error={reasoningError} />
    </label>
    <button type="button" className="text-button" onClick={() => reset('reasoning')} disabled={!own?.reasoning}>Reset reasoning</button>
  </fieldset>
}

function InteractionCard({ config, catalog, scope, document, interaction, errors, onChange, showSpecialists = true }: Omit<RouteEditorProps, 'interaction' | 'role'> & { interaction: ConfigResponse['bundle']['interactions'][number]; showSpecialists?: boolean }) {
  const [expanded, setExpanded] = useState(false)
  const specialists = showSpecialists ? specialistChoices(config, document, scope, interaction.id) : []
  const own = getOwnRoute(document, interaction.id)
  useEffect(() => { if (showSpecialists && Object.keys(errors).some((field) => field.startsWith(`interactions.${interaction.id}.specialists.`))) setExpanded(true) }, [errors, interaction.id, showSpecialists])
  return <article className="interaction-card">
    <header><div><h3>{interaction.label}</h3><p>{interaction.id === 'claude-review' ? 'One cross-review route, even when a packet contains several specialties.' : 'Route for this work type.'}</p></div><span className="badge">{interaction.provider}</span></header>
    <RouteEditor config={config} catalog={catalog} scope={scope} document={document} interaction={interaction.id} errors={errors} onChange={onChange} />
    <div className="card-actions"><button type="button" className="text-button" onClick={() => onChange(resetRoute(document, interaction.id), [`interactions.${interaction.id}`])} disabled={!own}>Reset route to inherited</button>
      {specialists.length > 0 && <button type="button" className="text-button" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>{expanded ? 'Hide' : 'Show'} specialist overrides</button>}
    </div>
    {expanded && <div className="specialists"><p>Optional overrides apply only to this interaction. Empty overrides inherit the interaction route.</p>
      {specialists.map((role) => <section className="specialist" key={role.id}><h4>{role.label}</h4><RouteEditor config={config} catalog={catalog} scope={scope} document={document} interaction={interaction.id} role={role.id} errors={errors} onChange={onChange} /><button type="button" className="text-button" onClick={() => onChange(resetRoute(document, interaction.id, role.id), [`interactions.${interaction.id}.specialists.${role.id}`])} disabled={!getOwnRoute(document, interaction.id, role.id)}>Reset specialist override</button></section>)}
    </div>}
  </article>
}


function actualActivityRoutes(config: ConfigResponse, role: string, activities: ConfigResponse['bundle']['interactions']) {
  return activities
    .map((interaction) => ({ interaction, route: config.effective?.interactions[interaction.id]?.specialists?.[role] }))
    .filter((item): item is { interaction: ConfigResponse['bundle']['interactions'][number]; route: EffectiveRoute } => Boolean(item.route))
}

function uniform<T>(values: T[]): T | undefined {
  if (values.length === 0) return undefined
  const serialized = JSON.stringify(values[0])
  return values.every((value) => JSON.stringify(value) === serialized) ? values[0] : undefined
}

function mixedEffortChoices(config: ConfigResponse, catalog: ModelCatalogResponse | null, provider: Provider, models: string[], selected: string) {
  const policy = config.bundle.effort_orders[provider] ?? []
  const metadata = [...new Set(models.filter(Boolean))].map((model) => catalog?.providers[provider]?.models.find((item) => item.id === model)?.efforts ?? null)
  const known = metadata.filter((efforts): efforts is string[] => efforts !== null)
  const allowed = known.length === 0 ? policy : policy.filter((effort) => known.every((efforts) => efforts.includes(effort)))
  const options = allowed.map((value) => ({ value, label: value, disabled: false }))
  if (selected && !allowed.includes(selected)) options.push({ value: selected, label: `${selected} (saved; unavailable for new selection)`, disabled: false })
  const unknown = metadata.some((efforts) => efforts === null)
  const note = unknown
    ? known.length === 0 ? 'Effort metadata is unverified for all activities; policy choices are shown.' : 'Effort metadata is unverified for some activities; known activity limits are enforced.'
    : null
  return { options, note, empty: known.length > 0 && allowed.length === 0 }
}

function ActivityOverride({ config, catalog, scope, document, interaction, role, errors, onChange }: RouteEditorProps & { role: string }) {
  const own = getOwnRoute(document, interaction, role)
  const path = `interactions.${interaction}.specialists.${role}`
  return <section className="specialist">
    <h4>{config.bundle.interactions.find((item) => item.id === interaction)?.label}</h4>
    <RouteEditor config={config} catalog={catalog} scope={scope} document={document} interaction={interaction} role={role} errors={errors} onChange={onChange} />
    <button type="button" className="text-button" onClick={() => onChange(resetRoute(document, interaction, role), [path])} disabled={!own}>Reset activity exception</button>
  </section>
}

function AgentCard({ config, catalog, scope, document, role, errors, onChange }: Omit<RouteEditorProps, 'interaction' | 'role'> & { role: ConfigResponse['bundle']['roles'][number] }) {
  const [customize, setCustomize] = useState(false)
  const own = getOwnAgentRoute(document, role.id)
  const [adaptiveOpen, setAdaptiveOpen] = useState(false)
  const activities = config.bundle.interactions.filter((interaction) =>
    interaction.provider === 'codex' && specialistChoices(config, document, scope, interaction.id).some((candidate) => candidate.id === role.id))
  const rawBaseline = config.effective?.agents?.[role.id]
  const baseline = rawBaseline ? { ...rawBaseline, route: {
    ...(rawBaseline.route?.model && !(rawBaseline.provenance?.model?.startsWith(`${scope}.agents.`) && !own?.model) ? { model: rawBaseline.route.model } : {}),
    ...(rawBaseline.route?.reasoning && !(rawBaseline.provenance?.reasoning?.startsWith(`${scope}.agents.`) && !own?.reasoning) ? { reasoning: rawBaseline.route.reasoning } : {}),
  } } : undefined
  const actual = actualActivityRoutes(config, role.id, activities)
  const actualModels = actual.map((item) => item.route.route?.model).filter((value): value is string => Boolean(value))
  const actualReasoning = actual.map((item) => item.route.route?.reasoning).filter((value): value is Reasoning => Boolean(value))
  const inheritedModel = baseline?.route?.model ?? uniform(actualModels)
  const inheritedReasoning = baseline?.route?.reasoning ?? uniform(actualReasoning)
  const modelMixed = !own?.model && !baseline?.route?.model && actualModels.length > 1 && !uniform(actualModels)
  const reasoningMixed = !own?.reasoning && !baseline?.route?.reasoning && actualReasoning.length > 1 && !uniform(actualReasoning)
  const valueModel = own?.model ?? inheritedModel ?? ''
  const valueReasoning = own?.reasoning ?? inheritedReasoning
  const provider: Provider = 'codex'
  const path = `agents.${role.id}`
  const routeError = errors[path]
  const modelError = errorFor(errors, `${path}.model`)
  const reasoningError = errorFor(errors, `${path}.reasoning`)
  const selectedEffort = valueReasoning?.mode === 'fixed' ? valueReasoning.effort : valueReasoning?.mode === 'adaptive' ? valueReasoning.max_effort ?? '' : ''
  const effort = modelMixed && !own?.model
    ? mixedEffortChoices(config, catalog, provider, actualModels, selectedEffort)
    : effortChoices(config, catalog, provider, valueModel, selectedEffort)
  const inheritedExceptions = scope === 'project' ? config.scopes.global.document : undefined
  const exceptionActivities = activities.filter((interaction) => Boolean(getOwnRoute(document, interaction.id, role.id) || getOwnRoute(inheritedExceptions ?? emptyPreferences(), interaction.id, role.id)))
  const actualDiffers = actual.some(({ route }) =>
    (baseline?.route?.model !== undefined && route.route?.model !== baseline.route.model) ||
    (baseline?.route?.reasoning !== undefined && JSON.stringify(route.route?.reasoning) !== JSON.stringify(baseline.route.reasoning)))
  const hasDifferences = modelMixed || reasoningMixed || actualDiffers
  useEffect(() => {
    if (reasoningError) setAdaptiveOpen(true)
    if (Object.keys(errors).some((field) => field.startsWith('interactions.') && field.includes(`.specialists.${role.id}`))) setCustomize(true)
  }, [errors, reasoningError, role.id])
  const update = (change: Partial<import('./types').AgentRoute>, field: 'model' | 'reasoning') =>
    onChange(updateAgentRoute(document, role.id, change), [`${path}.${field}`])
  return <article className="interaction-card agent-card">
    <header><div><h3>{role.label}</h3><p>Default route for this native specialist. Activity exceptions remain separate.</p></div><span className="badge">codex</span></header>
    <fieldset className="route-controls">
      <legend className="sr-only">{role.label} agent default</legend>
      <label>
        Model
        <ModelPicker catalog={catalog} provider={provider} value={valueModel} emptyLabel={modelMixed ? 'Varies by activity — choose a default' : 'Inherited model unresolved'}
          describedBy={`${path}-model-help ${path}-model-error${routeError ? ` ${path}-route-error` : ''}`}
          onChange={(model) => update({ model }, 'model')} />
        <span id={`${path}-model-help`} className="field-help">{modelMixed ? 'Varies by activity. Choose a default to replace only this field.' : own?.model ? sourceLabel('this scope') : baseline?.route?.model ? sourceLabel(baseline.provenance?.model) : inheritedModel ? 'Derived from activity routes' : sourceLabel()}</span>
        <FieldError id={`${path}-model-error`} error={modelError} />
        <FieldError id={`${path}-route-error`} error={routeError} />
      </label>
      <button type="button" className="text-button" onClick={() => onChange(resetAgentField(document, role.id, 'model'), [`${path}.model`])} disabled={!own?.model}>Reset model</button>
      <label>
        Reasoning mode
        <select value={valueReasoning?.mode ?? ''} aria-describedby={`${path}-reasoning-error${routeError ? ` ${path}-route-error` : ''}`}
          onChange={(event) => update({ reasoning: reasoningFor(event.target.value as 'fixed' | 'adaptive', valueReasoning) }, 'reasoning')}>
          {reasoningMixed && <option value="" disabled>Varies by activity — choose a mode</option>}
          {!valueReasoning && !reasoningMixed && <option value="" disabled>Inherited reasoning unresolved</option>}
          <option value="adaptive">Adaptive</option><option value="fixed">Fixed</option>
        </select>
        <span className="field-help">{reasoningMixed ? 'Varies by activity. Choose a mode to create a sparse agent default.' : own?.reasoning ? sourceLabel('this scope') : baseline?.route?.reasoning ? sourceLabel(baseline.provenance?.reasoning) : inheritedReasoning ? 'Derived from activity routes' : sourceLabel()}</span>
      </label>
      <button type="button" className="text-button" onClick={() => onChange(resetAgentField(document, role.id, 'reasoning'), [`${path}.reasoning`])} disabled={!own?.reasoning}>Reset reasoning</button>
      {valueReasoning?.mode === 'fixed' && <label className="agent-effort">
        Effort
        <select value={selectedEffort} aria-describedby={`${path}-reasoning-error`} onChange={(event) => update({ reasoning: reasoningFor('fixed', valueReasoning, event.target.value) }, 'reasoning')}>
          <option value="" disabled>{effort.empty ? 'Choose a default model or activity-specific reasoning' : 'Choose effort'}</option>
          {effort.options.map((item) => <option value={item.value} key={item.value} disabled={item.disabled}>{item.label}</option>)}
        </select>
        {effort.note && <span className="field-help">{effort.note}</span>}
        {effort.empty && <span className="field-help">No common known effort is available. Choose a main model or customize activity reasoning.</span>}
      </label>}
    </fieldset>
    <FieldError id={`${path}-reasoning-error`} error={reasoningError} />
    {valueReasoning?.mode === 'adaptive' && <details className="adaptive-details" open={adaptiveOpen} onToggle={(event) => setAdaptiveOpen((event.target as HTMLDetailsElement).open)}><summary>Adaptive maximum</summary><label>Maximum<select value={valueReasoning.max_effort ?? ''} aria-describedby={`${path}-reasoning-error`} onChange={(event) => update({ reasoning: reasoningFor('adaptive', valueReasoning, event.target.value) }, 'reasoning')}><option value="">Model profile default</option>{effort.options.map((item) => <option value={item.value} key={item.value} disabled={item.disabled}>{item.label}</option>)}</select>{effort.note && <span className="field-help">{effort.note}</span>}</label></details>}
    <div className="card-actions"><button type="button" className="text-button" onClick={() => onChange(resetAgentRoute(document, role.id), [path])} disabled={!own}>Reset agent default</button>
      <button type="button" className="text-button" aria-expanded={customize} onClick={() => setCustomize(!customize)}>{customize ? 'Hide' : 'Customize'} by activity</button>
      {(exceptionActivities.length > 0 || hasDifferences) && <span className="exception-note">{exceptionActivities.length > 0 ? `${exceptionActivities.length} activity exception${exceptionActivities.length === 1 ? '' : 's'}` : 'Activity values differ'}</span>}
    </div>
    {customize && <div className="specialists"><p>Activity-specific routes override this default. Existing exceptions are retained when this default changes.</p>{activities.map((interaction) => <ActivityOverride key={interaction.id} config={config} catalog={catalog} scope={scope} document={document} interaction={interaction.id} role={role.id} errors={errors} onChange={onChange} />)}</div>}
  </article>
}

function AdvancedActivityDefaults({ config, catalog, scope, document, errors, onChange }: Omit<RouteEditorProps, 'interaction' | 'role'>) {
  const [open, setOpen] = useState(false)
  useEffect(() => {
    if (Object.keys(errors).some((field) => field.startsWith('interactions.') && !field.includes('.specialists.'))) setOpen(true)
  }, [errors])
  return <section className="advanced">
    <button type="button" className="secondary" aria-expanded={open} onClick={() => setOpen(!open)}>{open ? 'Hide' : 'Show'} advanced activity defaults</button>
    {open && <div><p>Set shared model and reasoning defaults for each activity. Specialists inherit these defaults unless overridden by agent settings or activity-specific customization.</p><div className="interaction-grid advanced-grid">{config.bundle.interactions.filter((interaction) => interaction.provider === 'codex').map((interaction) => <InteractionCard key={interaction.id} config={config} catalog={catalog} scope={scope} document={document} interaction={interaction} errors={errors} onChange={onChange} showSpecialists={false} />)}</div></div>}
  </section>
}
function Preview({ config, catalog, scope, document, onError, onSuccess }: { config: ConfigResponse; catalog: ModelCatalogResponse | null; scope: Scope; document: Preferences; onError: (error: unknown) => void; onSuccess: () => void }) {
  const [interaction, setInteraction] = useState(config.bundle.interactions.some((item) => item.id === 'implementation') ? 'implementation' : config.bundle.interactions[0]?.id ?? '')
  const [role, setRole] = useState('')
  const [tier, setTier] = useState<typeof tiers[number]>('routine')
  const [reason, setReason] = useState('Preview a saved routing choice')
  const [selectedRisks, setSelectedRisks] = useState<string[]>([])
  const [sessionModel, setSessionModel] = useState('')
  const [sessionMode, setSessionMode] = useState<'adaptive' | 'fixed'>('adaptive')
  const [sessionEffort, setSessionEffort] = useState('')
  const [decision, setDecision] = useState<Decision | null>(null)
  const [busy, setBusy] = useState(false)
  const requestVersion = useRef(0)
  useEffect(() => { requestVersion.current += 1; setDecision(null); setBusy(false); onSuccess() }, [document, interaction, role, tier, reason, selectedRisks, sessionModel, sessionMode, sessionEffort])
  const selected = config.bundle.interactions.find((item) => item.id === interaction) ?? config.bundle.interactions[0]
  const selectedProvider = selected?.provider ?? 'codex'
  const specialists = specialistChoices(config, document, scope, interaction)
  useEffect(() => { if (role && !specialists.some((item) => item.id === role)) setRole('') }, [role, specialists])
  const specialistModel = role ? getOwnRoute(document, interaction, role)?.model : undefined
  const interactionModel = getOwnRoute(document, interaction)?.model
  const configuredModel = specialistModel ?? interactionModel ?? effectiveRoute(config, interaction, role).route?.model ?? selected?.default_model ?? ''
  const sessionEfforts = effortChoices(config, catalog, selectedProvider, sessionModel || configuredModel, sessionEffort)
  const runPreview = async (event: FormEvent) => {
    event.preventDefault()
    const version = ++requestVersion.current
    setBusy(true)
    const session_override = sessionModel || sessionEffort ? { ...(sessionModel ? { model: sessionModel } : {}), ...(sessionEffort ? { reasoning: reasoningFor(sessionMode, undefined, sessionEffort) } : {}) } : undefined
    try {
      const response = await api.preview(scope, document, { interaction, ...(role ? { role } : {}), tier, risk_flags: selectedRisks, reason, ...(session_override ? { session_override } : {}) })
      if (version === requestVersion.current) { setDecision(response.decision); onSuccess() }
    } catch (error) {
      if (version === requestVersion.current) { setDecision(null); onError(error) }
    } finally {
      if (version === requestVersion.current) setBusy(false)
    }
  }
  const setRisk = (value: string, checked: boolean) => setSelectedRisks((current) => checked ? [...current, value] : current.filter((item) => item !== value))
  return <section className="preview-panel" aria-labelledby="preview-title"><div><p className="eyebrow">Draft preview</p><h2 id="preview-title">Preview model and reasoning</h2><p>Uses this {scope} draft. Runtime model availability is never inferred from the catalog.</p></div>
    <form onSubmit={runPreview} className="preview-form">
      <label>Activity<select value={interaction} onChange={(event) => { setInteraction(event.target.value); setRole('') }}>{config.bundle.interactions.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
      {selectedProvider === 'codex' && <label>Agent (optional)<select value={role} onChange={(event) => setRole(event.target.value)}><option value="">Activity route</option>{specialists.map((item) => <option value={item.id} key={item.id}>{item.label}</option>)}</select></label>}
      <label>Task tier<select value={tier} onChange={(event) => setTier(event.target.value as typeof tier)}>{tiers.map((item) => <option value={item} key={item}>{item}</option>)}</select></label>
      <label className="wide">Reason<input required value={reason} onChange={(event) => setReason(event.target.value)} /></label>
      <fieldset className="risk-fieldset"><legend>Risk flags</legend>{risks.map((item) => <label key={item}><input type="checkbox" checked={selectedRisks.includes(item)} onChange={(event) => setRisk(item, event.target.checked)} />{item}</label>)}</fieldset>
      <fieldset className="session-fieldset"><legend>Temporary session override</legend><p>Applies only to this preview and is never saved.</p><label>Model<ModelPicker catalog={catalog} provider={selectedProvider} value={sessionModel} onChange={setSessionModel} allowEmpty /></label>{sessionModel && <button type="button" className="text-button" onClick={() => setSessionModel('')}>Reset session model</button>}<label>Mode<select value={sessionMode} onChange={(event) => setSessionMode(event.target.value as 'adaptive' | 'fixed')}><option value="adaptive">Adaptive</option><option value="fixed">Fixed</option></select></label><label>{sessionMode === 'fixed' ? 'Effort' : 'Maximum'}<select value={sessionEffort} onChange={(event) => setSessionEffort(event.target.value)}><option value="">No override</option>{sessionEfforts.options.map((item) => <option key={item.value} value={item.value} disabled={item.disabled}>{item.label}</option>)}</select>{sessionEfforts.note && <span className="field-help">{sessionEfforts.note}</span>}</label></fieldset>
      <button className="primary" disabled={busy}>{busy ? 'Previewing…' : 'Preview route'}</button>
    </form>
    {decision && <div className="decision" aria-live="polite"><h3>Predicted route</h3><dl><div><dt>Model</dt><dd>{decision.model}</dd></div><div><dt>Requested effort</dt><dd>{decision.effort}</dd></div><div><dt>Proposed effort</dt><dd>{decision.proposed_effort}</dd></div><div><dt>Ceiling</dt><dd>{decision.ceiling ?? 'None'}</dd></div><div><dt>Capability</dt><dd>{decision.capability_status}</dd></div></dl><p>{decision.reason}</p><p className="field-help">Model: {sourceLabel(decision.provenance.model)} · Reasoning: {sourceLabel(decision.provenance.reasoning)} · Profile: {sourceLabel(decision.provenance.profile)}</p>{decision.limitations.length > 0 && <ul>{decision.limitations.map((item) => <li key={item}>{item}</li>)}</ul>}</div>}
  </section>
}

function AdvancedProfiles({ config, catalog, document, errors, onChange }: { config: ConfigResponse; catalog: ModelCatalogResponse | null; document: Preferences; errors: Record<string, string>; onChange: (draft: Preferences, changedPaths?: string[]) => void }) {
  const [open, setOpen] = useState(false)
  const profiles = document.adaptive_profiles ?? {}
  const [model, setModel] = useState('')
  const [provider, setProvider] = useState<Provider>('codex')
  const availableModels = modelChoices(catalog, provider)
  useEffect(() => { if (Object.keys(errors).some((field) => field.startsWith('adaptive_profiles'))) setOpen(true) }, [errors])
  useEffect(() => { if (!availableModels.some((item) => item.id === model)) setModel('') }, [availableModels, model])
  const createProfile = () => {
    if (!model) return
    const key = `${provider}:${model}`
    const inherited = config.effective?.profiles[key]
    const fallback: AdaptiveProfile = inherited ?? { tiers: { mechanical: 'low', routine: 'medium', complex: 'high', exceptional: 'xhigh' }, default_ceiling: 'xhigh' }
    onChange({ ...clone(document), adaptive_profiles: { ...profiles, [key]: clone(fallback) } }, [`adaptive_profiles.${key}`]); setModel('')
  }
  const modify = (key: string, path: keyof AdaptiveProfile | `tiers.${typeof tiers[number]}`, value: string) => {
    const profile = clone(profiles[key])
    if (path === 'default_ceiling') profile.default_ceiling = value
    else profile.tiers[path.slice(6) as typeof tiers[number]] = value
    onChange({ ...clone(document), adaptive_profiles: { ...profiles, [key]: profile } }, [`adaptive_profiles.${key}.${path}`])
  }
  return <section className="advanced"><button type="button" className="secondary" aria-expanded={open} onClick={() => setOpen(!open)}>{open ? 'Hide' : 'Show'} advanced Adaptive profiles</button>{open && <div><p>Adaptive mappings are user-editable policy. Select a locally reported model to customize its profile.</p><div className="add-profile"><label>Provider<select value={provider} onChange={(event) => { setProvider(event.target.value as Provider); setModel('') }}><option value="codex">Codex</option><option value="claude">Claude</option></select></label><label>Model<select value={model} onChange={(event) => setModel(event.target.value)} disabled={availableModels.length === 0}><option value="">Select locally reported model</option>{availableModels.map((item) => <option value={item.id} key={item.id}>{choiceLabel(item, provider)}</option>)}</select></label><button type="button" className="secondary" onClick={createProfile} disabled={!model}>Add profile</button></div>{availableModels.length === 0 && <p className="field-help">No models were reported by the local {provider} CLI.</p>}{Object.entries(profiles).length === 0 && <p className="empty">No override profiles in this scope. Select a locally reported model to customize one.</p>}{Object.entries(profiles).map(([key, profile]) => {
      const path = `adaptive_profiles.${key}`
      const profileError = errorFor(errors, path)
      const separator = key.indexOf(':')
      const profileProvider = key.slice(0, separator) as Provider
      const profileModel = key.slice(separator + 1)
      const fields = [...tiers.map((tier) => ({ label: tier, field: `tiers.${tier}` as const, value: profile.tiers[tier] })), { label: 'Default ceiling', field: 'default_ceiling' as const, value: profile.default_ceiling }]
      return <section key={key} className="profile" aria-describedby={profileError ? `${path}-error` : undefined}>
        <header><h3>{key}</h3><button type="button" className="text-button" onClick={() => { const next = clone(document); delete next.adaptive_profiles![key]; if (Object.keys(next.adaptive_profiles!).length === 0) delete next.adaptive_profiles; onChange(next, [path]) }}>Reset profile</button></header>
        <FieldError id={`${path}-error`} error={profileError} />
        {fields.map(({ label, field, value }) => {
          const fieldPath = `${path}.${field}`
          const fieldError = errorFor(errors, fieldPath) ?? (field.startsWith('tiers.') ? errorFor(errors, `${path}.tiers`) : undefined)
          const effort = effortChoices(config, catalog, profileProvider, profileModel, value)
          return <label key={field}>{label}<select value={value} aria-describedby={fieldError ? `${fieldPath}-error` : undefined} onChange={(event) => modify(key, field, event.target.value)}>
            {effort.options.map((item) => <option key={item.value} value={item.value} disabled={item.disabled}>{item.label}</option>)}
          </select>{effort.note && <span className="field-help">{effort.note}</span>}<FieldError id={`${fieldPath}-error`} error={fieldError} /></label>
        })}
      </section>
    })}</div>}</section>
}


function CatalogStatusPanel({ catalog, loading, error, onRefresh }: { catalog: ModelCatalogResponse | null; loading: boolean; error: string; onRefresh: () => void }) {
  return <section className="catalog-status" aria-live="polite"><div><p className="eyebrow">Local model discovery</p><h2>CLI catalog</h2>{catalog ? <div className="catalog-providers">{(['codex', 'claude'] as const).map((provider) => {
    const item = catalog.providers[provider]
    return <p key={provider}><strong>{provider}</strong>: {item.status} via {item.source}{item.cli_version ? ` ${item.cli_version}` : ''}{item.updated_at ? ` · updated ${item.updated_at}` : ''}{item.error ? ` · ${item.error}` : ''}</p>
  })}</div> : <p>{error || 'Loading local CLI catalog…'}</p>}{catalog && error && <p className="field-error">{error}</p>}</div><button type="button" className="secondary" disabled={loading} onClick={onRefresh}>{loading ? 'Refreshing…' : 'Refresh models'}</button></section>
}

export function App() {
  const [config, setConfig] = useState<ConfigResponse | null>(null)
  const [catalog, setCatalog] = useState<ModelCatalogResponse | null>(null)
  const [catalogError, setCatalogError] = useState('')
  const [catalogLoading, setCatalogLoading] = useState(false)
  const [displayEffective, setDisplayEffective] = useState<ConfigResponse['effective']>(null)
  const [scope, setScope] = useState<Scope>('global')
  const [draft, setDraft] = useState<Preferences>(emptyPreferences())
  const [dirty, setDirty] = useState(false)
  const [persistentErrors, setErrors] = useState<Record<string, string>>({})
  const [previewErrors, setPreviewErrors] = useState<Record<string, string>>({})
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({})
  const errors = { ...validationErrors, ...previewErrors, ...persistentErrors }
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const draftVersion = useRef(0)
  const scopeRef = useRef(scope)
  const loadVersion = useRef(0)
  const catalogVersion = useRef(0)
  const clearPreviewError = () => setPreviewErrors({})
  const replaceSaveErrors = (error: unknown, message: string, includeFieldError: boolean) => setErrors((current) => {
    const preserved = Object.fromEntries(Object.entries(current).filter(([field]) => field !== 'save' && !field.startsWith('interactions.') && !field.startsWith('adaptive_profiles.')))
    return { ...preserved, ...(includeFieldError ? errorsFor(error, 'save') : {}), save: message }
  })
  const updateDraft = (next: Preferences, changedPaths: string[] = []) => {
    draftVersion.current += 1
    setDraft(next); setDirty(true); setNotice('')
    if (changedPaths.length > 0) setErrors((current) => Object.fromEntries(Object.entries(current).filter(([field]) => field !== 'save' && !changedPaths.some((path) => field === path || field.startsWith(`${path}.`) || path.startsWith(`${field}.`)))))
    setPreviewErrors({})
    if (changedPaths.length > 0) setValidationErrors((current) => Object.fromEntries(Object.entries(current).filter(([field]) => !changedPaths.some((path) => field === path || field.startsWith(`${path}.`) || path.startsWith(`${field}.`)))))
  }
  const load = async (): Promise<boolean> => {
    const version = ++loadVersion.current
    const versionAtStart = draftVersion.current
    const scopeAtStart = scopeRef.current
    setLoading(true); setDisplayEffective(null)
    try {
      const next = await api.config()
      if (version !== loadVersion.current) return false
      if (draftVersion.current !== versionAtStart || scopeRef.current !== scopeAtStart) return false
      setConfig(next)
      setDraft(documentFor(scopeAtStart, next)); setDirty(false); setErrors(next.error ? { load: next.error } : {}); setPreviewErrors({}); setValidationErrors({})
      return true
    } catch (error) {
      if (version === loadVersion.current) setErrors({ load: error instanceof Error ? error.message : 'Unable to load configuration' })
      return false
    } finally { if (version === loadVersion.current) setLoading(false) }
  }
  const loadCatalog = async (refresh = false) => {
    const version = ++catalogVersion.current
    setCatalogLoading(true)
    try {
      const next = await (refresh ? api.refreshModels() : api.models())
      if (version !== catalogVersion.current) return
      if (!next.providers?.codex || !next.providers?.claude) throw new Error('The local model catalog response was incomplete.')
      setCatalog(next); setCatalogError('')
    } catch (error) {
      if (version !== catalogVersion.current) return
      setCatalogError(error instanceof ApiError && error.status === 404
        ? 'Model discovery is unavailable on this editor service. Saved selections remain visible but cannot be changed until a local CLI catalog is available.'
        : error instanceof Error ? error.message : 'Unable to load the local model catalog.')
    } finally { if (version === catalogVersion.current) setCatalogLoading(false) }
  }
  useEffect(() => { void load(); void loadCatalog() }, [])
  useEffect(() => {
    if (!config) return
    let stale = false
    const timer = window.setTimeout(() => {
      void api.preview(scope, draft).then((response) => { if (!stale) { setDisplayEffective(response.effective); setValidationErrors({}) } }).catch((error) => { if (!stale) setValidationErrors(errorsFor(error, 'validation')) })
    }, 180)
    return () => { stale = true; window.clearTimeout(timer) }
  }, [config, scope, draft])
  const switchScope = (next: Scope) => { if (next === scope || saving) return; if (dirty && !window.confirm('Discard your unsaved changes and switch scope?')) return; scopeRef.current = next; draftVersion.current += 1; setDisplayEffective(null); setScope(next); if (config) { setDraft(documentFor(next, config)); setDirty(false); setErrors({}); setPreviewErrors({}); setValidationErrors({}); setNotice('') } }
  const save = async () => {
    if (!config || saving || loading) return
    const scopeAtSave = scopeRef.current
    const revision = config.scopes[scopeAtSave]?.revision
    if (!revision) return
    const versionAtSave = draftVersion.current
    const documentAtSave = draft
    setSaving(true)
    try {
      const next = await api.save(scopeAtSave, documentAtSave, revision)
      setConfig(next)
      if (draftVersion.current === versionAtSave && scopeRef.current === scopeAtSave) { setDraft(documentFor(scopeAtSave, next)); setDirty(false); setErrors({}); setPreviewErrors({}); setValidationErrors({}); setNotice(`Saved ${scopeAtSave} preferences.`) } else setNotice(`Saved ${scopeAtSave} preferences. Newer changes remain unsaved.`)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Save failed'
      if (draftVersion.current === versionAtSave && scopeRef.current === scopeAtSave) { replaceSaveErrors(error, message, true); setNotice((error instanceof ApiError && error.status === 409) || /changed since loading|changed during saving|locked/i.test(message) ? 'Save conflict: your draft is still available. Export it before reloading.' : '') } else { replaceSaveErrors(error, message, false); setNotice('Save did not replace newer changes.') }
    } finally { setSaving(false) }
  }
  const reload = async () => { if (saving) return; if (dirty) { const blob = new Blob([JSON.stringify(draft, null, 2)], { type: 'application/json' }); const anchor = document.createElement('a'); anchor.href = URL.createObjectURL(blob); anchor.download = `routing-${scope}-draft.json`; anchor.click(); URL.revokeObjectURL(anchor.href); if (!window.confirm('Your draft was exported. Discard it and reload the latest saved preferences?')) return } if (await load()) setNotice('Reloaded saved preferences.') }
  const reset = () => { updateDraft(emptyPreferences(), ['agents', 'interactions', 'adaptive_profiles']); setNotice(`Empty ${scope} override is ready to save.`) }
  const currentPath = config?.scopes[scope]?.path
  const displayConfig = config ? { ...config, effective: displayEffective } : null
  const content = useMemo(() => { const current = displayConfig; return current && <><section className="scope-bar"><div><p className="eyebrow">Editing</p><h2>{scope === 'global' ? 'Global defaults' : 'Selected project overrides'}</h2><p className="path">{currentPath}</p></div><label>Scope<select value={scope} disabled={saving || loading} onChange={(event) => switchScope(event.target.value as Scope)}><option value="global">Global</option><option value="project" disabled={!current.scopes.project}>Selected project{!current.scopes.project ? ' (unavailable)' : ''}</option></select></label></section><p className="session-note"><strong>Parent session settings are session-controlled.</strong> They remain read-only and are not changed by worker routes.</p><CatalogStatusPanel catalog={catalog} loading={catalogLoading} error={catalogError} onRefresh={() => void loadCatalog(true)} />{current.bundle.roles.length > 0 ? <><div className="interaction-grid">{current.bundle.roles.map((role) => <AgentCard key={role.id} config={current} catalog={catalog} scope={scope} document={draft} role={role} errors={errors} onChange={updateDraft} />)}</div>{current.bundle.interactions.filter((interaction) => interaction.id === 'claude-review').map((interaction) => <div className="interaction-grid claude-grid" key={interaction.id}><InteractionCard config={current} catalog={catalog} scope={scope} document={draft} interaction={interaction} errors={errors} onChange={updateDraft} /></div>)}</> : <div className="interaction-grid">{current.bundle.interactions.map((interaction) => <InteractionCard key={interaction.id} config={current} catalog={catalog} scope={scope} document={draft} interaction={interaction} errors={errors} onChange={updateDraft} />)}</div>}<AdvancedActivityDefaults config={current} catalog={catalog} scope={scope} document={draft} errors={errors} onChange={updateDraft} /><AdvancedProfiles config={current} catalog={catalog} document={draft} errors={errors} onChange={updateDraft} /><Preview config={current} catalog={catalog} scope={scope} document={draft} onError={(error) => setPreviewErrors(errorsFor(error, 'preview'))} onSuccess={clearPreviewError} /></> }, [displayConfig, scope, draft, errors, saving, loading, catalog, catalogLoading, catalogError])
  return <main><header className="hero"><div><p className="eyebrow">Clanker orchestration</p><h1>Routing editor</h1><p>Choose worker routes, see their inheritance, and preview a resolver decision before a future run.</p></div><div className={`save-state ${dirty ? 'dirty' : ''}`} aria-live="polite">{dirty ? notice || 'Unsaved changes' : notice || 'All changes saved'}</div></header>{loading && <p className="loading" role="status">Loading routing preferences…</p>}{errors.load && <div className="alert" role="alert">{errors.load}</div>}{displayConfig && content}{config && <footer className="actions"><div>{errors.save && <p className="alert" role="alert">{errors.save}</p>}{errors.validation && <p className="alert" role="alert">{errors.validation}</p>}{errors.preview && <p className="alert" role="alert">{errors.preview}</p>}</div><div><WranglerPanel status={config?.wrangler} /><button type="button" className="secondary" onClick={reload} disabled={saving || loading}>Export draft and reload</button><button type="button" className="secondary" onClick={reset}>Reset {scope} override</button><button type="button" className="primary" onClick={() => void save()} disabled={!dirty || saving || loading}>{saving ? 'Saving…' : `Save ${scope} preferences`}</button></div></footer>}</main>
}
