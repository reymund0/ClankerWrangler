# orchestration-run-log Specification

## Purpose

Give the user a durable, readable record of orchestration choices and outcomes for each orchestration run under either host, alongside existing Clanker output files.

## Requirements

### Requirement: Daily output filename
The skill SHALL write its audit output beneath the target repository's `.clanker` directory with filename `{date}-orchestration-nation.md`, where date is the local run-start date formatted as `YYYY-MM-DD` to match existing Clanker conventions. A continuing run SHALL retain its chosen file across midnight.

#### Scenario: Initial run
- **WHEN** a run starts on local date 2026-09-21
- **THEN** its output is `.clanker/2026-09-21-orchestration-nation.md`

### Requirement: Preserve previous runs
The skill SHALL append run-attributed entries without overwriting previous output. Separate invocations SHALL have distinct run identifiers, and each event SHALL carry its run identifier so concurrent or resumed activity stays attributable.

#### Scenario: Two invocations on the same date
- **WHEN** a second invocation finds an existing daily log
- **THEN** it appends a new run and preserves the previous run's content

#### Scenario: Resumption
- **WHEN** a session resumes work on an existing run
- **THEN** it reads the existing entries and appends a continuation using that run's identifier and original file

### Requirement: Decisions and outcomes
The log SHALL include session identity when available, workspace, branch, request summary, OpenSpec change, requested and known effective model/effort, complexity, role selections, resolved specialist instruction paths, brief rationales, assignments, ownership, status changes, verification results, and unresolved blockers. For configured routing, entries SHALL also identify the schema/policy version, configuration snapshot fingerprint and source paths, interaction and specialist, assessment tier and concise factors, fixed or Adaptive mode, mapped/proposed and requested effort, field provenance, session overrides, and capability validation status. Reloads SHALL identify the replacement snapshot without rewriting earlier entries. Preview output SHALL NOT count as observed execution. It SHALL record decisions not to delegate and unavailable settings honestly. Meaningful transitions SHALL use readable, timestamped run-attributed blocks with exact owned paths and evidence references. Closure SHALL distinguish task completion, native/external review, runtime acceptance and excluded or pending evidence.

#### Scenario: Dispatch and failure
- **WHEN** the orchestrator selects a worker and the dispatch fails
- **THEN** the log records the requested role/model/effort and failure without presenting the worker as running or complete

#### Scenario: Adaptive ceiling and unknown effective settings
- **WHEN** a policy-5 run appends entries to a log containing an earlier run's capped Luna request and the current runtime does not report effective effort
- **THEN** earlier ceiling-based entries remain intact, and the current entry records its direct mapped/requested effort and unknown observed effort without adding ceiling effects

#### Scenario: Ownership transfer
- **WHEN** an assignment changes readiness or transfers integration responsibility
- **THEN** a readable timestamped block identifies the run, assignment, owned paths, status, check/evidence and next owner

#### Scenario: Bounded capture or runtime acceptance
- **WHEN** implementation tasks are complete but some requested evidence is excluded, partial or pending
- **THEN** the closing entry records each evidence category separately without deriving acceptance from the task count or treating a disclosed exclusion as an implicit waiver

#### Scenario: Adaptive mapping and unknown effective settings
- **WHEN** Luna Adaptive maps demanding work to max and the runtime does not report effective effort
- **THEN** the log records proposed/requested max, the tier mapping and configuration provenance, and unknown observed effort without inventing a ceiling or observed execution

### Requirement: Single writer and safe log content
The orchestrator SHALL be the sole log writer within a run. Entries SHALL contain concise decision summaries and evidence references, excluding secrets, raw private payloads, and hidden chain-of-thought. A logging failure MUST be disclosed and MUST NOT be reported as a saved file.

#### Scenario: Worker returns a secret-containing error
- **WHEN** a worker's tool output includes credentials or unrelated private content
- **THEN** the orchestrator records a sanitized blocker summary instead of copying the payload

### Requirement: Final run outcome
Before ending a run the orchestrator SHALL append the completed, blocked, or interrupted outcome when execution permits and provide the actual log path to the user. Abrupt interruption MAY leave a running entry, which MUST be reconciled from observed state on resume.

#### Scenario: Verification blocked
- **WHEN** required validation cannot finish
- **THEN** the final entry identifies the remaining check and the conversation links the saved log without claiming full completion

### Requirement: Host identity in routing and review evidence
Run-start entries SHALL record the orchestration host and its preference source. Routing evidence SHALL retain host, provider, and execution kind from resolver output without manual transcription. External review entries SHALL identify the reviewer provider and link its report. Closing entries SHALL keep native review, external review, and runtime or visual acceptance as separate evidence states.

#### Scenario: Claude-led run with Codex review
- **WHEN** a Claude-host run dispatches Haiku implementation and a Codex plan review
- **THEN** the log records the Claude host and preference source, native Claude execution for the worker, external Codex execution for the review, requested settings, and unknown observed settings where not reported

### Requirement: Readable model and reasoning settings
Every worker dispatch and external review entry SHALL state, in its readable block, the model and reasoning effort requested, including fixed or Adaptive mode and the assessed tier, and the observed model and effort when the runtime or reviewer envelope reports them. Unreported observed values SHALL read as unknown and SHALL NOT be inferred from the request or from model self-description.

