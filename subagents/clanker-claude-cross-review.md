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

The coordinator owns review selection. Follow the selected checkpoint and preserve
planning-only scope, explicit requests, and opt-outs.

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
   the shared `clanker-code-review` skill. Apply its substantive review criteria;
   this handoff governs review scope and output format, including verdict labels.
   Guidance must be available but does not need a separate coverage item. Role
   instructions do not authorize implementation, command/test execution,
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
5. Write the manifest and run `--prepare-only` as described below. Parent task
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

Use the shared code-review criteria and evidence requirements. State required
files/scenarios not reviewed. Supplied test logs are parent evidence;
Claude must not claim it ran tests, inspected a browser, or verified anything beyond
the evidence it accessed.

## Launcher and prerequisites

Locate `scripts/claude_cross_review.py` relative to the coordinator package. In the
source checkout it is under `subagents/scripts/`. Use a verified Python 3.10+ executable;
no third-party packages are needed. The launcher requires an installed Claude Code CLI
and confirmed subscription login. Read its `--help` before invocation and use supported flags.

Model selection is independent of the Codex parent and native worker defaults. Resolve
the packet's `claude-review` route using the coordinator run snapshot and dispatch
procedure in `routing/usage.md`; reassess remaining risk for each recheck. Pass the
resolved model and effort explicitly. Keep persistent Claude settings unchanged and
unknown effective settings unknown. Do not
silently switch to API billing, install software, edit persistent configuration, or
initiate login. If preflight blocks, report the specific prerequisite.

The launcher checks subscription authentication and invocation capabilities. Use a
finite wall-clock timeout (default: 2700 seconds / 45 minutes), adjustable with
`--timeout-seconds`. Normal CLI and managed permissions apply. Do not add
permission-bypass flags or send a resume argument by default; each initial review
forms its own judgment.

## Manifest and invocation

Use argument arrays or literal shell arguments; do not concatenate untrusted prompt
text into commands. Choose a Git-ignored output location for captured source.
Write a JSON manifest in a parent-owned artifact location. Selected and context paths
are repository-relative or absolute external file references. `read_roots` is an
optional list of unique absolute existing directories already within the parent's
authorized read scope. It allows dependency investigation through the normal CLI; it
does not grant permissions beyond the parent or managed environment. An explicitly
selected external file is copied into the packet, without granting its source directory.
Requirements and `verification_evidence` are lists of non-empty strings. Exclusions
document parent scope decisions. Use a unique `run_id`; baseline must identify a verified Git ref.
The optional prompt can add task-specific focus but cannot expand the assignment.

Optional `requirement_paths` maps each requirement string to a nonempty list of paths
already supplied as selected, context, or guidance evidence. `required_context_paths`
must be a unique subset of `context_paths`. Do not exclude mapped or required evidence.
Report actual format or access limits instead of filtering evidence by name or content.

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
  "guidance_paths": [
    "C:/Users/example/.codex/skills/clanker-orchestration-nation/references/clanker-claude-cross-review.md",
    "C:/Users/example/.codex/skills/clanker-orchestration-nation/references/clanker-backend-developer.md",
    "C:/Users/example/.codex/skills/clanker-code-review/SKILL.md"
  ],
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

Run preparation before invocation. It checks manifest structure, required evidence,
and output readiness without Claude, login, effort, or a model call. `prepared` is not
approval; execution repeats the checks against current inputs.
The retained packet supplies line-readable Git diff files under
`_clanker_packet/diffs/`, referenced by `_clanker_packet/evidence.json`. Read those
files directly instead of extracting escaped diff strings from JSON.

## Run and collect

Launch each review once and retain its process/session handle. Prefer completion
notifications where the host supports them; otherwise use bounded waits rather than
rapid status polling. Do independent work while the review runs. Collect the compact
final report once, then inspect findings as needed. Do not repeatedly dump unchanged
logs, restart a healthy review, or spawn a native agent solely to wait. Read
`report.json` and `summary.md` from the returned attempt path.

If execution fails or is interrupted, inspect that attempt's diagnostics and the
launcher's help/source before retrying. Report unresolved failures and preserve the
attempt; do not paste raw diagnostic logs containing reviewed source into the chat.

## Findings and reconciliation

Model verdicts are `clean`, `changes_requested`, or `incomplete`. Coverage items identify
required acceptance subjects with `covered`, `partial`, or `unreviewed` status plus
concrete evidence or a reason for a gap.
Each finding includes an id, severity (`blocking`, `major`, `minor`, `info`), location,
scenario, evidence, confidence (`confirmed`/`plausible`), and `suggested_remedy`.
Host execution status, scope identity, requested settings, and observed runtime metadata
are separate from the model verdict.

A valid completed review keeps its captured-version verdict and execution status even
when source comparison later finds changes or becomes unavailable. Comparison errors
must not erase the captured result. The parent checks whether affected paths matter to
current findings and reconciles them before applying findings. Do not discard a report
solely because an optional file changed. A successful process exit, no findings, or
apparent agreement alone does not prove approval.

Use `--check-current` to query source changes without rewriting the report. Source
changes do not identify a writer; live consulted files outside the captured packet
are not covered by its source-freshness guarantee.

Verify findings against current evidence. Record accepted/rejected/deferred/
needs-evidence dispositions with reasons. Keep accepted blocking issues open until fixed
and verified, or explicitly waived by the user. Rechecks remain bounded to one
automatic recheck per phase; report remaining gaps after that limit.

The parent records the report link, coverage, dispositions, and remaining checks using
the coordinator's logging procedure. Preserve all attempts. Claude and the launcher
must not update the shared log or OpenSpec task state.

## Write coordination

New reviews create no full-run source reservations and require no writer quiescence or
pre-review write check. The parent coordinates overlapping writes through declared file
ownership and dependencies. Leave any legacy reservation records to their original owner.
