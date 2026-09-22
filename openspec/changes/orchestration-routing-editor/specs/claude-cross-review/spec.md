## MODIFIED Requirements

### Requirement: Reviewer settings are explicit and bounded
The workflow SHALL allow a user-selected Claude model and supported effort without changing persistent configuration. For orchestrated reviews, the parent SHALL resolve saved cross-review preferences and session overrides and pass the resulting model and effort explicitly. With no configured or explicit per-review model override, and for direct launcher calls without --model, it SHALL request Claude Opus 5 using claude-opus-5 regardless of ambient model defaults, and report the observed model when available; unknown effective settings SHALL remain unknown. The launcher SHALL enforce a finite timeout and turn bound, use no automatic model fallback, and report denied tools, usage exhaustion, unsupported settings, and interruption as incomplete or failed execution.

#### Scenario: User-selected reviewer model
- **WHEN** the user selects an available Claude model and effort
- **THEN** those settings are requested for that review and recorded separately from observed settings

#### Scenario: Opus 5 default with adaptive effort
- **WHEN** a Claude cross-review has no configured or explicit per-review model override, including when ambient settings select another model
- **THEN** the launcher explicitly requests claude-opus-5, records that requested model, preserves the separately selected effort, and leaves persistent settings unchanged

#### Scenario: Interrupted or exhausted review
- **WHEN** the process times out, reaches its turn limit, or exhausts subscription usage
- **THEN** execution is terminated or collected as incomplete, with no clean-review claim or unbounded retry

#### Scenario: Saved reviewer route
- **WHEN** a valid saved cross-review route selects a different supported Claude model
- **THEN** Codex passes that model and resolved effort explicitly to the launcher, while direct invocations without --model retain the Opus 5 default

### Requirement: Review reasoning adapts to scope and risk
The Codex parent SHALL choose Claude effort before each selected review from its complexity, uncertainty, and consequence of failure. Without configured overrides, it SHALL use low for explicitly requested mechanical documentation/consistency checks, medium for routine bounded planning or implementation review, and high for complex architecture, cross-layer contracts, security, data integrity/migrations, deployment/recovery, or complex performance reviews. Configured fixed or Adaptive cross-review effort SHALL resolve through the shared routing policy, including its model mapping and ceiling; explicit supported session effort SHALL take precedence. Existing review-selection criteria and launcher capability checks SHALL still apply. Small low-risk edits SHALL still skip Claude by default; file count alone SHALL NOT determine effort. The parent SHALL log the phase, selected effort, concise reason, and any override, and pass the chosen effort explicitly to the launcher. The launcher SHALL reject missing or blank effort before preflight/model execution, retain requested effort in report metadata, and keep freshness-only checks independent of effort. Each recheck SHALL reassess remaining scope and risk without automatic escalation or downgrade, within the existing one-recheck bound.

#### Scenario: Routine bounded review
- **WHEN** a selected review covers a routine feature plan, acceptance/test strategy, or bounded backend/UI change with clear requirements and no consequential risk
- **THEN** the parent, absent configured or session overrides, requests medium effort and records the scope-based reason

#### Scenario: Small edit and requested mechanical review
- **WHEN** a low-risk documentation or consistency edit is considered for review
- **THEN** Claude is skipped by default, or receives default low effort when the user explicitly requests that mechanical review

#### Scenario: Consequential review despite a small diff
- **WHEN** a selected review affects authorization, data integrity, or another consequential or complex behavior
- **THEN** the parent requests default high effort regardless of the number of changed lines, unless a configured or explicit user override applies

#### Scenario: User override
- **WHEN** the user explicitly selects a supported effort for a review
- **THEN** that value is passed unchanged and recorded as an override rather than replaced by the routing recommendation

#### Scenario: Recheck effort reflects remaining risk
- **WHEN** accepted fixes or additional evidence trigger the one allowed automatic recheck
- **THEN** the parent selects and logs effort from the remaining scope and risk, retaining default high for consequential unresolved concerns and allowing default low for a purely mechanical remainder, subject to configured or explicit user overrides

#### Scenario: Explicit effort required for execution
- **WHEN** a launcher review invocation omits effort or supplies only whitespace
- **THEN** it rejects the invocation before Claude preflight or model execution; freshness-only --check-current still works without effort
