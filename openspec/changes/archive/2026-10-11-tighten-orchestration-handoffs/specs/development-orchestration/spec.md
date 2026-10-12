## MODIFIED Requirements

### Requirement: Bounded parallel ownership
Every delegated assignment SHALL include scope, context, file ownership, dependencies, and expected verification. The orchestrator SHALL retain ownership of the shared log and OpenSpec task state, serialize overlapping edits, and respect the runtime's concurrency limit. Workers MUST return blockers and MUST NOT recursively delegate unless separately authorized. Artifact consumers SHALL wait for the owned producer to finish successfully. Write-capable handoffs SHALL report checked paths, and the parent SHALL reconcile them with changed-file ownership before integration.

#### Scenario: Shared-file dependency
- **WHEN** two assignments need to modify the same file or an unsettled shared interface
- **THEN** they are combined or sequenced rather than dispatched as conflicting parallel writers

#### Scenario: Verification consumes build output
- **WHEN** inventory, bytecode, hash or launcher verification needs build or staging output
- **THEN** the parent waits for successful producer completion and records the consumed artifact identity before accepting the check

#### Scenario: Changed file absent from checked paths
- **WHEN** a worker reports a change not covered by its cooperative write checks
- **THEN** the parent records the deviation, checks actual ownership and reservation impact, and corrects future batches without retrospectively claiming that the write was checked

### Requirement: Explicit worker readiness
Worker handoffs SHALL distinguish draft, locally checked, and ready for integration. Executable changes SHALL receive the smallest relevant authorized compile or contract check before a readiness claim. Every handoff SHALL state changed files, exact checks/results, and remaining blockers; parent integration verification remains required. Test assignments SHALL verify current fixture/API contracts against an analogous working test. When worker execution is unavailable, the parent SHALL assign an integration check owner before combined acceptance execution.

#### Scenario: Worker cannot run verification
- **WHEN** execution is unavailable or outside a worker's assignment
- **THEN** the worker returns a draft with the unrun check and reason, rather than claiming readiness

#### Scenario: New fixture setup families
- **WHEN** an assignment introduces materially different fixture setup
- **THEN** current API signatures and an analogous test are checked, and an owner performs the smallest authorized compile/representative setup checks before the combined acceptance selection

## ADDED Requirements

### Requirement: Prompt advisory evidence handback
An advisory worker SHALL promptly identify inaccessible required evidence, continue accessible inspection where useful, and return its evidence limits. The parent SHALL resolve access or retain a draft without requiring unnecessary project execution or concealing missing coverage.

#### Scenario: Required planning file inaccessible
- **WHEN** a read-only reviewer cannot access a required OpenSpec artifact
- **THEN** it reports the exact missing evidence to the parent, continues useful authorized inspection, and does not claim complete coverage while waiting for access
