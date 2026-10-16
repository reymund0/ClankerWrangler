## MODIFIED Requirements

### Requirement: Editable interaction routes and inheritance
The editor SHALL present the selected host's native specialist agents and its one external cross-review route in its primary worker matrix with a selected-route inspector, with model and Fixed or Adaptive reasoning. Native agent defaults SHALL be independently resettable by field and SHALL NOT erase activity-specific exceptions when edited. Inspector activity controls SHALL expose applicable activities and retain explicitly configured off-scenario exceptions. Existing interaction defaults SHALL remain editable in the Activity defaults tab. Adaptive reasoning SHALL have no maximum-effort control or ceiling summary; model tier mappings SHALL be available in the Adaptive profiles tab, and Fixed effort SHALL remain directly editable. The editor SHALL show the selected host and its global destination, inherited sources, unsaved changes and activity exceptions. It SHALL display differing inherited fields as varying by activity rather than silently selecting one value. Opening, expanding or refreshing SHALL NOT create overrides. CLI-only model and effort selection, parent session-controlled settings and existing save protection SHALL remain intact. Cross-review SHALL use a single route even when several specialist criteria are selected. Specialist filtering SHALL retain configured exceptions without changing stored preferences or resolver support.

#### Scenario: Project override
- **WHEN** an existing project override is present when the global editor opens
- **THEN** it is ignored and left untouched, and no project controls appear

#### Scenario: Sparse global override
- **WHEN** a user changes only the global implementation model
- **THEN** the editor saves that field without flattening inherited bundled values

#### Scenario: Reset an override
- **WHEN** a user resets a global specialist override
- **THEN** its lower-precedence global or bundled route becomes visible and saving removes only that override

#### Scenario: Set an agent default
- **WHEN** the user changes only the backend agent model in global scope
- **THEN** one sparse agent model override is saved, unrelated fields and saved activity exceptions remain unchanged, and applicable activities without exceptions use the new model

#### Scenario: Differing inherited activities
- **WHEN** an unconfigured backend agent inherits Sol for planning and Terra for implementation
- **THEN** its model control shows that the value varies by activity, its activity details show the effective values, and no preference is written until an edit is saved

#### Scenario: Advanced exceptions and errors
- **WHEN** an agent has an activity override or a validation error in an inspector activity editor
- **THEN** the matrix and owning tab indicate the error or customization, and selecting the erroneous route exposes its relevant controls so the user can inspect or reset the specific field without losing other preferences

#### Scenario: Global and project defaults
- **WHEN** the user opens the editor
- **THEN** only global configuration is editable and there is no project selection or project inheritance state

#### Scenario: Fixed effort with differing activity models
- **WHEN** an agent has no shared model and the user selects Fixed reasoning
- **THEN** new effort choices respect the common policy-supported levels of all known reported activity models, unknown metadata is labeled unverified, existing saved values remain visible, and an empty intersection directs the user to a shared model or activity-specific reasoning

#### Scenario: Adaptive route controls
- **WHEN** a user selects Adaptive reasoning for an activity, native agent, specialist exception, Claude route, or temporary session override
- **THEN** the controls and summaries expose Adaptive without an effort maximum, and selecting Fixed still exposes the supported fixed-effort choices

### Requirement: Worker route matrix and inspector
The worker screen SHALL display API-provided roles and the selected host's native activities with an agent-default column, applicable activity cells, exception counts and that host's external cross-review row. Cells SHALL distinguish inherited, set-in-scope, exception, varying and not-used states using text as well as color. Selection SHALL expose model/reasoning controls, per-field and whole-route reset, applicable activity exception controls, provenance and prefilled preview navigation. Applicable roles SHALL use existing specialist filtering, including configured exceptions for active roles. Catalog status and refresh SHALL remain available. Mockup values SHALL NOT replace response data. The matrix, inspector, activity choices, and preview selector SHALL expose only the ten active native roles; retired role overrides SHALL NOT restore a retired role as an existing exception.

#### Scenario: Inspect mixed inheritance and exceptions
- **WHEN** an active agent has differing activity routes and an inherited or own activity exception
- **THEN** its default cell shows Varies by activity, its exception count remains visible, and editing/resetting the agent default preserves activity exceptions

#### Scenario: Inspect Claude alias
- **WHEN** a Claude alias route is selected
- **THEN** the alias warning, route controls and reset-to-inherited action are available

