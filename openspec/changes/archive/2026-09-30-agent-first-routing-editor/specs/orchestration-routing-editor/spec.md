## MODIFIED Requirements

### Requirement: Editable interaction routes and inheritance
The editor SHALL present native specialist agents and one Claude cross-review route as its primary configuration cards, with model and Fixed or Adaptive reasoning. Native agent defaults SHALL be independently resettable by field and SHALL NOT erase activity-specific exceptions when edited. Optional Customize by activity controls SHALL expose applicable activities and retain explicitly configured off-scenario exceptions. Existing interaction defaults SHALL remain editable in a collapsed advanced area. Adaptive ceilings and model tier mappings SHALL be available under optional advanced controls; Fixed effort SHALL remain directly editable. The editor SHALL show global/project scope, inherited sources, unsaved changes and activity exceptions. It SHALL display differing inherited fields as varying by activity rather than silently selecting one value. Opening, expanding or refreshing SHALL NOT create overrides. CLI-only model and effort selection, parent session-controlled settings and existing save protection SHALL remain intact. Cross-review SHALL use a single route even when several specialist criteria are selected.

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
- **WHEN** an agent has an activity override or a validation error inside collapsed controls
- **THEN** the card indicates customization and errors reveal their relevant controls so the user can inspect or reset the specific field without losing other preferences

#### Scenario: Global and project defaults
- **WHEN** a project edits or resets an agent field
- **THEN** saving modifies only that project's sparse override, the displayed inherited and activity-specific values reflect the shared resolver, and the global document is unchanged


#### Scenario: Fixed effort with differing activity models
- **WHEN** an agent has no shared model and the user selects Fixed reasoning
- **THEN** new effort choices respect the common policy-supported levels of all known reported activity models, unknown metadata is labeled unverified, existing saved values remain visible, and an empty intersection directs the user to a shared model or activity-specific reasoning
