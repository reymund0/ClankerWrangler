## ADDED Requirements

### Requirement: Coherent review scopes
The parent SHALL assign static code review, browser acceptance, and executable verification to their appropriate owners. Before external dispatch it SHALL inspect local packet readiness and confirm authorization for that exact source/destination scope. Large packets SHALL be split into coherent scopes where needed; aggregate acceptance and unresolved checks SHALL remain parent-owned.

#### Scenario: Bounded recheck
- **WHEN** a review covers a small fix within a larger change
- **THEN** its static requirements and evidence match that scope, and unrelated acceptance remains explicitly tracked by the parent

### Requirement: Capacity-aware dispatch
The parent SHALL inspect available worker state before spawning and prefer suitable idle-worker reuse or sequencing when capacity is exhausted. Reuse SHALL preserve the resolved model/effort, role guidance, and ownership contract. Failed dispatch SHALL NOT count as a running assignment.

#### Scenario: No suitable worker slot
- **WHEN** the runtime rejects dispatch for capacity and no idle worker matches the resolved settings
- **THEN** the parent sequences the work or handles authorized work directly instead of repeatedly spawning or silently changing settings

### Requirement: Explicit worker readiness
Worker handoffs SHALL distinguish draft, locally checked, and ready for integration. Executable changes SHALL receive the smallest relevant authorized compile or contract check before a readiness claim. Every handoff SHALL state changed files, exact checks/results, and remaining blockers; parent integration verification remains required.

#### Scenario: Worker cannot run verification
- **WHEN** execution is unavailable or outside a worker's assignment
- **THEN** the worker returns a draft with the unrun check and reason, rather than claiming readiness
