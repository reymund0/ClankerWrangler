## MODIFIED Requirements

### Requirement: Versioned preferences and explicit precedence
The system SHALL support versioned bundled defaults, global user preferences, and optional project preferences. For each field, resolution SHALL apply bundled defaults, global interaction values, global native agent defaults, global interaction-specific specialist overrides, project interaction values, project native agent defaults, project interaction-specific specialist overrides, then explicit session overrides, in that order. Omitted fields SHALL inherit. Removing an override SHALL restore inheritance. A reasoning configuration SHALL be replaced as a complete unit rather than merging incompatible fixed and Adaptive fields. Missing preference files SHALL use inherited defaults; malformed files, unsupported schema versions, and invalid values SHALL be reported and SHALL block affected routing until corrected or bypassed for that run only on an explicit user instruction naming the affected file. Resolution SHALL preserve each field's source.

#### Scenario: Project and session precedence
- **WHEN** global planning uses Sol, a global architect override uses Astra, the project planning route selects Luna, and the session explicitly requests Sol
- **THEN** the requested model is Sol, its source is the session, and removing the session override exposes the project Luna selection

#### Scenario: Missing versus invalid preferences
- **WHEN** no preference files exist
- **THEN** existing Sol planning/review, Terra implementation, and Opus 5 cross-review model defaults remain available

#### Scenario: Invalid saved preferences
- **WHEN** a present preferences file has invalid syntax or an unsupported version
- **THEN** the error identifies its source and no dispatch silently proceeds using different settings

#### Scenario: Agent default and activity exception
- **WHEN** a global backend agent selects Terra, its native-review exception selects Sol, and a project backend agent selects Luna
- **THEN** project Luna wins for both activities unless a project activity-specific exception overrides it, with field-level provenance identifying the winning layer

#### Scenario: Legacy preferences and frozen snapshots
- **WHEN** existing schema-1 preferences without agent defaults are loaded after the update
- **THEN** new snapshots use the current policy version while preserving the prior routing behavior without automatic preference rewrites

#### Scenario: Frozen version-1 replay
- **WHEN** an existing policy-version-1 run snapshot is resolved after the update
- **THEN** its original routing semantics and reported policy version remain intact, and unknown future or mismatched versions are rejected

#### Scenario: Invalid agent default
- **WHEN** a native agent default has an unknown role, a known Claude model, nested specialist overrides, or invalid reasoning
- **THEN** validation rejects the field without silently dropping it

### Requirement: Interaction and specialist routing
The system SHALL distinguish planning/design, implementation/testing, native code review, visual/UX review, and Claude cross-review. Native agent defaults SHALL optionally apply across native interactions, with specialist overrides scoped to an interaction taking precedence within the same scope. Without agent defaults the existing phase-specific defaults SHALL remain. A cross-review using several specialist instruction files SHALL resolve one route from its cross-review interaction, without arbitrarily selecting one specialist's override. Rechecks SHALL retain their interaction and reassess their remaining scope. The parent model and effort SHALL remain the user's active session settings.

#### Scenario: One specialty in different phases
- **WHEN** a backend specialist plans a contract, implements it, and reviews it
- **THEN** planning, implementation, and native review routes are resolved separately

#### Scenario: Several Claude review specialties
- **WHEN** one Claude packet contains architect and data-engineer guidance
- **THEN** it uses one cross-review model/effort route and both instruction files only shape review criteria
