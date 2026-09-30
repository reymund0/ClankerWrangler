# orchestration-routing-editor Specification

## Purpose

Let users inspect and edit orchestration routing preferences through a local interface with clear inheritance, validation, and realistic previews.

## Requirements

### Requirement: Editable interaction routes and inheritance
The editor SHALL present native specialist agents and one Claude cross-review route in its primary worker matrix with a selected-route inspector, with model and Fixed or Adaptive reasoning. Native agent defaults SHALL be independently resettable by field and SHALL NOT erase activity-specific exceptions when edited. Inspector activity controls SHALL expose applicable activities and retain explicitly configured off-scenario exceptions. Existing interaction defaults SHALL remain editable in the Activity defaults tab. Adaptive ceilings SHALL remain reachable in route controls and model tier mappings SHALL be available in the Adaptive profiles tab; Fixed effort SHALL remain directly editable. The editor SHALL show global/project scope, inherited sources, unsaved changes and activity exceptions. It SHALL display differing inherited fields as varying by activity rather than silently selecting one value. Opening, expanding or refreshing SHALL NOT create overrides. CLI-only model and effort selection, parent session-controlled settings and existing save protection SHALL remain intact. Cross-review SHALL use a single route even when several specialist criteria are selected. Specialist filtering SHALL retain configured exceptions without changing stored preferences or resolver support.

#### Scenario: Project override
- **WHEN** a user opens a project with global defaults and changes only its implementation model
- **THEN** the editor shows that field as project-owned and leaves other fields inherited without writing a flattened copy of global defaults

#### Scenario: Reset an override
- **WHEN** a user resets a project specialist override
- **THEN** the inherited route becomes visible and saving removes that override without changing global preferences

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
- **WHEN** a project edits or resets an agent field
- **THEN** saving modifies only that project's sparse override, the displayed inherited and activity-specific values reflect the shared resolver, and the global document is unchanged


#### Scenario: Fixed effort with differing activity models
- **WHEN** an agent has no shared model and the user selects Fixed reasoning
- **THEN** new effort choices respect the common policy-supported levels of all known reported activity models, unknown metadata is labeled unverified, existing saved values remain visible, and an empty intersection directs the user to a shared model or activity-specific reasoning

### Requirement: Explainable preview without execution
The editor SHALL let users select an interaction, optional native specialist, task tier and risk factors, and temporary session overrides for preview. It SHALL display the predicted model/effort, provenance, rationale, ceiling effects, and capability status from the shared resolver. Preview SHALL NOT launch agents, call models, consume subscription usage, or save temporary session overrides as persistent settings. Previewing unsaved changes SHALL identify that draft state.

#### Scenario: Compare Luna ceilings
- **WHEN** a user previews exceptional work with Luna Adaptive and changes the ceiling from xhigh to max
- **THEN** the preview shows the resulting effort change and its reason without dispatching an agent or saving the draft

### Requirement: Local validated persistence
The editor SHALL read and save global preferences and optional preferences for the project explicitly selected at server startup. Saves SHALL validate configuration, be atomic, detect changes since the loaded revision before replacement and serialize cooperating editor saves, and report success only after persistence. Invalid drafts and write failures SHALL preserve prior saved content and keep the draft recoverable. Global preferences SHALL survive skill installation and upgrade. The editor SHALL make the destination and scope visible before saving; project preferences SHALL remain suitable for deliberate version control. The documented save guarantee SHALL acknowledge that a non-cooperating writer can race after the final revision check; atomic replacement alone SHALL NOT be presented as filesystem compare-and-swap.

#### Scenario: Concurrent edit
- **WHEN** another cooperating editor changes a preferences file after loading, or an external edit exists before the final save revision check
- **THEN** saving reports a conflict and preserves the newer file instead of silently overwriting it

#### Scenario: Failed save
- **WHEN** validation fails or the destination is not writable
- **THEN** the editor reports the error, preserves saved preferences, and keeps unsaved form values available

### Requirement: Restricted local service
The editor service SHALL be loopback-only, accept configuration operations only for its fixed global and startup-selected project destinations, and reject unauthorized origins and write requests. It SHALL NOT expose arbitrary filesystem reads/writes, credential access, model execution, or arbitrary shell execution. An authenticated explicit Run Wrangler action MAY execute only the fixed source-checkout installer, with no browser-supplied command, arguments or paths; it SHALL reject concurrent runs and report bounded output, failure and timeout honestly. Paths escaping the allowed destinations through traversal or links SHALL be rejected. Project selection SHALL NOT be driven by untrusted browser-supplied filesystem paths.

#### Scenario: External or arbitrary-path request
- **WHEN** a request comes from an unauthorized origin or attempts to write outside the selected configuration destinations
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

### Requirement: Explicit local Wrangler installation
The editor SHALL offer a Run Wrangler action with visible local-client installation scope, running and result states, and installer output. It SHALL preserve saved routing preferences and unsaved editor drafts. Installed bundles without the source installer SHALL explain that the action is unavailable.

#### Scenario: Install from checkout
- **WHEN** the user clicks Run Wrangler in the source-checkout editor
- **THEN** the authenticated service runs the platform-appropriate fixed installer once, prevents overlapping runs, and reports its outcome without invoking models or saving the current draft

#### Scenario: Unavailable or failed installer
- **WHEN** the installer is unavailable, exits unsuccessfully, or exceeds its finite timeout
- **THEN** the UI shows the unavailable or failed state and does not claim successful installation

### Requirement: Four-screen routing workspace
The editor SHALL provide Worker routes, Activity defaults, Adaptive profiles, and Preview a route tabs sharing the same scope, unsaved draft and errors. The header SHALL expose scope selection, destination path, unsaved change count, save, export/reload, reset scope and Run Wrangler with anchored install details/output. Scope switching SHALL retain its unsaved-draft confirmation. Save revision/conflict and validation behavior SHALL remain unchanged. Global errors SHALL be dismissible below the tabs and field errors SHALL mark their owning tab. Themes SHALL follow system preference by default with a manual override, readable offline font fallbacks, focus-visible controls and touch targets of at least 40px.

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
Activity defaults SHALL show every Codex activity, provider, ownership, applicable specialists, model and segmented Adaptive/Fixed controls, ceiling notes and resets. Adaptive profiles SHALL show effective and own profiles, locally reported model customization, CLI-constrained editable override fields, inherited read-only fields, per-model effort meters, changed-field highlighting and reset. An example SHALL calculate complex effort capped by the first customized profile's ceiling locally without calling preview. Unavailable saved selections SHALL remain visible.

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

### Requirement: Route preview explanation screen
Preview SHALL retain activity, optional specialist, tier, risk flags, required reason and temporary session overrides, with an explicit unsaved-draft/no-execution explanation. Results SHALL show predicted model, requested and proposed effort, ceiling, capability, limitations, risk-adjusted tier and effort explanation. An eight-layer precedence table SHALL highlight winning model and reasoning sources independently. Known layer values SHALL be shown with earlier overridden values struck through. Unknown or inconsistent lower-layer values SHALL be shown as an em dash rather than invented; returned resolver winners remain authoritative. Catalog information SHALL NOT be presented as runtime availability proof.

#### Scenario: Prefilled preview and risk adjustment
- **WHEN** preview is opened from a selected agent and submitted with risk flags
- **THEN** the form has its applicable activity and agent selected, and the returned resolver decision explains the actual tier, effort and winning sources without saving or executing a model
