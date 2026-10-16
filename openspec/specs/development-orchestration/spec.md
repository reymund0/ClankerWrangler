# development-orchestration Specification

## Purpose

Coordinate native specialists under a Codex or Claude Code orchestration host around the user's software-development scope, with explicit model selection, bounded ownership, and OpenSpec-based completion evidence.

## Requirements

### Requirement: Phase-aware model routing
The skill SHALL preserve the user-selected session model and effort for orchestration. Astra or Fable MAY be suggested where available, but another parent choice MUST NOT require approval or block work. Under the Codex host the skill SHALL default to GPT-5.6 Sol for planning and review workers and GPT-5.6 Terra for implementation workers; under the Claude host it SHALL default to Sonnet for planning and review workers and Haiku for implementation workers, unless the user chooses otherwise. The active host's saved global routing preferences and explicit session overrides SHALL resolve worker models and effort through the shared routing policy. With no saved overrides, the stated model defaults SHALL remain. It MUST select and disclose reasoning effort for each worker assignment and MUST NOT silently substitute unavailable worker models or claim to switch the parent model or effort. Unknown effective settings MUST remain reported as unknown.

#### Scenario: User-selected orchestrator
- **WHEN** the user invokes the skill with any available session model and effort
- **THEN** those settings remain the orchestrator settings without an approval gate for choosing a model other than Astra or Fable, while worker routing remains subject to actual runtime capabilities

#### Scenario: Bounded implementation and independent review
- **WHEN** a Codex-host feature needs implementation and review
- **THEN** in the absence of overrides the orchestrator requests Terra for implementation and Sol for review with explicit effort and concise assignment rationales

#### Scenario: Unavailable model or delegation capability
- **WHEN** the requested routing cannot be executed by the active runtime
- **THEN** the orchestrator reports the limitation and does not claim that an agent ran or silently use a different model

#### Scenario: Configured worker routing
- **WHEN** the user selects Luna Adaptive in Codex-host global preferences for implementation
- **THEN** the parent resolves and validates that route, supplies its explicit model and effort to native delegation, and retains its own session settings

#### Scenario: Claude-led default routing
- **WHEN** a Claude Code parent with no saved Claude-host overrides dispatches planning and implementation workers
- **THEN** it requests Sonnet for planning and Haiku for implementation with explicit effort, keeps its own Opus session settings, and reports observed worker settings as unknown unless the runtime reports them

### Requirement: Specialist coverage without mandatory full-team activation
The skill SHALL define architecture, UI/UX visual review, backend, data/database, UI implementation, QA planning, test implementation, code/security review, DevOps, and performance roles. It SHALL select only roles justified by the current scope, dependencies, uncertainty, and risk. The parent SHALL own product outcomes, scope, acceptance criteria, and routine documentation. The coordinator SHALL use supplied Claude Design handoffs for UX design without requiring or automatically invoking that external service, and SHALL NOT assign the retired UX designer, documentation writer, or product engineer profiles.

#### Scenario: Documentation-only change
- **WHEN** the user requests a bounded documentation update
- **THEN** the parent performs the documentation work without automatically spawning backend, data, DevOps, or performance workers or assigning a retired documentation profile

#### Scenario: Performance-sensitive deployment change
- **WHEN** the task includes deployment configuration and a measurable performance regression
- **THEN** the orchestrator considers DevOps and performance specialists, using the active host's resolved planning/review and implementation routes (Sol and Terra under default Codex-host routing)

#### Scenario: Product scope remains parent-owned
- **WHEN** a change needs clarified outcomes, scope boundaries, or acceptance criteria
- **THEN** the parent resolves those decisions with the user and records the applicable OpenSpec artifacts without dispatching a product engineer

#### Scenario: Supplied UX design and rendered verification
- **WHEN** the user supplies a Claude Design handoff for a UI change
- **THEN** the parent uses that handoff as design context, assigns bounded UI implementation where justified, and retains UI/UX review for rendered and interaction evidence without dispatching a UX designer

#### Scenario: Missing design decision
- **WHEN** a material UX decision is not resolved by the user's request, supplied handoff, or existing application patterns
- **THEN** the parent asks the user to resolve that decision rather than inventing it, reactivating a retired profile, or automatically calling Claude Design

