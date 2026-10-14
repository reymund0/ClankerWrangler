## MODIFIED Requirements

### Requirement: Codex owns the cross-review workflow
The integration SHALL run under a Codex orchestrator, preserve the user-selected parent model and effort, and use Claude Code only as an external reviewer. Codex SHALL retain ownership of application changes, OpenSpec state, findings reconciliation, and the shared run log. Existing native worker routing SHALL remain unchanged unless the user overrides it.

#### Scenario: Cross-review under Codex
- **WHEN** Codex selects a Claude review
- **THEN** Claude returns advisory findings through the CLI and Codex remains responsible for integration and the final result

#### Scenario: Unsupported orchestration host
- **WHEN** Claude Code is the orchestration host and a cross-review checkpoint is selected
- **THEN** Claude review is not selected; the host configuration's Codex reviewer is used instead, and this launcher is not recursively invoked

### Requirement: Single-skill distribution and verification
Both existing installers SHALL package the shared cross-review guidance, the shared review machinery, and the Claude launcher under the existing orchestration skill, preserve unrelated skills and existing specialist migration behavior, and create no additional discoverable skill. Installation SHALL NOT launch Claude, log in, install prerequisites, or modify model settings. Verification SHALL distinguish deterministic launcher/installer tests from live authenticated review checks.

#### Scenario: Fresh or repeated installation
- **WHEN** either wrangle installer runs against an isolated fresh or existing destination
- **THEN** the coordinator, shared cross-review reference, shared review machinery, and supporting launchers are installed together with one visible orchestration skill and unrelated content preserved, and a previously installed Claude-only reviewer reference is backed up under the existing retirement rules

#### Scenario: Live authentication unavailable during testing
- **WHEN** deterministic tests pass but a real subscription-authenticated review cannot run
- **THEN** the live check remains explicitly unverified and is not represented as a completed end-to-end test

## ADDED Requirements

### Requirement: Shared external-review contract
Claude and Codex reviews SHALL use one review contract for manifests, scoped evidence packets, required coverage, findings, limitations, verdicts, reports, source-change reconciliation, freshness queries, diagnostics, progress, timeouts, and owned-process cleanup. Reports SHALL identify the reviewer provider, external execution, and the orchestration host it implies. The Claude launcher's existing options, defaults, report fields, and exit codes SHALL remain compatible; guidance paths naming the retired Claude-only reference are the one documented manifest migration.

#### Scenario: Existing Claude review after refactor
- **WHEN** an existing manifest is prepared and reviewed with the Claude launcher after the update
- **THEN** preparation, preflight, report fields, and freshness behavior match the previous contract, with reviewer provider, external execution, and host added

#### Scenario: Manifest naming the retired reviewer reference
- **WHEN** an earlier manifest lists the retired Claude-only reviewer reference in its guidance and that file has been backed up
- **THEN** preparation blocks with the missing guidance path identified and the documented replacement path, without silently substituting guidance

#### Scenario: Reviews from both providers in one run
- **WHEN** Claude and Codex reviews are saved under the same run identifier
- **THEN** each attempt has a distinct report path and identifies its reviewer, and freshness queries work for both
