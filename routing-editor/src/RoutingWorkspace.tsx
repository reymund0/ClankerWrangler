import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from 'react'
import { api, ApiError } from './api'
import { WranglerPanel } from './WranglerPanel'
import { clone, emptyPreferences, getOwnRoute, reasoningFor, resetAgentField, resetAgentRoute, resetField, resetRoute, updateAgentRoute, updateRoute } from './draft'
import { specialistChoices } from './specialists'
import { deriveAgentState } from './routePresentation'
import type { AdaptiveProfile, AgentRoute, ConfigResponse, Decision, EffectiveRoute, Interaction, ModelCatalogResponse, Preferences, Reasoning, Route, Scope } from './types'

const tiers = ['mechanical', 'routine', 'complex', 'exceptional'] as const
const risks = ['security', 'data-integrity', 'recovery', 'cross-layer', 'uncertainty', 'performance'] as const
type Provider = 'codex' | 'claude'
type Choice = { id: string; label: string }
type Screen = 'routes' | 'activities' | 'profiles' | 'preview'
type Prefill = { interaction: string; role: string; serial: number }

function effectiveRoute(config: ConfigResponse, interaction: string, role?: string): EffectiveRoute {
  const route = config.effective?.interactions[interaction] ?? {}
  return role ? route.specialists?.[role] ?? route : route
}