### Requirement: Bounded parallel ownership
Every delegated assignment SHALL include scope, context, file ownership, dependencies, and expected verification. The orchestrator SHALL retain ownership of the shared log and OpenSpec task state, serialize overlapping edits, and respect the runtime's concurrency limit. Workers MUST return blockers and MUST NOT recursively delegate unless separately authorized. Artifact consumers SHALL wait for successful producer completion. Changed-file inventories SHALL be reconciled with ownership; new captured reviews SHALL NOT impose full-run input reservations or mandatory reservation prechecks.

#### Scenario: Shared-file dependency
- **WHEN** two assignments need to modify the same file or an unsettled shared interface
- **THEN** they are combined or sequenced rather than dispatched as conflicting parallel writers

#### Scenario: Verification consumes build output
- **WHEN** verification needs build or staging output
- **THEN** the parent waits for successful producer completion and records the consumed artifact identity

#### Scenario: Changed file absent from checked paths
- **WHEN** a legacy worker reports a changed file absent from its declared write checks
- **THEN** the parent records the legacy deviation and verifies actual ownership without reintroducing mandatory reservation checks for new captured reviews

### Requirement: OpenSpec continuity and scope
For meaningful changes the skill SHALL use OpenSpec as the requirements and acceptance source, resolve the selected change and its actual artifact paths, and respect planning versus implementation authorization. Tiny fixes MAY use a recorded lightweight path when no applicable change requires the full workflow. A routing log MUST NOT replace specs or authorize scope changes.

#### Scenario: Ready existing change
- **WHEN** the user requests implementation of a ready OpenSpec change
- **THEN** assignments reference its tasks and relevant scenarios and the orchestrator marks tasks complete only after verifying the specified behavior

#### Scenario: Planning-only or ambiguous change
- **WHEN** the user requests planning only or multiple changes could match
- **THEN** the orchestrator preserves the planning-only boundary or asks which change applies instead of starting guessed implementation

#### Scenario: OpenSpec unavailable
- **WHEN** a meaningful change requires OpenSpec but the CLI or workflow is unavailable
- **THEN** the orchestrator reports the limitation and does not fabricate CLI results, create a competing plan silently, or claim spec-driven completion

### Requirement: Evidence-based integration
The orchestrator SHALL reconcile worker results, verify the integrated changes, evaluate relevant tests and documentation, and distinguish completed work from failed or unrun checks. Review findings SHALL be assessed against the actual result rather than accepted as proof by themselves.

#### Scenario: Worker reports completion without verification
- **WHEN** a worker says a task is complete but a required check failed or could not run
- **THEN** the orchestrator records the missing evidence and keeps the affected task incomplete

### Requirement: Existing skill distribution
The skill SHALL remain installable through the repository's existing skill-copy workflows without changing global Codex model settings. Routing helpers SHALL require Python 3.10+, newly required for native routing and already required for Claude cross-review. Missing Python SHALL block routing with an actionable message even without preference files; Node and editor build dependencies SHALL be required only for developing/building the optional editor, not ordinary orchestration or skill installation. Both installers SHALL distribute routing helpers and default policy data without overwriting user routing preferences or creating additional discoverable skills. A missing editor build SHALL leave the core install usable with an explicit editor-unavailable notice.

#### Scenario: Install into an isolated destination
- **WHEN** the existing installer runs with temporary agent-root destinations
- **THEN** it creates a matching `clanker-orchestration-nation/SKILL.md` and Codex UI metadata without modifying real user configuration

#### Scenario: Reinstall preserves routing preferences
- **WHEN** either installer upgrades an existing package with global or project routing preferences
- **THEN** helpers and bundled defaults update while preferences remain byte-for-byte unchanged and no dependency install or model call occurs

### Requirement: Dedicated specialist guidance
Every catalog role SHALL map to a separately maintained instruction file containing specialty-specific inputs, working approach, boundaries, deliverables, and verification. An existing applicable skill SHALL be reused where it already supplies that guidance. The coordinator SHALL resolve the selected instructions' real source or installed path and require the assigned worker to read it before domain work.

#### Scenario: Specialist receives substantive instructions
- **WHEN** the orchestrator assigns backend implementation
- **THEN** the worker receives and reads the backend specialist skill along with the bounded task, rather than working only from the catalog description

