---
name: clanker-code-review
description: Review existing code changes against OpenSpec artifacts and repository conventions, covering correctness bugs, regressions, requirement coverage, spec and scope drift, and missing tests. Use after implementation work is complete, before committing, before opening a pull request, before archiving an OpenSpec change, and after refactors, backend, database, or API integration work. Use clanker-refactor-review for improvement proposals rather than defects.
---

# Clanker Code Review

## Purpose

Act as a focused technical reviewer for code that already exists.
Do not use this skill to author specs, write proposals, or plan implementation work.
Do not rewrite code unless the user asks for a fix.

For delegated reviews, the caller's explicit scope and report schema take precedence
over the standalone procedure and output template below. Preserve the evidence,
coverage, and issue criteria; report any scope or access limits.

## Step 1 — Establish the diff under review

Determine the baseline before reading any code.

```bash
git status --short --branch
```

- Use the caller's named base; otherwise verify the branch's integration base, preferring `main`, then `master`. Verify it with `git rev-parse --verify <base>`.
- Review task-owned committed changes with `<base>...HEAD`, plus staged and unstaged changes with `git diff HEAD`. Inspect `git diff --cached` when staging matters, including staged changes masked by working-tree edits.
- Enumerate untracked files with `git ls-files --others --exclude-standard` and read task-owned contents. Exclude unrelated user changes and state any exclusions.
- If there are no task-owned changes in any of these sources, report that there is nothing to review.

```bash
git diff --stat <base>...HEAD
git diff --name-status <base>...HEAD
git diff <base>...HEAD
```

Diff budget: above roughly 40 files or 2000 changed lines, read each applicable diff file-by-file, ordered by risk: data/schema, auth/security, API contracts, shared utilities, then UI. List any file not read in full as `not reviewed`.

Acknowledge but do not line-review: lockfiles, generated or vendored code, snapshots, minified assets, and pure formatting churn.

## Step 2 — Load the OpenSpec context

If no `openspec/` directory or applicable change exists, skip the OpenSpec checks and
record that limitation. Review the implementation against the user/caller's requirements.

Identify the change under review. Use the change the user names; otherwise:

```bash
openspec list --json
```

Match the active change to the branch name or the diff. If several active changes could apply and the diff does not clearly resolve it, ask the user which one to review rather than guessing.

Read the artifacts for that change:

```bash
openspec status --change <change-id> --json
openspec show <change-id> --json --deltas-only --no-interactive
openspec validate <change-id> --strict --no-interactive
```

Artifacts live under `openspec/changes/<change-id>/`:

- `proposal.md` — intended scope and impact.
- `specs/<capability>/spec.md` — requirement deltas; **their scenarios are the acceptance criteria.**
- `tasks.md` — claimed implementation status.
- `design.md`, when present — decisions and constraints.

For `MODIFIED`, `REMOVED`, and `RENAMED` requirements, also read the baseline in
`openspec/specs/<capability>/spec.md` and verify the transition from old to new behavior.

Also read `openspec/config.yaml` if present; its `context` and `rules` entries carry project conventions that apply to this review.

## Step 3 — Check requirement coverage

For every scenario in the change's spec deltas, assign one status:

- `Covered` — implementation and, where the scenario is testable, a test satisfy it.
- `Partially covered` — addressed but incomplete, or implemented with no test.
- `Not covered` — no supporting implementation evidence found in the reviewed scope.

Every `Covered` and `Partially covered` verdict must cite the file (and test file) that supports it. A status with no citation is a guess — downgrade it to `Not covered` and say the evidence was not found.

## Step 4 — Review the implementation

Verification discipline, which outranks breadth:

- The diff alone is not enough context. Before reporting a bug, open the full file and the relevant callers.
- Report a finding only when you can state a concrete failure scenario: specific input or state producing specific wrong behavior. If you cannot, drop it.
- Mark each finding `CONFIRMED` (traced through the surrounding code) or `PLAUSIBLE` (could not fully verify).
- Repository convention beats generic best practice. If the codebase does something consistently, that is the standard.
- Do not report style preferences, speculative refactors, or missing comments.