function sourceLabel(source?: string | null): string {
  if (!source || source === 'bundle.defaults') return 'Inherited from bundled defaults'
  if (source === 'this scope') return 'Set in this scope'
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

function errorFor(errors: Record<string, string> | undefined, path: string): string | undefined {
  return errors?.[path] ?? Object.entries(errors ?? {}).find(([field]) => field.startsWith(`${path}.`))?.[1]
}

function FieldError({ error, id }: { error?: string; id: string }) {
  return error ? <p id={id} className="field-error" role="alert">{error}</p> : null
}

function isClaudeAlias(id: string): boolean {
  return /^(default|opus|sonnet|haiku)(?:$|[.:/_\[-])/.test(id)
}

function modelChoices(catalog: ModelCatalogResponse | null, provider: Provider): Choice[] {
  const choices = new Map<string, Choice>()
  for (const model of catalog?.providers[provider]?.models ?? []) choices.set(model.id, { id: model.id, label: model.label })
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

function Segmented({ label, values, value, onChange, format = (item: string) => item }: {
  label: string
  values: readonly string[]
  value: string
  onChange: (value: string) => void
  format?: (value: string) => string
}) {
  return <div className="segmented" role="group" aria-label={label}>
    {values.map((item) => <button type="button" key={item} aria-pressed={value === item} onClick={() => onChange(item)}>{format(item)}</button>)}
  </div>
}

type RouteEditorProps = {
  config: ConfigResponse
  catalog: ModelCatalogResponse | null
  document: Preferences
  interaction: string
  role?: string
  errors: Record<string, string>
  onChange: (next: Preferences, changedPaths?: string[]) => void
}

function RouteEditor({ config, catalog, document, interaction, role, errors, onChange }: RouteEditorProps) {
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
  const selectedEffort = valueReasoning.mode === 'fixed' ? valueReasoning.effort : valueReasoning.max_effort ?? ''
  const effort = effortChoices(config, catalog, provider, valueModel, selectedEffort)
  const reset = (field: 'model' | 'reasoning') => onChange(resetField(document, interaction, role, field), [`${path}.${field}`])
  const described = (field: string) => `${path}-${field}-help ${path}-${field}-error${routeError ? ` ${path}-route-error` : ''}`

  return <fieldset className="route-controls">
    <legend className="sr-only">{role ? `${role} override` : `${interaction} route settings`}</legend>
    <label>Model
      <ModelPicker catalog={catalog} provider={provider} value={valueModel} describedBy={described('model')}
        onChange={(model) => onChange(updateRoute(document, interaction, role, { model }), [`${path}.model`])} />
      <span id={`${path}-model-help`} className="field-help">{sourceLabel(own?.model ? 'this scope' : effective.provenance?.model)}</span>
      <FieldError id={`${path}-model-error`} error={modelError} /><FieldError id={`${path}-route-error`} error={routeError} />
    </label>
    <div className="field-action"><button type="button" className="text-button" onClick={() => reset('model')} disabled={!own?.model}>Reset model</button></div>
    <div className="reasoning-field">
      <span className="field-label">Reasoning mode</span>
      <Segmented label={`${interaction} reasoning mode`} values={['adaptive', 'fixed']} value={valueReasoning.mode} onChange={(mode) => onChange(updateRoute(document, interaction, role, { reasoning: reasoningFor(mode as 'fixed' | 'adaptive', valueReasoning) }), [`${path}.reasoning`])} format={(mode) => mode === 'adaptive' ? 'Adaptive' : 'Fixed'} />
      <span id={`${path}-reasoning-help`} className="field-help">{sourceLabel(own?.reasoning ? 'this scope' : effective.provenance?.reasoning)}</span>
    </div>
    <div className="field-action"><button type="button" className="text-button" onClick={() => reset('reasoning')} disabled={!own?.reasoning}>Reset reasoning</button></div>
    <label className="effort-field">{valueReasoning.mode === 'fixed' ? 'Effort' : 'Adaptive maximum'}
      <select value={selectedEffort} aria-describedby={described('reasoning')}
        onChange={(event) => onChange(updateRoute(document, interaction, role, { reasoning: reasoningFor(valueReasoning.mode, valueReasoning, event.target.value) }), [`${path}.reasoning`])}>
        {valueReasoning.mode === 'adaptive' ? <option value="">Model profile default</option> : <option value="" disabled>Choose effort</option>}
        {effort.options.map((item) => <option value={item.value} key={item.value} disabled={item.disabled}>{item.label}</option>)}
      </select>
      {effort.note && <span className="field-help">{effort.note}</span>}
      {valueReasoning.mode === 'adaptive' && <span className="field-help">Adaptive ceiling: {effective.ceiling ?? 'Model profile default'} · {sourceLabel(effective.ceiling_source)}</span>}
      <FieldError id={`${path}-reasoning-error`} error={reasoningError} />
    </label>
  </fieldset>
}

function CatalogStatusPanel({ catalog, loading, error, onRefresh }: { catalog: ModelCatalogResponse | null; loading: boolean; error: string; onRefresh: () => void }) {
  return <section className="catalog-status" aria-live="polite"><div><p className="eyebrow">Local model discovery</p><h2>CLI catalog</h2>
    {catalog ? <div className="catalog-providers">{(['codex', 'claude'] as const).map((provider) => {
      const item = catalog.providers[provider]
      return <p key={provider}><span className={`catalog-dot ${item.status === 'unavailable' ? 'is-unavailable' : ''}`} aria-hidden="true" /><strong>{provider}</strong> {item.status} via {item.source}{item.cli_version ? ` ${item.cli_version}` : ''}{item.updated_at ? ` · updated ${item.updated_at}` : ''}{item.error ? ` · ${item.error}` : ''}</p>
    })}</div> : <p>{error || 'Loading local CLI catalog…'}</p>}{catalog && error && <p className="field-error">{error}</p>}</div>
    <button type="button" className="secondary" disabled={loading} onClick={onRefresh}>{loading ? 'Refreshing…' : 'Refresh models'}</button>
  </section>
}

function RouteSummary({ route, fallback = 'Unresolved' }: { route?: Route; fallback?: string }) {
  const model = route?.model || fallback
  const reasoning = route?.reasoning
  const summary = reasoning?.mode === 'fixed' ? `fixed · ${reasoning.effort}` : reasoning?.mode === 'adaptive' ? `adaptive ≤ ${reasoning.max_effort ?? 'profile default'}` : 'reasoning unresolved'
  return <><span className="route-model">{model}</span><span className="route-effort">{summary}</span></>
}

function WorkerMatrix({ config, document, scope, selectedRole, errors, onSelect }: {
  config: ConfigResponse
  document: Preferences
  scope: Scope
  selectedRole: string
  errors: Record<string, string>
  onSelect: (role: string, activity?: string) => void
}) {
  const interactions = config.bundle.interactions.filter((item) => item.provider === 'codex')
  return <div className="matrix-shell">
    <div className="matrix-scroll"><table className="route-matrix"><caption className="sr-only">Worker routes by activity</caption><thead><tr><th scope="col">Specialist</th><th scope="col">Agent default</th>{interactions.map((item) => <th scope="col" key={item.id}>{item.label}</th>)}</tr></thead><tbody>
      {config.bundle.roles.map((role) => {
        const state = deriveAgentState(config, document, scope, role)
        const exceptionCount = state.exceptionActivities.length
        const agentError = errorFor(errors, `agents.${role.id}`)
        const specialistErrors = interactions.filter((activity) => errorFor(errors, `interactions.${activity.id}.specialists.${role.id}`))
        const rowError = Boolean(agentError || specialistErrors.length)
        const defaultModelLabel = state.modelMixed || state.reasoningMixed ? 'Varies by activity' : state.valueModel || 'Unresolved'
        const defaultReasoningLabel = state.modelMixed || state.reasoningMixed ? 'Choose a default' : state.valueReasoning?.mode === 'fixed' ? `fixed · ${state.valueReasoning.effort}` : state.valueReasoning?.mode === 'adaptive' ? `adaptive ≤ ${state.valueReasoning.max_effort ?? 'profile default'}` : 'reasoning unresolved'
        const defaultStateLabel = state.modelMixed || state.reasoningMixed ? 'Varies' : state.own?.model || state.own?.reasoning ? 'Set in this scope' : 'Inherited'
        return <tr className={`matrix-row${selectedRole === role.id ? ' is-selected' : ''}${rowError ? ' has-error' : ''}`} key={role.id}>
          <th scope="row" className="matrix-specialist"><button type="button" className="specialist-select" onClick={() => onSelect(role.id)} aria-label={`Inspect ${role.label}${rowError ? ', has field errors' : ''}`} aria-pressed={selectedRole === role.id}><strong>{role.label}</strong><span className="mono">{role.id}</span>{rowError && <span className="row-error-label">Field error</span>}</button>{exceptionCount > 0 && <span className="exception-note">{exceptionCount} exception{exceptionCount === 1 ? '' : 's'}</span>}</th>
          <td><button type="button" className={`route-cell ${state.modelMixed || state.reasoningMixed ? 'state-varies' : state.own?.model || state.own?.reasoning ? 'state-set' : 'state-inherited'}`} onClick={() => onSelect(role.id)} aria-label={`${role.label}, agent default: ${defaultModelLabel}, ${defaultReasoningLabel}, ${defaultStateLabel}`}>
            {state.modelMixed || state.reasoningMixed ? <><span className="route-model">Varies by activity</span><span className="route-effort">Choose a default</span></> : <RouteSummary route={{ model: state.valueModel || undefined, reasoning: state.valueReasoning }} />}
            <span className="state-tag">{state.modelMixed || state.reasoningMixed ? 'Varies' : state.own?.model || state.own?.reasoning ? 'Set in this scope' : 'Inherited'}</span>
          </button></td>
          {interactions.map((interaction) => {
            const applicable = specialistChoices(config, document, scope, interaction.id).some((candidate) => candidate.id === role.id)
            if (!applicable) return <td className="not-used" key={interaction.id}><span>Not used</span></td>
            const ownException = getOwnRoute(document, interaction.id, role.id)
            const actual = effectiveRoute(config, interaction.id, role.id).route
            const route = { ...actual, ...(ownException?.model ? { model: ownException.model } : {}), ...(ownException?.reasoning ? { reasoning: ownException.reasoning } : {}) }
            const exception = state.exceptionActivities.includes(interaction.id)
            const exceptionError = errorFor(errors, `interactions.${interaction.id}.specialists.${role.id}`)
            return <td key={interaction.id}><button type="button" className={`route-cell ${exception ? 'state-exception' : 'state-inherited'}${exceptionError ? ' has-field-error' : ''}`} onClick={() => onSelect(role.id, interaction.id)} aria-label={`${role.label}, ${interaction.label}: ${route.model ?? 'Unresolved'}, ${route.reasoning?.mode === 'fixed' ? `fixed · ${route.reasoning.effort}` : route.reasoning?.mode === 'adaptive' ? `adaptive ≤ ${route.reasoning.max_effort ?? 'profile default'}` : 'reasoning unresolved'}, ${exception ? 'activity exception' : 'Inherited'}${exceptionError ? ', has field error' : ''}`}>
              <RouteSummary route={route} /><span className="state-tag">{exceptionError ? 'Field error' : exception ? 'Activity exception' : 'Inherited'}</span>
            </button></td>
          })}
        </tr>
      })}
      {config.bundle.interactions.filter((item) => item.id === 'claude-review').map((interaction) => {
        const route = effectiveRoute(config, interaction.id).route
        const own = getOwnRoute(document, interaction.id)
        const model = own?.model ?? route?.model ?? ''
        return <tr className="matrix-row claude-row" key={interaction.id}>
          <th scope="row" className="matrix-specialist"><button type="button" className="specialist-select" onClick={() => onSelect('claude-review')} aria-pressed={selectedRole === 'claude-review'}><strong>Claude cross-review</strong><span className="mono">{interaction.id}</span></button></th>
          <td className="matrix-claude-cell" colSpan={interactions.length + 1}><button type="button" className="route-cell state-claude" onClick={() => onSelect('claude-review')} aria-label={`Claude cross-review: ${model || 'Unresolved'}`}>
            <RouteSummary route={{ model, reasoning: own?.reasoning ?? route?.reasoning }} /><span className="state-tag">{own?.model || own?.reasoning ? 'Set in this scope' : 'Inherited'}</span>{model && isClaudeAlias(model) && <span className="badge">Alias · resolution may change</span>}
          </button></td>
        </tr>
      })}
    </tbody></table></div>
  </div>
}

function AgentInspector({ config, catalog, scope, document, roleId, selectedActivity, selectionSerial, errors, onChange, onPreview }: {
  config: ConfigResponse
  catalog: ModelCatalogResponse | null
  scope: Scope
  document: Preferences
  roleId: string
  selectedActivity: string
  selectionSerial: number
  errors: Record<string, string>
  onChange: (next: Preferences, changedPaths?: string[]) => void
  onPreview: (interaction: string, role: string) => void
}) {
  const claude = roleId === 'claude-review'
  const role = config.bundle.roles.find((item) => item.id === roleId)
  const [expandedActivity, setExpandedActivity] = useState<string | null>(null)
  const [adding, setAdding] = useState(false)
  const agentState = role && !claude ? deriveAgentState(config, document, scope, role) : null
  const exceptionErrorKeys = role ? Object.keys(errors).filter((field) => field.startsWith('interactions.') && field.includes(`.specialists.${role.id}`)).sort().join('\n') : ''
  useEffect(() => {
    const selectedIsApplicable = Boolean(selectedActivity && agentState?.activities.some((item) => item.id === selectedActivity))
    setExpandedActivity(selectedIsApplicable ? selectedActivity : null)
    setAdding(false)
  }, [roleId, selectedActivity, selectionSerial])
  useEffect(() => {
    if (!agentState || !exceptionErrorKeys) return
    const errored = agentState.activities.filter((activity) => exceptionErrorKeys.split('\n').some((field) => field.startsWith(`interactions.${activity.id}.specialists.${role?.id}`)))
    setExpandedActivity((current) => errored.some((activity) => activity.id === current) ? current : errored[0]?.id ?? current)
  }, [roleId, exceptionErrorKeys])

  if (claude) {
    const interaction = config.bundle.interactions.find((item) => item.id === 'claude-review')
    if (!interaction) return <aside className="inspector empty"><h2>Claude route</h2><p>No Claude cross-review activity is configured.</p></aside>
    const own = getOwnRoute(document, interaction.id)
    const effectiveModel = own?.model ?? effectiveRoute(config, interaction.id).route?.model ?? ''
    return <aside className="inspector" aria-labelledby="inspector-title"><div className="inspector-heading"><div><p className="eyebrow">Selected route</p><h2 id="inspector-title">Claude cross-review</h2><p className="mono">{interaction.id}</p></div><span className="badge">claude</span></div>
      {effectiveModel && isClaudeAlias(effectiveModel) && <p className="alias-note">Alias · resolution may change when the CLI resolves this route.</p>}
      <RouteEditor config={config} catalog={catalog} document={document} interaction={interaction.id} errors={errors} onChange={onChange} />
      <button type="button" className="text-button" onClick={() => onChange(resetRoute(document, interaction.id), [`interactions.${interaction.id}`])} disabled={!own?.model && !own?.reasoning}>Reset route to inherited</button>
      <button type="button" className="primary inspector-preview" onClick={() => onPreview(interaction.id, '')}>Preview a decision for this route</button>
    </aside>
  }
  if (!role) return <aside className="inspector empty"><h2>Choose a specialist</h2><p>Select a worker row to inspect its defaults and activity routes.</p></aside>

  const state = agentState!
  const path = `agents.${role.id}`
  const own = state.own
  const routeError = errors[path]
  const modelError = errorFor(errors, `${path}.model`)
  const reasoningError = errorFor(errors, `${path}.reasoning`)
  const model = state.valueModel
  const reasoning = state.valueReasoning
  const selectedEffort = reasoning?.mode === 'fixed' ? reasoning.effort : reasoning?.mode === 'adaptive' ? reasoning.max_effort ?? '' : ''
  const effort = state.modelMixed && !own?.model ? mixedEffortChoices(config, catalog, 'codex', state.actualModels, selectedEffort) : effortChoices(config, catalog, 'codex', model, selectedEffort)
  const update = (change: Partial<AgentRoute>, field: 'model' | 'reasoning') => onChange(updateAgentRoute(document, role.id, change), [`${path}.${field}`])
  const availableToAdd = state.activities.filter((activity) => !state.exceptionActivities.includes(activity.id))
  const pathHelp = (field: 'model' | 'reasoning') => `${path}-${field}-help ${path}-${field}-error${routeError ? ` ${path}-route-error` : ''}`

  return <aside className="inspector" aria-labelledby="inspector-title">
    <div className="inspector-heading"><div><p className="eyebrow">Selected specialist</p><h2 id="inspector-title">{role.label}</h2><p className="mono">{role.id}</p></div><span className="badge">codex</span></div>
    <p className="field-help">Default route for this specialist. Activity exceptions stay separate.</p>
    <fieldset className="agent-fields"><legend>Agent default</legend>
      <label>Model
        <ModelPicker catalog={catalog} provider="codex" value={model} emptyLabel={state.modelMixed ? 'Varies by activity — choose a default' : 'Inherited model unresolved'} describedBy={pathHelp('model')} onChange={(value) => update({ model: value }, 'model')} />
        <span id={`${path}-model-help`} className="field-help">{state.modelMixed ? 'Varies by activity. Choose a default to replace only this field.' : own?.model ? sourceLabel('this scope') : state.baseline?.route?.model ? sourceLabel(state.baseline.provenance?.model) : state.inheritedModel ? 'Derived from activity routes' : sourceLabel()}</span>
        <FieldError id={`${path}-model-error`} error={modelError} /><FieldError id={`${path}-route-error`} error={routeError} />
      </label>
      <button type="button" className="text-button" disabled={!own?.model} onClick={() => onChange(resetAgentField(document, role.id, 'model'), [`${path}.model`])}>Reset model</button>
      <div className="reasoning-field"><span className="field-label">Reasoning mode</span>
        {state.reasoningMixed && !own?.reasoning && <span className="field-help">Varies by activity. Choose a mode to set a sparse agent default.</span>}
        <Segmented label={`${role.label} reasoning mode`} values={['adaptive', 'fixed']} value={reasoning?.mode ?? ''} onChange={(mode) => update({ reasoning: reasoningFor(mode as 'fixed' | 'adaptive', reasoning) }, 'reasoning')} format={(mode) => mode === 'adaptive' ? 'Adaptive' : 'Fixed'} />
        <span id={`${path}-reasoning-help`} className="field-help">{state.reasoningMixed ? 'Varies by activity' : own?.reasoning ? sourceLabel('this scope') : state.baseline?.route?.reasoning ? sourceLabel(state.baseline.provenance?.reasoning) : state.inheritedReasoning ? 'Derived from activity routes' : sourceLabel()}</span>
        <FieldError id={`${path}-reasoning-error`} error={reasoningError} />
      </div>
      <button type="button" className="text-button" disabled={!own?.reasoning} onClick={() => onChange(resetAgentField(document, role.id, 'reasoning'), [`${path}.reasoning`])}>Reset reasoning</button>
      {reasoning?.mode === 'fixed' && <label>Effort<select value={selectedEffort} aria-describedby={`${path}-reasoning-error`} onChange={(event) => update({ reasoning: reasoningFor('fixed', reasoning, event.target.value) }, 'reasoning')}><option value="" disabled>{effort.empty ? 'Choose a default model or activity-specific reasoning' : 'Choose effort'}</option>{effort.options.map((item) => <option key={item.value} value={item.value} disabled={item.disabled}>{item.label}</option>)}</select>{effort.note && <span className="field-help">{effort.note}</span>}{effort.empty && <span className="field-help">No common known effort is available. Choose a model or customize activity reasoning.</span>}</label>}
      {reasoning?.mode === 'adaptive' && <label>Adaptive maximum<select value={selectedEffort} aria-describedby={`${path}-reasoning-error`} onChange={(event) => update({ reasoning: reasoningFor('adaptive', reasoning, event.target.value) }, 'reasoning')}><option value="">Model profile default</option>{effort.options.map((item) => <option key={item.value} value={item.value} disabled={item.disabled}>{item.label}</option>)}</select>{effort.note && <span className="field-help">{effort.note}</span>}</label>}
      <button type="button" className="text-button" disabled={!own} onClick={() => onChange(resetAgentRoute(document, role.id), [path])}>Reset agent default</button>
    </fieldset>

    <div className="activity-routes"><div className="section-subhead"><h3>By activity</h3>{state.exceptionActivities.length > 0 && <span className="exception-note">{state.exceptionActivities.length} exception{state.exceptionActivities.length === 1 ? '' : 's'}</span>}</div>
      {state.activities.map((activity) => {
        const ownException = getOwnRoute(document, activity.id, role.id)
        const current = effectiveRoute(config, activity.id, role.id)
        const actual = { ...current.route, ...(ownException?.model ? { model: ownException.model } : {}), ...(ownException?.reasoning ? { reasoning: ownException.reasoning } : {}) }
        const exception = state.exceptionActivities.includes(activity.id)
        const isOpen = expandedActivity === activity.id
        return <section className={`activity-route${exception ? ' has-exception' : ''}`} key={activity.id}>
          <button type="button" className="activity-route-toggle" aria-expanded={isOpen} onClick={() => setExpandedActivity(isOpen ? null : activity.id)}><span><strong>{activity.label}</strong><span className="field-help"><RouteSummary route={actual} /></span></span><span className={`state-tag ${exception ? 'state-exception-label' : ''}`}>{exception ? 'Activity exception' : 'Inherited'}</span></button>
          {isOpen && <div className="activity-route-editor"><RouteEditor config={config} catalog={catalog} document={document} interaction={activity.id} role={role.id} errors={errors} onChange={onChange} /><button type="button" className="text-button" disabled={!ownException} onClick={() => onChange(resetRoute(document, activity.id, role.id), [`interactions.${activity.id}.specialists.${role.id}`])}>Reset activity exception</button></div>}
        </section>
      })}
      {availableToAdd.length > 0 && <div className="add-exception"><button type="button" className="text-button" aria-expanded={adding} onClick={() => setAdding(!adding)}>+ Add activity exception</button>
        {adding && <div className="add-exception-list" role="group" aria-label="Choose activity for exception">{availableToAdd.map((activity) => <button type="button" key={activity.id} onClick={() => { setExpandedActivity(activity.id); setAdding(false) }}>{activity.label}</button>)}</div>}
      </div>}
    </div>
    {state.activities[0] ? <button type="button" className="primary inspector-preview" onClick={() => onPreview(state.activities.some((item) => item.id === selectedActivity) ? selectedActivity : state.activities[0].id, role.id)}>Preview a decision for this agent</button> : <p className="field-help">This specialist is not used by a Codex activity yet, so there is no activity to preview.</p>}
  </aside>
}

function ActivityDefaultCard({ config, catalog, scope, document, interaction, errors, onChange }: {
  config: ConfigResponse
  catalog: ModelCatalogResponse | null
  scope: Scope
  document: Preferences
  interaction: Interaction
  errors: Record<string, string>
  onChange: (next: Preferences, changedPaths?: string[]) => void
}) {
  const own = getOwnRoute(document, interaction.id)
  const hasOwnRoute = Boolean(own?.model || own?.reasoning)
  const users = specialistChoices(config, document, scope, interaction.id)
  const effective = effectiveRoute(config, interaction.id)
  const resetOwnRoute = () => {
    const modelReset = resetField(document, interaction.id, undefined, 'model')
    const reasoningReset = resetField(modelReset, interaction.id, undefined, 'reasoning')
    onChange(reasoningReset, [`interactions.${interaction.id}`])
  }
  return <article className={`interaction-card activity-default-card${hasOwnRoute ? ' is-set' : ''}`}>
    <header><div><h2>{interaction.label}</h2><p className="mono">{interaction.id}</p></div><div className="card-tags"><span className={`badge ${hasOwnRoute ? 'badge-set' : ''}`}>{hasOwnRoute ? 'Set here' : 'Inherited'}</span><span className="badge">{interaction.provider}</span></div></header>
    <div className="used-by"><strong>Used by {users.length}:</strong>{users.length ? users.map((item) => <span className="user-chip" key={item.id}>{item.label}</span>) : <span className="field-help">No specialist suggestions for this activity.</span>}</div>
    <RouteEditor config={config} catalog={catalog} document={document} interaction={interaction.id} errors={errors} onChange={onChange} />
    {effective.ceiling && <p className="field-help ceiling-note">Adaptive routes inherit a ceiling of <strong>{effective.ceiling}</strong> from {sourceLabel(effective.ceiling_source)}.</p>}
    <button type="button" className="text-button" disabled={!hasOwnRoute} onClick={resetOwnRoute}>Reset route to inherited</button>
  </article>
}

function profileEffort(config: ConfigResponse, provider: Provider, profile: AdaptiveProfile | undefined, tier: typeof tiers[number]) {
  if (!profile) return { mapped: 'Unknown', requested: 'Unknown' }
  const mapped = profile.tiers[tier]
  const order = config.bundle.effort_orders[provider] ?? []
  const mappedIndex = order.indexOf(mapped)
  const ceilingIndex = order.indexOf(profile.default_ceiling)
  const requested = mappedIndex < 0 || ceilingIndex < 0 ? mapped : order[Math.min(mappedIndex, ceilingIndex)]
  return { mapped, requested }
}

function profileFamily(key: string): string {
  if (key.startsWith('claude:')) return 'Claude · Models'
  const family = key.slice(key.indexOf(':') + 1).match(/^gpt-(\d+(?:\.\d+)*)(?:-|$)/)?.[1] ?? 'Other'
  return `Codex · ${family}`
}

function ProfileTable({ config, catalog, scope, document, errors, onChange }: {
  config: ConfigResponse
  catalog: ModelCatalogResponse | null
  scope: Scope
  document: Preferences
  errors: Record<string, string>
  onChange: (draft: Preferences, changedPaths?: string[]) => void
}) {
  const ownProfiles = document.adaptive_profiles ?? {}
  const [provider, setProvider] = useState<Provider>('codex')
  const [model, setModel] = useState('')
  const availableModels = modelChoices(catalog, provider)
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const globalProfiles = config.scopes.global.document?.adaptive_profiles ?? {}
  const bundledProfiles = config.bundle.defaults.adaptive_profiles ?? {}
  const keys = [...new Set([...Object.keys(config.effective?.profiles ?? {}), ...Object.keys(bundledProfiles), ...Object.keys(globalProfiles), ...Object.keys(ownProfiles)])].sort()
  const families = [...new Set(keys.map(profileFamily))].sort((a, b) => {
    if (a === b) return 0
    if (a.startsWith('Claude')) return -1
    if (b.startsWith('Claude')) return 1
    if (a.endsWith('Other')) return 1
    if (b.endsWith('Other')) return -1
    return b.localeCompare(a, undefined, { numeric: true })
  })
  const errorFamilies = [...new Set(keys.filter((key) => errorFor(errors, `adaptive_profiles.${key}`)).map(profileFamily))]
  const errorSignature = JSON.stringify({ families: errorFamilies, errors: Object.entries(errors).filter(([path]) => path.startsWith('adaptive_profiles.')) })
  useEffect(() => {
    const affected = (JSON.parse(errorSignature) as { families: string[] }).families
    if (affected.length) setExpanded((current) => ({ ...current, ...Object.fromEntries(affected.map((family) => [`${scope}:${family}`, true])) }))
  }, [errorSignature, scope])
  useEffect(() => { if (!availableModels.some((item) => item.id === model)) setModel('') }, [availableModels, model])

  const customizeKey = (key: string) => {
    if (ownProfiles[key]) return
    const separator = key.indexOf(':')
    const profileProvider = key.slice(0, separator) as Provider
    const profileModel = key.slice(separator + 1)
    if (!modelChoices(catalog, profileProvider).some((item) => item.id === profileModel)) return
    const inherited = scope === 'project' ? globalProfiles[key] ?? bundledProfiles[key] : bundledProfiles[key]
    const fallback = inherited ?? config.effective?.profiles[key] ?? { tiers: { mechanical: 'low', routine: 'medium', complex: 'high', exceptional: 'xhigh' }, default_ceiling: 'xhigh' }
    setExpanded((current) => ({ ...current, [`${scope}:${profileFamily(key)}`]: true }))
    onChange({ ...clone(document), adaptive_profiles: { ...ownProfiles, [key]: clone(fallback) } }, [`adaptive_profiles.${key}`])
    if (model === profileModel && provider === profileProvider) setModel('')
  }
  const customize = () => { if (model) customizeKey(`${provider}:${model}`) }
  const modify = (key: string, field: keyof AdaptiveProfile | `tiers.${typeof tiers[number]}`, value: string) => {
    const profile = clone(ownProfiles[key])
    if (field === 'default_ceiling') profile.default_ceiling = value
    else profile.tiers[field.slice(6) as typeof tiers[number]] = value
    onChange({ ...clone(document), adaptive_profiles: { ...ownProfiles, [key]: profile } }, [`adaptive_profiles.${key}.${field}`])
  }
  const reset = (key: string) => {
    const next = clone(document)
    delete next.adaptive_profiles?.[key]
    if (next.adaptive_profiles && Object.keys(next.adaptive_profiles).length === 0) delete next.adaptive_profiles
    onChange(next, [`adaptive_profiles.${key}`])
  }

  return <>
    <div className="profile-addbar">
      <div className="provider-switch" aria-label="Profile provider">{(['codex', 'claude'] as const).map((item) => <button type="button" key={item} aria-pressed={provider === item} onClick={() => { setProvider(item); setModel('') }}><svg className="provider-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">{item === 'codex' ? <><rect x="3" y="4" width="18" height="16" rx="4" /><path d="m7 9 3 3-3 3m6 0h4" /></> : <><path d="M12 2v5m0 10v5M2 12h5m10 0h5M5 5l3.5 3.5m7 7L19 19M5 19l3.5-3.5m7-7L19 5" /><circle cx="12" cy="12" r="3" /></>}</svg>{item === 'codex' ? 'Codex' : 'Claude'}</button>)}</div>
      <label><span>Model</span><select aria-label="Profile model" value={model} disabled={!availableModels.length} onChange={(event) => setModel(event.target.value)}>
        <option value="">{availableModels.length ? 'Select model' : 'No models available'}</option>
        {availableModels.map((item) => <option value={item.id} key={item.id}>{choiceLabel(item, provider)}</option>)}
      </select></label>
      <button type="button" className="primary" onClick={customize} disabled={!model || Boolean(ownProfiles[`${provider}:${model}`])}>Customize profile</button>
    </div>
    {!availableModels.length && <p className="field-help">No models were reported by the local {provider} CLI.</p>}
    {keys.length === 0 ? <p className="empty">No profile data was reported. Select a locally reported model to customize its profile.</p> : <div className="profile-table-scroll"><div className="profile-table" role="table" aria-label="Adaptive model profiles">
      <div className="profile-row profile-heading" role="row"><span role="columnheader">Model</span>{tiers.map((tier) => <span role="columnheader" key={tier}>{tier}</span>)}<span role="columnheader">Default ceiling</span><span role="columnheader">Actions</span></div>
      {families.map((family) => {
        const familyKeys = keys.filter((key) => profileFamily(key) === family)
        const customized = familyKeys.filter((key) => ownProfiles[key]).length
        const stateKey = `${scope}:${family}`
        const isExpanded = expanded[stateKey] ?? (customized > 0 || errorFamilies.includes(family))
        return <div role="rowgroup" key={family}>
          <div role="row" className="profile-family-heading"><div role="cell" aria-colspan={7}>
            <button type="button" aria-expanded={isExpanded} onClick={() => setExpanded((current) => ({ ...current, [stateKey]: !isExpanded }))}>
              <span aria-hidden="true">{isExpanded ? '▾' : '▸'}</span><strong>{family}</strong><span>{familyKeys.length} models</span>{customized > 0 && <span>· {customized} customized here</span>}
            </button>
          </div></div>
          {isExpanded && familyKeys.map((key) => {
        const separator = key.indexOf(':')
        const profileProvider = key.slice(0, separator) as Provider
        const profileModel = key.slice(separator + 1)
        const own = ownProfiles[key]
        const inherited = scope === 'project' ? globalProfiles[key] ?? bundledProfiles[key] : bundledProfiles[key]
        const displayed = own ?? inherited ?? config.effective?.profiles[key]
        if (!displayed) return null
        const path = `adaptive_profiles.${key}`
        const profileError = errorFor(errors, path)
        const fields = [...tiers.map((tier) => ({ label: tier, field: `tiers.${tier}` as const, value: displayed.tiers[tier], inheritedValue: inherited?.tiers[tier] })), { label: 'Default ceiling', field: 'default_ceiling' as const, value: displayed.default_ceiling, inheritedValue: inherited?.default_ceiling }]
        const effortOrder = config.bundle.effort_orders[profileProvider] ?? []
        return <div role="row" key={key} className={`profile-row${own ? ' is-customized' : ''}`}>
          <div role="rowheader" className="profile-model"><span className="mono">{key}</span><FieldError id={`${path}-error`} error={profileError} />{own && <span className="state-tag">Customized here</span>}</div>
          {fields.map(({ label, field, value, inheritedValue }) => {
            const fieldPath = `${path}.${field}`
            const fieldError = errorFor(errors, fieldPath) ?? (field.startsWith('tiers.') ? errorFor(errors, `${path}.tiers`) : undefined)
            const choices = effortChoices(config, catalog, profileProvider, profileModel, value)
            const meterLevels = [...new Set(choices.options.filter((item) => !item.disabled).map((item) => item.value))]
              .sort((a, b) => (effortOrder.includes(a) ? effortOrder.indexOf(a) : effortOrder.length) - (effortOrder.includes(b) ? effortOrder.indexOf(b) : effortOrder.length))
            const changed = Boolean(own && inheritedValue !== undefined && value !== inheritedValue)
            return <div role="cell" className={`profile-value${changed ? ' differs' : ''}`} key={field}>
              {own ? <label className="profile-editor"><span className="sr-only">{key} {label}</span><select value={value} aria-describedby={[fieldError ? `${fieldPath}-error` : '', choices.note ? `${fieldPath}-help` : ''].filter(Boolean).join(' ') || undefined} onChange={(event) => modify(key, field, event.target.value)}>{choices.options.map((item) => <option key={item.value} value={item.value} disabled={item.disabled}>{item.label}</option>)}</select></label> : <span className="profile-effort">{value}</span>}
              <span className="effort-meter" aria-hidden="true">{meterLevels.map((level, index) => <i key={level} data-effort={level} className={index <= meterLevels.indexOf(value) ? `filled effort-${level}` : ''} />)}</span>
              {own && choices.note && <span id={`${fieldPath}-help`} className="field-help">{choices.note}</span>}
              {changed && <span className="field-help">Different from inherited {inheritedValue}</span>}
              <FieldError id={`${fieldPath}-error`} error={fieldError} />
            </div>
          })}
          <div role="cell" className="profile-actions">{own ? <button type="button" className="text-button" onClick={() => reset(key)}>Reset profile</button> : <><button type="button" className="text-button" disabled={!modelChoices(catalog, profileProvider).some((item) => item.id === profileModel)} onClick={() => customizeKey(key)}>Customize</button>{!modelChoices(catalog, profileProvider).some((item) => item.id === profileModel) && <span className="field-help">Model not reported by local {profileProvider} CLI.</span>}</>}</div>
        </div>
          })}
        </div>
      })}
    </div></div>}
    {Object.entries(ownProfiles)[0] ? (() => {
      const [key, profile] = Object.entries(ownProfiles)[0]
      const providerForKey = key.slice(0, key.indexOf(':')) as Provider
      const example = profileEffort(config, providerForKey, profile, 'complex')
      return <p className="profile-example"><strong>Example:</strong> A complex task on <span className="mono">{key.slice(key.indexOf(':') + 1)}</span> maps to <strong>{example.mapped}</strong>; the {profile.default_ceiling} ceiling yields requested effort <strong>{example.requested}</strong>.</p>
    })() : null}
    <p className="profile-footnote">Only efforts reported by the local CLI can be chosen. Profiles are routing policy, not a quality guarantee.</p>
  </>
}

type TraceLayer = { label: string; source: string; route: Route }
type TraceDecision = { layers: TraceLayer[]; modelWinner: number | null; reasoningWinner: number | null; modelTrusted: boolean; reasoningTrusted: boolean }

function traceDecision(config: ConfigResponse, scope: Scope, document: Preferences, interaction: string, role: string, sessionRoute: Route, decision: Decision): TraceDecision {
  const bundled = config.bundle.defaults.interactions?.[interaction]
  const layers: TraceLayer[] = [
    { label: 'Bundled defaults', source: 'bundle.defaults', route: { model: bundled?.model, reasoning: bundled?.reasoning } },
  ]
  const scopeDocuments: { name: 'global' | 'project'; value: Preferences }[] = scope === 'global'
    ? [{ name: 'global', value: document }, { name: 'project', value: emptyPreferences() }]
    : [{ name: 'global', value: config.scopes.global.document ?? emptyPreferences() }, { name: 'project', value: document }]
  for (const item of scopeDocuments) {
    const activityRoute = item.value.interactions?.[interaction]
    layers.push({ label: `${item.name === 'global' ? 'Global' : 'Project'} activity`, source: `${item.name}.interactions.${interaction}`, route: { model: activityRoute?.model, reasoning: activityRoute?.reasoning } })
    layers.push({ label: `${item.name === 'global' ? 'Global' : 'Project'} agent default`, source: `${item.name}.agents.${role}`, route: role ? item.value.agents?.[role] ?? {} : {} })
    layers.push({ label: `${item.name === 'global' ? 'Global' : 'Project'} activity exception`, source: `${item.name}.interactions.${interaction}.specialists.${role}`, route: role ? activityRoute?.specialists?.[role] ?? {} : {} })
  }
  layers.push({ label: 'Session override', source: 'session_override', route: sessionRoute })

  let resolvedModel: string | undefined
  let resolvedReasoning: Reasoning | undefined
  let modelWinner: number | null = null
  let reasoningWinner: number | null = null
  layers.forEach((layer, index) => {
    if (layer.route.model !== undefined) { resolvedModel = layer.route.model; modelWinner = index }
    if (layer.route.reasoning !== undefined) { resolvedReasoning = layer.route.reasoning; reasoningWinner = index }
  })
  const exactWinner = (source: string, field: 'model' | 'reasoning'): number | null => {
    if (source === 'bundle.defaults') return 0
    if (source === 'session_override' || source === `session_override.${field}`) return 7
    return layers.findIndex((layer, index) => index > 0 && source === `${layer.source}.${field}`) >= 0
      ? layers.findIndex((layer, index) => index > 0 && source === `${layer.source}.${field}`)
      : null
  }
  const decisionModelWinner = exactWinner(decision.provenance.model, 'model')
  const decisionReasoningWinner = exactWinner(decision.provenance.reasoning, 'reasoning')
  const modelTrusted = resolvedModel === decision.model && (decisionModelWinner === null || decisionModelWinner === modelWinner)
  const sameReasoning = (left?: Reasoning, right?: Reasoning) => left?.mode === right?.mode && (left?.mode === 'fixed' ? left.effort === (right?.mode === 'fixed' ? right.effort : undefined) : left?.mode === 'adaptive' && left.max_effort === (right?.mode === 'adaptive' ? right.max_effort : undefined))
  const reasoningTrusted = sameReasoning(resolvedReasoning, decision.reasoning) && (decisionReasoningWinner === null || decisionReasoningWinner === reasoningWinner)

  return { layers, modelWinner: decisionModelWinner, reasoningWinner: decisionReasoningWinner, modelTrusted, reasoningTrusted }
}

function effortExplanation(decision: Decision, selectedTier: string, selectedRisks: string[]) {
  const profileSource = decision.provenance.profile ? sourceLabel(decision.provenance.profile) : decision.reasoning.mode === 'fixed' ? 'none (fixed reasoning)' : 'unavailable from resolver'
  return <ol className="effort-explanation">
    <li><span>1</span><p>Tier: <strong>{decision.tier}</strong>{decision.tier !== selectedTier ? `, raised from ${selectedTier} by ${selectedRisks.join(', ') || 'risk policy'}` : ', matching the selected task tier'}.</p></li>
    <li><span>2</span><p>{decision.reasoning.mode === 'fixed' ? <>The route uses fixed reasoning at <strong>{decision.proposed_effort}</strong>.</> : <>The resolver’s Adaptive profile proposed <strong>{decision.proposed_effort}</strong> for this {decision.tier} task.</>} Profile source: <strong>{profileSource}</strong>.</p></li>
    <li><span>3</span><p>Ceiling: <strong>{decision.ceiling ?? 'none'}</strong>{decision.ceiling_source ? ` (${sourceLabel(decision.ceiling_source)})` : ''}.</p></li>
    <li><span>4</span><p>Requested effort: <strong>{decision.effort}</strong>{decision.proposed_effort !== decision.effort ? ` after the ceiling capped proposed ${decision.proposed_effort}` : ''}.</p></li>
  </ol>
}

function Preview({ config, catalog, scope, document, prefill, onError, onSuccess }: {
  config: ConfigResponse
  catalog: ModelCatalogResponse | null
  scope: Scope
  document: Preferences
  prefill: Prefill | null
  onError: (error: unknown) => void
  onSuccess: () => void
}) {
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
  useEffect(() => { if (prefill) { setInteraction(prefill.interaction); setRole(prefill.role) } }, [prefill?.serial])
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
    } finally { if (version === requestVersion.current) setBusy(false) }
  }
  const toggleRisk = (risk: string) => setSelectedRisks((current) => current.includes(risk) ? current.filter((item) => item !== risk) : [...current, risk])
  const sessionRoute: Route = { ...(sessionModel ? { model: sessionModel } : {}), ...(sessionEffort ? { reasoning: reasoningFor(sessionMode, undefined, sessionEffort) } : {}) }
  const trace = decision ? traceDecision(config, scope, document, decision.interaction, decision.role ?? '', sessionRoute, decision) : null

  return <section className="preview-workspace" aria-labelledby="preview-title">
    <form onSubmit={runPreview} className="preview-form-panel">
      <p className="eyebrow">Draft preview</p><h1 id="preview-title">Preview a route</h1>
      <p className="preview-intro">Uses this unsaved {scope} draft. Nothing is saved or run.</p>
      <label>Activity<select value={interaction} onChange={(event) => { setInteraction(event.target.value); setRole('') }}>{config.bundle.interactions.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
      {selectedProvider === 'codex' && <label>Specialist (optional)<select value={role} onChange={(event) => setRole(event.target.value)}><option value="">Activity route</option>{specialists.map((item) => <option value={item.id} key={item.id}>{item.label}</option>)}</select></label>}
      <div><span className="field-label">Task tier</span><Segmented label="Task tier" values={tiers} value={tier} onChange={(value) => setTier(value as typeof tier)} format={(value) => value[0].toUpperCase() + value.slice(1)} /></div>
      <fieldset className="risk-fieldset"><legend>Risk flags</legend><div className="risk-chips">{risks.map((risk) => <button type="button" key={risk} aria-pressed={selectedRisks.includes(risk)} onClick={() => toggleRisk(risk)}>{risk}</button>)}</div></fieldset>
      <label>Reason<input required value={reason} onChange={(event) => setReason(event.target.value)} /></label>
      <details className="session-fieldset"><summary>Temporary session override</summary><p>Applies only to this preview and is never saved.</p>
        <label>Model<ModelPicker catalog={catalog} provider={selectedProvider} value={sessionModel} onChange={setSessionModel} allowEmpty /></label>
        {sessionModel && <button type="button" className="text-button" onClick={() => setSessionModel('')}>Reset session model</button>}
        <div><span className="field-label">Mode</span><Segmented label="Session override mode" values={['adaptive', 'fixed']} value={sessionMode} onChange={(value) => setSessionMode(value as 'adaptive' | 'fixed')} format={(value) => value === 'adaptive' ? 'Adaptive' : 'Fixed'} /></div>
        <label>{sessionMode === 'fixed' ? 'Effort' : 'Maximum'}<select value={sessionEffort} onChange={(event) => setSessionEffort(event.target.value)}><option value="">No override</option>{sessionEfforts.options.map((item) => <option key={item.value} value={item.value} disabled={item.disabled}>{item.label}</option>)}</select>{sessionEfforts.note && <span className="field-help">{sessionEfforts.note}</span>}</label>
      </details>
      <button className="primary preview-submit" disabled={busy}>{busy ? 'Previewing…' : 'Preview route'}</button>
    </form>
    <div className="preview-results">
      {!decision && <div className="preview-empty"><h2>Resolver decision</h2><p>Choose an activity, then preview the current draft to see the model and effort selected by the resolver.</p></div>}
      {decision && <>
        <section className="decision-hero" aria-live="polite"><p className="eyebrow">Predicted route · {config.bundle.interactions.find((item) => item.id === decision.interaction)?.label}{decision.role ? ` · ${config.bundle.roles.find((item) => item.id === decision.role)?.label ?? decision.role}` : ''}</p>
          <div className="decision-lead"><strong className="mono">{decision.model}</strong><strong>{decision.effort}</strong></div>
          <dl><div><dt>Proposed</dt><dd>{decision.proposed_effort}</dd></div><div><dt>Ceiling</dt><dd>{decision.ceiling ?? 'None'}</dd></div><div><dt>Capability</dt><dd>{decision.capability_status}</dd></div></dl><p>{decision.reason}</p>
        </section>
        <section className="trace-section"><h2>How it resolved</h2><p className="field-help">Saved global and project values are shown at their precedence layer; the resolver identifies the winning source for each field.</p>
          <div className="trace-scroll"><div role="table" className="trace-table" aria-label="Eight routing precedence layers">
            <div role="row" className="trace-row trace-heading"><span role="columnheader">Layer</span><span role="columnheader">Model</span><span role="columnheader">Reasoning</span></div>
            {trace?.layers.map((layer, index) => {
              const modelKnown = trace.modelTrusted ? layer.route.model : trace.modelWinner === index ? decision.model : undefined
              const reasoningKnown = trace.reasoningTrusted ? layer.route.reasoning : trace.reasoningWinner === index ? decision.reasoning : undefined
              const modelWins = trace.modelWinner !== null && trace.modelWinner === index
              const reasoningWins = trace.reasoningWinner !== null && trace.reasoningWinner === index
              const modelOverridden = trace.modelWinner !== null && trace.modelWinner !== index
              const reasoningOverridden = trace.reasoningWinner !== null && trace.reasoningWinner !== index
              return <div role="row" className="trace-row" key={layer.source}><span role="rowheader" className="trace-layer"><span>{index + 1}</span>{layer.label}</span>
                <span role="cell">{modelKnown ? <span className={`trace-value mono${modelWins ? ' is-winner' : modelOverridden ? ' is-overridden' : ''}`}>{modelKnown}{modelWins && <b>WINS</b>}</span> : '—'}</span>
                <span role="cell">{reasoningKnown ? <span className={`trace-value${reasoningWins ? ' is-winner' : reasoningOverridden ? ' is-overridden' : ''}`}>{reasoningKnown.mode === 'fixed' ? `Fixed · ${reasoningKnown.effort}` : `Adaptive${reasoningKnown.max_effort ? ` ≤ ${reasoningKnown.max_effort}` : ''}`}{reasoningWins && <b>WINS</b>}</span> : '—'}</span>
              </div>})}
          </div></div>
          {(!trace?.modelTrusted || !trace?.reasoningTrusted || trace?.modelWinner === null || trace?.reasoningWinner === null) && <p className="field-help">Resolver source: model {decision.provenance.model}; reasoning {decision.provenance.reasoning}.{(!trace?.modelTrusted || !trace?.reasoningTrusted) ? ' Some local layer values were hidden because the saved documents did not reproduce the returned decision.' : ''}</p>}
        </section>
        <div className="preview-detail-grid"><section className="effort-section"><h2>How effort was chosen</h2>{effortExplanation(decision, tier, selectedRisks)}</section>
          <section className="limitations"><h2>Limitations</h2>{decision.limitations.length ? <ul>{decision.limitations.map((item) => <li key={item}>{item}</li>)}</ul> : <p>No additional resolver limitations were reported.</p>}<p>The local CLI catalog is not proof of runtime model availability.</p></section>
        </div>
      </>}
    </div>
  </section>
}

function countChanges(saved: unknown, draft: unknown): number {
  if (JSON.stringify(saved) === JSON.stringify(draft)) return 0
  const savedObject = saved && typeof saved === 'object' && !Array.isArray(saved) ? saved as Record<string, unknown> : undefined
  const draftObject = draft && typeof draft === 'object' && !Array.isArray(draft) ? draft as Record<string, unknown> : undefined
  if (savedObject || draftObject) {
    const keys = new Set([...Object.keys(savedObject ?? {}), ...Object.keys(draftObject ?? {})])
    let count = 0
    for (const key of keys) count += countChanges(savedObject?.[key], draftObject?.[key])
    return count
  }
  return 1
}

function errorTab(field: string): Screen | null {
  if (field === 'preview') return 'preview'
  if (field.startsWith('adaptive_profiles')) return 'profiles'
  if (field.startsWith('agents.') || field.includes('.specialists.') || field.includes('claude-review')) return 'routes'
  if (field.startsWith('interactions.')) return 'activities'
  return null
}

const tabs: { id: Screen; label: string }[] = [
  { id: 'routes', label: 'Worker routes' },
  { id: 'activities', label: 'Activity defaults' },
  { id: 'profiles', label: 'Adaptive profiles' },
  { id: 'preview', label: 'Preview a route' },
]

export function RoutingWorkspace() {
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
  const [screen, setScreen] = useState<Screen>('routes')
  const [selectedRole, setSelectedRole] = useState('')
  const [selectedActivity, setSelectedActivity] = useState('')
  const [selectionSerial, setSelectionSerial] = useState(0)
  const [theme, setTheme] = useState<'system' | 'light' | 'dark'>(() => {
    try { return (localStorage.getItem('routing-editor-theme') as 'system' | 'light' | 'dark') || 'system' } catch { return 'system' }
  })
  const [prefill, setPrefill] = useState<Prefill | null>(null)
  const [prefillSerial, setPrefillSerial] = useState(0)
  const [dismissedAlerts, setDismissedAlerts] = useState<string[]>([])
  const draftVersion = useRef(0)
  const scopeRef = useRef(scope)
  const loadVersion = useRef(0)
  const catalogVersion = useRef(0)

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'system') root.removeAttribute('data-theme')
    else root.dataset.theme = theme
    try { localStorage.setItem('routing-editor-theme', theme) } catch { /* Theme remains active for this page. */ }
  }, [theme])

  const replaceSaveErrors = (error: unknown, message: string, includeFieldError: boolean) => setErrors((current) => {
    const preserved = Object.fromEntries(Object.entries(current).filter(([field]) => field !== 'save' && !field.startsWith('interactions.') && !field.startsWith('adaptive_profiles.')))
    return { ...preserved, ...(includeFieldError ? errorsFor(error, 'save') : {}), save: message }
  })
  const updateDraft = (next: Preferences, changedPaths: string[] = []) => {
    draftVersion.current += 1
    setDraft(next); setDirty(true); setNotice(''); setDismissedAlerts([])
    if (changedPaths.length > 0) setErrors((current) => Object.fromEntries(Object.entries(current).filter(([field]) => field !== 'save' && !changedPaths.some((path) => field === path || field.startsWith(`${path}.`) || path.startsWith(`${field}.`)))) )
    setPreviewErrors({})
    if (changedPaths.length > 0) setValidationErrors((current) => Object.fromEntries(Object.entries(current).filter(([field]) => !changedPaths.some((path) => field === path || field.startsWith(`${path}.`) || path.startsWith(`${field}.`)))) )
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
      setConfig(next); setDraft(documentFor(scopeAtStart, next)); setDirty(false); setErrors(next.error ? { load: next.error } : {}); setPreviewErrors({}); setValidationErrors({}); setDismissedAlerts([])
      return true
    } catch (error) {
      if (version === loadVersion.current) { setErrors({ load: error instanceof Error ? error.message : 'Unable to load configuration' }); setDismissedAlerts([]) }
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

  useEffect(() => {
    if (!config?.bundle.roles.length) return
    if (selectedRole === 'claude-review' || selectedRole && config.bundle.roles.some((role) => role.id === selectedRole)) return
    setSelectedRole(config.bundle.roles[0].id)
  }, [config])
  const switchScope = (next: Scope) => {
    if (next === scope || saving) return
    if (dirty && !window.confirm('Discard your unsaved changes and switch scope?')) return
    scopeRef.current = next; draftVersion.current += 1; setDisplayEffective(null); setScope(next); setDismissedAlerts([])
    if (config) { setDraft(documentFor(next, config)); setDirty(false); setErrors({}); setPreviewErrors({}); setValidationErrors({}); setNotice('') }
  }
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
      if (draftVersion.current === versionAtSave && scopeRef.current === scopeAtSave) { setDraft(documentFor(scopeAtSave, next)); setDirty(false); setErrors({}); setPreviewErrors({}); setValidationErrors({}); setNotice(`Saved ${scopeAtSave} preferences.`); setDismissedAlerts([]) }
      else setNotice(`Saved ${scopeAtSave} preferences. Newer changes remain unsaved.`)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Save failed'
      if (draftVersion.current === versionAtSave && scopeRef.current === scopeAtSave) { replaceSaveErrors(error, message, true); setNotice((error instanceof ApiError && error.status === 409) || /changed since loading|changed during saving|locked/i.test(message) ? 'Save conflict: your draft is still available. Export it before reloading.' : ''); setDismissedAlerts([]) }
      else { replaceSaveErrors(error, message, false); setNotice('Save did not replace newer changes.') }
    } finally { setSaving(false) }
  }
  const reload = async () => {
    if (saving) return
    if (dirty) {
      const blob = new Blob([JSON.stringify(draft, null, 2)], { type: 'application/json' })
      const anchor = document.createElement('a'); anchor.href = URL.createObjectURL(blob); anchor.download = `routing-${scope}-draft.json`; anchor.click(); URL.revokeObjectURL(anchor.href)
      if (!window.confirm('Your draft was exported. Discard it and reload the latest saved preferences?')) return
    }
    if (await load()) setNotice('Reloaded saved preferences.')
  }
  const reset = () => { updateDraft(emptyPreferences(), ['agents', 'interactions', 'adaptive_profiles']); setNotice(`Empty ${scope} override is ready to save.`) }
  const openPreview = (interaction: string, role: string) => {
    const serial = prefillSerial + 1
    setPrefillSerial(serial); setPrefill({ interaction, role, serial }); setScreen('preview')
  }
  const handleTabKey = (event: KeyboardEvent<HTMLButtonElement>) => {
    const index = tabs.findIndex((tab) => tab.id === screen)
    const next = event.key === 'ArrowRight' ? (index + 1) % tabs.length : event.key === 'ArrowLeft' ? (index + tabs.length - 1) % tabs.length : event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : -1
    if (next >= 0) { event.preventDefault(); setScreen(tabs[next].id); document.getElementById(`tab-${tabs[next].id}`)?.focus() }
  }
  const currentPath = config?.scopes[scope]?.path
  const projectPathParts = config?.scopes.project?.path.split(/[\\/]/).filter(Boolean) ?? []
  const projectName = projectPathParts.at(-2) === '.clanker' ? projectPathParts.at(-3) ?? 'selected' : 'selected'
  const displayConfig = config ? { ...config, effective: displayEffective } : null
  const fieldErrorScreens = new Set(Object.keys(errors).map(errorTab).filter((item): item is Screen => item !== null))
  const savedChanges = config ? countChanges(documentFor(scope, config), draft) : 0
  const dirtyLabel = savedChanges === 1 ? '1 unsaved change' : `${savedChanges} unsaved changes`
  const knownAlerts = ['load', 'save', 'validation', 'preview']
  const alerts = [
    ...(dirty && notice ? [{ key: 'notice', message: notice }] : []),
    ...knownAlerts.flatMap((key) => errors[key] ? [{ key, message: errors[key] }] : []),
    ...Object.entries(errors).filter(([key]) => !knownAlerts.includes(key) && errorTab(key) === null).map(([key, message]) => ({ key: `field:${key}`, message })),
  ]
  const resetScopeLabel = `Reset ${scope} override`

  return <div className="routing-workspace">
    <header className="workspace-header">
      <div className="header-top">
        <div className="brand-block"><span className="brand-mark" aria-hidden="true">ON</span><div><strong>Orchestration Nation</strong><span>Routing</span></div></div>
        <div className="scope-switch" role="group" aria-label="Scope"><button type="button" aria-pressed={scope === 'global'} disabled={saving || loading} onClick={() => switchScope('global')}>Global</button><button type="button" aria-pressed={scope === 'project'} disabled={!config?.scopes.project || saving || loading} onClick={() => switchScope('project')}>Project{config?.scopes.project ? ' · ' + projectName : ' · unavailable'}</button></div>
        <div className="header-path"><span className="sr-only">Configuration file</span><code>{currentPath ?? 'Loading configuration path…'}</code></div>
        <div className={`save-state ${dirty ? 'dirty' : ''}`} aria-live="polite" role="status">{dirty ? dirtyLabel : notice || 'All changes saved'}</div>
        <label className="theme-select">Theme<select aria-label="Theme" value={theme} onChange={(event) => setTheme(event.target.value as typeof theme)}><option value="system">System theme</option><option value="light">Light</option><option value="dark">Dark</option></select></label>
        <div className="header-actions"><WranglerPanel status={config?.wrangler} /><button type="button" className="secondary" onClick={() => void reload()} disabled={saving || loading}>Export draft &amp; reload</button><button type="button" className="secondary" onClick={reset} disabled={saving || loading}>{resetScopeLabel}</button><button type="button" className="primary save-button" onClick={() => void save()} disabled={!dirty || saving || loading}>{saving ? 'Saving…' : `Save ${scope === 'global' ? 'global' : 'project'} preferences`}</button></div>
      </div>
    </header>
    <nav className="screen-tabs" role="tablist" aria-label="Routing editor screens" onKeyDown={(event) => { if (event.target instanceof HTMLButtonElement) handleTabKey(event as unknown as KeyboardEvent<HTMLButtonElement>) }}>
      {tabs.map((tab) => <button id={`tab-${tab.id}`} key={tab.id} type="button" role="tab" aria-selected={screen === tab.id} aria-controls={`panel-${tab.id}`} tabIndex={screen === tab.id ? 0 : -1} onClick={() => setScreen(tab.id)}>
        {tab.label}{fieldErrorScreens.has(tab.id) && <><span className="tab-error-dot" aria-hidden="true" /><span className="sr-only">, has field errors</span></>}
      </button>)}
    </nav>
    {alerts.length > 0 && <section className="alert-stack" aria-label="Routing editor alerts">{alerts.map(({ key, message }) => !dismissedAlerts.includes(key) && <div className={`alert-banner${key === 'notice' ? ' alert-banner--notice' : ''}`} role={key === 'load' || key === 'save' || key.startsWith('field:') ? 'alert' : 'status'} key={key}><p><strong>{key === 'load' ? 'Unable to load' : key === 'save' ? 'Save status' : key === 'validation' ? 'Draft validation' : key === 'preview' ? 'Preview failed' : key === 'notice' ? 'Draft status' : 'Configuration field needs attention'}</strong><span>{message}</span></p>{key === 'load' && <button type="button" className="text-button" onClick={() => void load()}>Retry load</button>}<button type="button" className="dismiss-alert" aria-label={`Dismiss ${key} message`} onClick={() => setDismissedAlerts((current) => [...current, key])}>×</button></div>)}</section>}
    {loading && <p className="loading" role="status">Loading routing preferences…</p>}
    {!config && !loading && dismissedAlerts.includes('load') && <div className="alert-stack"><p>Routing preferences are unavailable.</p><button type="button" className="secondary" onClick={() => void load()}>Retry load</button></div>}
    {displayConfig && <main className="screen-content">
      <section id="panel-routes" className="tab-panel" role="tabpanel" aria-labelledby="tab-routes" hidden={screen !== 'routes'}>
        <div className="screen-title"><div><p className="eyebrow">Configure native specialists</p><h1>Worker routes</h1><p>Compare each specialist’s default with its activity routes, then inspect or edit the selected worker.</p></div><div className="legend"><span><i className="legend-dot inherited" />Inherited</span><span><i className="legend-dot set" />Set in this scope</span><span><i className="legend-dot exception" />Activity exception</span></div></div>
        <p className="session-note"><strong>Parent session settings are session-controlled.</strong> They remain read-only and are not changed by worker routes.</p>
        <CatalogStatusPanel catalog={catalog} loading={catalogLoading} error={catalogError} onRefresh={() => void loadCatalog(true)} />
        <div className="worker-layout"><section className="matrix-panel" aria-label="Worker route matrix"><div className="panel-heading"><h2>Route matrix</h2><p>Choose a cell to inspect that specialist.</p></div><WorkerMatrix config={displayConfig} document={draft} scope={scope} selectedRole={selectedRole} errors={errors} onSelect={(role, activity) => { setSelectedRole(role); setSelectedActivity(activity ?? ''); setSelectionSerial((current) => current + 1) }} /></section>
          <AgentInspector config={displayConfig} catalog={catalog} scope={scope} document={draft} roleId={selectedRole} selectedActivity={selectedActivity} selectionSerial={selectionSerial} errors={errors} onChange={updateDraft} onPreview={openPreview} />
        </div>
      </section>
      <section id="panel-activities" className="tab-panel" role="tabpanel" aria-labelledby="tab-activities" hidden={screen !== 'activities'}>
        <div className="screen-title"><div><p className="eyebrow">Shared routes</p><h1>Activity defaults</h1><p>Within each scope, activity defaults are followed by agent defaults and activity exceptions. Project settings override global settings, including global agent defaults.</p></div></div>
        <ol className="precedence-strip"><li>Bundled defaults</li><li aria-current="step">Activity default</li><li>Agent default</li><li>Activity exception</li></ol>
        <div className="interaction-grid activity-grid">{displayConfig.bundle.interactions.filter((item) => item.provider === 'codex').map((interaction) => <ActivityDefaultCard key={interaction.id} config={displayConfig} catalog={catalog} scope={scope} document={draft} interaction={interaction} errors={errors} onChange={updateDraft} />)}</div>
      </section>
      <section id="panel-profiles" className="tab-panel" role="tabpanel" aria-labelledby="tab-profiles" hidden={screen !== 'profiles'}>
        <div className="screen-title"><div><p className="eyebrow">Adaptive reasoning policy</p><h1>Adaptive profiles</h1><p>Task tiers map to model effort levels, then the route ceiling caps the requested effort.</p></div></div>
        <ProfileTable config={displayConfig} catalog={catalog} scope={scope} document={draft} errors={errors} onChange={updateDraft} />
      </section>
      <section id="panel-preview" className="tab-panel preview-panel-wrap" role="tabpanel" aria-labelledby="tab-preview" hidden={screen !== 'preview'}>
        <Preview config={displayConfig} catalog={catalog} scope={scope} document={draft} prefill={prefill} onError={(error) => { setPreviewErrors(errorsFor(error, 'preview')); setDismissedAlerts([]) }} onSuccess={() => setPreviewErrors({})} />
      </section>
    </main>}
  </div>
}
