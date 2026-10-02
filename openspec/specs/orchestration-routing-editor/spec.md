# orchestration-routing-editor Specification

## Purpose

Let users inspect and edit orchestration routing preferences through a local interface with clear inheritance, validation, and realistic previews.

## Requirements

### Requirement: Editable interaction routes and inheritance
The editor SHALL present native specialist agents and one Claude cross-review route in its primary worker matrix with a selected-route inspector, with model and Fixed or Adaptive reasoning. Native agent defaults SHALL be independently resettable by field and SHALL NOT erase activity-specific exceptions when edited. Inspector activity controls SHALL expose applicable activities and retain explicitly configured off-scenario exceptions. Existing interaction defaults SHALL remain editable in the Activity defaults tab. Adaptive ceilings SHALL remain reachable in route controls and model tier mappings SHALL be available in the Adaptive profiles tab; Fixed effort SHALL remain directly editable. The editor SHALL show the global destination, inherited sources, unsaved changes and activity exceptions. It SHALL display differing inherited fields as varying by activity rather than silently selecting one value. Opening, expanding or refreshing SHALL NOT create overrides. CLI-only model and effort selection, parent session-controlled settings and existing save protection SHALL remain intact. Cross-review SHALL use a single route even when several specialist criteria are selected. Specialist filtering SHALL retain configured exceptions without changing stored preferences or resolver support.

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

### Requirement: Explainable preview without execution
The editor SHALL let users select an interaction, optional native specialist, one of straightforward, involved, or demanding and risk factors, and temporary session overrides for preview. It SHALL display the predicted model/effort, provenance, rationale, ceiling effects, and capability status from the shared resolver. Preview SHALL NOT launch agents, call models, consume subscription usage, or save temporary session overrides as persistent settings. Previewing unsaved changes SHALL identify that draft state.

#### Scenario: Compare Luna ceilings
- **WHEN** a user previews demanding work with Luna Adaptive and changes the ceiling from xhigh to max
- **THEN** the preview shows the resulting effort change and its reason without dispatching an agent or saving the draft

### Requirement: Local validated persistence
The editor SHALL read and save only global preferences. Saves SHALL validate configuration, be atomic, detect changes since the loaded revision before replacement and serialize cooperating editor saves, and report success only after persistence. Invalid drafts and write failures SHALL preserve prior saved content and keep the draft recoverable. Global preferences SHALL survive skill installation and upgrade. The editor SHALL make the global destination visible before saving; existing project preference files SHALL remain untouched. The documented save guarantee SHALL acknowledge that a non-cooperating writer can race after the final revision check; atomic replacement alone SHALL NOT be presented as filesystem compare-and-swap.

#### Scenario: Concurrent edit
- **WHEN** another cooperating editor changes a preferences file after loading, or an external edit exists before the final save revision check
- **THEN** saving reports a conflict and preserves the newer file instead of silently overwriting it

#### Scenario: Failed save
- **WHEN** validation fails or the destination is not writable
- **THEN** the editor reports the error, preserves saved preferences, and keeps unsaved form values available

### Requirement: Restricted local service
The editor service SHALL be loopback-only, accept configuration operations only for its fixed global destination, and reject unauthorized origins and write requests. It SHALL NOT expose arbitrary filesystem reads/writes, credential access, model execution, or arbitrary shell execution. An authenticated explicit Run Wrangler action MAY execute only the fixed source-checkout installer, with no browser-supplied command, arguments or paths; it SHALL reject concurrent runs and report bounded output, failure and timeout honestly. Paths escaping the allowed destinations through traversal or links SHALL be rejected. Project-scoped API requests SHALL be rejected without accessing a project file.

#### Scenario: External or arbitrary-path request
- **WHEN** a request comes from an unauthorized origin or attempts to write outside the global configuration destination
- **THEN** the service rejects it without accessing or changing the requested file

#### Scenario: Automatic local session initialization
- **WHEN** the user opens or refreshes the plain local editor URL in development or built-server mode
- **THEN** the served HTML supplies the current session token without caching, the frontend prefers it over stale stored credentials, and API token, Host and Origin checks remain enforced

### Requirement: Accessible editor states
The editor SHALL provide labeled keyboard-operable controls, visible focus, associated validation messages, and readable layouts on desktop and narrow screens. Loading, empty/inherited, invalid, unsaved, saved, unavailable-capability, and save-conflict states SHALL be distinguishable without relying on color alone. Verification SHALL include rendered interaction evidence rather than source inspection alone.

#### Scenario: Keyboard editing and error recovery
- **WHEN** a user edits an invalid route using only the keyboard
- **THEN** they can identify the invalid control, correct it, preview the result, and save without losing their draft

### Requirement: Portable source-checkout commands
The source checkout SHALL provide root commands to build the editor, start the built editor, and start Python plus Vite with hot reload without requiring shell-specific syntax or new third-party launcher dependencies. The launcher SHALL resolve its repository paths independently of the caller's working directory, discover a supported Python executable with an explicit override, wait for readiness, and clean up owned servers after graceful termination or startup failure. Installed bundles SHALL retain their existing Python-only runtime.

#### Scenario: Local startup and shutdown
- **WHEN** a user starts either editor mode with compatible assets and prerequisites available
- **THEN** the launcher prints a usable local bootstrap URL and gracefully stopping the launcher closes its owned servers

