# codex-cross-review Specification

## Purpose
Provide independent Codex CLI plan and implementation reviews under a Claude Code orchestrator, with explicit scope, ChatGPT-login preflight, explicit model and effort, structured findings, and honest completion status.

## Requirements

### Requirement: Claude owns the Codex review workflow
Codex review SHALL run under a Claude Code orchestrator as an advisory external reviewer. The parent SHALL retain ownership of application changes, OpenSpec state, findings reconciliation, and the run log, and SHALL apply the shared checkpoint selection: plan review before substantial implementation, implementation review before completing substantial changes, skips for small low-risk edits, and explicit requests and opt-outs.

#### Scenario: Codex review under Claude
- **WHEN** a Claude-host parent selects an implementation review
- **THEN** Codex returns advisory findings through the launcher and the parent verifies and dispositions them before integration

#### Scenario: Planning-only request
- **WHEN** the user authorizes planning only for a substantial feature
- **THEN** Codex reviews the plan and the workflow stops without implementing it

### Requirement: Codex preflight without login or billing changes
Before any model call, the launcher SHALL resolve a verified Codex executable, confirm the controls the invocation uses, confirm ChatGPT login and the default model provider from the same effective configuration the review will use, and confirm that the exact requested model and effort are advertised by local model metadata. Any unverified prerequisite or override SHALL block with an actionable message. The launcher MUST NOT log in, switch billing, install software, or change persistent Codex settings.

#### Scenario: API key environment present
- **WHEN** an OpenAI or Codex API key or base-URL override is present
- **THEN** no review model call starts and the report names the blocking prerequisite without printing its value

#### Scenario: Alternate provider or missing control
- **WHEN** effective configuration from persistent, project, or invocation sources selects a non-default model provider or credential source, or the CLI lacks a control the invocation uses
- **THEN** preflight blocks before any model call and names the prerequisite

#### Scenario: Unadvertised effort
- **WHEN** the requested model is listed but does not advertise the requested effort
- **THEN** preflight blocks with the requested combination identified and no other effort or model is used

#### Scenario: Not logged in with ChatGPT
- **WHEN** login status is missing, unrecognized, or reports API-key authentication
- **THEN** the review is blocked as an authentication prerequisite and no login flow is started

### Requirement: Explicit per-review Codex settings
The launcher SHALL require an explicit model and effort, normally resolved from the `codex-review` route, and SHALL apply them to that invocation only. It SHALL have no implicit model or effort default and SHALL NOT fall back automatically. Reports SHALL record the requested model and reasoning effort, and the observed model and effort when reported, or unknown otherwise.

#### Scenario: Effort omitted
- **WHEN** an invocation omits model or effort or supplies whitespace
- **THEN** it is rejected before preflight or model execution, while freshness-only queries still work

#### Scenario: Ambient Codex defaults differ
- **WHEN** the user's Codex configuration names a different default model or effort
- **THEN** the review requests the resolved model and effort and leaves the configuration unchanged

### Requirement: Advisory read-only Codex review
Codex review SHALL be advisory and read-only. It SHALL be able to investigate the repository and declared read roots under the user's ordinary configuration, SHALL NOT edit files, deploy, or start nested agents, and SHALL NOT use approval or sandbox bypass options. Denied optional investigation SHALL be a limitation; observed nested agent activity SHALL fail the attempt as incomplete.

#### Scenario: Review instructions request edits
- **WHEN** supplied guidance or repository instructions ask for implementation or delegation
- **THEN** the review remains advisory and returns findings within the existing authorization

#### Scenario: Nested agent activity observed
- **WHEN** the review output reports that Codex started another agent
- **THEN** host execution is failed, the checkpoint is incomplete, and a process diagnostic is recorded

### Requirement: Scoped evidence for plan and implementation review
Codex review SHALL use the shared manifest and packet contract: repository, phase, verified Git baseline for implementation, selected committed, staged, unstaged, and untracked contents, required and optional context, specialist guidance, requirement mappings, exclusions, parent-owned checks, and verification evidence. Plan reviews SHALL be supported without a code diff. Missing required evidence SHALL block preparation.

#### Scenario: Plan review packet
- **WHEN** the parent supplies OpenSpec planning artifacts for a plan phase
- **THEN** preparation succeeds without a code diff and Codex reviews against plan criteria without treating absent implementation as a defect

#### Scenario: Missing required evidence
- **WHEN** a selected path, required context, or mapped requirement evidence is unavailable
- **THEN** preparation blocks with the missing item identified and no model call starts

### Requirement: Validated Codex findings and honest status
The launcher SHALL accept only structured output with a valid verdict, required coverage, findings, and limitations, and SHALL save execution status separately from the model verdict. Malformed or missing output, omitted required coverage, authentication or usage failures, timeouts, and interruption SHALL produce failed or incomplete results with sanitized diagnostics. Timeouts and interruption SHALL terminate the owned process tree. Process success SHALL NOT establish approval.

#### Scenario: Schema-valid empty optional data
- **WHEN** Codex returns a schema-valid report whose optional lists are empty
- **THEN** the shared validator accepts it with the same verdict and coverage as an equivalent Claude report

#### Scenario: Malformed output
- **WHEN** Codex returns output that does not match the review schema
- **THEN** the attempt fails with a sanitized diagnostic and no clean verdict is inferred

#### Scenario: Usage limit reached
- **WHEN** Codex reports a usage or rate limit
- **THEN** the attempt is recorded as failed with a usage diagnostic and is not retried automatically

#### Scenario: Timeout
- **WHEN** the review exceeds its finite wall-clock limit
- **THEN** the owned process tree is terminated, progress and the reason are retained, and the result is incomplete

#### Scenario: Source changes after capture
- **WHEN** captured inputs change during or after a completed review
- **THEN** the report keeps its captured-version verdict, freshness queries identify the changed inputs, and the parent reconciles them within the one-recheck bound

### Requirement: Codex review verification
Deterministic launcher tests SHALL be distinguished from live Codex review checks. Live acceptance that cannot run because of missing CLI, login, or model access SHALL remain explicitly incomplete and SHALL NOT be replaced by mocked results.

#### Scenario: Live review unavailable
- **WHEN** deterministic tests pass but a real Codex review cannot run
- **THEN** the live check is reported as unverified with its blocking prerequisite
