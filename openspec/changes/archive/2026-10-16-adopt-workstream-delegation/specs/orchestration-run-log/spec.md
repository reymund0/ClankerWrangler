## ADDED Requirements

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

## REMOVED Requirements

### Requirement: First-pass route outcome
**Reason**: The closing route-outcome table needs a single end of run, but runs continue after their completion entry (NA-358's QA and task updates landed after it). Outcomes are now recorded per workstream when its thread retires, in the analysis ledger.

**Migration**: Use the `retire` rows defined by "Workstream outcomes" in `.clanker/orchestration-ledger.csv`. The outcome values (`first-pass`, `revised`, `rerouted`, `blocked`) keep their meaning, except that `rerouted` no longer covers parent-initiated escalation. Earlier daily logs that contain closing tables stay unchanged. Host attribution of earlier entries remains covered by "Preserve previous runs" and "Host identity in routing and review evidence".