#### Scenario: Development API boundary
- **WHEN** Vite forwards an API request to Python
- **THEN** it validates the incoming local Host, session token, and exact write Origin before translating headers to the fixed backend origin, and rejects unauthorized requests

#### Scenario: Missing prerequisites
- **WHEN** dependencies, supported Python, or a compatible initial build are unavailable
- **THEN** startup fails with actionable instructions and leaves no owned server running

#### Scenario: Removed project startup option
- **WHEN** a caller passes --project to the Node launcher or Python editor service
- **THEN** startup rejects the unsupported option before starting a server; the isolated --global-config-dir option remains available

### Requirement: Explicit local Wrangler installation
The editor SHALL offer a Run Wrangler action with visible local-client installation scope, running and result states, and installer output. It SHALL preserve saved routing preferences and unsaved editor drafts. Installed bundles without the source installer SHALL explain that the action is unavailable.

#### Scenario: Install from checkout
- **WHEN** the user clicks Run Wrangler in the source-checkout editor
- **THEN** the authenticated service runs the platform-appropriate fixed installer once, prevents overlapping runs, and reports its outcome without invoking models or saving the current draft

#### Scenario: Unavailable or failed installer
- **WHEN** the installer is unavailable, exits unsuccessfully, or exceeds its finite timeout
- **THEN** the UI shows the unavailable or failed state and does not claim successful installation

### Requirement: Four-screen routing workspace
The editor SHALL provide Worker routes, Activity defaults, Adaptive profiles, and Preview a route tabs sharing one global unsaved draft and its errors. The header SHALL expose the global destination path, unsaved change count, save, export/reload, reset global preferences and Run Wrangler with anchored install details/output. Save revision/conflict and validation behavior SHALL remain unchanged. Global errors SHALL be dismissible below the tabs and field errors SHALL mark their owning tab. Themes SHALL follow system preference by default with a manual override, readable offline font fallbacks, focus-visible controls and touch targets of at least 40px.

#### Scenario: Navigate an unsaved invalid draft
- **WHEN** a user edits a route, receives a field error and switches tabs
- **THEN** the draft is retained, its owning tab indicates the error, and returning exposes the associated field error without requiring a save

#### Scenario: Narrow and themed workspace
- **WHEN** the workspace is used in light or dark mode at 375px width
- **THEN** actions remain reachable, the matrix scrolls horizontally and the inspector stacks below it

### Requirement: Worker route matrix and inspector
The worker screen SHALL display API-provided roles and Codex activities with an agent-default column, applicable activity cells, exception counts and a Claude cross-review row. Cells SHALL distinguish inherited, set-in-scope, exception, varying and not-used states using text as well as color. Selection SHALL expose model/reasoning controls, per-field and whole-route reset, applicable activity exception controls, provenance and prefilled preview navigation. Applicable roles SHALL use existing specialist filtering, including configured exceptions. Catalog status and refresh SHALL remain available. Mockup values SHALL NOT replace response data.

#### Scenario: Inspect mixed inheritance and exceptions
- **WHEN** an agent has differing activity routes and an inherited or own activity exception
- **THEN** its default cell shows Varies by activity, its exception count remains visible, and editing/resetting the agent default preserves activity exceptions

#### Scenario: Inspect Claude alias
- **WHEN** a Claude alias route is selected
- **THEN** the alias warning, route controls and reset-to-inherited action are available

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
Preview SHALL retain activity, optional specialist, a current three-tier selection, risk flags, required reason and temporary session overrides, with an explicit unsaved-draft/no-execution explanation. Results SHALL show predicted model, requested and proposed effort, ceiling, capability, limitations, risk-adjusted tier and effort explanation. A five-layer precedence table (bundled defaults, global activity, global agent, global activity-specific specialist, session) SHALL highlight winning model and reasoning sources independently. Known layer values SHALL be shown with earlier overridden values struck through. Unknown or inconsistent lower-layer values SHALL be shown as an em dash rather than invented; returned resolver winners remain authoritative. Catalog information SHALL NOT be presented as runtime availability proof.

#### Scenario: Prefilled preview and risk adjustment
- **WHEN** preview is opened from a selected agent and submitted with risk flags
- **THEN** the form has its applicable activity and agent selected, and the returned resolver decision explains the actual tier, effort and winning sources without saving or executing a model

#### Scenario: Shared current-tier resolution
- **WHEN** the user previews a current tier with the same preferences, reason, risk flags, and capabilities as a dispatch request
- **THEN** the preview matches its tier, effort, ceiling effects, and provenance and does not execute a model or persist temporary overrides

### Requirement: Visible migration on explicit save
Legacy preferences SHALL display as converted three-tier profiles without changing the saved file or creating overrides on open. The editor SHALL explain the mapping and retirement of mechanical before save. An explicit save SHALL persist global preferences in current form, retaining an exact recoverable copy of the previous legacy document. Existing validation, revision, lock, atomic-write, and path protections SHALL apply; migration SHALL NOT read or modify project preferences.

#### Scenario: Load and save a legacy profile
- **WHEN** legacy global preferences are opened, previewed, and then explicitly saved
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
