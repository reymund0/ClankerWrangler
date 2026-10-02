## ADDED Requirements

### Requirement: Local packet readiness
The launcher SHALL offer a local preparation operation that validates the manifest, evidence availability, and writable report/reservation locations without launching Claude. Normal execution SHALL perform the same checks before model execution. Filtered or unavailable required evidence SHALL block dispatch with actionable coverage feedback, without weakening exclusion rules.

#### Scenario: Missing or filtered evidence
- **WHEN** a required selected/context file is filtered or missing without reviewable deletion evidence
- **THEN** preparation and normal execution report the affected subject and reason without invoking Claude

#### Scenario: Readable deleted file
- **WHEN** a selected file was deleted and a scoped Git diff contains its deleted contents
- **THEN** preparation treats the deletion as reviewable and preserves freshness checks

#### Scenario: Preparation succeeds
- **WHEN** the manifest and local packet pass checks
- **THEN** the launcher saves a unique preparation result with scope, fingerprint, counts, and split-scope warnings, without claiming authorization, model availability, or review approval

### Requirement: Explicit acceptance ownership
Manifests SHALL retain support for existing string requirements and MAY map every static requirement to supplied evidence paths. Invalid or unavailable mappings SHALL block preparation. Optional parent-owned checks SHALL remain visible in reports but SHALL NOT be counted as external static-review coverage or automatically marked passed.

#### Scenario: Visual acceptance belongs to parent
- **WHEN** a manifest lists a browser check separately from static requirements
- **THEN** the reviewer evaluates static requirements only and the report preserves the browser check's owner and supplied status for parent reconciliation

#### Scenario: Invalid requirement mapping
- **WHEN** a mapping refers to an unknown requirement or a path outside selected/context/guidance evidence, or omits a mapped requirement
- **THEN** manifest validation rejects it before model execution

### Requirement: Line-readable diff evidence
The packet SHALL provide committed, staged, and unstaged Git differences as ordinary UTF-8 diff files discoverable through its metadata and reviewer instructions. The packet SHALL preserve path filtering, deleted/renamed-file evidence, secret/binary checks, aggregate bounds, and freshness fingerprints.

#### Scenario: Mixed tree changes
- **WHEN** selected changes include committed, staged, unstaged, new, renamed, and deleted files
- **THEN** the reviewer can read the corresponding differences by line without extracting long JSON strings, and unrelated or private contents remain excluded

### Requirement: Actionable sanitized launch failures
Failure reports SHALL identify the failed stage and a safe diagnostic category with a suggested next action. Known permission, authentication, usage, model, and process errors SHALL NOT expose raw stdout/stderr, credentials, or private source. Unknown errors SHALL remain unknown with their exit code or exception type. Each attempt SHALL retain its own report.

#### Scenario: Permission failure before model execution
- **WHEN** the report or reservation location is not writable
- **THEN** the launcher reports filesystem preparation as blocked before invoking Claude

#### Scenario: CLI failure contains sensitive text
- **WHEN** Claude exits with an error containing a recognizable failure and private payload
- **THEN** the report retains only a fixed diagnostic category, exit code, stage, and action, without echoing the payload
