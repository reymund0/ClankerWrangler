## Purpose

Provide consistent, explainable model and reasoning choices from user preferences across software-development interactions and supported runtimes.

## ADDED Requirements

### Requirement: Versioned preferences and explicit precedence
The system SHALL support versioned bundled defaults, global user preferences, and optional project preferences. For each field, resolution SHALL apply bundled defaults, global interaction values, global interaction-specific specialist overrides, project interaction values, project interaction-specific specialist overrides, then explicit session overrides, in that order. Omitted fields SHALL inherit. Removing an override SHALL restore inheritance. A reasoning configuration SHALL be replaced as a complete unit rather than merging incompatible fixed and Adaptive fields. Missing preference files SHALL use inherited defaults; malformed files, unsupported schema versions, and invalid values SHALL be reported and SHALL block affected routing until corrected or bypassed for that run only on an explicit user instruction naming the affected file. Resolution SHALL preserve each field's source.

#### Scenario: Project and session precedence
- **WHEN** global planning uses Sol, a global architect override uses Astra, the project planning route selects Luna, and the session explicitly requests Sol
- **THEN** the requested model is Sol, its source is the session, and removing the session override exposes the project Luna selection

#### Scenario: Missing versus invalid preferences
- **WHEN** no preference files exist
- **THEN** existing Sol planning/review, Terra implementation, and Opus 5 cross-review model defaults remain available

#### Scenario: Invalid saved preferences
- **WHEN** a present preferences file has invalid syntax or an unsupported version
- **THEN** the error identifies its source and no dispatch silently proceeds using different settings

### Requirement: Interaction and specialist routing
The system SHALL distinguish planning/design, implementation/testing, native code review, visual/UX review, and Claude cross-review. Specialist overrides SHALL be scoped to an interaction; a specialty SHALL NOT imply one model for every phase. A cross-review using several specialist instruction files SHALL resolve one route from its cross-review interaction, without arbitrarily selecting one specialist's override. Rechecks SHALL retain their interaction and reassess their remaining scope. The parent model and effort SHALL remain the user's active session settings.

#### Scenario: One specialty in different phases
- **WHEN** a backend specialist plans a contract, implements it, and reviews it
- **THEN** planning, implementation, and native review routes are resolved separately

#### Scenario: Several Claude review specialties
- **WHEN** one Claude packet contains architect and data-engineer guidance
- **THEN** it uses one cross-review model/effort route and both instruction files only shape review criteria

### Requirement: Model-aware Adaptive effort
Routes SHALL support fixed effort or Adaptive effort with a resolved maximum. An omitted ceiling SHALL use the effective model profile default; an explicit ceiling inherited from a user layer SHALL remain authoritative when a higher layer changes only the model. Adaptive SHALL resolve a documented task assessment using complexity, uncertainty, and consequence, then apply the selected model's configurable effort mapping and ceiling. Task assessments SHALL distinguish mechanical, routine, complex, and exceptional scopes; consequential security, data-integrity, and recovery concerns SHALL classify at least as complex regardless of diff size. Exceptional SHALL require an identified reason beyond using a smaller model. The resolver SHALL return assessed tier, proposed effort, capped effort, reason, and any ceiling limitation. Higher effort SHALL NOT be described as proof of quality or equivalence to a stronger model.

#### Scenario: Luna receives model-specific effort
- **WHEN** a routine assignment selects Luna with Adaptive, a routine mapping of high, a ceiling of xhigh, and runtime support for high
- **THEN** the requested effort is high and the decision identifies the Luna mapping

#### Scenario: Exceptional Luna assignment and max
- **WHEN** an exceptionally difficult assignment selects Luna with an exceptional mapping of max and verified support for max
- **THEN** a max ceiling permits max, while an xhigh ceiling limits the request to xhigh and reports the limitation without switching models

#### Scenario: Mechanical work does not automatically receive max
- **WHEN** Luna is selected for a mechanical assignment with a mechanical mapping of medium
- **THEN** Adaptive requests medium rather than max solely because of the model choice

#### Scenario: Fixed effort overrides Adaptive
- **WHEN** a user explicitly chooses a supported fixed effort
- **THEN** that effort is requested unchanged and Adaptive is not applied to that assignment

#### Scenario: Astra Adaptive planning without a custom profile
- **WHEN** a user selects gpt-6-astra for Planning with Adaptive reasoning and has no user-defined Astra profile
- **THEN** the bundled profile resolves mechanical/routine/complex/exceptional tasks to low/medium/high/xhigh with an xhigh default ceiling, permits saving and previewing, and still honors explicit inherited ceilings and native capability checks

#### Scenario: Claude CLI review IDs retain exact selections
- **WHEN** a user selects default, opus[1m], claude-fable-5-1[1m], or sonnet for Adaptive Claude cross-review
- **THEN** the bundled review profile maps mechanical/routine/complex/exceptional tasks to low/medium/high/high with a high ceiling, saving and preview work without a user profile, and the exact model ID is preserved subject to launcher preflight

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
- **WHEN** global Adaptive reasoning explicitly caps effort at high and the project changes only the model to Luna
- **THEN** the cap remains high; resetting reasoning to Adaptive without a ceiling uses Luna's profile default instead
