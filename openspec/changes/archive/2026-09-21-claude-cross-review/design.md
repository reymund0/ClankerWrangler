## Context

See proposal.md for motivation and specs/claude-cross-review/spec.md for the behavior contract. The existing coordinator and twelve specialist references are under subagents/. Both wrangle installers copy the coordinator as one visible SKILL.md and specialist Markdown as references. They currently do not distribute supporting scripts. The shared implementation review contract is skills/clanker-code-review.md.

The implemented orchestration-nation change remains unarchived and its main capability specs have not been published. This new change depends on that implementation; it introduces a separate capability rather than modifying unpublished delta requirements. The current policy reserves delegation for native Codex workers and routes planning/review to Sol. It needs an explicit external-review exception without weakening the native-worker policy.

Claude Code 2.1.278 was verified locally at C:/Users/Raymo/.local/bin/claude.exe. Its help advertises print mode, JSON/schema output, safe mode, restricted mode, tool selection, no-session-persistence, and noninteractive permission denial. Installation and version availability do not prove subscription login, model access, or successful restricted execution. No review model call was made while preparing this proposal.

## Goals / Non-Goals

**Goals:** A small, inspectable bridge from Codex to a subscription-authenticated Claude reviewer; repeatable review inputs; useful independent findings; deterministic failure handling; source and installed-package parity.

**Non-Goals:** Claude-led orchestration, another agent framework, native Codex registration of a Claude model, Claude editing code, Claude browser/visual review, replacing Sol review or tests, automatic login/install, and API-billed fallback.

## Decisions

### 1. Keep one parent and one external review adapter

Codex invokes the launcher directly while native Codex workers continue to use existing collaboration tools. Do not spend a native worker slot merely wrapping a CLI process. Treat the external reviewer as one of the existing maximum three concurrent work assignments and run at most one Claude process at a time per orchestration run. Independent read-only review can overlap, but the target must remain stable.

Add subagents/clanker-claude-cross-review.md as a bundled reference with separate plan and implementation modes. Reuse architecture/product/QA criteria for plans and the shared code-review contract for implementation. Do not direct the implementation-only code-review skill to review unimplemented plans. Include the source/installed instruction paths in dispatch evidence. Mark the entire orchestration workflow as Codex-driven in the coordinator and README; packaging into Claude's skills directory does not imply support for Claude as the parent.

Select specialist instructions from the existing coordinator role catalog for each Claude review, using the same source/installed files as native workers. Resolve and verify the selected files even when the user says both clients have them; isolated safe mode still requires explicit guidance_paths. Include only relevant profiles alongside the cross-review reference and shared implementation code-review contract. Record original paths and snapshot hashes using the existing guidance provenance mechanism; add no duplicate Claude-specific role catalog. Translate a role's implementation/tool instructions into advisory review criteria: Claude never edits, executes tests, deploys, or launches nested agents. A role's native model defaults do not change the separately selected Claude model/effort. Visual evidence remains native UI/UX responsibility; a textual profile cannot establish rendered acceptance.

Alternative: create separate native profiles or a new visible skill for each provider/phase. Rejected because the selected one-entry bundle already expresses roles without expanding menus or introducing a second scheduler.

### 2. Use one portable standard-library launcher

Proposed source: subagents/scripts/claude_cross_review.py; installed location: scripts/claude_cross_review.py beneath the coordinator package. A single Python 3.10+ implementation handles subprocess arguments, JSON, timeouts, fingerprints, and output validation consistently across Windows and POSIX. Python is an optional cross-review prerequisite, not a dependency of basic wrangle installation. Resolve a real Python runtime from the active environment; never assume another machine has this workstation's C:/Python314 path. Do not auto-install dependencies.

The interface accepts a manifest path, output directory, optional absolute Claude executable, an optional model override, a required explicit effort selection, and bounded execution settings. Use subprocess argument arrays and stdin, never shell-built prompt commands. Accept a native executable on Windows; unsupported launch shims produce a diagnostic rather than unsafe shell evaluation. Defaults proposed for initial use: 600-second timeout, 20 agentic turns, and one automatic recheck per checkpoint after accepted fixes. User overrides must remain finite. A timeout terminates the owned process tree and preserves an incomplete result; cancellation follows the same cleanup path.

Alternative: separate PowerShell and Bash implementations. Rejected because maintaining equivalent JSON validation, error semantics, and subprocess handling in two shells adds avoidable divergence. Python adds a runtime prerequisite, so missing Python is an explicit blocked cross-review rather than an installer failure.

### 3. Preflight subscription authentication and actual CLI capabilities

Resolve Claude using an explicit executable, PATH, then the documented platform-native location. Verify executable identity/version and required controls with local help plus targeted capability tests during implementation; do not infer all behavior solely from a version number. Query auth status in JSON when supported, normalize only the fields needed to establish subscription login, and never persist identity or credential payloads. An unknown schema or auth method blocks rather than guessing.