#### Scenario: Installed skill resolution
- **WHEN** the coordinator is installed outside the ClankerWrangler source repository
- **THEN** specialists resolve to actual references/<role-name>.md files relative to the installed coordinator, while the shared code-review role resolves to its separate installed SKILL.md

#### Scenario: Missing specialist skill
- **WHEN** a selected specialist skill is missing or unreadable
- **THEN** the orchestrator reports and logs the affected assignment as blocked and does not claim specialist guidance was loaded

### Requirement: Evidence-based UI/UX review
The orchestrator SHALL provide a dedicated `clanker-ui-ux-reviewer` skill for inspecting rendered application visuals and user flows. This role SHALL use the visual/UX review route, defaulting to the existing review-phase model without overrides, compare against relevant design or acceptance context, and report actual viewport/state coverage with evidence. It MUST distinguish live review from static screenshot review and MUST NOT treat source-only inspection as visual acceptance. UI fixes SHALL remain with the assigned implementer, followed by a recheck of affected states.

#### Scenario: Review an implemented UI change
- **WHEN** a UI change needs visual acceptance and the running application is available
- **THEN** the reviewer inspects rendered captures and relevant interactions at representative supported viewports and returns prioritized, reproducible findings with observed evidence

#### Scenario: Application or visual access unavailable
- **WHEN** the reviewer cannot inspect the running application or rendered visual evidence
- **THEN** it reports the missing prerequisite and partial or blocked coverage rather than passing the UI from source inspection

#### Scenario: Static screenshots only
- **WHEN** the reviewer receives screenshots without access to the running application
- **THEN** it limits findings to the shown states and does not claim interaction, responsive, accessibility, or current-build coverage beyond the evidence

#### Scenario: Shared browser state and follow-up fixes
- **WHEN** another worker would change the same browser state or application build during review, or an implementer fixes a finding
- **THEN** the orchestrator sequences conflicting work and requires the reviewer to revisit the affected state on the updated build before declaring the finding resolved

### Requirement: One discoverable orchestration package
The coordinator and nine native specialist instruction files SHALL live under root-level `subagents/`, alongside the shared cross-review guidance and per-host configuration sources. Both installers SHALL install the coordinator as `skills/clanker-orchestration-nation/SKILL.md` with the nine specialist references and the shared cross-review reference in its `references/` directory, plus that client's host reference and host configuration. They MUST NOT install specialist instructions as separate discoverable skills or per-role native agent definitions. The Claude installation SHALL additionally install exactly one generic orchestration worker agent definition; the Codex installation SHALL install none. Existing standalone skills, including shared code review, SHALL retain their normal installation. The three retired profiles SHALL NOT be included in a fresh package.

#### Scenario: Fresh bundled installation
- **WHEN** either installer runs against empty agent roots
- **THEN** one orchestration skill, nine active native specialist references, the shared cross-review reference, and the matching host reference and configuration are installed in each client, the Claude root also receives the generic worker definition, all selected role paths resolve, and no retired reference or separate specialist SKILL.md, per-role agent definition, or metadata entry is created

#### Scenario: Upgrade from standalone specialist skills
- **WHEN** earlier standalone specialist directories exist in an agent's skills folder and any retired entries pass the retirement preflight
- **THEN** after successfully writing the bundle the installer moves eligible entries into the agent root's backups/orchestration-nation directory, preserving custom content and unrelated skills; retired links are rejected, while retained-role migration keeps its existing handling of linked standalone entries

#### Scenario: Repeated installation and backup collisions
- **WHEN** the installer runs again or an earlier backup already uses a specialist's name
- **THEN** it preserves earlier backups, chooses an unused backup name for any newly migrated entry, and creates no migration backups when there are no specialist entries to retire or migrate

### Requirement: Shared collaboration guidance
The shared global rules SHALL distinguish primary coordination from delegated work, preserve bounded ownership and existing authorization, and require verification of worker results. They SHALL reference selected OpenSpec requirements where applicable while leaving model names and detailed orchestration procedures in the relevant skills.

#### Scenario: Primary agent chooses how to work
- **WHEN** a primary agent evaluates a development task
- **THEN** it handles straightforward work directly and uses a supported orchestration workflow when multiple specialties improve the result

#### Scenario: Delegated worker and existing authorization
- **WHEN** a worker receives a bounded assignment or an action has already been explicitly authorized within the current scope
- **THEN** the worker follows its assigned role without starting another orchestration layer, and approval is requested again only for a material scope expansion or unapproved consequential change without expanding tool permissions

