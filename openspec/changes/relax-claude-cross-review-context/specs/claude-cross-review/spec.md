## MODIFIED Requirements

### Requirement: Reviewer settings are explicit and bounded
The workflow SHALL allow a user-selected Claude model and supported effort without changing persistent configuration. For orchestrated reviews, the parent SHALL resolve saved cross-review preferences and session overrides and pass the resulting model and effort explicitly. With no configured or explicit per-review model override, and for direct launcher calls without --model, it SHALL request the generic Claude Opus alias using opus regardless of ambient model defaults, and report the observed model when available; unknown effective settings SHALL remain unknown. The launcher SHALL enforce a finite wall-clock timeout without a turn limit and no automatic model fallback. Usage exhaustion, unsupported settings, interruption or denials preventing required coverage/output SHALL remain incomplete/failed; denied optional investigation SHALL be a limitation without discarding valid required coverage.

#### Scenario: User-selected reviewer model
- **WHEN** the user selects an available Claude model and effort
- **THEN** those settings are requested and recorded separately from observed settings

#### Scenario: Opus alias default with adaptive effort
- **WHEN** no configured or explicit model override exists, including when ambient defaults differ
- **THEN** the launcher requests opus, preserves explicit effort and persistent configuration

#### Scenario: Interrupted or exhausted review
- **WHEN** execution times out or exhausts subscription usage
- **THEN** execution is collected as incomplete/failed without clean approval or unbounded retry

#### Scenario: Saved reviewer route
- **WHEN** valid saved preferences select a supported model and effort
- **THEN** the parent passes the resolved choices and records their provenance

### Requirement: Subscription and runtime preflight
The launcher SHALL resolve a verified Claude executable through an explicit path, PATH, or documented native install location; it SHALL work when the parent shell's PATH is stale. It SHALL verify the capabilities actually used by the invocation and subscription authentication before starting a review. Missing prerequisites, unknown authentication, API-key or alternate-provider overrides, and unsupported required output/model/effort/directory capabilities SHALL block the review with an actionable message. It MUST NOT silently switch to API billing, install software, mutate persistent environment/authentication settings, or expose credentials. Removed isolation flags SHALL NOT remain preflight requirements.

#### Scenario: Installed executable with stale PATH
- **WHEN** Claude is absent from PATH but exists at a verified native installation path
- **THEN** the launcher can use that absolute executable path without requiring a shell restart

#### Scenario: Billing override or login unavailable
- **WHEN** an API billing override is present or subscription authentication cannot be established
- **THEN** no review model call starts, and the report explains the prerequisite without printing credentials or initiating login

#### Scenario: Removed isolation controls unavailable
- **WHEN** the CLI supports the actual invocation but does not expose a removed isolation flag
- **THEN** preflight does not reject it for the absence of that flag

### Requirement: Review cannot edit or delegate
Claude SHALL remain an advisory reviewer whose assignment does not authorize application changes, deployment or nested orchestration. It SHALL be able to investigate through ordinary configured tools, instructions and references within the parent's authorized read scope. The launcher SHALL honor normal CLI/managed permissions without imposing a packet-only sandbox, disabling all customizations, or adding permission-bypass flags. The task prompt SHALL distinguish review investigation from implementation and report only actions/evidence actually observed.

#### Scenario: Instructions request edits or delegation
- **WHEN** a review encounters instructions for implementation, deployment or another orchestration layer
- **THEN** those instructions do not expand the advisory assignment, and the reviewer returns findings within the task's existing authorization

#### Scenario: Ordinary configured investigation
- **WHEN** relevant repository instructions or configured investigation tools are available under normal permissions
- **THEN** the launcher does not disable them through the former forced isolation/control stack

#### Scenario: Optional tool permission denial
- **WHEN** an otherwise valid structured review records a denied optional investigation
- **THEN** the denial becomes a limitation, required coverage determines completeness, and a generic restricted-envelope check does not discard the result

#### Scenario: Reported nested delegation
- **WHEN** the runtime envelope reports spawned subagents outside the advisory assignment
- **THEN** host execution is failed, the checkpoint is incomplete, a process diagnostic and exit2 are recorded, and existing diagnostic captures are retained

