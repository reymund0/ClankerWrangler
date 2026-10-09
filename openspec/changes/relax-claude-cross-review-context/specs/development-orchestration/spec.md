## MODIFIED Requirements

### Requirement: Coherent review scopes
The parent SHALL assign code review, browser acceptance and executable verification to their appropriate owners. Cross-review SHALL receive the parent's authorized read scope and explicitly selected evidence without a second export policy or redundant approval. Required changes/requirements SHALL be distinguished from optional context. The packet SHALL seed investigation and preserve versions without preventing dependency discovery or reserving originals throughout review. The parent SHALL retain aggregate acceptance and reconcile later relevant changes before integrating findings.

#### Scenario: Bounded recheck
- **WHEN** review covers a bounded correction within a larger change
- **THEN** its required evidence matches the correction, relevant supporting context remains available, and broader acceptance remains parent-owned

#### Scenario: Already authorized cross-review
- **WHEN** the user's request already authorizes review of the task and its relevant files
- **THEN** the parent supplies that scope without asking again merely because the same files go to Claude

#### Scenario: Writers continue after capture
- **WHEN** a reviewer is running against captured change evidence
- **THEN** original-source writes are coordinated by actual ownership/dependencies and are not blocked solely by that review's existence

### Requirement: Bounded parallel ownership
Every delegated assignment SHALL include scope, context, file ownership, dependencies, and expected verification. The orchestrator SHALL retain ownership of the shared log and OpenSpec task state, serialize overlapping edits, and respect the runtime's concurrency limit. Workers MUST return blockers and MUST NOT recursively delegate unless separately authorized. Artifact consumers SHALL wait for successful producer completion. Changed-file inventories SHALL be reconciled with ownership; new captured reviews SHALL NOT impose full-run input reservations or mandatory reservation prechecks.

#### Scenario: Shared-file dependency
- **WHEN** two assignments need to modify the same file or an unsettled shared interface
- **THEN** they are combined or sequenced rather than dispatched as conflicting parallel writers

#### Scenario: Verification consumes build output
- **WHEN** verification needs build or staging output
- **THEN** the parent waits for successful producer completion and records the consumed artifact identity

#### Scenario: Changed file absent from checked paths
- **WHEN** a legacy worker reports a changed file absent from its declared write checks
- **THEN** the parent records the legacy deviation and verifies actual ownership without reintroducing mandatory reservation checks for new captured reviews
