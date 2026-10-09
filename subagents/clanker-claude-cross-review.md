---
name: clanker-claude-cross-review
description: Obtain an independent Claude Code plan or implementation review of parent-authorized evidence, using the repository, a retained change packet, and evidence-based reconciliation.
---

# Claude Cross-Review

## Ownership and selection

This reference is loaded by the Codex parent, not dispatched as a native Codex role.
Codex owns scope, artifact preparation, invocation, reconciliation, logging, and fixes.
Claude reviews within the task's existing authorization. Do not invoke another
orchestrator or agent team from the reviewer.

Use for substantial plans before implementation and integrated substantial changes
before completion: contracts across layers, consequential architecture, auth,
data integrity/migrations, UI/API/data contract changes, deployment, or measured
performance risks. Record a skip for small low-risk edits. Explicit requests and
opt-outs prevail. Preserve planning-only scope.

## Prepare the review

1. Resolve the selected OpenSpec artifacts and actual repository root. Verify the base
   ref and merge base for implementation reviews. Inventory task-owned committed,
   staged, unstaged, and untracked work; include new contents, not just file names.
2. Identify relevant full files, callers, acceptance scenarios, repository instructions,
   and actual test evidence. Parent selection controls inclusion, including names,
   credential-like examples, ignored files, links, external files, and readable binary
   artifacts. Preserve parent-declared exclusions from capture and task findings; an
   exclusion does not restrict filesystem access. Keep unrelated work out of the task
   findings. Do not send the entire conversation. Trace each static requirement to its
   implementation and relevant caller/guard, configuration binding, and fixture/test
   contract. Include neighboring fixtures when their guards determine a claim. For
   preservation claims, inspect supplied baseline/diffs for actual before/after change;
   when prior evidence is absent, keep the comparison with its named owner and limit
   Claude's claim to supported current correctness.
3. Select relevant specialist files from the coordinator's existing role catalog, as for
   native workers. Resolve source files beside this reference, or installed files under
   the loaded coordinator's `references/`. Verify each selected path. Supply this
   reference and selected profiles as `guidance_paths`; for implementation, also include
   the shared `clanker-code-review` skill. Explicit guidance must be available and
   applied, but does not need a separate coverage item. Role instructions are advisory
   review criteria: they do not authorize implementation, command/test execution,
   deployment, or delegation beyond the current assignment. Native model defaults do
   not change Claude's selected model or effort. Visual acceptance stays with the native
   UI/UX reviewer. Record selected roles and resolved paths in the dispatch log.
4. Define acceptance using selected change evidence, requirement mappings, and any
   `required_context_paths`. Ordinary `context_paths` and guidance remain available
   supporting material; they do not each require a coverage item or determine
   completeness. Existing requirement mappings must point to available supplied
   evidence. Missing selected, mapped, or required context is a preparation/coverage
   problem; an unavailable optional context item is a limitation. Keep browser/runtime
   acceptance in `parent_checks` with its owner, status, and evidence. A clean static
   verdict cannot complete a pending parent check. For a narrow recheck, focus required
   evidence on the correction and retain broader acceptance with the parent.
5. Run local `--prepare-only` to check manifest structure, required evidence, and output
   locations before invocation. It is a readiness check, not a model call. Parent task
   authorization already governs selected files and the review; the handoff does not
   require a second per-file export approval. Keep the captured packet and source-change
   evidence for reconciliation if files change during review.

## Plan review criteria

Check user outcomes, acceptance completeness, edge cases, API/data contracts, existing
architecture fit, migration/rollback needs, operational concerns, and verification
strategy. Cite an actual artifact or relevant repository evidence for each concern.
Distinguish a confirmed contradiction from a plausible risk. Do not flag absent code
or tests as a defect when implementation has not been authorized. Identify missing
required context explicitly and return focused questions, not speculative redesigns.

## Implementation review criteria

