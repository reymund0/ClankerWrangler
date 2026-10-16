## ADDED Requirements

### Requirement: Delegation threshold
The parent SHALL delegate build work except two kinds: fixes it has already diagnosed that it can finish in a few calls, and its own git, OpenSpec, and log work. Each piece of build work the parent keeps SHALL be logged with a one-line reason. When these criteria do not settle a case, straightforward work SHALL lean to the parent and involved or demanding work to a workstream.

#### Scenario: Parent-diagnosed fix
- **WHEN** parent verification finds a defect, the parent has already identified the cause, and the fix takes a few calls
- **THEN** the parent makes the fix, logs that it kept the work and why, and records the affected workstream's outcome accordingly

#### Scenario: Small undiagnosed task
- **WHEN** a bounded straightforward change requires reading code the parent has not yet inspected
- **THEN** the parent assigns it to the workstream that owns that area, or starts one, instead of doing it in the orchestrator context

### Requirement: Workstream threads
Build work SHALL be grouped into workstreams. Each workstream owns a code area, recorded as its file ownership, and has one lead role plus optional further role checklists. Each workstream SHALL have at most one native thread at a time. Follow-up work in a workstream's area SHALL be sent to that thread with the ownership restated and any changes since its last brief, rather than to a new thread.

#### Scenario: Review fix in an owned area
- **WHEN** a review finding needs a fix in files owned by an active workstream
- **THEN** the parent sends the fix to that workstream's thread as a continued assignment instead of starting a new worker

#### Scenario: Specification revised mid-run
- **WHEN** an OpenSpec artifact changes after a workstream received its brief
- **THEN** the next continued assignment states the revision explicitly, so the thread does not act on its earlier understanding

#### Scenario: Thin vertical slice
- **WHEN** a change touches a small API surface and the UI that consumes it, with no stable contract between them yet
- **THEN** one workstream owns both areas and carries both the backend and UI role checklists

### Requirement: Workstream boundaries
Work that crosses a stack boundary SHALL be split into separate workstreams only when the parent can write the contract between them before dispatch and each side is substantial enough to run in parallel. Otherwise one workstream SHALL carry both role checklists. Workstreams SHALL NOT own overlapping files.

#### Scenario: Contract written up front
- **WHEN** API work and UI work are each substantial and the parent records their shared contract before dispatch
- **THEN** they run as separate workstreams in parallel, each owning its own files

#### Scenario: Contract still moving
- **WHEN** the interface between two areas is still being decided
- **THEN** both areas stay in one workstream rather than running as parallel threads that wait on each other

### Requirement: Workstream route
A workstream's route SHALL be resolved once, when its thread starts, from its lead role and the hardest tier expected in its area. Continued assignments SHALL keep the thread's original model and effort. The parent SHALL NOT change a workstream's route on its own; a different route requires an explicit user choice.

#### Scenario: Follow-up at the original route
- **WHEN** a workstream started at haiku/high receives a continued assignment
- **THEN** the assignment runs at haiku/high without a new resolver request, and its log entry references the workstream's routing evidence

#### Scenario: Thread struggles with its work
- **WHEN** a workstream thread's fixes keep failing parent verification
- **THEN** the parent continues the thread, takes the fix over itself, or asks the user, and does not start a stronger route on its own

### Requirement: Workstream retirement
A workstream thread SHALL be retired once its work is parent-verified and no follow-up is pending. When the parent abandons a workstream's unfinished work, or the run ends blocked or interrupted with that work unfinished, the thread SHALL be retired with a `blocked` outcome. A temporary blocker that awaits the user SHALL NOT retire the thread. Context compaction SHALL be left to the host's default and recorded when observed. When work arrives in a retired workstream's area, the parent SHALL continue the retired thread if the host can still reach it, and otherwise start a new thread seeded with a parent-written summary.

#### Scenario: Run ends with unfinished work
- **WHEN** a run ends blocked while a workstream's assignment has not passed parent verification
- **THEN** the parent retires that thread with a `blocked` outcome, so the workstream still appears in the outcome record

#### Scenario: Waiting on the user
- **WHEN** a workstream pauses because the parent needs a product decision from the user
- **THEN** the thread stays active, and it continues once the user answers

#### Scenario: Acceptance finds a defect after retirement
- **WHEN** acceptance testing finds a defect in an area whose thread was already retired and the host can still continue that thread
- **THEN** the parent continues that thread with the defect and records a new assignment and later a new outcome, leaving earlier records unchanged