Inspect credential/provider override presence without printing values, including API keys, custom base URLs, provider-selection settings, and API credential helpers relevant to the installed CLI. Subscription mode must be positively established for the actual invocation environment. Conflicting or unverified configuration reports a corrective action; do not mutate persistent settings or silently switch providers. Do not use --bare: current official documentation says it skips subscription credentials. Authentication refresh performed by the official CLI is distinct from changing the user's selected account/provider.

Default every cross-review to the pinned Claude Opus 5 identifier, claude-opus-5, unless the user supplies an explicit per-review --model override. Pass the selected model explicitly and record it even when preflight blocks. Ambient ANTHROPIC_MODEL and settings model defaults do not override this review-specific choice; continue checking settings for provider/credential conflicts without modifying persistent configuration. This is a fixed model preference with adaptive effort, not a task-based model classifier. If the requested model is unavailable, report failure without substituting another model. The model identifier is verified in Anthropic's Opus 5 documentation (https://platform.claude.com/docs/en/models/opus-5/whats-new-opus-5). The parent selects effort before each dispatch using the adaptive policy below, preserving explicit user choices. Record the request separately from the effective model and effort returned by the CLI. Never pass automatic model fallback. Unsupported requested settings block that review. The parent's Codex model remains unchanged.

### 3a. Select effort from the actual review scope

The orchestrator owns semantic effort selection; the launcher does not infer risk from file counts or keywords. First decide whether review is warranted: small low-risk edits still skip Claude unless explicitly requested. For a selected review, use low for mechanical documentation/consistency checks, medium for routine feature plans, acceptance/test strategy, or bounded backend/UI changes with clear requirements, and high for complex architecture, cross-layer contracts, auth, migrations/data integrity, deployment/recovery, or complex performance behavior. A small security-sensitive diff can warrant high.

Honor an explicit supported user effort over this routing. Reassess the remaining scope and risk for a recheck: a narrowly mechanical correction can use low, while unresolved security or data risks retain high; neither inherit nor lower the prior effort automatically. The existing one-recheck bound stays intact. Visual acceptance remains with the native UI/UX reviewer.

Pass the chosen value explicitly with --effort and record phase, scope/risk reason, and any user override in the parent-owned run log. The launcher has no effort default and rejects missing/blank effort before preflight or model execution; --check-current remains usable without effort. Existing requested_settings.effort records the selection independently of observed runtime settings. Unsupported selections still fail without fallback. Direct callers that relied on the former high default must add --effort; README and bundled examples must show it. Model selection and parent/native routing remain unchanged.

### 4. Restrict Claude to an explicit review packet

Use safe mode to disable ambient hooks, skills, plugins, memory, and project configuration while preserving authentication. Combine supported restricted mode with a Read/Glob/Grep tool set, matching read-tool preapprovals, disabled MCP tools/configuration, and noninteractive permission denial. No shell, edit, write, agent, browser, or command execution tools are exposed. Do not use bypass-permissions flags. Managed policy remains in force; if the effective restrictions cannot be established, stop before review.

Create an ephemeral review snapshot outside the working checkout containing only selected text files, necessary caller/context files, rules, selected OpenSpec artifacts, and precomputed Git diffs. Claude's working directory is that snapshot; it receives explicit instructions because safe mode disables automatic instruction discovery. Paths retain their project-relative identity, and the manifest records mappings. A separate guidance_paths list selects exact absolute Markdown instruction files from verified source/installed skill locations outside the target repository. Copy only those files into a snapshot guidance directory, preserve source path/hash provenance, and include them in coverage and freshness checks; never grant their whole parent directory or write a copy into the live checkout. Do not grant the live repository as an additional directory. Explicitly reject traversal, out-of-root symlinks, credentials, ignored/private files, and unknown binary content; identify relevant omitted binaries as uncovered rather than silently dropping them. Caller/context files are selected before dispatch; if Claude needs additional context, return an evidence request for a bounded rerun rather than broadening access autonomously.

The parent resolves a verified baseline/merge base and selects task-owned paths. The launcher captures baseline-to-HEAD changes plus staged/unstaged state and selected untracked contents; use Git in the parent/launcher to prepare evidence, never grant Claude shell access. Include deletion/rename metadata and relevant prior content where needed. Supply test evidence as reported evidence, not as tests Claude claims to have executed. Omit existing reviewers' conclusions from the initial packet.

Record hashes for HEAD, index/diff inputs, selected artifacts, files, and missing/deleted entries. Recheck after completion and immediately before accepting the checkpoint. A changed target is stale even if Claude returned a valid review. Source stability is orchestrator-owned; the snapshot gives Claude consistent inputs but does not prevent users from editing the source. Remove only the uniquely owned temporary snapshot after processing, verifying its absolute containment first.