### Requirement: Routing prerequisite disclosure
The coordinator SHALL disclose the Python routing prerequisite and the global preference source at run start. It SHALL NOT bypass a missing resolver by silently reverting to Markdown defaults.

#### Scenario: Native routing without Python
- **WHEN** Python is unavailable for a native-only run with no saved preferences
- **THEN** routing is blocked with an actionable prerequisite message, and no worker dispatch is claimed

### Requirement: Coherent review scopes
The parent SHALL assign code review, browser acceptance and executable verification to their appropriate owners. Cross-review SHALL receive the parent's authorized read scope and explicitly selected evidence without a second export policy or redundant approval. Required changes/requirements SHALL be distinguished from optional context. The packet SHALL seed investigation and preserve versions without preventing dependency discovery or reserving originals throughout review. The parent SHALL retain aggregate acceptance and reconcile later relevant changes before integrating findings.

#### Scenario: Bounded recheck
- **WHEN** review covers a bounded correction within a larger change
- **THEN** its required evidence matches the correction, relevant supporting context remains available, and broader acceptance remains parent-owned

#### Scenario: Already authorized cross-review
- **WHEN** the user's request already authorizes review of the task and its relevant files
- **THEN** the parent supplies that scope without asking again merely because the same files go to Claude

#### Scenario: Writers continue after capture
- **WHEN** a reviewer is running against captured change evidence
- **THEN** original-source writes are coordinated by actual ownership/dependencies and are not blocked solely by that review's existence

### Requirement: Capacity-aware dispatch
The parent SHALL inspect available worker state and capacity before starting a thread. When capacity is exhausted, it SHALL sequence the work, or keep it under the delegation threshold, instead of repeatedly spawning or silently changing settings. Thread reuse SHALL follow workstream threads and reviewer recheck reuse, preserving the thread's route, role guidance, and ownership contract. Failed dispatch SHALL NOT count as a running assignment.

#### Scenario: No suitable worker slot
- **WHEN** the runtime rejects dispatch for capacity and no existing workstream thread can take the work
- **THEN** the parent sequences the work or handles authorized work directly instead of repeatedly spawning or silently changing settings

### Requirement: Explicit worker readiness
Worker handoffs SHALL distinguish draft, locally checked, and ready for integration. Executable changes SHALL receive the smallest relevant authorized compile or contract check before a readiness claim. Every handoff SHALL state changed files, exact checks/results, and remaining blockers; parent integration verification remains required. Test assignments SHALL verify current fixture/API contracts against an analogous working test. When worker execution is unavailable, the parent SHALL assign an integration check owner before combined acceptance execution.

#### Scenario: Worker cannot run verification
- **WHEN** execution is unavailable or outside a worker's assignment
- **THEN** the worker returns a draft with the unrun check and reason, rather than claiming readiness

#### Scenario: New fixture setup families
- **WHEN** an assignment introduces materially different fixture setup
- **THEN** current API signatures and an analogous test are checked, and an owner performs the smallest authorized compile/representative setup checks before the combined acceptance selection

### Requirement: Prompt advisory evidence handback
An advisory worker SHALL promptly identify inaccessible required evidence, continue accessible inspection where useful, and return its evidence limits. The parent SHALL resolve access or retain a draft without requiring unnecessary project execution or concealing missing coverage.

#### Scenario: Required planning file inaccessible
- **WHEN** a read-only reviewer cannot access a required OpenSpec artifact
- **THEN** it reports the exact missing evidence to the parent, continues useful authorized inspection, and does not claim complete coverage while waiting for access

### Requirement: Recoverable retirement of installed specialist guidance
Both installers SHALL preserve custom content when backing up only retired `clanker-ux-designer`, `clanker-documentation-writer`, and `clanker-product-engineer` references and standalone directories. Source ancestors below the explicitly chosen agent root, entry types, and backup paths SHALL be validated before replacement-bundle writes. The explicitly chosen agent root MAY itself be linked. After the bundle is ready, moves SHALL use unused backup names. Failure SHALL stop installation with a nonzero exit, retaining the affected entry and completed backups.

