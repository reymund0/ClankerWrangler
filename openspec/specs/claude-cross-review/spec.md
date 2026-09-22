# claude-cross-review Specification

## Purpose

Provide independent Claude Code plan and implementation reviews under a Codex orchestrator, with explicit scope, subscription authentication, evidence, and honest completion status.

## Requirements

### Requirement: Codex owns the cross-review workflow
The integration SHALL run under a Codex orchestrator, preserve the user-selected parent model and effort, and use Claude Code only as an external reviewer. Codex SHALL retain ownership of application changes, OpenSpec state, findings reconciliation, and the shared run log. Existing native worker routing SHALL remain unchanged unless the user overrides it.

#### Scenario: Cross-review under Codex
- **WHEN** Codex selects a Claude review
- **THEN** Claude returns advisory findings through the CLI and Codex remains responsible for integration and the final result

#### Scenario: Unsupported orchestration host
- **WHEN** the cross-review workflow is invoked with Claude Code as the orchestrator
- **THEN** it reports that Claude-led orchestration is unsupported and does not recursively launch this workflow

### Requirement: Scope determines review checkpoints
The orchestrator SHALL select plan cross-review before implementing a substantial plan and implementation cross-review after integrating substantial changes. Substantial scope SHALL include changes crossing UI/API/data contracts, consequential architecture decisions, or authentication, authorization, migration, data-integrity, deployment, or measured performance risks. Small low-risk edits SHALL be skipped by default. Explicit requests and opt-outs SHALL override automatic selection. Each selection or skip SHALL record its phase and concise reason; reviewers SHALL NOT be launched after every individual implementation task.

#### Scenario: Substantial feature
- **WHEN** a feature changes UI, API, and persistence behavior
- **THEN** the plan and integrated implementation are selected for separate cross-review checkpoints within the phases authorized by the user

#### Scenario: Small edit or explicit override
- **WHEN** a change is a small low-risk edit or the user explicitly opts out
- **THEN** automatic Claude review is skipped and the reason is recorded

#### Scenario: Planning-only request
- **WHEN** the user requests planning only for a substantial feature
- **THEN** Claude reviews the plan and the workflow stops without implementing it

### Requirement: Subscription and runtime preflight
The launcher SHALL resolve a verified Claude executable through an explicit path, PATH, or documented native install location; it SHALL work when the parent shell's PATH is stale. It SHALL verify supported invocation capabilities and subscription authentication before starting a review. Missing prerequisites, unknown authentication, API-key or alternate-provider overrides, and unsupported required controls SHALL block the review with an actionable message. It MUST NOT silently switch to API billing, install software, mutate persistent environment/authentication settings, or expose credentials.

#### Scenario: Installed executable with stale PATH
- **WHEN** Claude is absent from PATH but exists at a verified native installation path
- **THEN** the launcher can use that absolute executable path without requiring a shell restart

#### Scenario: Billing override or login unavailable
- **WHEN** an API billing override is present or subscription authentication cannot be established
- **THEN** no review model call starts, and the report explains the prerequisite without printing credentials or initiating login

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

### Requirement: Review cannot edit or delegate
Claude SHALL receive only the built-in read/search capabilities needed for review. Application edits, shell/code execution, browser actions, MCP actions, and nested delegation SHALL be unavailable. Invocation SHALL disable ambient hooks, plugins, skills, and other customizations that could expand the reviewer role, while retaining subscription authentication and honoring managed policy. Repository and review instructions SHALL be supplied explicitly. Unavailable restrictions SHALL block invocation rather than weaken the boundary.

#### Scenario: Instructions request edits or delegation
- **WHEN** repository content or a review instruction asks Claude to modify files, run a command, or spawn a worker
- **THEN** the corresponding capability is unavailable and Claude can only return findings or an access limitation

### Requirement: Review scope is explicit and current
Every review SHALL identify its repository, phase, baseline where applicable, selected requirements, authorized paths, exclusions, and verification evidence. Implementation review SHALL cover selected committed changes, staged and unstaged changes, and selected untracked files; new file names alone SHALL NOT count as reviewed content. Relevant full files and callers SHALL be available for verification. Secrets, ignored files, and unrelated user work SHALL NOT be automatically included. Evidence and file state SHALL be fingerprinted before and after review; changes to the reviewed target SHALL invalidate its applicability.

#### Scenario: Mixed working tree
- **WHEN** task work includes committed, staged, unstaged, and new files alongside unrelated edits
- **THEN** the manifest includes the authorized changes and full selected file contents, identifies exclusions, and makes no coverage claim for excluded work

#### Scenario: Review target changes
- **WHEN** a file or requirement used as review evidence changes during or after the review
- **THEN** the previous verdict is marked stale for the changed target and requires a new review or explicit user waiver before that checkpoint can be considered satisfied

### Requirement: Review modes use distinct acceptance criteria
Plan review SHALL evaluate acceptance criteria, architecture, contracts, risks, and verification strategy without demanding implementation that is not yet authorized. Implementation review SHALL reuse the existing code-review correctness, requirement-coverage, and drift criteria. Both SHALL require concrete evidence, distinguish confirmed problems from plausible concerns, and identify unreviewed scope. Initial Claude review input SHALL omit other reviewers' findings and verdicts.

