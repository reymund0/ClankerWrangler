## Purpose

Give the user a durable, readable record of orchestration choices and outcomes for each Codex run, alongside existing Clanker output files.

## ADDED Requirements

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
The log SHALL include session identity when available, workspace, branch, request summary, OpenSpec change, requested and known effective model/effort, complexity, role selections, resolved specialist instruction paths, brief rationales, assignments, ownership, status changes, verification results, and unresolved blockers. It SHALL record decisions not to delegate and unavailable settings honestly.

#### Scenario: Dispatch and failure
- **WHEN** the orchestrator selects a worker and the dispatch fails
- **THEN** the log records the requested role/model/effort and failure without presenting the worker as running or complete

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