Check correctness, regressions, security/data integrity, requirement coverage, test
gaps, and spec/scope drift using the shared code-review contract. Trace relevant full
files and callers before claiming a bug. Every finding needs a concrete failure
scenario, location, impact, evidence, and suggested remedy. Ignore stylistic preferences.
State required files/scenarios not reviewed. Supplied test logs are parent evidence;
Claude must not claim it ran tests, inspected a browser, or verified anything beyond
the evidence it accessed.

## Launcher and prerequisites

Locate `scripts/claude_cross_review.py` relative to the coordinator package. In the
source checkout it is under `subagents/scripts/`. Use a verified Python 3.10+ executable;
no third-party packages are needed. Never hard-code the current developer's Python path
into a task for another machine. The launcher requires an installed Claude Code CLI and
confirmed subscription login. It resolves a verified absolute executable even if PATH
is stale. Read its `--help` before invocation and use supported flags.

Model selection is independent of the Codex parent and native worker defaults. Resolve
the packet's `claude-review` route using the coordinator run snapshot and dispatch
procedure in `routing/usage.md`. Pass the resolved model and effort explicitly. Keep
persistent Claude settings unchanged and unknown effective settings unknown. Do not
silently switch to API billing, install software, edit persistent configuration, or
initiate login. If preflight blocks, report the specific prerequisite.

Preflight checks subscription authentication, the actual capabilities used by this
invocation, and provider/credential overrides from user, repository `.claude/settings.json`,
and `.claude/settings.local.json` in the same repository working directory used for
review. It does not require removed isolation flags. Use a finite wall-clock timeout
(default: 2700 seconds / 45 minutes); there is no turn limit. Session persistence and
ordinary configured tools, MCP, instructions, and permissions follow the user's normal
CLI and managed settings. The review remains advisory. Do not add permission-bypass flags
or send a resume argument by default; each initial review forms its own judgment.

## Waiting and diagnostics

Launch each review once and retain its process/session handle. Prefer completion
notifications where the host supports them; otherwise use bounded waits rather than
rapid status polling. Do independent work while the review runs. Collect the compact
final report once, then inspect findings as needed. Do not repeatedly dump unchanged
logs, restart a healthy review, or spawn a native agent solely to wait. The wall-clock
limit can be overridden with `--timeout-seconds`.

Add `--debug` to retain the review process's raw stdout/stderr in local `stdout.log`
and `stderr.log` files. These can contain reviewed source; they are Git-ignored and
must not be pasted wholesale into the parent context. Capture does not enable Claude
debug mode or alter its review settings. Use argument arrays or literal shell arguments;
do not concatenate untrusted prompt text into commands. The helper returns its unique
report path. Read `report.json` and `summary.md` from that location, not from a guessed
most-recent directory.

The retained packet contains copies of explicitly selected evidence. Choose a
Git-ignored output location so those artifact copies are not accidentally committed.

The launcher prints its attempt directory and log paths immediately to stderr. Stdout
remains one final JSON result. Each attempt saves flushed `events.jsonl` stage events
and an atomically replaced `progress.json`, with launcher/Claude PIDs, elapsed time,
output byte counts, and the last observed output time. During review it updates these
every 30 seconds without printing the transcript or heartbeats. A running process or
recent heartbeat is not proof of model progress. If the calling tool interrupts the
launcher before a final report is saved, inspect these existing files; a last running
state may be stale and is not a diagnosis of the external interruption.

On failure, use the reported stage, safe diagnostic category, and suggested action.
The final JSON also includes the diagnostic and launcher exit code (`0` or `2` for
review/preparation; legacy queries also use `3`);
the progress/report process metadata records Claude's exit code separately, including
its unsigned 32-bit hex representation. Numeric OS error codes are retained when
available. A caller's `-1` without a recorded Claude exit is not evidence that Claude
returned `-1`. Known CLI errors retain only recognized fixed phrases, not surrounding
private text. For an unknown failure, inspect existing logs and enable `--debug` on
the next authorized attempt to preserve raw diagnostic output locally. Do not retry
unchanged manifest, access, or runtime failures without resolving the cause; retain
previous attempts. Unknown CLI failures remain unknown, with an exit code and no raw
payload in reports or console output. Debug capture covers the review process, not
preflight output.

