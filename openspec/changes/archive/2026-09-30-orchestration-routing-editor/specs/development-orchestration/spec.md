## MODIFIED Requirements

### Requirement: Phase-aware model routing
The skill SHALL preserve the user-selected session model and effort for orchestration. Astra or Fable MAY be suggested where available, but another parent choice MUST NOT require approval or block work. The skill SHALL default to GPT-5.6 Sol for planning and review workers and GPT-5.6 Terra for implementation workers unless the user chooses otherwise. Saved global/project routing preferences and explicit session overrides SHALL resolve worker models and effort through the shared routing policy. With no saved overrides, the stated model defaults SHALL remain. It MUST select and disclose reasoning effort for each worker assignment and MUST NOT silently substitute unavailable worker models or claim to switch the parent model or effort. Unknown effective settings MUST remain reported as unknown.

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
- **WHEN** a project selects Luna Adaptive for implementation
- **THEN** the parent resolves and validates that route, supplies its explicit model and effort to native delegation, and retains its own session settings

### Requirement: Existing skill distribution
The skill SHALL remain installable through the repository's existing skill-copy workflows without changing global Codex model settings. Routing helpers SHALL require Python 3.10+, newly required for native routing and already required for Claude cross-review. Missing Python SHALL block routing with an actionable message even without preference files; Node and editor build dependencies SHALL be required only for developing/building the optional editor, not ordinary orchestration or skill installation. Both installers SHALL distribute routing helpers and default policy data without overwriting user routing preferences or creating additional discoverable skills. A missing editor build SHALL leave the core install usable with an explicit editor-unavailable notice.

#### Scenario: Install into an isolated destination
- **WHEN** the existing installer runs with temporary agent-root destinations
- **THEN** it creates a matching `clanker-orchestration-nation/SKILL.md` and Codex UI metadata without modifying real user configuration

#### Scenario: Reinstall preserves routing preferences
- **WHEN** either installer upgrades an existing package with global or project routing preferences
- **THEN** helpers and bundled defaults update while preferences remain byte-for-byte unchanged and no dependency install or model call occurs

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


### Requirement: Routing prerequisite disclosure
The coordinator SHALL disclose the Python routing prerequisite and any active project override source at run start. It SHALL NOT bypass a missing resolver by silently reverting to Markdown defaults.

#### Scenario: Native routing without Python
- **WHEN** Python is unavailable for a native-only run with no saved preferences
- **THEN** routing is blocked with an actionable prerequisite message, and no worker dispatch is claimed
