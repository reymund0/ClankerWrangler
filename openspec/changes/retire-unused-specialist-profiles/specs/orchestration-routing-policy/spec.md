## MODIFIED Requirements

### Requirement: Versioned preferences and explicit precedence
For new runs, the system SHALL support versioned bundled defaults and global user preferences only. For each field, resolution SHALL apply bundled defaults, global interaction values, global native agent defaults, global interaction-specific specialist overrides, then explicit session overrides, in that order. Omitted fields SHALL inherit. Removing an override SHALL restore inheritance. A reasoning configuration SHALL be replaced as a complete unit rather than merging incompatible fixed and Adaptive fields. Missing global preferences SHALL use inherited defaults; malformed global files, unsupported schema versions, and invalid values SHALL be reported and SHALL block affected routing until corrected or bypassed for that run only on an explicit user instruction naming the affected file. Resolution SHALL preserve each field's source. New snapshots and helpers SHALL use policy version 6 with preference schema 1; snapshots from policy version 5 or any other mismatched version SHALL require a new run.

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
- **WHEN** existing schema-1 preferences without agent defaults, retired role IDs, or retired ceiling fields are loaded after the update
- **THEN** new snapshots use the current policy version and global-only precedence, convert legacy profile tiers as specified, and do not rewrite preference files

#### Scenario: Frozen version-1 replay
- **WHEN** an existing policy-version-1 run snapshot is resolved after the update
- **THEN** resolution rejects the snapshot with instructions to start a new run; unknown future or mismatched versions are also rejected

#### Scenario: Frozen version-2 replay
- **WHEN** an existing policy-version-2 snapshot with agent defaults and activity exceptions is resolved after the update
- **THEN** resolution rejects the snapshot with instructions to start a new run; unknown future or mismatched versions are also rejected

#### Scenario: Invalid agent default
- **WHEN** a native agent default has an unknown or retired role, a known Claude model, nested specialist overrides, or invalid reasoning
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
- **THEN** resolution rejects the snapshot with instructions to start a new run; new snapshots use policy version 6, and unknown future or mismatched versions remain rejected

#### Scenario: Frozen version-5 replay
- **WHEN** a policy-version-5 snapshot containing the earlier thirteen-role catalog is validated, used for effective configuration, or resolved after the update
- **THEN** the current helper rejects it with instructions to start a new run rather than replaying it, changing its role IDs, or rewriting the snapshot

#### Scenario: Current snapshots retain existing routing behavior
- **WHEN** schema-1 preferences using only active roles and valid current effort fields create a new snapshot
- **THEN** the snapshot uses policy version 6 and retains the same model, effort mapping, field precedence, and capability checks for each remaining role without rewriting preferences

## ADDED Requirements

### Requirement: Active native specialist catalog
The current policy SHALL support exactly ten native roles covering architecture, backend, data, DevOps, performance, QA, testing, UI implementation, UI/UX review, and code/security review. Retired UX designer, documentation writer, and product engineer IDs SHALL be invalid in bundled catalogs, requests, agent defaults, and interaction-specific overrides. Rejection SHALL identify the field without remapping, ignoring it, or permitting dispatch.

#### Scenario: Active catalog membership
- **WHEN** a current bundled catalog is validated and exposed to routing consumers
- **THEN** its native IDs are exactly clanker-architect, clanker-backend-developer, clanker-data-engineer, clanker-devops-engineer, clanker-performance-engineer, clanker-qa-engineer, clanker-test-engineer, clanker-ui-developer, clanker-ui-ux-reviewer, and clanker-code-review

#### Scenario: Retired request role
- **WHEN** a request names clanker-ux-designer, clanker-documentation-writer, or clanker-product-engineer
- **THEN** validation rejects request.role before dispatch and does not substitute another role or a role-less route

#### Scenario: Retired saved overrides
- **WHEN** global preferences contain any retired role ID in agents or an interaction's specialists
- **THEN** validation identifies that full field path and prevents snapshot creation from that invalid document, leaving the saved bytes unchanged

#### Scenario: Retired catalog entry
- **WHEN** a current bundle includes a retired role or substitutes it for one of the ten active roles
- **THEN** bundle validation rejects that catalog rather than making the retired role selectable or dispatchable

#### Scenario: Explicit owner correction
- **WHEN** the owner explicitly supplies and saves an otherwise valid replacement that removes retired role overrides
- **THEN** existing revision and validation protections apply, unrelated retained-role overrides remain intact, and a new policy-6 run can be created without role migration or automatic preference cleanup
