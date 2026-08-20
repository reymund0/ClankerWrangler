---
name: clanker-refactor-review
description: Propose refactors for the code the current branch touches, anchored to the branch diff and directly related code. Covers function extraction, conditional complexity, duplication, magic values, naming, local convention drift, dead code, oversized files, and file placement. Use after implementation work is done and before committing or opening a pull request, when you want improvement proposals rather than a defect hunt. Plans only; it does not implement changes. Use clanker-code-review for correctness, regressions, and requirement coverage; use clanker-refactor-sisyphus for repo-wide structural debt.
---

# Clanker Refactor Review

## Purpose

Propose refactors for the code the current branch touches. This skill plans improvements; it does not implement them.

This is not a correctness review. Do not hunt for bugs, regressions, or test gaps — mention a defect only when it is glaringly obvious while analyzing a refactor candidate, and hand correctness work to `clanker-code-review`.

Scope discipline is the point of this skill. Every proposal must be anchored to the branch diff and the code directly related to it.

## Step 1 — Establish the diff under review

```bash
git status --short --branch
```

- Use the base branch the user names. Otherwise prefer `main`, else `master`. Verify it exists with `git rev-parse --verify <base>` before using it.
- On a feature branch, analyze `<base>...HEAD` (merge-base diff).
- If the branch has no commits ahead of base, analyze the working tree instead: `git diff HEAD` plus `git diff --cached`, and say so in the output.
- If both are empty, report that there is nothing to analyze and stop.

```bash
git diff --stat <base>...HEAD
git diff --name-status <base>...HEAD
git diff <base>...HEAD
```

Diff budget: if the branch exceeds roughly 40 files or 2000 changed lines, do not pull the whole diff at once. Work file-by-file with `git diff <base>...HEAD -- <path>`, ordered by how much each file changed. Tracing related code in Step 3 costs more context than the diff itself, so leave room for it. Any file you did not read in full must be listed as `not analyzed` in the output.

Never propose refactors for lockfiles, generated or vendored code, snapshots, minified assets, or files whose diff is pure formatting churn. Skip them silently.

## Step 2 — Apply the scope rules

In scope:

- code added, removed, or modified in the diff
- callers and callees of changed functions or methods
- other code in the same file as a change
- code that duplicates a pattern the diff introduced or modified
- code left orphaned or unreachable by a removal in the diff

Out of scope:

- pre-existing code unrelated to the diff
- files the branch did not touch, unless they contain a direct caller, callee, or duplicate of changed code
- broad architectural rewrites
- speculative or stylistic preferences not grounded in the diff

When a proposal would reach beyond directly related code, do not make it. Record the boundary under `OUT OF SCOPE NOTED` instead.

## Step 3 — Trace directly related code

For the changed code only, locate callers and callees of changed functions, duplicated or near-duplicated logic the change introduced or touched, and code a removal may have orphaned. Read only what is needed to confirm the relationship to the diff. Do not survey the whole codebase.

## Step 4 — Look for these refactor candidates

Judge size and complexity against the code around them, not against an abstract ideal. "Long," "nested," and "large" mean long, nested, or large relative to the other functions in the same file and the other files in the same module. This keeps proposals aligned with the repository's own conventions.

**Function extraction** — functions or methods the diff added or grew that are now long or deeply nested relative to their neighbors. Suggest extracting cohesive pieces into well-named units.

**Conditional complexity** — nested conditionals or repeated branching the change introduced. Suggest guard clauses, a lookup table, or polymorphism where it genuinely simplifies the change.

**Duplication** — logic the diff repeats that could be consolidated. Prefer extending an existing utility over creating a new one.

**Magic values** — literals the change introduced that should be named constants. Prefer an existing constant or config location over a new one.

**Naming clarity** — symbols the diff introduced or renamed that are misleading or inconsistent with their neighbors. Suggest names aligned with the surrounding code.

**Local convention drift** — code in the diff that handles errors, logging, async style, or return shapes differently from the rest of its file or module. Recommend aligning with the prevailing local convention.

**Orphaned or dead code** — functions, exports, imports, variables, or files left unused by a removal in the diff, and code paths the change made unreachable.

**Oversized files** — files the diff pushed past the size or responsibility boundary of their peers in the same module, but only when the change is what made the file unwieldy or expanded an already large one.

**File organization** — helpers, types, or constants the change introduced that would be clearer in a different existing module.

## Step 5 — Judge each candidate before proposing it

- **Repository conventions win.** Do not propose a new pattern or abstraction unless the diff already moved in that direction.
- **Note the safety net.** For each proposal, state whether the code it touches has test coverage that would catch a mistake during the refactor: `protected` (tests cover this code), `unprotected` (no covering tests), or `n/a` (a rename or move with no behavior surface). An unprotected refactor is not disqualified, but the reader needs to know a test comes first.
- **Calibrate effort by blast radius.** `low` — contained to a single function or file. `medium` — touches several call sites within one module. `high` — crosses module boundaries or changes a shared interface.
- **Stay proportional.** Prefer a few high-value proposals over an exhaustive list. Around eight is a sensible ceiling; if more survive, keep the highest-value ones and note the rest under `OUT OF SCOPE NOTED`.

## Step 6 — Save the proposals

Write the full required output to `.clanker/refactor/{YYYY-MM-DD}-{scope}.md`.

- `{scope}` is the active OpenSpec change id when the repository has an `openspec/` directory and `openspec list --json` reports a single active change. Otherwise use the current branch name, lowercased with non-alphanumeric characters replaced by hyphens.
- Create the directory if it does not exist.
- Then summarize the proposals concisely in the conversation and give the user the file path for the full detail.

## Required output

**CHANGED FILES**
Each changed file with its purpose in one line. Mark any file `not analyzed` if you did not read it in full.

**PROPOSALS**
A single list ordered by value — benefit weighed against effort, highest first. Omit categories entirely when they produced nothing; do not emit empty placeholders. Each entry:

- **category** — one of: function extraction, conditional complexity, duplication, magic values, naming clarity, local convention drift, orphaned or dead code, oversized files, file organization
- **location** — file and, where relevant, symbol or line range
- **relation to the diff** — why this code is directly related to the change
- **proposal** — the concrete refactor
- **benefit** — what improves
- **effort** — `low`, `medium`, or `high`
- **test safety** — `protected`, `unprotected`, or `n/a`

If nothing survives Step 5, state: `No refactor proposals — the branch diff is clean relative to its surroundings.`

**OUT OF SCOPE NOTED**
Anything you deliberately set aside because it fell outside the diff and its directly related code, or because it lost the proportionality cut. One line each. State `None` when nothing was set aside.

## Rules

- Do not implement any change; this skill only plans.
- Never invent a proposal to fill a category.
- Anchor every proposal to the diff, and say what that anchor is.
