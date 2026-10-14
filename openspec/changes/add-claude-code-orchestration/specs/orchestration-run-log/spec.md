## ADDED Requirements

### Requirement: Host identity in routing and review evidence
Run-start entries SHALL record the orchestration host and its preference source. Routing evidence SHALL retain host, provider, and execution kind from resolver output without manual transcription. External review entries SHALL identify the reviewer provider and link its report. Closing entries SHALL keep native review, external review, and runtime or visual acceptance as separate evidence states.

#### Scenario: Claude-led run with Codex review
- **WHEN** a Claude-host run dispatches Haiku implementation and a Codex plan review
- **THEN** the log records the Claude host and preference source, native Claude execution for the worker, external Codex execution for the review, requested settings, and unknown observed settings where not reported

### Requirement: Readable model and reasoning settings
Every worker dispatch and external review entry SHALL state, in its readable block, the model and reasoning effort requested, including fixed or Adaptive mode and the assessed tier, and the observed model and effort when the runtime or reviewer envelope reports them. Unreported observed values SHALL read as unknown and SHALL NOT be inferred from the request or from model self-description.

#### Scenario: Codex review with unreported model
- **WHEN** a Codex review completes and its output reports no model or effort
- **THEN** the entry shows the requested model and reasoning effort and observed model and effort as unknown

#### Scenario: Claude review with reported model
- **WHEN** a Claude review envelope reports the model used
- **THEN** the entry shows that observed model beside the requested model and effort

### Requirement: First-pass route outcome
The closing entry SHALL summarize each native worker assignment with its requested model, reasoning effort, tier, and one outcome. `first-pass` means accepted by parent verification without fixes. `revised` means accepted after fixes on the same route. `rerouted` means reassigned to a different model, effort, or role, or taken over by the parent. `blocked` means not completed. The parent SHALL decide outcomes from verification evidence, not worker reports, and SHALL name the replacement route for `rerouted`.

#### Scenario: Implementation accepted after one fix
- **WHEN** a Haiku implementation passes parent verification only after a requested correction on the same route
- **THEN** the closing summary records it as revised with its requested model, effort, and tier

#### Scenario: Escalated assignment
- **WHEN** the parent reassigns failed work to a higher-effort or different-model route
- **THEN** the original assignment is recorded as rerouted with the replacement route, and the replacement assignment receives its own outcome

#### Scenario: Worker claims completion without passing verification
- **WHEN** a worker reports ready for integration but required parent verification fails and the work is not completed
- **THEN** the outcome is blocked rather than first-pass

#### Scenario: Earlier Codex-led entries
- **WHEN** a Claude-led run appends to a daily log containing earlier Codex-led runs
- **THEN** earlier entries remain unchanged and each run's host stays attributable