#### Scenario: Thread unavailable in a resumed session
- **WHEN** a resumed session needs more work in a workstream whose thread belonged to an earlier session
- **THEN** the parent starts a new thread with a summary of the workstream's state and records it as a new thread for that workstream

### Requirement: Reviewer recheck reuse
A native reviewer SHALL perform its own single automatic recheck in the same thread. The brief SHALL contain the finding IDs, the fix diff, and a request to check the changed lines for regressions. A fresh reviewer SHALL be used instead when the specification or design changed after the first review, or when the change grew beyond the reviewed scope. External cross-review rechecks SHALL keep their existing fresh-session behavior.

#### Scenario: Fixes verified by the original reviewer
- **WHEN** fixes for a native review's findings are integrated and the recheck budget allows one recheck
- **THEN** the original reviewer thread verifies those findings and reports any regression in the changed lines

#### Scenario: Ground moved after review
- **WHEN** a requirement was revised after the native review completed
- **THEN** the parent starts a fresh native review of the affected scope instead of a recheck in the original thread

### Requirement: Acceptance outside the orchestrator
Browser QA and other long acceptance work SHALL run in a worker that owns the browser state and records evidence, not in the parent. The exception is when the user explicitly directs the parent to do it. The parent SHALL keep the acceptance evidence states and verify the worker's evidence before marking acceptance tasks complete.

#### Scenario: User requests manual QA
- **WHEN** the user asks for browser QA of an integrated change
- **THEN** the parent assigns it to a visual-review or test worker with browser ownership and acceptance context, and records the returned evidence as partial, complete, or pending

#### Scenario: User directs the parent to run QA
- **WHEN** the user explicitly asks the parent itself to drive the browser
- **THEN** the parent drives the browser itself and logs that it kept the acceptance work at the user's direction

## MODIFIED Requirements

### Requirement: Capacity-aware dispatch
The parent SHALL inspect available worker state and capacity before starting a thread. When capacity is exhausted, it SHALL sequence the work, or keep it under the delegation threshold, instead of repeatedly spawning or silently changing settings. Thread reuse SHALL follow workstream threads and reviewer recheck reuse, preserving the thread's route, role guidance, and ownership contract. Failed dispatch SHALL NOT count as a running assignment.

#### Scenario: No suitable worker slot
- **WHEN** the runtime rejects dispatch for capacity and no existing workstream thread can take the work
- **THEN** the parent sequences the work or handles authorized work directly instead of repeatedly spawning or silently changing settings

### Requirement: Host-specific native dispatch
Native workers SHALL run through the active host's subagent mechanism with the resolved model and effort passed explicitly when each thread starts, under the existing ownership, readiness, and reply contracts. A continued assignment SHALL use the host's mechanism for continuing an existing worker, and SHALL keep that worker's model and effort. Under the Claude host, workers SHALL use the generic orchestration worker definition, which cannot spawn further agents and sets no model or effort of its own. Worker completion reports SHALL NOT establish correctness, and observed settings SHALL remain unknown unless the runtime reports them.

#### Scenario: Claude-native worker dispatch
- **WHEN** a Claude-host parent dispatches a resolved Haiku implementation assignment
- **THEN** it starts the generic worker with that model and effort, supplies the role instruction path and bounded ownership, and records the requested settings separately from observed settings

#### Scenario: Claude-native continued assignment
- **WHEN** a Claude-host parent sends a follow-up to an existing workstream thread
- **THEN** it continues that worker with the follow-up brief instead of starting a new worker, and the worker keeps the model and effort it was started with

#### Scenario: Worker attempts nested delegation
- **WHEN** a Claude-native worker's assignment or guidance suggests delegating further
- **THEN** the worker cannot start another agent and returns the need to the parent as a blocker or recommendation

#### Scenario: Shadowed worker definition
- **WHEN** a project-level or session-supplied agent definition with the generic worker's name differs from the installed definition
- **THEN** the parent blocks Claude-native dispatch, reports the shadowing source, and does not rely on the shadowing definition's tools or settings

#### Scenario: Route-replacing setting detected
- **WHEN** the parent observes a setting that forces subagent model or effort, or a spawn hook that can replace the requested route
- **THEN** it reports the setting as blocking that dispatch and does not claim the requested settings were used
