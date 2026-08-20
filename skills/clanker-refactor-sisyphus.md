---
name: clanker-refactor-sisyphus
description: Survey the whole repository for high-leverage refactor opportunities and propose a bounded, ranked plan. Scope is anchored to hotspots (files ranked by git churn and size/complexity), not an exhaustive scan, and output is capped to the highest-leverage findings. Targets duplication clusters, god files and functions, inconsistent patterns, and module boundary or dead-code issues. Use when you want to plan down structural debt across the repo, not changes tied to a branch diff. This is a planning skill only; it does not implement changes and is not a correctness code review. Use clanker-refactor-review for refactors scoped to the current branch diff; use clanker-code-review for correctness and requirement coverage.
---

When invoked, follow this workflow exactly.

## Purpose

Survey the whole repository and propose a bounded, ranked set of high-leverage refactors.

Refactoring a repo is an endless struggle, so this skill does not try to list every pain point. It surfaces the few findings worth acting on now and explicitly sets the rest aside.

This skill plans improvements. It does not implement them.

This is not a code review skill. Do not hunt for bugs, regressions, or test gaps.
Only mention correctness when a defect is glaringly obvious while analyzing a refactor candidate.

## Invocation behavior

- Preferred usage: `/clanker-refactor-sisyphus`
- Optionally accept a path or subsystem argument to scope the run to one area of the repo.
- If a path argument is given, restrict all analysis to that path.

## Scope rules

These rules keep the survey bounded. Apply them strictly.

- Analyze hotspots only, not every file. Hotspots are files ranked high by a combination of git churn and size or complexity.
- Surface a pattern only when it recurs. Require at least 3 occurrences for duplication or inconsistency findings. One-offs are out of scope.
- Report only systemic issues that span multiple files, modules, or a clearly oversized unit. Line-level nitpicks are out of scope.
- Anchor every finding to the repo's own established patterns. Flag deviations from existing conventions, not deviations from generic ideals.
- Cap the output to the highest-leverage findings. Do not enumerate everything found.

## Workflow

1. Identify hotspots.

Rank files by change frequency:

```bash
git log --since="12 months ago" --name-only --pretty=format: -- . | grep -v '^$' | sort | uniq -c | sort -rn | head -40
```

Identify the largest files for cross-reference:

```bash
git ls-files | xargs wc -l 2>/dev/null | sort -rn | head -40
```

If a path argument was provided, scope both commands to that path.

If git history is too shallow for churn to be meaningful (for example a shallow clone or a brand-new repo), fall back to size and fan-in only and state in the output that churn data was unavailable.

2. Select the hotspot set.

Prioritize files that rank high on both churn and size or complexity. A file that is large but rarely changes, or churns often but is small and simple, is lower priority. Focus the rest of the analysis on this set.

3. Analyze the hotspot set for refactor candidates in these categories.

## Duplication clusters
- the same logic reimplemented in 3 or more places across the hotspots
- prefer consolidating into an existing shared utility over inventing a new one

## God files and functions
- files, functions, or classes that are both oversized and carrying too many responsibilities
- draw candidates from the hotspot set, with a suggested split or extraction boundary

## Inconsistent patterns
- 3 or more competing ways of doing the same thing (for example error handling, HTTP clients, date utilities, configuration access)
- recommend the variant most aligned with the repo's prevailing convention

## Boundaries and dead code
- misplaced code, leaky layering, or tangled and circular dependencies
- repo-scale orphaned code: unused exports, unreferenced files, abandoned flags

4. Rank by leverage.

Score each candidate by impact divided by effort. Keep only the highest-leverage findings, capped at roughly 10 to 15 total. Drop the rest.

5. Let repository conventions override generic best practices.

Prefer the repo's existing structure, naming, and patterns. Do not propose new architectural patterns or abstractions unless they reduce a clearly demonstrated, recurring pain.

6. Save the proposals to `.clanker/refactor/{YYYY-MM-DD}-repo.md`.
   - Use the current date (e.g. `.clanker/refactor/2026-06-05-repo.md`).
   - One file per run; do not create a per-run subdirectory.
   - Create the `.clanker/refactor` directory if it does not exist.
   - Write the full **Required Output** to this file.
   - Summarize the proposals concisely in the conversation and provide the file path so the user can view the full detail.

## Required Output

Return exactly these sections.

## HOTSPOTS ANALYZED
List the hotspot files the survey focused on and why each ranked high (churn, size, or both). Note if churn data was unavailable.

## DUPLICATION CLUSTERS
Consolidation proposals for logic repeated in 3 or more places. State `None found` when none exist.

## GOD FILES AND FUNCTIONS
Oversized, over-responsible units with a suggested split boundary. State `None found` when none exist.

## INCONSISTENT PATTERNS
Competing ways of doing the same thing, with the recommended convention. State `None found` when none exist.

## BOUNDARIES AND DEAD CODE
Misplaced code, layering or dependency issues, and repo-scale orphaned code. State `None found` when none exist.

## NOT SURFACED
Briefly state that lower-leverage findings were deliberately set aside to keep the plan bounded, and characterize what kinds were dropped. This makes the cap intentional, not a blind spot.

Each proposal must include:
- location: file and, where relevant, the symbol or line range
- evidence: occurrence count or the locations that establish the pattern
- proposal: the concrete refactor
- benefit: what improves
- effort: `low`, `medium`, or `high`

Rank proposals within each section by leverage, highest first.

## Rules

- Analyze hotspots, not the entire repo.
- Require recurrence (3 or more occurrences) for duplication and inconsistency findings.
- Surface systemic issues only; no line-level nitpicks.
- Cap the output to the highest-leverage findings and rank by impact divided by effort.
- Do not implement any changes; this skill only plans.
- Do not perform a correctness review; mention defects only when glaringly obvious.
- Prefer extending existing utilities and following existing conventions over new abstractions.
- State `None found` for any empty category rather than inventing proposals.
- Every proposal must include location, evidence, proposal, benefit, and effort.
