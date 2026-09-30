# local-model-discovery Specification

## Purpose

Expose local CLI model and reasoning metadata honestly in the routing editor while preserving configured routes and runtime dispatch safeguards.

## Requirements

### Requirement: Metadata-only provider discovery
The editor SHALL discover model identifiers, labels and reported effort capabilities from installed Codex and Claude CLIs without submitting user prompts, starting model turns, running tools, installing software or changing CLI settings. Each probe SHALL have bounded runtime/output and clean up owned processes. Missing CLIs, unsupported protocols and malformed responses SHALL produce sanitized provider-specific failures, not fabricated capabilities.

#### Scenario: Successful discovery
- **WHEN** an installed provider CLI returns valid model metadata
- **THEN** its choices and reported effort levels are available with their provider and CLI provenance, without a model inference request

#### Scenario: Failed provider
- **WHEN** one CLI is missing, times out or returns unsupported metadata
- **THEN** its status explains the failure without exposing credentials or raw process output and the other provider and editor remain usable

### Requirement: Refresh and honest caching
The editor SHALL load catalogs separately from preference loading and offer explicit refresh. It SHALL cache results in memory for the editor process, coalesce concurrent refresh requests, retain the last successful provider result after a failed refresh, and distinguish live, cached, stale and unavailable results with success timestamps where available. Refresh SHALL NOT modify saved preferences or silently select another model.

#### Scenario: Refresh failure after success
- **WHEN** a previously discovered provider fails to refresh
- **THEN** the previous choices remain available as stale with an explanatory status and the saved model remains unchanged

### Requirement: Full model and effort selectors
All route and temporary-session model controls SHALL offer all CLI-reported provider choices without filtering them down to the prefilled value. Manual model entry and static bundled alternatives SHALL NOT be offered. Current saved or inherited choices absent from the CLI catalog SHALL remain visible as labeled disabled options without preference mutation. Adaptive profile creation SHALL choose from the provider's CLI catalog, while existing profiles remain editable and resettable. Known discovered effort levels SHALL guide model-specific controls, including dropdowns for all four Adaptive profile tiers and the default ceiling; existing unsupported effort values SHALL stay visible rather than being silently replaced. Unknown effort metadata SHALL remain distinguishable from reported support.

#### Scenario: Existing selection and newly discovered choices
- **WHEN** the selected model differs from newly discovered local models
- **THEN** the selector retains it and displays CLI-reported alternatives, with the absent current value labeled and disabled without changing preferences

#### Scenario: CLI-only profile creation
- **WHEN** a user chooses a model to customize its Adaptive profile
- **THEN** only models from that provider's CLI catalog are offered, no manual ID input exists, and existing profiles remain editable even when absent from discovery

### Requirement: Discovery is not dispatch authorization
The editor SHALL treat CLI discovery only as catalog evidence. It SHALL NOT modify native session capability checks, Claude launcher preflight, parent settings, Adaptive tier mappings, immutable run snapshots or fixed routing overrides. Provider-level Adaptive thinking support SHALL NOT be treated as a task-to-effort mapping.

#### Scenario: CLI and active session differ
- **WHEN** the local CLI reports a model or effort that the active Codex subagent tool does not support
- **THEN** it can be shown as CLI metadata but native dispatch remains blocked by the existing exact-pair gate

### Requirement: Restricted discovery entry points
Discovery endpoints SHALL use the existing editor token and Host/Origin boundary. Browser requests SHALL NOT supply executable paths, process arguments or arbitrary providers. Executable selection SHALL remain local and startup-controlled. Source and installed packages SHALL provide equivalent behavior without requiring Node for the Python server.

#### Scenario: Unauthorized refresh
- **WHEN** an unauthenticated or foreign-origin client requests a refresh or supplies a command path
- **THEN** the service rejects the request before starting a discovery subprocess

#### Scenario: New metadata exceeds routing policy
- **WHEN** a CLI advertises an effort outside the current routing policy
- **THEN** it is annotated as unavailable for new selection, supported choices use the intersection, and an existing selected value remains visible without mutation

#### Scenario: Older service
- **WHEN** the catalog endpoint returns 404
- **THEN** the editor explains that discovery is unavailable and preserves current selections and the draft but offers no new model choices until CLI metadata becomes available

#### Scenario: Editor stops during discovery
- **WHEN** the editor closes while a probe is active
- **THEN** its owned process tree is cancelled and no new discovery starts
