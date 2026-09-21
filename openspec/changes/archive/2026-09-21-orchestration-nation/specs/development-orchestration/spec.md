## Purpose

Coordinate Codex specialists around the user's software-development scope, with explicit model selection, bounded ownership, and OpenSpec-based completion evidence.

## ADDED Requirements

### Requirement: Phase-aware model routing
The skill SHALL preserve the user-selected session model and effort for orchestration. Astra or Fable MAY be suggested where available, but another parent choice MUST NOT require approval or block work. The skill SHALL default to GPT-5.6 Sol for planning and review workers and GPT-5.6 Terra for implementation workers unless the user chooses otherwise. It MUST select and disclose reasoning effort for each worker assignment and MUST NOT silently substitute unavailable worker models or claim to switch the parent model or effort. Unknown effective settings MUST remain reported as unknown.

#### Scenario: User-selected orchestrator
- **WHEN** the user invokes the skill with any available session model and effort
- **THEN** those settings remain the orchestrator settings without an approval gate for choosing a model other than Astra or Fable, while worker routing remains subject to actual runtime capabilities

#### Scenario: Bounded implementation and independent review
- **WHEN** a feature needs implementation and review
- **THEN** the orchestrator requests Terra for implementation and Sol for review with explicit effort and concise assignment rationales

#### Scenario: Unavailable model or delegation capability
- **WHEN** the requested routing cannot be executed by the active runtime
- **THEN** the orchestrator reports the limitation and does not claim that an agent ran or silently use a different model

### Requirement: Specialist coverage without mandatory full-team activation
The skill SHALL define product engineering, architecture, UX/UI design, UI/UX visual review, backend, data/database, UI implementation, QA planning, test implementation, code/security review, documentation, DevOps, and performance roles. It SHALL select only roles justified by the current scope, dependencies, uncertainty, and risk.

#### Scenario: Documentation-only change
- **WHEN** the user requests a bounded documentation update
- **THEN** the orchestrator selects documentation work without automatically spawning backend, data, DevOps, or performance workers

#### Scenario: Performance-sensitive deployment change
- **WHEN** the task includes deployment configuration and a measurable performance regression
- **THEN** the orchestrator considers DevOps and performance specialists, with Sol planning/review and Terra implementation as applicable

### Requirement: Bounded parallel ownership
Every delegated assignment SHALL include scope, context, file ownership, dependencies, and expected verification. The orchestrator SHALL retain ownership of the shared log and OpenSpec task state, serialize overlapping edits, and respect the runtime's concurrency limit. Workers MUST return blockers and MUST NOT recursively delegate unless separately authorized.

#### Scenario: Shared-file dependency
- **WHEN** two assignments need to modify the same file or an unsettled shared interface
- **THEN** they are combined or sequenced rather than dispatched as conflicting parallel writers

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
The skill SHALL remain installable through the repository's existing skill-copy workflows without changing global Codex settings or requiring new dependencies.

#### Scenario: Install into an isolated destination
- **WHEN** the existing installer runs with temporary agent-root destinations
- **THEN** it creates a matching `clanker-orchestration-nation/SKILL.md` and Codex UI metadata without modifying real user configuration

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
The orchestrator SHALL provide a dedicated `clanker-ui-ux-reviewer` skill for inspecting rendered application visuals and user flows. This role SHALL use the review-phase model, compare against relevant design or acceptance context, and report actual viewport/state coverage with evidence. It MUST distinguish live review from static screenshot review and MUST NOT treat source-only inspection as visual acceptance. UI fixes SHALL remain with the assigned implementer, followed by a recheck of affected states.

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
The coordinator and twelve specialist source files SHALL live under root-level `subagents/`. Both installers SHALL install the coordinator as `skills/clanker-orchestration-nation/SKILL.md` with the specialist files in its `references/` directory. They MUST NOT install specialist instructions as separate discoverable skills or native agent definitions. Existing standalone skills, including shared code review, SHALL retain their normal installation.

#### Scenario: Fresh bundled installation
- **WHEN** either installer runs against empty agent roots
- **THEN** one orchestration skill and twelve matching reference files are installed, all selected role paths resolve, and no separate specialist SKILL.md or metadata entries are created

#### Scenario: Upgrade from standalone specialist skills
- **WHEN** earlier standalone specialist directories exist in an agent's skills folder
- **THEN** after successfully writing the bundle the installer moves those directories into the agent root's backups/orchestration-nation directory, preserving custom content and unrelated skills

#### Scenario: Repeated installation and backup collisions
- **WHEN** the installer runs again or an earlier backup already uses a specialist's name
- **THEN** it preserves earlier backups, chooses an unused backup name for any newly migrated directory, and creates no migration backups when there are no standalone specialist directories remaining


### Requirement: Shared collaboration guidance
The shared global rules SHALL distinguish primary coordination from delegated work, preserve bounded ownership and existing authorization, and require verification of worker results. They SHALL reference selected OpenSpec requirements where applicable while leaving model names and detailed orchestration procedures in the relevant skills.

#### Scenario: Primary agent chooses how to work
- **WHEN** a primary agent evaluates a development task
- **THEN** it handles straightforward work directly and uses a supported orchestration workflow when multiple specialties improve the result

#### Scenario: Delegated worker and existing authorization
- **WHEN** a worker receives a bounded assignment or an action has already been explicitly authorized within the current scope
- **THEN** the worker follows its assigned role without starting another orchestration layer, and approval is requested again only for a material scope expansion or unapproved consequential change without expanding tool permissions
