# orchestration-routing-policy Specification

## Purpose

Provide consistent, explainable model and reasoning choices from user preferences across software-development interactions and supported runtimes.

## Requirements

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
- **WHEN** existing schema-1 preferences without agent defaults or retired ceiling fields are loaded after the update
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

#### Scenario: Frozen version-4 replay
- **WHEN** a policy-version-4 snapshot using ceiling-based routing is resolved after the update
- **THEN** resolution rejects the snapshot with instructions to start a new run; new snapshots use policy version 5, and unknown future or mismatched versions remain rejected

### Requirement: Interaction and specialist routing
The system SHALL distinguish planning/design, implementation/testing, native code review, visual/UX review, and Claude cross-review. Native agent defaults SHALL optionally apply across native interactions, with specialist overrides scoped to an interaction taking precedence within the same scope. Without agent defaults the existing phase-specific defaults SHALL remain. A cross-review using several specialist instruction files SHALL resolve one route from its cross-review interaction, without arbitrarily selecting one specialist's override. Rechecks SHALL retain their interaction and reassess their remaining scope. The parent model and effort SHALL remain the user's active session settings.

#### Scenario: One specialty in different phases
- **WHEN** a backend specialist plans a contract, implements it, and reviews it
- **THEN** planning, implementation, and native review routes are resolved separately

#### Scenario: Several Claude review specialties
- **WHEN** one Claude packet contains architect and data-engineer guidance
- **THEN** it uses one cross-review model/effort route and both instruction files only shape review criteria

### Requirement: Model-aware Adaptive effort
Routes SHALL support fixed effort or Adaptive effort with no configurable ceiling. Current-policy task assessments SHALL distinguish straightforward, involved, and demanding assignments using the worker's remaining decisions, uncertainty, and interacting constraints. The parent SHALL supply the tier and a concise assignment-specific reason; no additional assessment fields SHALL be required. Adaptive SHALL request the selected model profile's configured effort for the assessed tier directly, preserving the exact tier values without clamping or treating Demanding as another automatic cap. Consequential security, data-integrity, and recovery flags SHALL impose at least involved, and SHALL describe the assignment's responsibility rather than its surrounding project. Demanding SHALL require a concrete reasoning challenge, not merely a smaller model or a large diff. The resolver SHALL return assessed tier, mapped/requested effort, reason, provenance, and non-ceiling limitations. The existing proposed_effort field SHALL equal requested effort for Adaptive and Fixed reasoning. Higher effort SHALL NOT be described as proof of quality or equivalence to a stronger model.

#### Scenario: Luna receives model-specific effort
- **WHEN** an established implementation approach with direct acceptance checks selects Luna with a straightforward mapping of high and runtime support for high
- **THEN** the requested effort is high and the decision identifies the Luna mapping

#### Scenario: Demanding Luna assignment and max
- **WHEN** unresolved interacting constraints justify demanding work with a Luna mapping of max and verified support for max
- **THEN** the requested effort is max without a second cap, and the selected model remains unchanged

#### Scenario: Model choice does not determine difficulty
- **WHEN** a straightforward assignment selects a smaller model whose straightforward mapping is medium
- **THEN** Adaptive requests medium rather than promoting the assignment solely because of the model choice

#### Scenario: Fixed effort overrides Adaptive
- **WHEN** a user explicitly chooses a supported fixed effort
- **THEN** that effort is requested unchanged and Adaptive is not applied to that assignment

#### Scenario: Astra Adaptive planning without a custom profile
- **WHEN** a user selects gpt-6-astra for Planning with Adaptive reasoning and has no user-defined Astra profile
- **THEN** the bundled profile maps straightforward/involved/demanding to medium/high/xhigh without a default ceiling, permits saving and previewing, and retains capability checks

#### Scenario: Claude CLI review IDs retain exact selections
- **WHEN** a user selects default, opus[1m], claude-fable-5-1[1m], or sonnet for Adaptive Claude cross-review
- **THEN** the bundled profile maps straightforward/involved/demanding to medium/high/high without a default ceiling, saving and preview work without a custom profile, and the exact model ID remains subject to launcher preflight

#### Scenario: Assignment-specific risk floor
- **WHEN** a straightforward assignment carries a consequential security, data-integrity, or recovery flag
- **THEN** the resolver raises its assessed tier to involved and explains the floor while preserving fixed effort; Adaptive requests the involved mapping directly

#### Scenario: Reassessment after investigation
- **WHEN** demanding investigation yields an established approach with direct acceptance checks for a subsequent worker
- **THEN** the parent can classify the subsequent assignment as straightforward with its own reason, subject to its actual risk flags

#### Scenario: Exceptional Luna assignment and max
- **WHEN** a frozen legacy-policy snapshot resolves an exceptionally difficult Luna assignment with an exceptional mapping of max and verified support for max
- **THEN** resolution rejects the obsolete snapshot with instructions to start a new run

#### Scenario: Mechanical work does not automatically receive max
- **WHEN** a frozen legacy-policy snapshot selects Luna for a mechanical assignment with a mechanical mapping of medium
- **THEN** resolution rejects the obsolete snapshot with instructions to start a new run

#### Scenario: Each tier retains its exact configured value
- **WHEN** a valid customized profile maps straightforward, involved, and demanding to specific provider-supported efforts
- **THEN** each assessment requests its own exact mapped value, without reordering, lowering, averaging, or changing any tier values