#### Scenario: Ten active worker roles
- **WHEN** the current editor opens with valid preferences
- **THEN** its worker matrix contains the ten active native roles and one separate external cross-review row for the selected host, and UX designer, documentation writer, and product engineer are absent from every native role selector

#### Scenario: Retired exception cannot reappear
- **WHEN** a saved document or an attempted draft contains a retired specialist override
- **THEN** the retired role is not presented as a selectable existing override, validation identifies the invalid field, and valid off-scenario exceptions for remaining roles retain their existing behavior

#### Scenario: Claude-host matrix
- **WHEN** the Claude host is selected
- **THEN** native activity cells offer Claude models, the external row is Codex cross-review with Codex models, and no Codex-native activity or Claude cross-review row is shown

### Requirement: Dedicated default and profile screens
Activity defaults SHALL show every native activity of the selected host, provider, ownership, applicable specialists, model and segmented Adaptive/Fixed controls and resets. Adaptive profiles SHALL show effective and own profiles, locally reported model customization, CLI-constrained editable override fields, inherited read-only fields, per-model effort meters, changed-field highlighting and reset. The profile table SHALL contain exactly three tier columns labeled Straightforward, Involved, and Demanding, each with a short accessible definition matching routing guidance. An example SHALL show the first customized profile's involved mapping as the requested effort locally without calling preview. The profile table SHALL have no default-ceiling column, selector, or meter. Unavailable saved selections SHALL remain visible.

#### Scenario: Customize and reset a profile
- **WHEN** a locally reported inherited model profile is customized and changed
- **THEN** its editable row marks fields differing from inheritance, reports field errors and returns to the inherited row after reset

#### Scenario: Reset only an activity default
- **WHEN** an activity contains a same-scope specialist exception and its activity default is reset
- **THEN** only the activity model and reasoning are removed, and specialist exceptions remain unchanged; an exceptions-only activity is labeled Inherited on the defaults screen

#### Scenario: Add a locally reported profile
- **WHEN** a provider is selected in the add bar
- **THEN** one model select lists its locally reported models with alias warnings and Customize profile creates a same-scope copy without overwriting an existing customization; an empty provider disables the select and explains why

#### Scenario: Browse family accordions
- **WHEN** profile rows are displayed
- **THEN** their keys determine Claude · Models first, descending numerically sorted Codex version families, and Other last only when needed, within one table with shared column widths
- **AND** full-width header buttons expose aria-expanded, model counts and nonzero customized counts; sections initially expand for own profiles or field errors and otherwise collapse
- **AND** new field errors expand the affected section, customization reveals its row, and manual expansion state is never persisted in preferences

#### Scenario: Model-specific colored effort meter
- **WHEN** a profile field shows its current effort
- **THEN** its aria-hidden meter has one bar per selectable model effort in provider order, including the current saved-unavailable effort once while excluding other disabled options; bars through the current effort use their own level colors and later bars use the empty color
- **AND** light and dark effort tokens match the handoff, visible text conveys the value, and changed cells retain their accent border and fill independently of the meter

#### Scenario: Three-tier profile controls
- **WHEN** an inherited or customized profile is displayed on desktop or a narrow screen
- **THEN** it exposes only the three current tier values as effort columns, retains its model-specific effort options and meters, and permits keyboard users to find tier definitions and associated validation errors

## ADDED Requirements

### Requirement: Host-isolated editing
The editor SHALL provide an explicit orchestration-host selector. Each host SHALL have its own fixed global destination, loaded revision, save lock, unsaved draft, and errors. Loading, previewing, resetting, or saving one host SHALL NOT read for write, modify, or invalidate the other host's file or draft. Requests naming an unknown host SHALL be rejected before any file access. Preview SHALL resolve through the same resolver and host-specific snapshot used for dispatch.

#### Scenario: Save Claude-host routes
- **WHEN** a user edits and saves the Claude host's implementation route
- **THEN** only the Claude-host file changes, the Codex file bytes and revision are unchanged, and the Codex draft is retained

#### Scenario: Switch hosts with unsaved changes
- **WHEN** a user has unsaved Codex-host edits and selects the Claude host
- **THEN** the Codex draft and its unsaved count remain available on return, and no draft is merged or discarded

#### Scenario: Preview matches host dispatch
- **WHEN** a Claude-host preview and dispatch preparation receive identical preferences, request, and capabilities
- **THEN** their model, effort, limitations, provenance, host, provider, and execution kind match

#### Scenario: Unknown host request
- **WHEN** an authenticated request names an unsupported host
- **THEN** the service rejects it without reading or writing any preference file
