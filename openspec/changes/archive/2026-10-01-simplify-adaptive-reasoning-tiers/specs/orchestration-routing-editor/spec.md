## MODIFIED Requirements

### Requirement: Explainable preview without execution
The editor SHALL let users select an interaction, optional native specialist, one of straightforward, involved, or demanding and risk factors, and temporary session overrides for preview. It SHALL display the predicted model/effort, provenance, rationale, ceiling effects, and capability status from the shared resolver. Preview SHALL NOT launch agents, call models, consume subscription usage, or save temporary session overrides as persistent settings. Previewing unsaved changes SHALL identify that draft state.

#### Scenario: Compare Luna ceilings
- **WHEN** a user previews demanding work with Luna Adaptive and changes the ceiling from xhigh to max
- **THEN** the preview shows the resulting effort change and its reason without dispatching an agent or saving the draft

### Requirement: Dedicated default and profile screens
Activity defaults SHALL show every Codex activity, provider, ownership, applicable specialists, model and segmented Adaptive/Fixed controls, ceiling notes and resets. Adaptive profiles SHALL show effective and own profiles, locally reported model customization, CLI-constrained editable override fields, inherited read-only fields, per-model effort meters, changed-field highlighting and reset. The profile table SHALL contain exactly three tier columns labeled Straightforward, Involved, and Demanding, each with a short accessible definition matching routing guidance. An example SHALL calculate involved effort capped by the first customized profile's ceiling locally without calling preview. Unavailable saved selections SHALL remain visible.

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
- **THEN** it exposes the three current tier values and the separate default ceiling, retains its model-specific effort options and meters, and permits keyboard users to find tier definitions and associated validation errors

### Requirement: Route preview explanation screen
Preview SHALL retain activity, optional specialist, a current three-tier selection, risk flags, required reason and temporary session overrides, with an explicit unsaved-draft/no-execution explanation. Results SHALL show predicted model, requested and proposed effort, ceiling, capability, limitations, risk-adjusted tier and effort explanation. An eight-layer precedence table SHALL highlight winning model and reasoning sources independently. Known layer values SHALL be shown with earlier overridden values struck through. Unknown or inconsistent lower-layer values SHALL be shown as an em dash rather than invented; returned resolver winners remain authoritative. Catalog information SHALL NOT be presented as runtime availability proof.

#### Scenario: Prefilled preview and risk adjustment
- **WHEN** preview is opened from a selected agent and submitted with risk flags
- **THEN** the form has its applicable activity and agent selected, and the returned resolver decision explains the actual tier, effort and winning sources without saving or executing a model

#### Scenario: Shared current-tier resolution
- **WHEN** the user previews a current tier with the same preferences, reason, risk flags, and capabilities as a dispatch request
- **THEN** the preview matches its tier, effort, ceiling effects, and provenance and does not execute a model or persist temporary overrides

## ADDED Requirements

### Requirement: Visible migration on explicit save
Legacy preferences SHALL display as converted three-tier profiles without changing the saved file or creating overrides on open. The editor SHALL explain the mapping and retirement of mechanical before save. An explicit save SHALL persist the selected scope in current form, retaining an exact recoverable copy of the previous legacy document. Existing validation, revision, lock, atomic-write, and path protections SHALL apply; migration SHALL NOT modify the other scope.

#### Scenario: Load and save a legacy profile
- **WHEN** a legacy scope is opened, previewed, and then explicitly saved
- **THEN** open and preview leave its bytes unchanged, the UI identifies the pending conversion, and save preserves the original bytes in a reported backup before persisting the three-tier values

#### Scenario: Conversion conflicts or backup fails
- **WHEN** the source revision changes before save or its required backup cannot be safely persisted
- **THEN** the save fails without replacing the preferences, preserves the draft, and reports the conflict or failure

#### Scenario: Install or reload without saving
- **WHEN** the editor is reloaded or the skill bundle is installed with legacy preferences present
- **THEN** preference files remain unchanged and no migration backup or extra override is created

#### Scenario: Old editor assets
- **WHEN** a current routing service is paired with assets built for a different policy version
- **THEN** startup rejects the mismatch with rebuild instructions instead of serving an incompatible profile form