### Requirement: Runtime compatibility and fixed model choice
The system SHALL validate a resolved request against the active runtime's model and effort capabilities before dispatch. Native dispatch SHALL require advertised exact model/effort evidence. Claude dispatch SHALL require successful CLI preflight while marking account/model access unverified until invocation; that remaining uncertainty SHALL NOT be mislabeled as native capability verification. A saved catalog SHALL be presented as configuration guidance, not proof of account access or runtime availability. Unknown or unsupported model/effort combinations SHALL be surfaced without silent substitution or clamping to an unrequested supported value. New models without an Adaptive mapping SHALL require a mapping or an explicit supported fixed effort. The first version SHALL NOT automatically switch models. Recommendations to change model or request independent review SHALL leave the selection unchanged until the user acts.

#### Scenario: Unsupported effort
- **WHEN** a profile selects max but the active runtime does not support max for that model
- **THEN** the assignment is blocked with the requested combination identified and no silent effort or model fallback

#### Scenario: Preview without live capabilities
- **WHEN** the editor can resolve a route but has no current runtime capability evidence
- **THEN** it shows the predicted settings as unverified and does not claim the model is available

### Requirement: Shared deterministic resolution
The editor preview and dispatch preparation SHALL use the same versioned resolver and policy data. Identical preference, session override, assessment, and capability inputs SHALL produce identical requests and provenance. Natural-language task assessment SHALL remain the parent's responsibility and SHALL be supplied explicitly to the resolver with a concise rationale. Configuration SHALL be snapshotted per run; saved changes SHALL affect new runs, with an explicit logged reload required to change an existing run.

#### Scenario: Preview matches dispatch preparation
- **WHEN** a preview and dispatch preparation receive identical inputs
- **THEN** their requested model, effort, limitations, and provenance match

#### Scenario: Preferences change during a run
- **WHEN** preferences are saved while a run is in progress
- **THEN** existing assignments and subsequent assignments in that run retain its snapshot unless the parent explicitly reloads and logs the new snapshot

#### Scenario: Inherited user ceiling survives model change
- **WHEN** global Adaptive reasoning contains a retired max_effort field and a global agent default changes only the model to Luna
- **THEN** validation rejects max_effort at its preference path before routing; the retired ceiling is neither inherited nor discarded and the saved file remains unchanged

#### Scenario: Model-only override selects its own Adaptive profile
- **WHEN** global Adaptive reasoning is inherited and a global agent default changes only the model to Luna
- **THEN** Adaptive requests the assessed tier's Luna mapping directly, preserves model and reasoning provenance, and adds no effort override

### Requirement: Legacy profile conversion
Current-policy loading SHALL accept complete legacy four-tier or current three-tier profiles and normalize them to straightforward/involved/demanding using routine/complex/exceptional respectively. Exact model keys, effort values, and unrelated supported preferences SHALL be preserved. Profiles containing retired ceiling fields SHALL be rejected, rather than accepted for conversion. Mechanical SHALL be retired rather than averaged or substituted. Loading and snapshot creation SHALL NOT rewrite preferences. Incomplete or mixed tier keys within a profile SHALL be rejected.

#### Scenario: Custom legacy mappings across scopes
- **WHEN** global profiles contain customized legacy tier mappings without retired ceiling fields
- **THEN** each profile converts before global precedence applies, including exact model IDs absent from the catalog, and the global file remains unchanged

#### Scenario: Invalid partial migration
- **WHEN** a profile combines routine and involved keys or omits a required tier
- **THEN** validation identifies the invalid profile and blocks routing without inventing missing effort values

#### Scenario: Current requests and old vocabulary
- **WHEN** a current-policy request uses mechanical, routine, complex, or exceptional
- **THEN** validation directs it to the three current tiers without silently interpreting it as another tier; obsolete snapshots are rejected before request resolution

### Requirement: Ceiling-free configuration contract
Adaptive reasoning SHALL accept only mode: adaptive, and profiles SHALL contain only the complete tier mapping. Retired max_effort and default_ceiling SHALL be rejected through strict validation in every input. Configuration processing SHALL NOT migrate or strip retired fields; explicitly saving a replacement document SHALL retain existing revision-safe behavior. Effective-route and decision outputs SHALL omit ceiling and ceiling_source.

#### Scenario: Current configuration without ceiling fields
- **WHEN** a current preference document supplies Adaptive reasoning and a complete three-tier profile without ceiling fields
- **THEN** validation accepts it, and preview and snapshot resolution use its mapped effort directly

#### Scenario: Retired route or session field
- **WHEN** max_effort appears in an interaction route, native agent default, interaction-specific specialist route, or temporary session override
- **THEN** validation rejects the field at its input path, without ignoring it, creating a replacement setting, or allowing dispatch from that input

#### Scenario: Retired profile field
- **WHEN** default_ceiling appears in a bundled or user-defined Adaptive profile, including a profile with legacy tier keys
- **THEN** validation rejects the field without converting or removing it

#### Scenario: Rejected saved preferences remain intact
- **WHEN** a saved global preference document contains a retired ceiling field and is loaded or used to create a snapshot
- **THEN** the source is identified as invalid, affected routing is blocked under the existing invalid-preference rules, and the file remains unchanged with no ceiling-migration backup

#### Scenario: Explicit replacement of invalid saved preferences
- **WHEN** an owner supplies a separate valid ceiling-free replacement document and explicitly saves it against the loaded revision of an invalid saved file
- **THEN** existing save protections apply to that replacement, while submitting a document that still contains retired fields remains invalid; no field-stripping or ceiling migration is performed

#### Scenario: Current output shape
- **WHEN** current-policy effective configuration or a route decision is returned for Adaptive or Fixed reasoning
- **THEN** ceiling and ceiling_source are absent rather than null, synthesized, or retained as compatibility placeholders