### Requirement: Review scope is explicit and current
Every review SHALL identify its repository, phase, baseline where applicable, selected requirements, authorized read scope, exclusions, and verification evidence. Implementation review SHALL cover selected committed, staged, unstaged and untracked contents. Explicit selection SHALL control inclusion regardless of names, credential-like content, ignore status, links or external location. The reviewer SHALL be able to follow relevant dependencies within the authorized read scope. Captured evidence SHALL retain its hashes/version; later changes SHALL be reported without rewriting its historical verdict or silently certifying the new source. The parent SHALL trace static requirements to relevant guards, bindings and test contracts. Preservation claims SHALL use actual before/after evidence; mechanical readiness SHALL NOT establish semantic completeness.

#### Scenario: Mixed working tree
- **WHEN** task work includes committed, staged, unstaged and new files alongside unrelated edits
- **THEN** the manifest includes the selected contents and parent-declared exclusions, and no unrelated work is included automatically

#### Scenario: Review target changes
- **WHEN** source used as evidence changes during or after the review
- **THEN** the report retains its captured-version verdict, identifies changed inputs separately, and the parent reconciles the affected evidence before applying findings to current source

#### Scenario: Source comparison fails
- **WHEN** comparison encounters deleted/replaced/linked/external inputs or a failed Git query
- **THEN** a versioned completed report keeps its verdict/status, records changed/removed/unavailable inputs separately, and freshness queries retain their documented compatibility behavior

#### Scenario: Explicitly selected evidence previously filtered
- **WHEN** the parent selects an ignored log, credential-like fixture, sensitive-looking filename or linked/external reference
- **THEN** it is included or reports an actual access/format problem, without a filename/content/ignore-status veto or another export approval requirement

#### Scenario: Dependency absent from the packet
- **WHEN** a relevant caller or fixture is not among the captured files but lies within the authorized read scope
- **THEN** Claude can inspect it and identify the live evidence consulted rather than being confined to the packet

#### Scenario: Harness safety depends on fixture guards
- **WHEN** a static isolation requirement depends on a neighboring fixture's guards
- **THEN** it is supplied or investigated as relevant authorized evidence; unverified required behavior remains explicit

#### Scenario: Preservation baseline unavailable
- **WHEN** prior-version evidence is unavailable for a preservation claim
- **THEN** comparison remains with an identified evidence owner and the review claims only supported current correctness

#### Scenario: Supplied required context skipped
- **WHEN** a genuinely required subject is unread
- **THEN** required coverage remains partial/unreviewed with a reason under the existing recheck budget

### Requirement: Review modes use distinct acceptance criteria
Plan review SHALL evaluate acceptance criteria, architecture, contracts, risks and verification strategy without demanding unauthorized implementation. Implementation review SHALL reuse existing correctness, requirement-coverage and drift criteria. Both SHALL require concrete evidence, distinguish confirmed problems from plausible concerns, and identify unreviewed required scope. Parent-provided notes or prior reports MAY be available as context; the reviewer SHALL form its own conclusions from source evidence rather than treating another verdict as approval.

#### Scenario: Independent plan critique
- **WHEN** Claude reviews an unimplemented OpenSpec plan
- **THEN** it evaluates the proposed behavior on its merits without treating absent implementation or another reviewer's agreement as proof

#### Scenario: Unread implementation scope
- **WHEN** Claude cannot inspect required change evidence or verify a required scenario
- **THEN** it reports that gap and the checkpoint remains incomplete

### Requirement: Claude reuses shared specialist guidance
The parent SHALL select relevant specialist instructions from the existing native role catalog and supply their actual paths through guidance alongside applicable cross-review/code-review criteria. Provenance and hashes SHALL remain recorded. Claude SHALL apply these instructions as review criteria while retaining the advisory assignment and explicit reviewer settings; native profile model defaults SHALL NOT change Claude's model/effort. Normal instruction discovery SHALL remain available. Explicit guidance must be actually available, without filename/extension/default-size vetoes, but SHALL NOT require a separate per-file coverage attestation merely because it was supplied.

