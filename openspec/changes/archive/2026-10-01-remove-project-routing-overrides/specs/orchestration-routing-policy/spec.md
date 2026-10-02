## MODIFIED Requirements

### Requirement: Versioned preferences and explicit precedence
For new runs, the system SHALL support versioned bundled defaults and global user preferences only. For each field, resolution SHALL apply bundled defaults, global interaction values, global native agent defaults, global interaction-specific specialist overrides, then explicit session overrides, in that order. Omitted fields SHALL inherit. Removing an override SHALL restore inheritance. A reasoning configuration SHALL be replaced as a complete unit rather than merging incompatible fixed and Adaptive fields. Missing global preferences SHALL use inherited defaults; malformed global files, unsupported schema versions, and invalid values SHALL be reported and SHALL block affected routing until corrected or bypassed for that run only on an explicit user instruction naming the affected file. Resolution SHALL preserve each field's source.

#### Scenario: Project and session precedence
- **WHEN** global planning uses Sol, a global architect default uses Astra, an existing project file selects Luna, and the session explicitly requests Sol
- **THEN** Sol wins from the session; removing that override exposes the global architect selection and the project file has no effect on the new run

#### Scenario: Missing versus invalid preferences
- **WHEN** no preference files exist
- **THEN** existing Sol planning/review, Terra implementation, and generic Opus cross-review model defaults remain available

#### Scenario: Invalid saved preferences
- **WHEN** a present preferences file has invalid syntax or an unsupported version
- **THEN** the error identifies its source and no dispatch silently proceeds using different settings

#### Scenario: Agent default and activity exception
- **WHEN** a global backend agent selects Terra and its native-review exception selects Sol
- **THEN** native review uses Sol and other applicable activities use Terra, with field-level provenance

#### Scenario: Legacy preferences and frozen snapshots
- **WHEN** existing schema-1 preferences without agent defaults are loaded after the update
- **THEN** new snapshots use the current policy version and global-only precedence, convert legacy profile tiers as specified, and do not rewrite preference files

#### Scenario: Frozen version-1 replay
- **WHEN** an existing policy-version-1 run snapshot is resolved after the update
- **THEN** resolution rejects the snapshot with instructions to start a new run; unknown future or mismatched versions are also rejected

#### Scenario: Frozen version-2 replay
- **WHEN** an existing policy-version-2 snapshot with agent defaults and activity exceptions is resolved after the update
- **THEN** resolution rejects the snapshot with instructions to start a new run; unknown future or mismatched versions are also rejected

#### Scenario: Invalid agent default
- **WHEN** a native agent default has an unknown role, a known Claude model, nested specialist overrides, or invalid reasoning
- **THEN** validation rejects the field without silently dropping it

#### Scenario: Existing project file is ignored
- **WHEN** a new run starts in a repository containing a project routing file, including invalid JSON
- **THEN** that file is neither read nor changed and cannot affect or block the route

#### Scenario: Frozen version-3 replay
- **WHEN** a policy-version-3 snapshot containing project routes or profiles is resolved
- **THEN** resolution rejects the snapshot with instructions to start a new run; unknown future or mismatched versions are also rejected

#### Scenario: Removed project input
- **WHEN** a caller supplies a project preference argument to current snapshot creation
- **THEN** creation rejects the unsupported input without reading that file

### Requirement: Shared deterministic resolution
The editor preview and dispatch preparation SHALL use the same versioned resolver and policy data. Identical preference, session override, assessment, and capability inputs SHALL produce identical requests and provenance. Natural-language task assessment SHALL remain the parent's responsibility and SHALL be supplied explicitly to the resolver with a concise rationale. Configuration SHALL be snapshotted per run; saved changes SHALL affect new runs, with an explicit logged reload required to change an existing run.

#### Scenario: Preview matches dispatch preparation
- **WHEN** a preview and dispatch preparation receive identical inputs
- **THEN** their requested model, effort, limitations, and provenance match

#### Scenario: Preferences change during a run
- **WHEN** preferences are saved while a run is in progress
- **THEN** existing assignments and subsequent assignments in that run retain its snapshot unless the parent explicitly reloads and logs the new snapshot


#### Scenario: Inherited user ceiling survives model change
- **WHEN** global Adaptive reasoning explicitly caps effort at high and a global agent default changes only the model to Luna
- **THEN** the cap remains high; resetting reasoning to Adaptive without a ceiling uses Luna's profile default instead

### Requirement: Legacy profile conversion
Current-policy loading SHALL accept complete legacy four-tier or current three-tier profiles and normalize them to straightforward/involved/demanding using routine/complex/exceptional respectively. Exact model keys, effort values, ceilings, and unrelated preferences SHALL be preserved. Mechanical SHALL be retired rather than averaged or substituted. Loading and snapshot creation SHALL NOT rewrite preferences. Incomplete or mixed tier keys within a profile SHALL be rejected.

#### Scenario: Custom legacy mappings across scopes
- **WHEN** global profiles contain customized legacy tier mappings and ceilings
- **THEN** each profile converts before global precedence applies, including exact model IDs absent from the catalog, and the global file remains unchanged

#### Scenario: Invalid partial migration
- **WHEN** a profile combines routine and involved keys or omits a required tier
- **THEN** validation identifies the invalid profile and blocks routing without inventing missing effort values

#### Scenario: Current requests and old vocabulary
- **WHEN** a current-policy request uses mechanical, routine, complex, or exceptional
- **THEN** validation directs it to the three current tiers without silently interpreting it as another tier; obsolete snapshots are rejected before request resolution

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
- **THEN** resolution rejects the obsolete snapshot with instructions to start a new run

#### Scenario: Mechanical work does not automatically receive max
- **WHEN** a frozen legacy-policy snapshot selects Luna for a mechanical assignment with a mechanical mapping of medium
- **THEN** resolution rejects the obsolete snapshot with instructions to start a new run
