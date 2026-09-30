## 1. Review policy and contracts

- [x] 1.1 Update the coordinator and add bundled Claude review guidance for substantial-scope plan and implementation checkpoints, preserving parent settings, native routing, one visible skill, and the Codex-only host boundary; verify small-edit skips, explicit requests/opt-outs, and planning-only scenarios against the new spec.
- [x] 1.2 Define manifest and report contracts, phase-specific criteria, host-owned metadata, finding dispositions, and the implementation-review mapping to clanker-code-review; verify representative complete, partial, stale, and defect-bearing reports have unambiguous outcomes.

## 2. Launcher preflight and execution

- [x] 2.1 Add the portable standard-library launcher with explicit/PATH/native executable resolution and Python prerequisite guidance; test missing executable, stale PATH, native Windows paths with spaces, unsupported shims, and unsupported CLI controls using a fake executable.
- [x] 2.2 Implement sanitized subscription-auth and provider-override preflight plus explicit model/effort resolution; verify missing/unknown auth, API billing conflicts, unsupported settings, no fallback, and no credential-value leakage without making model calls.
- [x] 2.3 Implement safe/restricted read-only invocation with no MCP, shell, edit, browser, nested delegation, or ambient customizations; verify constructed arguments and unsupported-control refusal, then confirm actual tool restrictions in the live fixture checks.
- [x] 2.4 Implement finite timeout, turn limits, process-tree cancellation, exit/error handling, and bounded diagnostics; verify success, nonzero exit, timeout, interruption, usage-limit, denied-read, and output-truncation cases with fake CLI tests and confirm no owned child process remains after cancellation.

## 3. Review evidence and artifacts

- [x] 3.1 Build explicit ephemeral review snapshots and manifests from selected OpenSpec/rule files, verified baseline diffs, relevant full files/callers, staged/unstaged changes, and untracked contents; verify mixed-state fixtures including renames/deletions and exclusions for unrelated, ignored, sensitive, binary, traversal, and out-of-root symlink paths.
- [x] 3.2 Fingerprint source evidence, detect stale targets, and clean only owned temporary snapshots; verify edits during review, deleted/new files, requirement changes, same-state acceptance, and containment checks for cleanup.
- [x] 3.3 Parse and validate structured CLI results and write unique metadata/report/summary artifacts under .clanker/reviews/; verify missing fields, invalid types/enums, error envelopes despite exit zero, incomplete coverage, rejected overwrites, output-write failure, and sanitized diagnostics.

## 4. Orchestrator integration and distribution

- [x] 4.1 Wire parent-owned selection, bounded dispatch, evidence verification, findings reconciliation, one automatic recheck, and explicit waivers into the coordinator; verify findings with accepted/rejected/deferred/needs-evidence dispositions and that unresolved or stale checkpoints never become silent approvals.
- [x] 4.2 Link report outcomes and dispositions into the existing append-only daily log while keeping Claude and the launcher out of shared log/OpenSpec mutation; verify multiple phases and same-day runs preserve prior events and distinct report paths.
- [x] 4.3 Extend both wrangle installers to copy only owned supporting resources into the coordinator bundle; run fresh, upgrade, and repeat installation fixtures to verify exact source bytes, installed resource resolution, single-skill discovery, prior specialist backups, unrelated-file preservation, and no Claude/login invocation.
- [x] 4.4 Update README with the Codex-driven scope, review checkpoints, overrides, Python/Claude prerequisites, subscription setup, reports, and failure behavior; verify examples against the implemented launcher help and both source and installed layouts.

## 5. Integrated acceptance

- [x] 5.1 Run deterministic launcher and isolated-installer tests across the available Windows PowerShell/Git Bash environment and a POSIX environment when available; record actual platform coverage and any unrun checks instead of inferring portability from syntax alone.
- [x] 5.2 Run a small subscription-authenticated plan review and an implementation fixture containing a known defect, using the installed bundle; verify CLI/auth compatibility, read-only restrictions, coverage, structured findings, model evidence, and source-file preservation. Keep this task incomplete if login or usage prevents live checks.
- [x] 5.3 Review the integrated change against every new requirement, run strict OpenSpec validation and relevant diff/format checks, reconcile tasks and documentation, and record actual verification evidence and remaining limitations. Do not install globally or archive changes as part of this task.

## 6. Adaptive review reasoning

- [x] 6.1 Replace fixed-high guidance with scope/risk effort selection in the coordinator, bundled reviewer reference, and README; retain skip rules, user overrides, native visual review, and one recheck with fresh effort assessment. Verify representative routing scenarios.
- [x] 6.2 Require explicit nonblank --effort for review execution without affecting --check-current; verify low/medium/high and explicit overrides reach Claude arguments and report metadata, missing/blank effort starts no preflight, and unsupported effort never silently falls back.
- [x] 6.3 Run focused regression and isolated package checks on Windows and available POSIX, review the delta against the new scenarios, run strict OpenSpec validation, and append actual verification and routing evidence to the existing daily log.

- [x] 6.4 Route Claude reviews through relevant shared specialist instruction files using existing guidance_paths and provenance; verify multiple profiles reach the packet and remain advisory without nested delegation, model changes, or visual/test-execution claims.

## 7. Opus 5 review default

- [x] 7.1 Default Claude reviews to claude-opus-5 with explicit --model overrides, independent adaptive effort, unchanged persistent settings and no model fallback; align coordinator/reference/README and verify ambient model defaults cannot replace it.
- [x] 7.2 Verify default/override model arguments and report metadata, retained provider safeguards, focused regressions, isolated installer parity, and strict OpenSpec validation; record actual evidence.