#### Scenario: Specialist review across domains
- **WHEN** review involves architecture and data contracts
- **THEN** existing relevant profiles are available with provenance, without creating another role catalog or disabling normal instruction discovery

#### Scenario: Implementation profile remains advisory
- **WHEN** supplied guidance includes implementation or model-routing directions
- **THEN** it does not expand the assigned review phase or change explicit settings, and actual runtime/visual evidence remains attributed to its owner

#### Scenario: Explicit guidance unavailable
- **WHEN** an explicitly selected role instruction cannot be read or captured
- **THEN** preparation blocks for actual missing guidance without deriving acceptance from a guidance coverage checkbox

### Requirement: Structured findings and Codex reconciliation
The launcher SHALL save validated execution status, phase, scope identity, requested/observed settings, required coverage, findings, limitations and verdict. Process success SHALL NOT establish approval. Codex SHALL verify findings, record dispositions and assign fixes. Accepted blockers and incomplete required coverage SHALL keep the checkpoint unresolved. Optional context SHALL NOT determine completeness. Source changes SHALL be attributed and reconciled without discarding a valid captured-version review. Rechecks SHALL remain bounded and tied to changed evidence.

#### Scenario: Valid review finds a defect
- **WHEN** Claude completes with an evidence-backed blocking finding
- **THEN** Codex verifies and dispositions it, retaining the accepted issue despite successful process exit

#### Scenario: Invalid output or missing result
- **WHEN** Claude returns malformed output or omits required coverage
- **THEN** the launcher reports the failure or incomplete checkpoint rather than inferring approval

#### Scenario: Optional context not consulted
- **WHEN** required changes/requirements are covered but optional supporting files were not read
- **THEN** the report may retain its supported verdict while identifying consulted or unavailable context without a blanket incomplete conversion

### Requirement: Local packet readiness
The launcher SHALL offer preparation that validates manifest structure, required evidence availability and writable report/packet locations without invoking Claude. Normal execution SHALL repeat these checks. Unavailable required evidence SHALL block with actionable feedback. Optional context problems SHALL be reported as limitations. Filename/content/ignore/link rules and default input byte thresholds SHALL NOT veto explicit selection.

#### Scenario: Missing or filtered evidence
- **WHEN** required evidence is actually unavailable or available selected evidence would have been rejected by the former automatic filters
- **THEN** only the actual missing required evidence blocks preparation, while former filename/content/ignore/link exclusions do not veto inclusion

#### Scenario: Readable deleted file
- **WHEN** a selected file was deleted and a scoped diff supplies its contents
- **THEN** preparation treats the deletion as reviewable and preserves captured evidence identity

#### Scenario: Preparation succeeds
- **WHEN** required evidence and local output checks pass
- **THEN** the launcher saves preparation counts, provenance and warnings without claiming review execution or approval

### Requirement: Explicit acceptance ownership
Existing manifests and requirement mappings SHALL remain supported. Selected change files, explicit requirements and declared required context SHALL determine static acceptance. Supporting context SHALL be optional by default, with an explicit way to identify genuinely required context. Invalid mappings or unavailable mapped evidence SHALL block preparation. Parent-owned runtime/visual checks SHALL remain separately attributed and SHALL NOT be automatically marked passed by static review.

#### Scenario: Visual acceptance belongs to parent
- **WHEN** a manifest lists a browser check separately
- **THEN** its owner/status remain available for parent reconciliation without a static reviewer attesting to unobserved execution

#### Scenario: Invalid requirement mapping
- **WHEN** a mapping names an unknown requirement or evidence outside the supplied paths
- **THEN** validation reports the actual structural error before execution

#### Scenario: Legacy context list
- **WHEN** an existing manifest supplies context without marking it required
- **THEN** it uses the new optional-context default without requiring a mode flag

### Requirement: Line-readable diff evidence
The packet SHALL retain ordinary UTF-8 committed, staged and unstaged diff artifacts with path provenance, deletions/renames and captured hashes. Explicit selection and exclusions SHALL control scope. Binary markers SHALL NOT abort the whole review; selected non-text originals SHALL remain identifiable attachments/references. Former input byte thresholds SHALL be warnings, with optional explicit resource limits. Large inputs SHALL avoid unnecessary eager loading.