#### Scenario: Independent plan critique
- **WHEN** Claude reviews an unimplemented OpenSpec plan
- **THEN** it evaluates the proposed behavior and design on their merits without reporting absence of implementation as a defect or copying another review's verdict

#### Scenario: Unread implementation scope
- **WHEN** Claude cannot inspect a required file or verify a claimed scenario
- **THEN** it reports the gap and the review is not treated as complete approval

### Requirement: Claude reuses shared specialist guidance
The parent SHALL select relevant specialist instruction files from the same role catalog used for native workers, verify their actual source/installed paths, and supply them explicitly through guidance_paths alongside the Claude cross-review reference and applicable shared code-review contract. The existing report SHALL record their provenance and fingerprints. Claude SHALL apply these files as advisory review criteria while preserving its read-only tool restrictions and independent Claude settings; implementation directives or native model defaults in a profile SHALL NOT authorize edits, execution, nested delegation, or model changes. Missing selected instructions SHALL block dispatch or be resolved by the parent before review. Shared availability SHALL NOT be treated as automatic discovery under isolated safe mode.

#### Scenario: Specialist review across domains
- **WHEN** a selected review involves architecture and data contracts
- **THEN** the parent includes the existing architect and data-engineer instructions explicitly, and the report identifies those supplied files without creating separate Claude role definitions

#### Scenario: Implementation profile remains advisory
- **WHEN** a supplied specialist profile normally includes implementation, test execution, or model-routing instructions
- **THEN** Claude uses its relevant review criteria and returns findings within the read-only boundary, while rendered visual checks and actual test execution remain with native workers

### Requirement: Structured findings and Codex reconciliation
The launcher SHALL save a validated report containing execution status, phase, scope identity, requested/observed settings, coverage, findings with evidence, limitations, and the review verdict. Process success alone SHALL NOT establish review success. Codex SHALL verify findings, record each disposition with its reason, and assign accepted fixes to the appropriate implementer. Accepted blocking findings, incomplete required coverage, or stale results SHALL keep the checkpoint unresolved unless the user explicitly waives it. Rechecks SHALL be bounded and tied to changed evidence.

#### Scenario: Valid review finds a defect
- **WHEN** Claude completes execution with an evidence-backed blocking finding
- **THEN** Codex verifies it, records its disposition, and keeps the checkpoint open for an accepted defect despite the successful process exit

#### Scenario: Invalid output or missing result
- **WHEN** Claude exits successfully but returns malformed, missing, or semantically incomplete review output
- **THEN** the launcher records an output failure and Codex does not infer approval

### Requirement: Reports integrate with the existing run log
The workflow SHALL preserve the existing daily orchestration log and parent-only writing rule. Each review SHALL have unique report paths linked to its orchestration run and phase; reruns SHALL preserve earlier results. Logs SHALL record selection, dispatch, outcome, staleness, findings dispositions, and any waiver without credentials or unnecessary source payloads. Failure to save a required report SHALL be surfaced as an incomplete review.

#### Scenario: Multiple reviews on the same day
- **WHEN** separate phases or runs produce reports on one date
- **THEN** each report remains independently identifiable and the daily log retains earlier events and links each outcome to the correct report

### Requirement: Single-skill distribution and verification
Both existing installers SHALL package Claude reviewer guidance and the launcher under the existing orchestration skill, preserve unrelated skills and existing specialist migration behavior, and create no additional discoverable skill. Installation SHALL NOT launch Claude, log in, install prerequisites, or modify model settings. Verification SHALL distinguish deterministic launcher/installer tests from live authenticated review checks.

#### Scenario: Fresh or repeated installation
- **WHEN** either wrangle installer runs against an isolated fresh or existing destination
- **THEN** the coordinator, reviewer reference, and supporting launcher are installed together with one visible orchestration skill and unrelated content preserved

#### Scenario: Live authentication unavailable during testing
- **WHEN** deterministic tests pass but a real subscription-authenticated review cannot run
- **THEN** the live check remains explicitly unverified and is not represented as a completed end-to-end test

### Requirement: Cooperative review input reservations
Before launching a final review, the coordinator SHALL quiesce writers to its selected
code, context, manifest, and external guidance. The launcher SHALL publish a unique
per-user reservation with absolute paths and initial hashes before snapshot creation.
Every write-capable assignment SHALL require checking intended file and directory
writes against active reservations. Overlapping writes SHALL be deferred; independent
work MAY continue. Reservations are advisory and SHALL NOT replace final freshness
validation or authorize filesystem permission changes.

#### Scenario: Shared guidance or directory overlaps
- **WHEN** an agent proposes editing shared guidance or moving a directory containing a reserved file
- **THEN** the write check reports the reservation and the worker defers the write and notifies the coordinator

#### Scenario: Review exits or fails
- **WHEN** a review completes, fails, times out, or is interrupted through the launcher
- **THEN** the launcher releases its own reservation without releasing other reviews' reservations

#### Scenario: Uncooperative edit or hard process termination
- **WHEN** reviewed inputs change despite the reservation
- **THEN** the completed review is reported as stale and incomplete with an explicit changed-input explanation
- **WHEN** a launcher is killed without cleanup
- **THEN** its reservation remains until the coordinator verifies the owned review has stopped and explicitly removes the orphan; elapsed time alone does not authorize removal
