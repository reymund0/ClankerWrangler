## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Harness-neutral coordinator with installed host configuration
The coordinator SHALL support Codex and Claude Code as orchestration hosts from one maintained body that names no harness. Host-specific behavior SHALL come only from the installed host reference and host configuration, which identify the host, its preference source, native dispatch procedure, and external reviewer. A missing or invalid host configuration SHALL block routing with an actionable message; the parent SHALL NOT infer its host.

#### Scenario: Same skill in either harness
- **WHEN** the orchestration skill is installed into both Codex and Claude Code
- **THEN** both installations contain the same coordinator, specialist, and cross-review guidance, and differ only in host reference, host configuration, and the Claude worker definition

#### Scenario: Host configuration missing
- **WHEN** the coordinator runs from an installation or checkout without a usable host configuration and the user has not named the host
- **THEN** it reports the missing prerequisite and dispatches no worker rather than guessing the host

### Requirement: Host-specific native dispatch
Native workers SHALL run through the active host's subagent mechanism with the resolved model and effort passed explicitly for each assignment, under the existing ownership, readiness, and reply contracts. Under the Claude host, workers SHALL use the generic orchestration worker definition, which cannot spawn further agents and sets no model or effort of its own. Worker completion reports SHALL NOT establish correctness, and observed settings SHALL remain unknown unless the runtime reports them.

#### Scenario: Claude-native worker dispatch
- **WHEN** a Claude-host parent dispatches a resolved Haiku implementation assignment
- **THEN** it starts the generic worker with that model and effort, supplies the role instruction path and bounded ownership, and records the requested settings separately from observed settings

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
