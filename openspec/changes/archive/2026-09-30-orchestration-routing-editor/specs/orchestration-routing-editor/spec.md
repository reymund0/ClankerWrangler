## Purpose

Let users inspect and edit orchestration routing preferences through a local interface with clear inheritance, validation, and realistic previews.

## ADDED Requirements

### Requirement: Editable interaction routes and inheritance
The editor SHALL expose the five routing interactions, model selection, fixed or Adaptive reasoning, and an Adaptive effort ceiling. It SHALL show the active global or project scope, effective inherited values, override sources, and unsaved changes. Native interactions SHALL offer optional specialist overrides and reset-to-inherited controls. Override panels and preview specialist choices SHALL be filtered to specialties relevant to the interaction while retaining explicitly configured exceptions in the draft or inherited scopes, labeled as existing overrides. Filtering SHALL NOT change stored preferences or resolver role support. Cross-review SHALL use a single route even when several specialist criteria are selected. Parent settings SHALL be shown as session-controlled and SHALL NOT be editable as a worker route. Model-specific Adaptive tier mappings SHALL be editable in an advanced area.

#### Scenario: Project override
- **WHEN** a user opens a project with global defaults and changes only its implementation model
- **THEN** the editor shows that field as project-owned and leaves other fields inherited without writing a flattened copy of global defaults

#### Scenario: Reset an override
- **WHEN** a user resets a project specialist override
- **THEN** the inherited route becomes visible and saving removes that override without changing global preferences

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