#### Scenario: Upgrade with retired reference files
- **WHEN** an existing orchestration bundle contains any of the three retired Markdown references, including locally customized content
- **THEN** each safe regular retired reference is moved with its exact content into the agent root's backups/orchestration-nation directory and is absent from the active references directory after successful installation; reference names use <id>.md then <id>-2.md, <id>-3.md, and so on, while standalone directory names use <id> then <id>-2, <id>-3, and so on

#### Scenario: Preserve unrelated files and preferences
- **WHEN** the installation contains unrelated reference notes, other skills, saved routing preferences, and earlier retirement backups
- **THEN** those files remain unchanged while only present retired references and the existing standalone specialist migration targets are moved

#### Scenario: Repeat an already completed retirement
- **WHEN** installation repeats after all retired entries have been moved
- **THEN** no additional retirement backup is created and the active package still excludes all three retired profiles

#### Scenario: Linked owner-selected agent root
- **WHEN** either installer uses an explicitly chosen linked agent root and all retirement source and backup components below it are ordinary entries
- **THEN** installation succeeds through that chosen root, preserves recoverable retired content, and continues to reject linked descendants

#### Scenario: Unsafe or failed retirement
- **WHEN** a retirement entry, source ancestor below the chosen agent root, or backup path is linked or escapes its permitted root, has an unexpected type, or cannot be safely backed up
- **THEN** the installer refuses the unsafe or failed move, preserves that entry and earlier backups, and aborts with a nonzero exit without processing later entries, steps, or agent roots or claiming retirement succeeded

#### Scenario: Linked references ancestor
- **WHEN** the references directory or another source ancestor under the agent root is linked, even though each retired reference itself is a regular file
- **THEN** component-wise preflight rejects that path before replacement orchestration-bundle writes or retirement moves, leaving the linked target's contents untouched

#### Scenario: Linked retired standalone entry
- **WHEN** an old standalone skill for a retired role is a symlink, junction, or other reparse entry
- **THEN** retirement preflight rejects it without moving the link or accessing its target; retained-role standalone link handling remains unchanged in runs that pass retirement preflight

#### Scenario: Unexpected retirement entry type
- **WHEN** a retired reference path is a directory or a retired standalone skill path is a regular file
- **THEN** preflight rejects the unexpected type before replacement orchestration-bundle writes and preserves its content without creating a retirement backup

#### Scenario: Partial failure and recovery
- **WHEN** a backup move fails after earlier bundle writes or retirement moves have completed
- **THEN** completed writes and backups remain, later steps and roots are not processed, and the failure output identifies the affected path without claiming rollback; after the owner corrects the cause, a rerun finishes remaining retirement without duplicating successful backups

### Requirement: Harness-neutral coordinator with installed host configuration
The coordinator SHALL support Codex and Claude Code as orchestration hosts from one maintained body that names no harness. Host-specific behavior SHALL come only from the installed host reference and host configuration, which identify the host, its preference source, native dispatch procedure, and external reviewer. A missing or invalid host configuration SHALL block routing with an actionable message; the parent SHALL NOT infer its host.

#### Scenario: Same skill in either harness
- **WHEN** the orchestration skill is installed into both Codex and Claude Code
- **THEN** both installations contain the same coordinator, specialist, and cross-review guidance, and differ only in host reference, host configuration, and the Claude worker definition

#### Scenario: Host configuration missing
- **WHEN** the coordinator runs from an installation or checkout without a usable host configuration and the user has not named the host
- **THEN** it reports the missing prerequisite and dispatches no worker rather than guessing the host

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

### Requirement: Host-matched external review
External cross-review SHALL use the model provider that is not the host: Claude Code reviews Codex-led work and Codex reviews Claude-led work, through the launcher named by the installed host configuration. Native workers SHALL NOT be treated as external reviews, and external review SHALL NOT require the host's native collaboration tools. Visual and runtime acceptance SHALL remain separately owned evidence that static review cannot certify.

#### Scenario: Claude-led substantial plan
- **WHEN** a Claude-host parent selects a plan cross-review checkpoint
- **THEN** it prepares the shared review packet and runs the Codex review launcher, not a Claude-native reviewer, and retains reconciliation ownership

#### Scenario: Native review alongside external review
- **WHEN** a run uses both a native code-review worker and an external cross-review
- **THEN** their results are recorded as distinct evidence categories and neither substitutes for the other or for rendered acceptance

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
