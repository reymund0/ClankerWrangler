## MODIFIED Requirements

### Requirement: Versioned preferences and explicit precedence
For new runs, the system SHALL support versioned bundled defaults and the active host's global user preferences only. For each field, resolution SHALL apply bundled defaults, global interaction values, global native agent defaults, global interaction-specific specialist overrides, then explicit session overrides, in that order. Omitted fields SHALL inherit. Removing an override SHALL restore inheritance. A reasoning configuration SHALL be replaced as a complete unit rather than merging incompatible fixed and Adaptive fields. Missing global preferences SHALL use inherited defaults; malformed global files, unsupported schema versions, and invalid values SHALL be reported and SHALL block affected routing until corrected or bypassed for that run only on an explicit user instruction naming the affected file. Resolution SHALL preserve each field's source. New snapshots and helpers SHALL use policy version 7 with preference schema 1; snapshots from policy version 6 or any other mismatched version SHALL require a new run.

#### Scenario: Project and session precedence
- **WHEN** global planning uses Sol, a global architect default uses Astra, an existing project file selects Luna, and the session explicitly requests Sol
- **THEN** Sol wins from the session; removing that override exposes the global architect selection and the project file has no effect on the new run

#### Scenario: Missing versus invalid preferences
- **WHEN** no preference files exist for the Codex host
- **THEN** existing Sol planning/review, Terra implementation, and generic Opus cross-review model defaults remain available

#### Scenario: Invalid saved preferences
- **WHEN** a present preferences file has invalid syntax or an unsupported version
- **THEN** the error identifies its source and no dispatch silently proceeds using different settings

#### Scenario: Agent default and activity exception
- **WHEN** a global backend agent selects Terra and its native-review exception selects Sol
- **THEN** native review uses Sol and other applicable activities use Terra, with field-level provenance

#### Scenario: Legacy preferences and frozen snapshots
- **WHEN** existing schema-1 preferences without agent defaults, retired role IDs, or retired ceiling fields are loaded after the update
- **THEN** new snapshots use the current policy version and global-only precedence, convert legacy profile tiers as specified, and do not rewrite preference files

#### Scenario: Frozen version-1 replay
- **WHEN** an existing policy-version-1 run snapshot is resolved after the update
- **THEN** resolution rejects the snapshot with instructions to start a new run; unknown future or mismatched versions are also rejected

#### Scenario: Frozen version-2 replay
- **WHEN** an existing policy-version-2 snapshot with agent defaults and activity exceptions is resolved after the update
- **THEN** resolution rejects the snapshot with instructions to start a new run; unknown future or mismatched versions are also rejected

#### Scenario: Invalid agent default
- **WHEN** a native agent default has an unknown or retired role, a known model of the provider other than its host's, nested specialist overrides, or invalid reasoning
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
- **THEN** resolution rejects the snapshot with instructions to start a new run; new snapshots use policy version 7, and unknown future or mismatched versions remain rejected

#### Scenario: Frozen version-5 replay
- **WHEN** a policy-version-5 snapshot containing the earlier thirteen-role catalog is validated, used for effective configuration, or resolved after the update
- **THEN** the current helper rejects it with instructions to start a new run rather than replaying it, changing its role IDs, or rewriting the snapshot

#### Scenario: Current snapshots retain existing routing behavior
- **WHEN** schema-1 preferences using only active roles and valid current effort fields create a new snapshot
- **THEN** the snapshot uses policy version 7 and retains the same model, effort mapping, field precedence, and capability checks for each remaining role without rewriting preferences

#### Scenario: Frozen version-6 replay
- **WHEN** a policy-version-6 snapshot without host identity is validated, used for effective configuration, or resolved after the update
- **THEN** the current helper rejects it with instructions to start a new run rather than assuming a host or rewriting the snapshot

#### Scenario: Claude-native agent default
- **WHEN** Claude-host preferences set a backend agent default to Haiku with Adaptive reasoning
- **THEN** validation accepts it and each applicable Claude-native activity without an exception resolves Haiku with field-level provenance

### Requirement: Interaction and specialist routing
The system SHALL distinguish planning/design, implementation/testing, native code review, visual/UX review, and the host's external cross-review: `claude-review` under the Codex host and `codex-review` under the Claude host. Native agent defaults SHALL optionally apply across native interactions, with specialist overrides scoped to an interaction taking precedence within the same scope. Without agent defaults the existing phase-specific defaults SHALL remain. A cross-review using several specialist instruction files SHALL resolve one route from its cross-review interaction, without arbitrarily selecting one specialist's override. Rechecks SHALL retain their interaction and reassess their remaining scope. The parent model and effort SHALL remain the user's active session settings.

#### Scenario: One specialty in different phases
- **WHEN** a backend specialist plans a contract, implements it, and reviews it
- **THEN** planning, implementation, and native review routes are resolved separately

#### Scenario: Several Claude review specialties
- **WHEN** one Claude packet contains architect and data-engineer guidance
- **THEN** it uses one cross-review model/effort route and both instruction files only shape review criteria

#### Scenario: Several Codex review specialties
- **WHEN** one Codex review packet under the Claude host contains architect and data-engineer guidance
- **THEN** it uses one `codex-review` model/effort route and both instruction files only shape review criteria

