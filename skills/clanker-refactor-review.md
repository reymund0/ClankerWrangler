---
name: clanker-refactor-review
description: Analyze the changes on the current branch and propose refactors for the code those changes touch. Scope is anchored to the branch diff and the code directly related to it. Identifies function extraction, conditional complexity, DRY opportunities, magic values, naming clarity, local convention drift, orphaned or dead code, large files worth splitting, and file organization improvements. Use after implementation work is done and you want refactor suggestions before committing or opening a PR. This is a planning skill only; it does not implement changes and is not a correctness code review.
---

When invoked, follow this workflow exactly.

## Purpose

Propose refactors for the code the current branch touches.

This skill plans improvements. It does not implement them.

This is not a code review skill. Do not hunt for bugs, regressions, or test gaps.
Only mention correctness when a defect is glaringly obvious while analyzing a refactor candidate.

The single most important rule is scope discipline. Anchor every proposal to the branch diff and the code directly related to it. Do not propose changes across the broader codebase.

## Invocation behavior

- Preferred usage: `/clanker-refactor-review`
- Default base branch is `main`. Allow overriding the base branch if the user supplies one.
- If the branch has no diff against the base branch, report that there is nothing to analyze and stop the skill run.

## Scope rules

These rules define what is in scope. Apply them strictly.

In scope:
- code added, removed, or modified in the branch diff
- code that directly relates to the diff:
  - callers and callees of changed functions or methods
  - other code in the same file as a change
  - code that duplicates a pattern introduced or modified by the diff
  - code left orphaned or unreachable by a removal in the diff

Out of scope:
- pre-existing code unrelated to the diff
- refactors in files the branch did not touch, unless the file contains a direct caller, callee, or duplicate of changed code
- broad architectural rewrites
- speculative or stylistic preferences not grounded in the diff

When a proposal would reach beyond directly related code, do not make it. State the boundary instead.

## Workflow

1. Inspect the branch state.

Identify the touched files:

```bash
git diff --name-status main...HEAD
```

Read the full branch diff:

```bash
git diff main...HEAD
```

If a base branch other than `main` was provided, substitute it in both commands.

2. Build a focused understanding of what changed.

For each changed file, note its likely purpose and what the diff did to it (added, modified, removed).

3. Trace directly related code.

For the changed code only, locate:
- callers and callees of changed functions or methods
- duplicated or near-duplicated logic the change introduced or touched
- code that a removal may have orphaned

Read only what is needed to confirm a relationship to the diff. Do not survey the whole codebase.

4. Identify refactor candidates in these categories.

## Function extraction
- functions or methods the diff added or grew that are now too long or too deeply nested
- suggest extracting cohesive pieces into well-named units

## Conditional complexity
- nested conditionals or repeated branching the change introduced
- suggest guard clauses, a lookup table, or polymorphism where it simplifies the change

## DRY opportunities
- logic the diff duplicates that could be consolidated into an existing or new shared utility
- repeated patterns introduced by the change
- prefer extending an existing utility over creating a new one

## Magic values
- literals the change introduced that should become named constants
- prefer an existing constant or config location over a new one

## Naming clarity
- symbols the diff introduced or renamed that are misleading or inconsistent with their neighbors
- suggest names aligned with the surrounding code

## Local convention drift
- code in the diff that does something differently than the rest of the same file or module
- examples: error handling, logging, async style, return shapes
- recommend aligning with the module's prevailing convention

## Orphaned or dead code
- functions, exports, imports, variables, or files left unused by a removal in the diff
- code paths the change made unreachable

## Large file splits
- files the diff pushed past a reasonable size or responsibility boundary
- only when the change is what made the file unwieldy or expanded an already large file

## File organization
- code that would be clearer in a different existing module
- misplaced helpers, types, or constants introduced by the change

5. Let repository conventions override generic best practices.

Prefer the repo's existing structure, naming, and patterns. Do not introduce new patterns or abstractions as proposals unless the diff already moved in that direction.

6. Keep proposals practical and proportional.

Favor a small number of high-value proposals over a long list. If no meaningful refactor exists in a category, say so.

7. Save the proposals to `.clanker/DATE_TICKETNUM/refactor-proposals.md`.
   - `DATE_TICKETNUM` is derived from the current session: use the date as `YYYYMMDD` and the ticket key used in the current session (e.g. `20260605_MR-42`). If no ticket key is available in the session, use `YYYYMMDD_refactor`.
   - Create the directory if it does not exist.
   - Write the full **Required Output** to this file.
   - Summarize the proposals concisely in the conversation and provide the file path so the user can view the full detail.

## Required Output

Return exactly these sections.

## CHANGED FILES
List each changed file from `git diff --name-status main...HEAD` and its likely purpose.

## FUNCTION EXTRACTION
Overly long or deeply nested functions the change grew, with suggested extractions. State `None found` when none exist.

## CONDITIONAL COMPLEXITY
Branching the change introduced that could be simplified. State `None found` when none exist.

## DRY OPPORTUNITIES
Consolidation proposals grounded in the diff. State `None found` when none exist.

## MAGIC VALUES
Literals the change introduced that should become named constants. State `None found` when none exist.

## NAMING CLARITY
Misleading or inconsistent names the diff introduced or renamed. State `None found` when none exist.

## LOCAL CONVENTION DRIFT
Places the change diverges from the surrounding file or module's conventions. State `None found` when none exist.

## ORPHANED / DEAD CODE
Code left unused or unreachable by the change. State `None found` when none exist.

## LARGE FILE SPLITS
Files the change made worth splitting, with a suggested split boundary. State `None found` when none exist.

## FILE ORGANIZATION
Placement or module-boundary improvements grounded in the diff. State `None found` when none exist.

## OUT OF SCOPE NOTED
Briefly list anything you deliberately did not propose because it fell outside the diff and its directly related code. State `None` when nothing was set aside.

Each proposal must include:
- location: file and, where relevant, the symbol or line range
- relation to the diff: why this code is directly related to the change
- proposal: the concrete refactor
- benefit: what improves
- effort: `low`, `medium`, or `high`

## Rules

- Anchor every proposal to the branch diff and directly related code.
- Do not propose changes across the broader codebase.
- Do not implement any changes; this skill only plans.
- Do not perform a correctness review; mention defects only when glaringly obvious.
- Prefer extending existing utilities and following existing conventions over new abstractions.
- Favor a few high-value proposals over an exhaustive list.
- State `None found` for any empty category rather than inventing proposals.
- Every proposal must include location, relation to the diff, proposal, benefit, and effort.
