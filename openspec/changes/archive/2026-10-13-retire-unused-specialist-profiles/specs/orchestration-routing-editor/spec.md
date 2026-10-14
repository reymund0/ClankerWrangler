## MODIFIED Requirements

### Requirement: Worker route matrix and inspector
The worker screen SHALL display API-provided roles and Codex activities with an agent-default column, applicable activity cells, exception counts and a Claude cross-review row. Cells SHALL distinguish inherited, set-in-scope, exception, varying and not-used states using text as well as color. Selection SHALL expose model/reasoning controls, per-field and whole-route reset, applicable activity exception controls, provenance and prefilled preview navigation. Applicable roles SHALL use existing specialist filtering, including configured exceptions for active roles. Catalog status and refresh SHALL remain available. Mockup values SHALL NOT replace response data. The matrix, inspector, activity choices, and preview selector SHALL expose only the ten active native roles; retired role overrides SHALL NOT restore a retired role as an existing exception.

#### Scenario: Inspect mixed inheritance and exceptions
- **WHEN** an active agent has differing activity routes and an inherited or own activity exception
- **THEN** its default cell shows Varies by activity, its exception count remains visible, and editing/resetting the agent default preserves activity exceptions

#### Scenario: Inspect Claude alias
- **WHEN** a Claude alias route is selected
- **THEN** the alias warning, route controls and reset-to-inherited action are available

#### Scenario: Ten active worker roles
- **WHEN** the current editor opens with valid preferences
- **THEN** its worker matrix contains the ten active native roles and one separate Claude cross-review row, and UX designer, documentation writer, and product engineer are absent from every native role selector

#### Scenario: Retired exception cannot reappear
- **WHEN** a saved document or an attempted draft contains a retired specialist override
- **THEN** the retired role is not presented as a selectable existing override, validation identifies the invalid field, and valid off-scenario exceptions for remaining roles retain their existing behavior

### Requirement: Local validated persistence
The editor SHALL read and save only global preferences. Saves SHALL validate configuration, be atomic, detect changes since the loaded revision before replacement and serialize cooperating editor saves, and report success only after persistence. Invalid drafts and write failures SHALL preserve prior saved content and keep the draft recoverable. Global preferences SHALL survive skill installation and upgrade. The editor SHALL make the global destination visible before saving; existing project preference files SHALL remain untouched. The documented save guarantee SHALL acknowledge that a non-cooperating writer can race after the final revision check; atomic replacement alone SHALL NOT be presented as filesystem compare-and-swap. Loading invalid saved preferences or preparing a Reset draft SHALL NOT save automatically; replacing the saved document SHALL require an explicit Save. Retired role IDs SHALL be rejected on load, preview, and save without automatic role migration or stripping.

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

#### Scenario: Retired role in saved preferences
- **WHEN** saved preferences contain a retired native role in an agent default or activity-specific specialist override
- **THEN** the editor reports its invalid field path and leaves the file unchanged; preserving unrelated customizations requires an owner-edited valid replacement, while Reset remains a draft followed by a separate explicit Save

#### Scenario: Invalid retired-role preview or save
- **WHEN** a preview request names a retired role or a preview/save draft contains a retired override
- **THEN** the service rejects that input before execution or persistence and does not silently remove or remap the role