Review for:

**Correctness** — broken control flow, unhandled null or undefined, incorrect async/await and unawaited promises, swallowed or over-broad exception handling, off-by-one and boundary errors, validation gaps, race conditions, stale assumptions about state.

**Regression risk** — behavior drift in existing features, changed interfaces and DTO or serialization shape, route and signature changes, migration and schema impacts, defaults that silently change, removed behavior that other call sites still expect.

**Security and data integrity** — injection and unsanitized input, authorization checks missing on new paths, secrets or credentials in code or logs, unbounded queries and writes, non-idempotent operations on retryable paths, personal data in logs or URLs.

**Maintainability that carries risk** — duplicated logic that can drift out of sync, dead code that misleads later changes, functions too tangled to test. Pure improvement proposals with no correctness or regression risk belong to `clanker-refactor-review`; do not duplicate them here.

**Tests** — missing unit, integration, edge case, negative path, and regression coverage. Assess whether the tests actually assert the scenario's THEN, not merely that the code runs.

## Step 5 — Check spec and task drift

Flag:

- **Uncovered scenarios** — delta scenarios with no implementation.
- **Contradicted spec** — code whose behavior conflicts with a requirement. Either the code is wrong or the delta must be updated before archiving; say which you believe and why.
- **Scope drift** — substantive code outside the proposal's `What Changes` and `Impact`. Small incidental fixes are fine; new capabilities are not.
- **Task drift** — tasks checked off with no corresponding implementation, or implemented work still unchecked.
- **Validation failures** — anything `openspec validate --strict` reports.
- **Baseline drift** — for `MODIFIED` or `REMOVED` requirements, old behavior still live in the code, or removed behavior still referenced elsewhere.

## Required output

For standalone reviews, use these sections and verdicts. Delegated reviews use the
caller's schema. Order findings by severity, give each a stable ID, and describe it
once; coverage, drift, and test-gap entries should cross-reference that finding.

**CHANGED FILES**
Each changed file with its purpose in one line. Mark any file as `not reviewed` if you did not read it in full.

**REQUIREMENT COVERAGE**
Each scenario from the change's spec deltas, grouped by capability, with status and supporting file. Include a reason for anything not `Covered`.
If the repository has no OpenSpec change under review, state: `No OpenSpec change found — requirement coverage skipped.`

**SPEC AND TASK DRIFT**
Findings from Step 5. State `None found` when there are none.

**CRITICAL ISSUES**
Must-fix bugs, regressions, security or data integrity risks, contradicted requirements, or `Not covered` scenarios. Each entry: location, observed problem, concrete failure scenario, user impact, suggested fix, and `CONFIRMED` or `PLAUSIBLE`.

**NON-CRITICAL ISSUES**
Non-blocking maintainability risks, test gaps, or `Partially covered` scenarios. Same entry format; exclude pure improvement proposals.

**TEST GAPS**
Specific missing test scenarios, named by the requirement or behavior they would protect. State `None found` when no meaningful gap exists.

**FINAL VERDICT**
Exactly one of `APPROVED`, `APPROVED WITH FIXES`, `REQUIRES CHANGES`.

- `REQUIRES CHANGES` — any correctness, regression, security, data integrity, or API contract issue marked `CONFIRMED`; any `Not covered` scenario; any contradicted requirement.
- `APPROVED WITH FIXES` — non-blocking improvements, meaningful test gaps, `Partially covered` scenarios, task drift, or unresolved `PLAUSIBLE` findings.
- `APPROVED` — no material issues, and every scenario `Covered` (or no OpenSpec change applies).

When the change is otherwise `APPROVED` but tasks remain unchecked or `openspec validate --strict` fails, state that it is not ready to archive.

## Rules

- Focus on root cause, not symptoms.
- Never invent a requirement the specs do not state.