### Requirement: Runtime compatibility and fixed model choice
The system SHALL validate a resolved request against the active runtime's model and effort capabilities before dispatch. Native dispatch under either host SHALL require exact model/effort evidence advertised by the active host's subagent mechanism. External review dispatch SHALL require successful preflight by its launcher while marking account/model access unverified until invocation; that remaining uncertainty SHALL NOT be mislabeled as native capability verification. A saved catalog SHALL be presented as configuration guidance, not proof of account access or runtime availability. Unknown or unsupported model/effort combinations SHALL be surfaced without silent substitution or clamping to an unrequested supported value. New models without an Adaptive mapping SHALL require a mapping or an explicit supported fixed effort. The first version SHALL NOT automatically switch models. Recommendations to change model or request independent review SHALL leave the selection unchanged until the user acts.

#### Scenario: Unsupported effort
- **WHEN** a profile selects max but the active runtime does not support max for that model
- **THEN** the assignment is blocked with the requested combination identified and no silent effort or model fallback

#### Scenario: Preview without live capabilities
- **WHEN** the editor can resolve a route but has no current runtime capability evidence
- **THEN** it shows the predicted settings as unverified and does not claim the model is available

#### Scenario: Claude-native alias evidence
- **WHEN** a Claude-host route requests an exact model ID while the active subagent mechanism advertises only model aliases
- **THEN** dispatch is blocked with the requested model identified and no alias is substituted

#### Scenario: Codex external review without collaboration tools
- **WHEN** a Claude-host run resolves `codex-review`
- **THEN** the decision requires Codex launcher preflight and does not require or consult native Codex collaboration tool capabilities

## ADDED Requirements

### Requirement: Host, provider, and execution identity
Every snapshot SHALL record exactly one orchestration host. Each interaction SHALL have a native or external execution kind; native interactions SHALL use the host's model provider and external interactions the other provider. Models known to belong to a different provider SHALL be rejected at their field path. Snapshots, effective configuration, and route decisions SHALL report host, provider, and execution kind alongside the existing fields.

#### Scenario: Codex-led decisions remain unchanged
- **WHEN** the same Codex preferences, request, and capabilities are resolved by the previous policy and by the current policy under the Codex host, including fixed-effort routes for exact model IDs without a custom profile
- **THEN** model, effort, tier, limitations, capability status, and provenance, including profile provenance, match, with host, provider, and execution added

#### Scenario: Wrong-provider native model
- **WHEN** Claude-host preferences select a known Codex model for implementation
- **THEN** validation rejects that field instead of routing a Codex model through Claude-native dispatch

### Requirement: Separate host preference sources
Each host SHALL read its own global preference file with the same schema: the Codex host `~/.clanker/orchestration-routing.json` and the Claude host `~/.clanker/orchestration-routing-claude.json`. Existing Codex preference paths and bytes SHALL be preserved. Neither host SHALL read, import, or change the other's file. Each document SHALL be validated against its host's interaction set, so the other host's external-review interaction is rejected.

#### Scenario: Existing Codex preferences after upgrade
- **WHEN** a Codex-led run starts after the update with the user's existing preference file
- **THEN** it reads the same file unchanged and resolves the same routes, and no Claude-host file is created

#### Scenario: Missing Claude preferences
- **WHEN** a Claude-led run starts with no Claude-host preference file
- **THEN** bundled Claude-host defaults apply and the Codex preference file is neither read nor modified

#### Scenario: Cross-host interaction key
- **WHEN** Claude-host preferences contain `claude-review` or Codex-host preferences contain `codex-review`
- **THEN** validation identifies the unsupported interaction at its field path and blocks affected routing

### Requirement: Claude-host bundled defaults
Without Claude-host overrides, planning, native review, and visual review SHALL default to Sonnet, implementation SHALL default to Haiku, and `codex-review` SHALL default to `gpt-6.1-sol`, each with Adaptive reasoning backed by a bundled profile. Bundled profiles SHALL be host-scoped so that adding Claude-host profiles does not change Codex-host resolution. Bundled defaults SHALL remain configuration guidance subject to runtime capability checks.

#### Scenario: Default Claude-host preview
- **WHEN** a Claude-host route is previewed with no saved preferences
- **THEN** it shows the bundled model, the Adaptive tier mapping, and an unverified capability status without claiming account access

### Requirement: Installed host configuration
Installed bundles SHALL contain a strictly validated host configuration naming the host, its preference file, its external-review interaction, and its launcher. Snapshot creation SHALL default to that host, SHALL default to the Codex host only when no host configuration exists, and SHALL reject an explicit host that contradicts the installed configuration.

#### Scenario: Same snapshot command in both harnesses
- **WHEN** the coordinator runs the documented snapshot command from a Codex or a Claude installation without naming a host
- **THEN** each snapshot records its installation's host and preference source

#### Scenario: Contradictory host request
- **WHEN** a caller requests the Claude host from a bundle whose host configuration names Codex
- **THEN** snapshot creation fails without reading either preference file

### Requirement: Route-replacing runtime overrides
Requests SHALL be able to report observed runtime settings that would replace the requested route. Any reported override SHALL block dispatch with a limitation naming it, without predicting the substituted value. Requested settings SHALL be recorded separately from observed settings.

#### Scenario: Forced subagent model
- **WHEN** a Claude-host request reports a forced subagent model setting
- **THEN** the decision is not dispatchable and names the setting, while still showing the requested model and effort