Preparation retains selected inputs above the former 1 MB per-file/diff and 8 MB
packet thresholds with warnings. Optional `--max-file-bytes` and `--max-packet-bytes`
budgets are disabled by default. These source-input budgets are separate from report
and diagnostic output limits.

## Manifest and invocation

Write a JSON manifest in a parent-owned artifact location. Selected and context paths
are repository-relative or absolute external file references. `read_roots` is an
optional list of unique absolute existing directories already within the parent's
authorized read scope. It allows dependency investigation through the normal CLI; it
does not grant permissions beyond the parent or managed environment. An explicitly
selected external file is copied into the packet, without granting its source directory.
Use `required_context_paths` only for context that determines acceptance. Requirements
and `verification_evidence` are lists of non-empty strings. Exclusions document parent
scope decisions. Use a unique `run_id`; baseline must identify a verified Git ref.
The optional prompt can add task-specific focus but cannot expand the assignment.

Optional `requirement_paths` maps each requirement string to a nonempty list of paths
already supplied as selected, context, or guidance evidence. Existing manifests remain
valid; context is optional by default. Explicit guidance must be readable and captured.
`required_context_paths` must be a unique subset of `context_paths`; malformed or
unavailable `read_roots` are structural errors. Excluding mapped or required context is
a contradictory manifest. Preserve original subjects and mappings while resolving
native path identity, including Windows slash differences. Selected links and external
references retain original/resolved provenance and deterministic packet paths, including
when basenames collide. Non-text originals remain identifiable; report actual format or
access limits instead of filtering them by name or content.

```json
{
  "repository": "C:/work/my-app",
  "phase": "implementation",
  "run_id": "team-invitations-2026-09-21-1",
  "baseline": "main",
  "selected_paths": ["src/invitations.py", "tests/test_invitations.py"],
  "context_paths": ["AGENTS.md", "openspec/changes/team-invitations/specs/invitations/spec.md"],
  "required_context_paths": ["AGENTS.md"],
  "read_roots": ["C:/work/shared-contracts"],
  "guidance_paths": ["C:/Users/example/.codex/skills/clanker-backend-developer.md"],
  "requirements": ["Expired invitations cannot be accepted."],
  "requirement_paths": {
    "Expired invitations cannot be accepted.": ["src/invitations.py", "tests/test_invitations.py"]
  },
  "exclusions": [],
  "verification_evidence": ["Focused test run recorded by the parent"]
}
```

The paths and evidence above are illustrative. Supply actual existing paths and observed
evidence. For a plan review, select planning artifacts and use phase `plan`. Use
`guidance_paths` for individually selected absolute instruction files outside the
repository, including this reference and the shared code-review contract for
implementation. The launcher captures those files and records provenance and hashes.
`parent_checks`, when supplied, contain parent-owned `{subject, owner, status, evidence}`
records with `pending`, `passed`, or `failed` status; they are not reviewer attestations.

```text
python <package>/scripts/claude_cross_review.py --manifest <manifest.json> --output-dir <repo>/.clanker/reviews --prepare-only
python <package>/scripts/claude_cross_review.py --manifest <manifest.json> --output-dir <repo>/.clanker/reviews --model <resolved-model> --effort <resolved-effort>
python <package>/scripts/claude_cross_review.py --check-current <saved-report.json>
```

Required for review execution: `--effort <selected supported level>`. Optional switches:
`--claude-exe <absolute executable>`, `--model <selection>`, and
`--timeout-seconds <positive integer>`. Reviews are bounded by timeout only.
`--check-current` does not require effort. The launcher validates subscription and
actual invocation capabilities before model execution.