#### Scenario: Mixed tree changes
- **WHEN** selected evidence contains committed, staged, unstaged, new, renamed, deleted or non-text files
- **THEN** the review receives readable differences and identifiable originals without automatic private-content rejection

#### Scenario: Former input cap exceeded
- **WHEN** an input exceeds the old 1 MB/file-diff or 8 MB packet threshold and no explicit limit was configured
- **THEN** preparation reports a size warning and retains the selected evidence

#### Scenario: Operator-selected resource budget
- **WHEN** an explicit byte budget is exceeded
- **THEN** preparation reports the actual resource limit and affected input instead of classifying it as a security exclusion

### Requirement: Native guidance path identity
Preparation SHALL recognize explicit captured guidance by its native original/resolved identity, including Windows slash differences. Original subjects and mappings SHALL be preserved. Actual unavailable required or mapped evidence SHALL block, while removed content/filename/ignore/default-size filters SHALL NOT return through identity matching.

#### Scenario: Windows forward-slash guidance
- **WHEN** explicit guidance uses forward slashes and native capture uses Windows separators
- **THEN** guidance/mappings resolve without changing original subjects

#### Scenario: Missing or filtered mapped evidence
- **WHEN** mapped required evidence is truly unavailable or would have met a former automatic filter
- **THEN** actual absence blocks while former filters do not veto available selected evidence

### Requirement: Actionable sanitized launch failures
Failure reports SHALL identify the failed stage and a safe diagnostic category with a suggested next action. Reports and console output SHALL NOT expose raw stdout/stderr, credentials, or private source. Known CLI errors MAY retain fixed recognized diagnostic phrases without surrounding payloads. Unknown errors SHALL remain unknown with their exit code or exception type; numeric OS error codes SHALL be retained when available. The launcher and Claude exit codes SHALL be distinguished, with Claude's unsigned 32-bit hex exit code available. An explicit --debug option MAY capture raw review stdout/stderr locally as they arrive, in per-attempt Git-ignored files referenced by path rather than echoed into the parent context. Each attempt SHALL retain its own report.

#### Scenario: Permission failure before model execution
- **WHEN** the report or packet location is not writable
- **THEN** the launcher reports filesystem preparation as blocked before invoking Claude

#### Scenario: CLI failure contains sensitive text
- **WHEN** Claude exits with an error containing a recognizable failure and private payload
- **THEN** the report retains a safe diagnostic category, exit code, stage, action, and recognized fixed phrases, without echoing the private payload

#### Scenario: Unknown error with local debug capture
- **WHEN** the user enables --debug and Claude returns an unknown failure
- **THEN** local stdout/stderr files retain the raw review output, while reports and console output retain safe metadata and capture paths without echoing the payload

## ADDED Requirements

### Requirement: Legacy review query compatibility
The legacy write-check interface SHALL remain usable for existing records without creating new reservations or removing another owner's records. Freshness queries SHALL retain current/eligible fields and 0/3 exits for versioned and unversioned reports and SHALL NOT rewrite saved reports. New host status SHALL remain actual execution status; source applicability SHALL be separate.

#### Scenario: Existing reservation query
- **WHEN** an older caller checks an existing active record
- **THEN** the retained query reports its overlap or record error without sweeping it

#### Scenario: Changed-input freshness query
- **WHEN** captured input is changed or comparison is unavailable
- **THEN** current is false, the conservative eligibility shortcut is false and exit3 is returned without erasing the historical verdict, including optional-only/guidance-only drift

#### Scenario: Unchanged-input freshness query
- **WHEN** captured inputs are unchanged
- **THEN** exit0/current=true are returned, with eligibility dependent on actual completed clean required coverage

## REMOVED Requirements

### Requirement: Cooperative review input reservations
**Reason**: A captured review need not reserve original files for its entire execution. Parent-owned write coordination and revision-aware reconciliation remain.
**Migration**: New reviews create no full-run reservations or mandatory writer prechecks. Retain legacy check compatibility for existing callers/records during transition and leave old record cleanup with their owner.
