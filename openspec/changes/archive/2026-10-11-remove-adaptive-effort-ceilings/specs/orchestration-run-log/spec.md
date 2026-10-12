# Spec Delta

## MODIFIED Requirements

### Requirement: Decisions and outcomes
The log SHALL include session identity when available, workspace, branch, request summary, OpenSpec change, requested and known effective model/effort, complexity, role selections, resolved specialist instruction paths, brief rationales, assignments, ownership, status changes, verification results, and unresolved blockers. For configured routing, entries SHALL also identify the schema/policy version, configuration snapshot fingerprint and source paths, interaction and specialist, assessment tier and concise factors, fixed or Adaptive mode, mapped/proposed and requested effort, field provenance, session overrides, and capability validation status. Reloads SHALL identify the replacement snapshot without rewriting earlier entries. Preview output SHALL NOT count as observed execution. It SHALL record decisions not to delegate and unavailable settings honestly. Meaningful transitions SHALL use readable, timestamped run-attributed blocks with exact owned paths and evidence references. Closure SHALL distinguish task completion, native/external review, runtime acceptance and excluded or pending evidence.

#### Scenario: Dispatch and failure
- **WHEN** the orchestrator selects a worker and the dispatch fails
- **THEN** the log records the requested role/model/effort and failure without presenting the worker as running or complete

#### Scenario: Adaptive mapping and unknown effective settings
- **WHEN** Luna Adaptive maps demanding work to max and the runtime does not report effective effort
- **THEN** the log records proposed/requested max, the tier mapping and configuration provenance, and unknown observed effort without inventing a ceiling or observed execution

#### Scenario: Adaptive ceiling and unknown effective settings
- **WHEN** a policy-5 run appends entries to a log containing an earlier run's capped Luna request and the current runtime does not report effective effort
- **THEN** earlier ceiling-based entries remain intact, and the current entry records its direct mapped/requested effort and unknown observed effort without adding ceiling effects

#### Scenario: Ownership transfer
- **WHEN** an assignment changes readiness or transfers integration responsibility
- **THEN** a readable timestamped block identifies the run, assignment, owned paths, status, check/evidence and next owner

#### Scenario: Bounded capture or runtime acceptance
- **WHEN** implementation tasks are complete but some requested evidence is excluded, partial or pending
- **THEN** the closing entry records each evidence category separately without deriving acceptance from the task count or treating a disclosed exclusion as an implicit waiver
