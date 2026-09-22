---
name: clanker-claude-cross-review
description: Obtain an independent Claude Code plan or implementation review under Codex orchestration, using subscription authentication, a bounded read-only packet, and evidence-based reconciliation.
---

# Claude Cross-Review

## Ownership and selection

This reference is loaded by the Codex parent, not dispatched as a native Codex role.
Codex owns scope, artifact preparation, invocation, reconciliation, logging, and fixes.
Claude only reviews. Do not invoke another orchestrator or agent team from the reviewer.

Use for substantial plans before implementation and integrated substantial changes
before completion: contracts across layers, consequential architecture, auth, data
integrity/migrations, deployment, or measured performance risks. Record a skip for small
low-risk edits. Explicit requests and opt-outs prevail. Preserve planning-only scope.

## Prepare the review

1. Resolve the selected OpenSpec artifacts and actual repository root. Verify the base
   ref and merge base for implementation reviews. Inventory task-owned committed,
   staged, unstaged, and untracked work; include new contents, not just file names.
2. Identify relevant full files, callers, acceptance scenarios, repository instructions,
   and actual test evidence. Exclude unrelated work, ignored/private files, credentials,
   binary/generated content that cannot be reviewed, and other reviewers' conclusions.
   Explain any excluded scope that affects acceptance. Do not send the entire conversation.
3. Select the relevant specialist files from the coordinator's existing role catalog,
   just as for native workers: for example architect/product/QA for a plan, or backend,
   data, DevOps, and performance for those implementation risks. Use the same profiles;
   do not create a separate Claude catalog. Resolve source files beside this reference,
   or installed files under the loaded coordinator's references/. Verify each selected
   path; missing guidance must be resolved before dispatch. Even when both clients have
   the profiles installed, safe mode does not discover them automatically.
4. Supply this reference and selected profiles as guidance_paths. For implementation,
   also resolve and include the shared clanker-code-review skill. Treat role instructions
   as advisory criteria: implementation, command/test execution, deployment, or delegation
   steps become checks against supplied evidence, not permission to perform those actions.
   Native model defaults in profiles do not change Claude's selected model/effort. Rendered
   visual acceptance stays with the native UI/UX reviewer; profile text is not visual proof.
   Map review sections into coverage/findings/limitations/verdict, preserving JSON output.
   Record selected roles and resolved paths in the dispatch log; the launcher records
   guidance paths and hashes in the report.
5. Keep the target stable during review. Use a new attempt directory for a rerun. A
   changed source fingerprint invalidates the old verdict even if the snapshot was stable.

## Plan review criteria

Check user outcomes, acceptance completeness, edge cases, API/data contracts, existing
architecture fit, migration/rollback needs, operational concerns, and the verification
strategy. Cite an actual artifact or relevant repository evidence for each concern.
Distinguish a confirmed contradiction from a plausible risk. Do not flag absent code
or tests as a defect when implementation has not been authorized. Identify missing
context explicitly and return focused questions, not speculative redesigns.

## Implementation review criteria

Check correctness, regressions, security/data integrity, requirement coverage, test
gaps, and spec/scope drift using the shared code-review contract. Trace relevant full
files and callers before claiming a bug. Every finding needs a concrete failure
scenario, location, impact, evidence, and suggested remedy. Ignore stylistic preferences.
State files/scenarios not reviewed. Supplied test logs are parent evidence; Claude must
not claim it ran tests, inspected a browser, or verified anything beyond the packet.

## Launcher and prerequisites

Locate `scripts/claude_cross_review.py` relative to the coordinator package. In the
source checkout it is under `subagents/scripts/`. Use a verified Python 3.10+ executable;
no third-party packages are needed. Never hard-code the current developer's Python path
into a task for another machine. The launcher requires an installed Claude Code CLI
and confirmed subscription login. It resolves a verified absolute executable even if
PATH is stale. Read its `--help` before invocation and use supported flags.

Model selection is independent of the Codex parent and Sol/Terra worker defaults.
Default the review model to Claude Opus 5 (claude-opus-5), independently of ambient
Claude settings. Honor an explicit per-review model override, and select effort using
the policy below unless the user overrides it. Keep persistent Claude settings unchanged. Log unknown effective settings as unknown. No automatic fallback, API-key billing, persistent configuration edits, login,
or installation is authorized by a review request. If preflight blocks, report the
specific prerequisite; never bypass restrictions to obtain a result.

Use a finite wall-clock timeout (default: 600 seconds). The launcher supplies a snapshot,
read/search tools, disabled ambient customizations/MCP, and noninteractive permission
denial. No `--bare`, bypass-permissions, unrestricted shell, editor, browser, or nested
agent capabilities. Resolve resources using the package actually loaded and supply
instructions explicitly because safe mode skips automatic discovery.

## Select reasoning effort

First decide whether Claude review is warranted; small low-risk work still skips it
unless explicitly requested. For each selected plan or implementation review, assess
complexity, uncertainty, and consequences rather than counting files or lines:

| Review scope | Effort |
| --- | --- |
| Explicitly requested mechanical documentation or consistency check | Low |
| Routine feature plan, acceptance criteria, or test strategy | Medium |
| Bounded backend/UI change with clear requirements and no consequential risk | Medium |
| Complex architecture or contracts spanning UI, API, and data | High |
| Authentication, authorization, migrations, or data integrity | High |
| Deployment/recovery changes or complex performance behavior | High |

An explicit supported user effort overrides this selection. A two-line authorization
change can still warrant high. For a recheck, reassess the remaining scope and risk:
a purely mechanical remainder may use low; unresolved security/data concerns retain
high. Never lower or raise effort solely because it is a recheck. Preserve the existing
one-automatic-recheck limit. Live visual acceptance stays with the native UI/UX reviewer.

Before dispatch, log the phase, chosen effort, concise scope/risk reason, and any user
override. Pass the choice explicitly as --effort; the launcher has no effort default
and rejects missing or blank values before preflight or model execution. It records
the request separately from observed settings. Unsupported settings fail without
fallback. --check-current does not require effort.

## Manifest and invocation

Write a JSON manifest in a parent-owned artifact location. The repository must be a
Git checkout so ignore status can be verified. Packets are limited to 8 MB including
metadata and 1 MB per file/diff; narrow scope when a bound is exceeded. Inspect selected
content for secrets: automatic recognizable-credential filtering is only a backstop. Paths in selected_paths and
context_paths are repository-relative; include the applicable repository instructions
and OpenSpec files as context_paths. requirements and verification_evidence are lists
of non-empty strings. Record intentionally omitted paths and reasons in exclusions.
Use a unique run_id; baseline must identify a verified Git ref.
The optional prompt can add task-specific focus, but cannot loosen the review boundary.

```json
{
  "repository": "C:/work/my-app",
  "phase": "implementation",
  "run_id": "team-invitations-2026-09-21-1",
  "baseline": "main",
  "selected_paths": ["src/invitations.py", "tests/test_invitations.py"],
  "context_paths": ["AGENTS.md", "openspec/changes/team-invitations/specs/invitations/spec.md"],
  "guidance_paths": [
    "C:/Users/example/.codex/skills/clanker-orchestration-nation/references/clanker-claude-cross-review.md",
    "C:/Users/example/.codex/skills/clanker-orchestration-nation/references/clanker-backend-developer.md",
    "C:/Users/example/.codex/skills/clanker-code-review/SKILL.md"
  ],
  "requirements": ["Expired invitations cannot be accepted."],
  "exclusions": [],
  "verification_evidence": ["python -m unittest tests.test_invitations: 8 passed"]
}
```

The paths and test result above are illustrative. Supply actual existing paths and
observed evidence; never copy the sample passing count as evidence. For a plan review,
select the planning artifacts and use phase plan. Use guidance_paths for individually
verified absolute Markdown instruction files outside the repository, including this
reference and the shared code-review contract for implementation. The launcher copies
only those files into the snapshot and records their provenance and hashes. Do not
copy instructions into the live checkout or grant access to whole skill directories.

```text
python <package>/scripts/claude_cross_review.py --manifest <manifest.json> --output-dir <repo>/.clanker/reviews --effort <selected-effort>
python <package>/scripts/claude_cross_review.py --check-current <saved-report.json>
```

Required for review execution: --effort <selected supported level>. Optional switches:
--claude-exe <absolute executable>, --model <selection>, --timeout-seconds <positive
integer>. Reviews are bounded by the timeout only; no turn limit is imposed.
Use argument arrays or literal shell arguments; do not concatenate untrusted prompt
text into commands. The helper returns its unique report path. Read report.json and
summary.md from that location, not from a guessed most-recent directory.

Model verdicts are clean, changes_requested, or incomplete. Coverage items identify a
subject with covered, partial, or unreviewed status plus concrete evidence (or a reason
for a coverage gap). Empty evidence cannot support covered status. Each finding includes an id,
severity (blocking/major/minor/info), location, scenario, evidence, confidence
(confirmed/plausible), and suggested_remedy. Host execution status, scope identity,
requested settings, and observed runtime metadata are separate from the model verdict.

## Results and reconciliation

Execution status and review verdict are separate. Check host-owned metadata, complete
coverage, report validity, and evidence before considering a review complete. A zero
process exit, no findings, or apparent reviewer agreement alone proves nothing.

Verify every finding against current evidence. Record accepted/rejected/deferred/
needs-evidence dispositions with reasons. Keep accepted blocking issues open until
fixed and verified, or until explicitly waived by the user. Check the saved report's
fingerprint immediately before accepting it. Stale, failed, blocked, interrupted, or
partial reports are not approval. Allow one automatic recheck after fixes or additional
context per phase; report remaining gaps after that limit rather than retry indefinitely.

Only the parent appends to `.clanker/YYYY-MM-DD-orchestration-nation.md`, using the
existing run ID and original log date. Link the unique report and summarize selection,
requested/observed settings, actual coverage, failures, dispositions, and waivers.
Preserve all attempts. Claude and the launcher must not update the shared log or
OpenSpec task state. Report unsuccessful saves and unrun verification honestly.