Resolve effort for each review from the existing run snapshot. Assess scope, uncertainty,
and consequences rather than file count; let the resolver apply configured effort and
ceilings. Reassess the remaining risk for a recheck instead of automatically carrying
the prior effort forward. Live visual acceptance stays with the native UI/UX reviewer.

Preparation needs no Claude executable, login, or effort and makes no model call. It
checks manifest structure, required evidence and local writable locations, saves a
unique readiness result, and releases temporary resources. `prepared` is not approval
or a claim of model access; normal execution repeats checks against current inputs.
The retained packet supplies line-readable Git diff files under
`_clanker_packet/diffs/`, referenced by `_clanker_packet/evidence.json`. Read those
files directly instead of extracting escaped diff strings from JSON.

## Findings and reconciliation

Model verdicts are `clean`, `changes_requested`, or `incomplete`. Coverage items identify
required acceptance subjects with `covered`, `partial`, or `unreviewed` status plus
concrete evidence or a reason for a gap. Optional context does not need a coverage item.
Each finding includes an id, severity (`blocking`, `major`, `minor`, `info`), location,
scenario, evidence, confidence (`confirmed`/`plausible`), and `suggested_remedy`.
Host execution status, scope identity, requested settings, and observed runtime metadata
are separate from the model verdict.

New host reports use `schema_version: 2`. `source_evidence.read_scope` records
`repository` (absolute path), `packet` (absolute retained attempt/packet directory),
and `additional_roots` (canonical absolute paths). Optional top-level
`consulted_paths` records reviewer-attested live paths; those paths are unhashed and
outside the source-freshness guarantee. `source_changes` records `current`, `changed`, or
`unavailable`, with `attribution: unattributed` and entries for changed, removed, or
unavailable inputs. Each entry has `path`, `status`, `kind`, and `reason`, and may include
`resolved_path`; kinds are `required`, `optional`, `guidance`, `manifest`, or `git`.
These fields describe source applicability; they do not identify a writer.

A valid completed review keeps its captured-version verdict and execution status even
when source comparison later finds changes or becomes unavailable. Comparison errors
must not erase the captured result. The parent checks whether affected paths matter to
current findings and reconciles them before applying findings. Do not discard a report
solely because an optional file changed. A successful process exit, no findings, or
apparent agreement alone does not prove approval.

`--check-current` is a read-only query. For schema v2 it prints live source changes and
the recorded execution status, returns 0 when sources are current and 3 when changed or
unavailable, and never rewrites the report. Its `eligible_for_parent_review` is a
conservative shortcut: true only when sources were current at completion and remain
current, execution completed, and the verdict is clean. Optional-only or guidance-only
drift still returns current=false/exit 3, without changing completeness or the verdict.
Legacy unversioned reports retain their prior display behavior.

Verify findings against current evidence. Record accepted/rejected/deferred/
needs-evidence dispositions with reasons. Keep accepted blocking issues open until fixed
and verified, or explicitly waived by the user. Rechecks remain bounded to one
automatic recheck per phase; report remaining gaps after that limit.

Only the parent appends to `.clanker/YYYY-MM-DD-orchestration-nation.md`, using the
existing run ID and original log date. Link the unique report and summarize selection,
requested/observed settings, actual coverage, failures, dispositions, and waivers.
Preserve all attempts. Claude and the launcher must not update the shared log or
OpenSpec task state. Report unsuccessful saves and unrun verification honestly.

## Write coordination

New reviews create no full-run source reservations and require no writer quiescence or
pre-review write check. The parent coordinates overlapping writes through declared file
ownership and dependencies. The legacy `--check-writes` query remains available to old
callers and reports existing records; it creates no review reservation. Do not sweep
old records. Their original owner may remove one only after verifying that its owned
process has stopped. A later `source_changes` result supports parent reconciliation; it
does not establish who changed a file.
