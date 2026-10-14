# development-orchestration Specification

## Purpose

Coordinate native specialists under a Codex or Claude Code orchestration host around the user's software-development scope, with explicit model selection, bounded ownership, and OpenSpec-based completion evidence.

## Requirements

### Requirement: Phase-aware model routing
The skill SHALL preserve the user-selected session model and effort for orchestration. Astra or Fable MAY be suggested where available, but another parent choice MUST NOT require approval or block work. The skill SHALL default to GPT-5.6 Sol for planning and review workers and GPT-5.6 Terra for implementation workers unless the user chooses otherwise. Saved global routing preferences and explicit session overrides SHALL resolve worker models and effort through the shared routing policy. With no saved overrides, the stated model defaults SHALL remain. It MUST select and disclose reasoning effort for each worker assignment and MUST NOT silently substitute unavailable worker models or claim to switch the parent model or effort. Unknown effective settings MUST remain reported as unknown.

#### Scenario: User-selected orchestrator
- **WHEN** the user invokes the skill with any available session model and effort
- **THEN** those settings remain the orchestrator settings without an approval gate for choosing a model other than Astra or Fable, while worker routing remains subject to actual runtime capabilities

#### Scenario: Bounded implementation and independent review
- **WHEN** a feature needs implementation and review
- **THEN** in the absence of overrides the orchestrator requests Terra for implementation and Sol for review with explicit effort and concise assignment rationales

#### Scenario: Unavailable model or delegation capability
- **WHEN** the requested routing cannot be executed by the active runtime
- **THEN** the orchestrator reports the limitation and does not claim that an agent ran or silently use a different model

#### Scenario: Configured worker routing
- **WHEN** the user selects Luna Adaptive in global preferences for implementation
- **THEN** the parent resolves and validates that route, supplies its explicit model and effort to native delegation, and retains its own session settings

### Requirement: Specialist coverage without mandatory full-team activation
The skill SHALL define architecture, UI/UX visual review, backend, data/database, UI implementation, QA planning, test implementation, code/security review, DevOps, and performance roles. It SHALL select only roles justified by the current scope, dependencies, uncertainty, and risk. The parent SHALL own product outcomes, scope, acceptance criteria, and routine documentation. The coordinator SHALL use supplied Claude Design handoffs for UX design without requiring or automatically invoking that external service, and SHALL NOT assign the retired UX designer, documentation writer, or product engineer profiles.

#### Scenario: Documentation-only change
- **WHEN** the user requests a bounded documentation update
- **THEN** the parent performs the documentation work without automatically spawning backend, data, DevOps, or performance workers or assigning a retired documentation profile

#### Scenario: Performance-sensitive deployment change
- **WHEN** the task includes deployment configuration and a measurable performance regression
- **THEN** the orchestrator considers DevOps and performance specialists, with Sol planning/review and Terra implementation as applicable

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
The coordinator and nine native specialist instruction files SHALL live under root-level `subagents/`, alongside the retained Claude cross-review guidance. Both installers SHALL install the coordinator as `skills/clanker-orchestration-nation/SKILL.md` with those ten reference files in its `references/` directory. They MUST NOT install specialist instructions as separate discoverable skills or native agent definitions. Existing standalone skills, including shared code review, SHALL retain their normal installation. The three retired profiles SHALL NOT be included in a fresh package.

#### Scenario: Fresh bundled installation
- **WHEN** either installer runs against empty agent roots
- **THEN** one orchestration skill, nine active native specialist references, and the Claude cross-review reference are installed, all selected role paths resolve, and no retired reference or separate specialist SKILL.md or metadata entry is created

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
The parent SHALL inspect available worker state before spawning and prefer suitable idle-worker reuse or sequencing when capacity is exhausted. Reuse SHALL preserve the resolved model/effort, role guidance, and ownership contract. Failed dispatch SHALL NOT count as a running assignment.

#### Scenario: No suitable worker slot
- **WHEN** the runtime rejects dispatch for capacity and no idle worker matches the resolved settings
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
