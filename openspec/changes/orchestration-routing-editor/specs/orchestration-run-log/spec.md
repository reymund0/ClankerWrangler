## MODIFIED Requirements

### Requirement: Decisions and outcomes
The log SHALL include session identity when available, workspace, branch, request summary, OpenSpec change, requested and known effective model/effort, complexity, role selections, resolved specialist instruction paths, brief rationales, assignments, ownership, status changes, verification results, and unresolved blockers. For configured routing, entries SHALL also identify the schema/policy version, configuration snapshot fingerprint and source paths, interaction and specialist, assessment tier and concise factors, fixed or Adaptive mode, proposed and requested effort, ceiling effects, field provenance, session overrides, and capability validation status. Reloads SHALL identify the replacement snapshot without rewriting earlier entries. Preview output SHALL NOT count as observed execution. It SHALL record decisions not to delegate and unavailable settings honestly.

#### Scenario: Dispatch and failure
- **WHEN** the orchestrator selects a worker and the dispatch fails
- **THEN** the log records the requested role/model/effort and failure without presenting the worker as running or complete

#### Scenario: Adaptive ceiling and unknown effective settings
- **WHEN** Luna Adaptive proposes max but the user ceiling is xhigh and the runtime does not report effective effort
- **THEN** the log records proposed max, requested xhigh, the ceiling reason and configuration provenance, and unknown observed effort