#### Scenario: Codex review with unreported model
- **WHEN** a Codex review completes and its output reports no model or effort
- **THEN** the entry shows the requested model and reasoning effort and observed model and effort as unknown

#### Scenario: Claude review with reported model
- **WHEN** a Claude review envelope reports the model used
- **THEN** the entry shows that observed model beside the requested model and effort

### Requirement: Clock-sourced timestamps
Every run-log block and ledger row SHALL carry a time read from the host clock when it is written, including the timezone offset. Times SHALL NOT be estimated, reconstructed, or copied from an earlier entry.

#### Scenario: Entry written after a long gap
- **WHEN** the parent appends an entry an hour after the previous one
- **THEN** the entry's time is the clock time at the moment of writing, not an estimate of when the event occurred

#### Scenario: Work continues after the completion entry
- **WHEN** acceptance work is appended after a run's completion entry
- **THEN** each later entry carries its own clock time, so file order and recorded times agree

### Requirement: Orchestration analysis ledger
The orchestrator SHALL append one CSV row per orchestration event to `.clanker/orchestration-ledger.csv` in the target repository. When the file is absent it SHALL create it with a header row. It SHALL never rewrite or reorder existing rows, and SHALL write each row with standard CSV quoting. If the columns change, rows SHALL go to a new versioned file instead of mixing headers in one file.

#### Scenario: First event in a repository
- **WHEN** a run records its first event and the ledger file does not exist
- **THEN** the orchestrator creates the file with the header row and appends the event row

#### Scenario: Detail text with commas or quotes
- **WHEN** an event's detail contains commas, quotes, or other characters that are special in CSV
- **THEN** the row is quoted so every value stays in its own column when the file is imported

#### Scenario: Concurrent runs in one repository
- **WHEN** two runs append events to the same ledger
- **THEN** each row carries its run identifier, and no earlier row is changed

### Requirement: Ledger events and columns
Ledger rows SHALL use these columns in order: `time`, `run`, `workstream`, `event`, `thread`, `lead_role`, `route`, `detail`, `followup_kind`, `defect_source`, `observed_model`, `observed_effort`, `final_context`, `outcome`. The `event` value SHALL be one of `start`, `assign-new`, `assign-continued`, `parent-kept`, or `retire`. `followup_kind` SHALL be `defect` or `scope` on `assign-continued` rows. Columns that do not apply to an event SHALL be left empty.

#### Scenario: Continued assignment
- **WHEN** the parent sends a review fix to an existing workstream thread
- **THEN** the ledger gains an `assign-continued` row naming the workstream, thread, and fix, with `followup_kind` set to `defect`, the finding source in `defect_source`, and the outcome columns empty

#### Scenario: Parent keeps a fix
- **WHEN** the parent makes a diagnosed fix itself
- **THEN** the ledger gains a `parent-kept` row naming the workstream and the reason

### Requirement: Workstream outcomes
Each `retire` row SHALL record the workstream's outcome, decided from parent verification evidence rather than worker reports:
- `first-pass`: accepted without fixes;
- `revised`: fixed by the same thread;
- `rerouted`: the parent took over a fix, or the user directed the work to a different route, naming the replacement;
- `blocked`: not completed.

Follow-up counts SHALL be derived from the workstream's `assign-continued` rows by `followup_kind`; the retire row SHALL name what found the defects. Observed model, effort, and final context SHALL come from runtime evidence when readable, and otherwise read `unknown`. Work after a retire row SHALL be recorded in new rows.

#### Scenario: Review fixes made by the same thread
- **WHEN** a workstream thread fixes two native-review findings and passes parent verification
- **THEN** its two `assign-continued` rows carry `followup_kind` `defect`, and its retire row records `revised` with native review as the defect source

#### Scenario: Scope change follow-up
- **WHEN** a workstream receives a follow-up because the user revised a requirement, and passes verification without defect fixes
- **THEN** that `assign-continued` row carries `followup_kind` `scope`, and the retire row records `first-pass`

#### Scenario: Unfinished work at run end
- **WHEN** a run ends blocked with a workstream's assignment still unverified
- **THEN** the ledger gains a retire row for that workstream with outcome `blocked`

#### Scenario: Transcript evidence available
- **WHEN** the host keeps a readable transcript recording the worker's model, effort, and context size
- **THEN** the retire row records those observed values; otherwise those columns read `unknown`

#### Scenario: Parent takes over a fix
- **WHEN** the parent makes a workstream's fix itself after the thread's attempt failed verification
- **THEN** the ledger gains a `parent-kept` row, and the workstream's retire row records `rerouted` naming the parent as the replacement

#### Scenario: Worker claims completion without passing verification
- **WHEN** a worker reports ready for integration but required parent verification fails and the work is not completed
- **THEN** the workstream's retire row records `blocked` rather than `first-pass`

#### Scenario: Outcome recorded without an end-of-run summary
- **WHEN** a workstream is retired before the run's completion entry and more work follows that entry
- **THEN** the workstream's outcome is already in the ledger, and later work adds rows without rewriting or delaying earlier outcomes
