## MODIFIED Requirements

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

### Requirement: Routing prerequisite disclosure
The coordinator SHALL disclose the Python routing prerequisite and the global preference source at run start. It SHALL NOT bypass a missing resolver by silently reverting to Markdown defaults.

#### Scenario: Native routing without Python
- **WHEN** Python is unavailable for a native-only run with no saved preferences
- **THEN** routing is blocked with an actionable prerequisite message, and no worker dispatch is claimed
