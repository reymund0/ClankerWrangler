## Purpose

Record each design or orchestration run in an append-only event log and summarize it in run and findings tables for analysis.

## ADDED Requirements

### Requirement: Append-only run log
Every design or orchestration chat run SHALL keep one append-only event log at `<repo>/.clanker/runs/<run>.jsonl`, created when the run starts. Each state change SHALL be appended as one JSON line, and existing lines SHALL never be rewritten. The run ID SHALL be `<YYYYMMDD-HHMMSS>-<change>` from the host clock at start.

#### Scenario: Finding resolved after being logged
- **WHEN** a finding is recorded as accepted and later fixed by the Implementor
- **THEN** the log has the original `finding` event and a later event recording the fix, and neither line is rewritten

#### Scenario: Run stopped by the user
- **WHEN** the user stops a run after a gate's second round
- **THEN** the run log contains a start event and an end event with outcome `blocked`

### Requirement: Logged run content
The run log SHALL record the run identity, chat kind, host, change, the model and effort per role at start, gate and round starts and results, each finding and every change to its triage or resolution, user decisions, functional rounds, usage as it becomes available, and the end outcome.

#### Scenario: User decision recorded
- **WHEN** the user skips a `user-decision` finding
- **THEN** an event records the finding ID and the `skip` decision

### Requirement: Run outcomes
A run SHALL end with one outcome: `done`, or `blocked` when the user stops it.

#### Scenario: User stops at the round limit
- **WHEN** findings remain after a gate's second round and the user chooses to stop
- **THEN** the run ends with outcome `blocked`

### Requirement: Design run ends at the plan gate
The design chat's run SHALL end when the plan gate passes, with outcome `done`, or with `blocked` when the user stops it.

#### Scenario: Plan gate passes
- **WHEN** the plan gate passes in the design chat
- **THEN** the design run ends with outcome `done` and its final rows are written

### Requirement: Final CSV tables built from the run log
When a run ends, the caller SHALL append one row to `<repo>/.clanker/runs.csv` and one final row per finding to `<repo>/.clanker/findings.csv`, built from the run log. The tables SHALL hold only final values.

#### Scenario: Implementation run completes
- **WHEN** the orchestrator hands the thread to the user
- **THEN** one `runs.csv` row with outcome `done` and one `findings.csv` row per finding are appended

### Requirement: Run table columns
Each `runs.csv` row SHALL record the run ID, chat kind, host, change, start and end times, and outcome. It SHALL also record the model and effort per role, tokens per role including cross-review, cross-review seconds, plan, code, and refactor rounds, functional cycles, small fixes by the orchestrator, and short notes.

#### Scenario: Design chat completes
- **WHEN** the design run ends with the plan gate passed
- **THEN** its `runs.csv` row has chat `design`, the change name, outcome `done`, and `plan_rounds` filled

### Requirement: Per-role model columns
The run table SHALL record each role's model and effort as `model/effort` from runtime evidence. When only the requested value is known, it SHALL record `model/effort (req)`. It SHALL NOT present a requested value as observed.

#### Scenario: Observed settings unavailable
- **WHEN** the runtime does not report the Reviewer's model
- **THEN** `reviewer_model` holds the routed value with the `(req)` suffix

### Requirement: Findings table columns
Each `findings.csv` row SHALL record the run, gate, round, finding ID, source, severity (`blocking`, `major`, `minor`, `info`, or `proposal`), summary, triage, the user's decision when asked, what fixed it, and the reject reason when rejected.

#### Scenario: Refactor proposal accepted
- **WHEN** the caller confirms a refactor proposal
- **THEN** its row has severity `proposal`, triage `accept`, and no `user_decision`

### Requirement: Usage from runtime evidence
Token and time values SHALL come from runtime evidence, such as subagent completion usage, transcripts, and cross-review reports. Values that are not available SHALL stay empty and SHALL NOT be estimated.

#### Scenario: Cross-review reports elapsed time only
- **WHEN** a cross-review report has elapsed time but no token count
- **THEN** `cross_review_seconds` is filled, `cross_review_tokens` stays empty, and no token value is invented

### Requirement: Append-only CSV with stable columns
Both tables SHALL be created with a header row when absent and appended with a CSV writer that quotes values. Existing rows SHALL never be rewritten. A column change SHALL go to a new versioned file.

#### Scenario: Table absent
- **WHEN** `findings.csv` does not exist
- **THEN** it is created with the header row before the first row is appended

### Requirement: Safe log content
Run logs and table rows SHALL NOT contain secrets, raw private payloads, or hidden reasoning. A failed write SHALL be reported, and the caller SHALL NOT claim a write succeeded when it did not.

#### Scenario: Write fails
- **WHEN** appending to `runs.csv` fails
- **THEN** the caller reports the failure to the user
