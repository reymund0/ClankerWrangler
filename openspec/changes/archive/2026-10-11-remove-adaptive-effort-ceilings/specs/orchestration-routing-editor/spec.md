# Spec Delta

## MODIFIED Requirements

### Requirement: Editable interaction routes and inheritance
The editor SHALL present native specialist agents and one Claude cross-review route in its primary worker matrix with a selected-route inspector, with model and Fixed or Adaptive reasoning. Native agent defaults SHALL be independently resettable by field and SHALL NOT erase activity-specific exceptions when edited. Inspector activity controls SHALL expose applicable activities and retain explicitly configured off-scenario exceptions. Existing interaction defaults SHALL remain editable in the Activity defaults tab. Adaptive reasoning SHALL have no maximum-effort control or ceiling summary; model tier mappings SHALL be available in the Adaptive profiles tab, and Fixed effort SHALL remain directly editable. The editor SHALL show the global destination, inherited sources, unsaved changes and activity exceptions. It SHALL display differing inherited fields as varying by activity rather than silently selecting one value. Opening, expanding or refreshing SHALL NOT create overrides. CLI-only model and effort selection, parent session-controlled settings and existing save protection SHALL remain intact. Cross-review SHALL use a single route even when several specialist criteria are selected. Specialist filtering SHALL retain configured exceptions without changing stored preferences or resolver support.

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

### Requirement: Explainable preview without execution
The editor SHALL let users select an interaction, optional native specialist, one of straightforward, involved, or demanding and risk factors, and temporary session overrides for preview. It SHALL display the predicted model/effort, provenance, rationale, mapped/requested effort, and capability status from the shared resolver. Preview SHALL NOT launch agents, call models, consume subscription usage, or save temporary session overrides as persistent settings. Previewing unsaved changes SHALL identify that draft state.

#### Scenario: Preview Luna Demanding directly
- **WHEN** a user previews demanding work with bundled Luna Adaptive
- **THEN** the preview shows requested effort max from the Demanding mapping, without a cap or ceiling explanation, and neither dispatches an agent nor saves the draft

#### Scenario: Compare Luna ceilings
- **WHEN** a preview request supplies a retired max_effort field with either xhigh or max for Luna Adaptive
- **THEN** preview rejects the unsupported field instead of comparing capped results, without dispatching an agent or saving preferences

### Requirement: Local validated persistence
The editor SHALL read and save only global preferences. Saves SHALL validate configuration, be atomic, detect changes since the loaded revision before replacement and serialize cooperating editor saves, and report success only after persistence. Invalid drafts and write failures SHALL preserve prior saved content and keep the draft recoverable. Global preferences SHALL survive skill installation and upgrade. The editor SHALL make the global destination visible before saving; existing project preference files SHALL remain untouched. The documented save guarantee SHALL acknowledge that a non-cooperating writer can race after the final revision check; atomic replacement alone SHALL NOT be presented as filesystem compare-and-swap. Loading invalid saved preferences or preparing a Reset draft SHALL NOT save automatically; replacing the saved document SHALL require an explicit Save.

#### Scenario: Concurrent edit
- **WHEN** another cooperating editor changes a preferences file after loading, or an external edit exists before the final save revision check
- **THEN** saving reports a conflict and preserves the newer file instead of silently overwriting it

#### Scenario: Failed save
- **WHEN** validation fails or the destination is not writable
- **THEN** the editor reports the error, preserves saved preferences, and keeps unsaved form values available

#### Scenario: Retired fields and explicit Reset
- **WHEN** saved global preferences contain a retired ceiling field and the owner opens the editor
- **THEN** the editor reports the field-path validation error and leaves the file unchanged; Reset prepares an empty draft, and a separate explicit Save replaces all overrides with revision protection
- **AND** preserving customizations requires a valid replacement retaining them or hand-editing the retired keys; Reset is a whole-file replacement action rather than ceiling cleanup

### Requirement: Dedicated default and profile screens
Activity defaults SHALL show every Codex activity, provider, ownership, applicable specialists, model and segmented Adaptive/Fixed controls and resets. Adaptive profiles SHALL show effective and own profiles, locally reported model customization, CLI-constrained editable override fields, inherited read-only fields, per-model effort meters, changed-field highlighting and reset. The profile table SHALL contain exactly three tier columns labeled Straightforward, Involved, and Demanding, each with a short accessible definition matching routing guidance. An example SHALL show the first customized profile's involved mapping as the requested effort locally without calling preview. The profile table SHALL have no default-ceiling column, selector, or meter. Unavailable saved selections SHALL remain visible.

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

### Requirement: Route preview explanation screen
Preview SHALL retain activity, optional specialist, a current three-tier selection, risk flags, required reason and temporary session overrides, with an explicit unsaved-draft/no-execution explanation. Results SHALL show predicted model, requested and proposed effort, capability, limitations, risk-adjusted tier and the direct tier-to-effort explanation. Results and precedence rows SHALL NOT show ceiling fields, a clamping step, or Adaptive maximum summaries. A five-layer precedence table (bundled defaults, global activity, global agent, global activity-specific specialist, session) SHALL highlight winning model and reasoning sources independently. Known layer values SHALL be shown with earlier overridden values struck through. Unknown or inconsistent lower-layer values SHALL be shown as an em dash rather than invented; returned resolver winners remain authoritative. Catalog information SHALL NOT be presented as runtime availability proof.

#### Scenario: Prefilled preview and risk adjustment
- **WHEN** preview is opened from a selected agent and submitted with risk flags
- **THEN** the form has its applicable activity and agent selected, and the returned resolver decision explains the actual tier, effort and winning sources without saving or executing a model

#### Scenario: Shared current-tier resolution
- **WHEN** the user previews a current tier with the same preferences, reason, risk flags, and capabilities as a dispatch request
- **THEN** the preview matches its tier, direct mapped effort, and provenance and does not execute a model or persist temporary overrides

#### Scenario: Unsupported direct mapping remains visible
- **WHEN** an Adaptive profile maps the selected tier to an effort that current runtime evidence does not support
- **THEN** preview shows that exact requested effort and the unsupported capability result without silently lowering effort or switching models