Alternative: review the live repository with broad read/shell access. Rejected for the first version because it makes review scope, concurrent edits, and side effects harder to establish. This packet approach trades some context flexibility for explicit coverage.

### 5. Separate execution status from findings

Request JSON/schema output and validate the returned envelope and report locally using standard-library checks of the defined schema. Treat nonzero exits, error envelopes, truncated output, absent results, invalid types/enums, missing evidence fields, denied required reads, and incomplete coverage as non-success even if stdout contains plausible prose. Do not equate CLI exit zero with approval.

The report schema includes phase, scope fingerprint, execution status, requested/observed settings, coverage by file/scenario, findings, limitations, and verdict. The launcher owns execution status, scope identity, timestamps, and runtime metadata; model-supplied values cannot override those facts. Findings include a stable identifier, severity, location, concrete failure/plan scenario, evidence, confidence (confirmed/plausible), and suggested remedy. Plan coverage refers to acceptance/design quality; implementation coverage refers to the existing code-review criteria. Execution statuses include completed, blocked, failed, timed_out, interrupted, and stale; a completed report can still require changes.

The launcher validates metadata and structural coverage; the Codex parent checks semantic evidence, reconciles duplicate/conflicting findings with Sol, and records accepted, rejected, deferred, or needs-evidence dispositions with reasons. A rejection needs repository evidence, not model preference. Accepted blocking findings keep the checkpoint open. An incomplete required review does not prevent independent work, but completion must identify the unresolved checkpoint. Only an explicit user waiver can waive it, and a waiver is never described as approval. After the single automatic recheck is exhausted, report remaining issues and request direction instead of looping.

### 6. Store bounded reports and preserve the existing run log

Reserve a unique directory under .clanker/reviews/<run-id>/<phase>-<attempt>/ for manifest metadata, validated report JSON, and a readable findings summary. Sanitize run IDs and refuse overwrite/path escape. Do not save raw source snapshots, auth responses, or unbounded debug transcripts in durable reports. Redact sensitive error text before persisting bounded diagnostics. A report-write failure is an incomplete outcome.

The parent appends selection, dispatch, outcome, reconciliation, and waiver events to the existing run-start-date orchestration log and links the unique report. Claude and the launcher do not edit that shared log or OpenSpec tasks. The parent verifies the result and records successful completion only for the reviewed state. New run output follows existing .clanker conventions; this proposal does not modify the earlier run log.

### 7. Package without expanding installation side effects

Both wrangle installers copy the new reference through their existing Markdown path and copy explicitly owned supporting files under scripts/. Include any schema resources only if the implementation uses separate files; do not copy tests, caches, or arbitrary nested content. Resolve resources relative to the loaded coordinator in source and installed layouts. Keep unrelated files and existing standalone-specialist backup migration intact. Do not add native agent definitions or another visible SKILL.md. The regular shared code-review skill stays separately installed.

Alternative: install the runner globally on PATH or create an MCP service. Rejected because the existing skill bundle provides a stable resource path and requires no background process.

## Risks / Trade-offs

- Another provider can repeat the same mistakes -> independent initial context plus evidence-based Codex reconciliation; never replace tests with reviewer agreement.
- CLI flags/auth behavior can change -> capability preflight, recorded version, fixture tests, and one live authenticated check; unsupported behavior blocks explicitly.
- Snapshot omits important context -> record coverage, request the missing files, and re-review within bounds; never interpret partial coverage as a pass.
- Read-only tool configuration is not a general OS sandbox on Windows -> constrain tools, settings, snapshot roots, and managed-policy behavior; test actual restrictions rather than relying on the prompt alone.
- More reviews increase latency and subscription usage -> substantial-scope checkpoints, one Claude process at a time per run, finite bounds, explicit skip/override controls.
- Python availability varies -> document the prerequisite and resolve it explicitly; no package installation during wrangle or review.

## Migration Plan

1. Implement and validate against the existing orchestration-nation source state without archiving or rewriting that change.
2. Exercise source and installed layouts in temporary Codex/Claude destinations for both installers, including repeated installs and preservation of unrelated content.
3. Run deterministic fake-CLI cases first, then a small subscription-authenticated plan/code fixture review with version and effective settings recorded. If login or limits block the live check, keep that task incomplete and state the limitation.
4. Deliver the source changes and docs for review. Apply them to real user configuration only when separately requested through wrangle.
5. Rollback by restoring the prior coordinator/installer sources and reinstalling; remove only owned added resources after path verification if cleanup is needed. Existing review reports and unrelated skills remain intact.

## References

- https://code.claude.com/docs/en/headless - print mode, JSON results, and bare-mode authentication limits.
- https://code.claude.com/docs/en/cli-reference - safe/restricted modes, tool restriction, permission handling, and execution options.
- https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan - subscription login and API-key override behavior.
- Local Claude Code 2.1.278 --help and auth status --help were read during proposal preparation; authentication and live review remain unverified.
