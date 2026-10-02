## MODIFIED Requirements

### Requirement: Versioned preferences and explicit precedence
The system SHALL support versioned bundled defaults, global user preferences, and optional project preferences. For each field, resolution SHALL apply bundled defaults, global interaction values, global native agent defaults, global interaction-specific specialist overrides, project interaction values, project native agent defaults, project interaction-specific specialist overrides, then explicit session overrides, in that order. Omitted fields SHALL inherit. Removing an override SHALL restore inheritance. A reasoning configuration SHALL be replaced as a complete unit rather than merging incompatible fixed and Adaptive fields. Missing preference files SHALL use inherited defaults; malformed files, unsupported schema versions, and invalid values SHALL be reported and SHALL block affected routing until corrected or bypassed for that run only on an explicit user instruction naming the affected file. Resolution SHALL preserve each field's source.

#### Scenario: Project and session precedence
- **WHEN** global planning uses Sol, a global architect override uses Astra, the project planning route selects Luna, and the session explicitly requests Sol
- **THEN** the requested model is Sol, its source is the session, and removing the session override exposes the project Luna selection

#### Scenario: Missing versus invalid preferences
- **WHEN** no preference files exist
- **THEN** existing Sol planning/review, Terra implementation, and generic Opus cross-review model defaults remain available

#### Scenario: Invalid saved preferences
- **WHEN** a present preferences file has invalid syntax or an unsupported version
- **THEN** the error identifies its source and no dispatch silently proceeds using different settings

#### Scenario: Agent default and activity exception
- **WHEN** a global backend agent selects Terra, its native-review exception selects Sol, and a project backend agent selects Luna
- **THEN** project Luna wins for both activities unless a project activity-specific exception overrides it, with field-level provenance identifying the winning layer

#### Scenario: Legacy preferences and frozen snapshots
- **WHEN** existing schema-1 preferences without agent defaults are loaded after the update
- **THEN** new snapshots use the current policy version, preserve route precedence, convert legacy profile tiers as specified, and do not rewrite preference files

#### Scenario: Frozen version-1 replay
- **WHEN** an existing policy-version-1 run snapshot is resolved after the update
- **THEN** its original four-tier mappings, risk floors, agent support, fingerprint, and reported policy version remain intact, and unknown future or mismatched versions are rejected

#### Scenario: Frozen version-2 replay
- **WHEN** an existing policy-version-2 snapshot with agent defaults and activity exceptions is resolved after the update
- **THEN** its original four-tier decisions, precedence, risk floors, fingerprint, and reported version remain intact

#### Scenario: Invalid agent default
- **WHEN** a native agent default has an unknown role, a known Claude model, nested specialist overrides, or invalid reasoning
- **THEN** validation rejects the field without silently dropping it

### Requirement: Model-aware Adaptive effort
Routes SHALL support fixed effort or Adaptive effort with a resolved maximum. An omitted ceiling SHALL use the effective model profile default; an explicit ceiling inherited from a user layer SHALL remain authoritative when a higher layer changes only the model. Current-policy task assessments SHALL distinguish straightforward, involved, and demanding assignments using the worker's remaining decisions, uncertainty, and interacting constraints. The parent SHALL supply the tier and a concise assignment-specific reason; no additional assessment fields SHALL be required. Adaptive SHALL apply the selected model's configurable mapping and ceiling. Consequential security, data-integrity, and recovery flags SHALL impose at least involved, and SHALL describe the assignment's responsibility rather than its surrounding project. Demanding SHALL require a concrete reasoning challenge, not merely a smaller model or a large diff. The resolver SHALL return assessed tier, proposed effort, capped effort, reason, and any ceiling limitation. Higher effort SHALL NOT be described as proof of quality or equivalence to a stronger model.

#### Scenario: Luna receives model-specific effort
- **WHEN** an established implementation approach with direct acceptance checks selects Luna with a straightforward mapping of high, an xhigh ceiling, and runtime support for high
- **THEN** the requested effort is high and the decision identifies the Luna mapping

#### Scenario: Demanding Luna assignment and max
- **WHEN** unresolved interacting constraints justify demanding work with a Luna mapping of max and verified support for max
- **THEN** a max ceiling permits max, while an xhigh ceiling requests xhigh and reports the limitation without switching models

#### Scenario: Model choice does not determine difficulty
- **WHEN** a straightforward assignment selects a smaller model whose straightforward mapping is medium
- **THEN** Adaptive requests medium rather than promoting the assignment solely because of the model choice

#### Scenario: Fixed effort overrides Adaptive
- **WHEN** a user explicitly chooses a supported fixed effort
- **THEN** that effort is requested unchanged and Adaptive is not applied to that assignment

#### Scenario: Astra Adaptive planning without a custom profile
- **WHEN** a user selects gpt-6-astra for Planning with Adaptive reasoning and has no user-defined Astra profile
- **THEN** the bundled profile maps straightforward/involved/demanding to medium/high/xhigh with an xhigh default ceiling, permits saving and previewing, and still honors inherited ceilings and capability checks

#### Scenario: Claude CLI review IDs retain exact selections
- **WHEN** a user selects default, opus[1m], claude-fable-5-1[1m], or sonnet for Adaptive Claude cross-review
- **THEN** the bundled profile maps straightforward/involved/demanding to medium/high/high with a high ceiling, saving and preview work without a custom profile, and the exact model ID remains subject to launcher preflight

#### Scenario: Assignment-specific risk floor
- **WHEN** a straightforward assignment carries a consequential security, data-integrity, or recovery flag
- **THEN** the resolver raises its assessed tier to involved and explains the floor while preserving fixed effort and configured ceilings

#### Scenario: Reassessment after investigation
- **WHEN** demanding investigation yields an established approach with direct acceptance checks for a subsequent worker
- **THEN** the parent can classify the subsequent assignment as straightforward with its own reason, subject to its actual risk flags

#### Scenario: Exceptional Luna assignment and max
- **WHEN** a frozen legacy-policy snapshot resolves an exceptionally difficult Luna assignment with an exceptional mapping of max and verified support for max
- **THEN** a max ceiling permits max, while an xhigh ceiling limits the request to xhigh and reports the limitation without switching models

#### Scenario: Mechanical work does not automatically receive max
- **WHEN** a frozen legacy-policy snapshot selects Luna for a mechanical assignment with a mechanical mapping of medium
- **THEN** Adaptive requests medium rather than max solely because of the model choice

## ADDED Requirements

### Requirement: Legacy profile conversion
Current-policy loading SHALL accept complete legacy four-tier or current three-tier profiles and normalize them to straightforward/involved/demanding using routine/complex/exceptional respectively. Exact model keys, effort values, ceilings, and unrelated preferences SHALL be preserved. Mechanical SHALL be retired rather than averaged or substituted. Loading and snapshot creation SHALL NOT rewrite preferences. Incomplete or mixed tier keys within a profile SHALL be rejected.

#### Scenario: Custom legacy mappings across scopes
- **WHEN** global and project profiles contain independently customized legacy tier mappings and ceilings
- **THEN** each profile converts independently before existing precedence applies, even for exact model IDs absent from the bundled catalog, and input files remain unchanged

#### Scenario: Invalid partial migration
- **WHEN** a profile combines routine and involved keys or omits a required tier
- **THEN** validation identifies the invalid profile and blocks routing without inventing missing effort values

#### Scenario: Current requests and old vocabulary
- **WHEN** a current-policy request uses mechanical, routine, complex, or exceptional
- **THEN** validation directs it to the three current tiers without silently interpreting it as another tier; old snapshot requests retain their own vocabulary
