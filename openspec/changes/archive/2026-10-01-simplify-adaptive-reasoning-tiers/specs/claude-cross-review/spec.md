## MODIFIED Requirements

### Requirement: Review reasoning adapts to scope and risk
The Codex parent SHALL choose Claude effort before each selected review from its complexity, uncertainty, and consequence of failure. Without configured overrides, it SHALL use the shared straightforward/involved/demanding assessment and bundled medium/high/high mapping, with consequential responsibilities imposing at least involved. Configured fixed or Adaptive cross-review effort SHALL resolve through the shared routing policy, including its model mapping and ceiling; explicit supported session effort SHALL take precedence. Existing review-selection criteria and launcher capability checks SHALL still apply. Small low-risk edits SHALL still skip Claude by default; file count alone SHALL NOT determine effort. The parent SHALL log the phase, selected effort, concise reason, and any override, and pass the chosen effort explicitly to the launcher. The launcher SHALL reject missing or blank effort before preflight/model execution, retain requested effort in report metadata, and keep freshness-only checks independent of effort. Each recheck SHALL reassess remaining scope and risk without automatic escalation or downgrade, within the existing one-recheck bound.

#### Scenario: Routine bounded review
- **WHEN** a selected review covers a straightforward review with an established approach, direct checks, and no consequential responsibility
- **THEN** the parent, absent configured or session overrides, requests medium effort and records the scope-based reason

#### Scenario: Small edit and requested mechanical review
- **WHEN** a low-risk documentation or consistency edit is considered for review
- **THEN** Claude is skipped by default, or receives default medium effort when the user explicitly requests that straightforward review

#### Scenario: Consequential review despite a small diff
- **WHEN** a selected review affects authorization, data integrity, or another consequential or complex behavior
- **THEN** the parent requests default high effort regardless of the number of changed lines, unless a configured or explicit user override applies

#### Scenario: User override
- **WHEN** the user explicitly selects a supported effort for a review
- **THEN** that value is passed unchanged and recorded as an override rather than replaced by the routing recommendation

#### Scenario: Recheck effort reflects remaining risk
- **WHEN** accepted fixes or additional evidence trigger the one allowed automatic recheck
- **THEN** the parent selects and logs effort from the remaining scope and risk, retaining default high for consequential unresolved concerns and allowing default medium for a straightforward remainder, subject to configured or explicit user overrides

#### Scenario: Explicit effort required for execution
- **WHEN** a launcher review invocation omits effort or supplies only whitespace
- **THEN** it rejects the invocation before Claude preflight or model execution; freshness-only --check-current still works without effort
