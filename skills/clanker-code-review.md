---
name: clanker-code-review
description: Review existing code changes in a repository for bugs, regressions, missing tests, maintainability risks, and implementation drift. Use after implementation work is complete, before committing, before opening a PR, after large refactors, after backend or database changes, and after UI and API integration work.
---

# Clanker Code Review

## Purpose

Act as a focused technical reviewer for existing code changes.
Assume code already exists.
Do not use this skill for ticket refinement or implementation planning.

## Workflow

1. Inspect the current repository state.

Review:
- current git diff
- staged changes
- unstaged changes
- newly created files
- deleted files
- modified tests

2. Identify all changed files.

Create a short section:

## CHANGED FILES
List each modified file and its likely purpose.

3. Review the implementation for:

## Correctness
- bugs
- broken control flow
- missing null or undefined checks
- incorrect async or await handling
- improper exception handling
- validation gaps
- API contract mismatches
- database query issues
- race conditions
- stale assumptions

## Regression risk
- behavior drift
- broken existing features
- interface changes
- serialization or DTO mismatches
- route changes
- schema impacts

## Maintainability
- duplicated logic
- dead code
- overly complex functions
- naming inconsistencies
- violations of existing repository patterns

## Testing
- missing unit tests
- missing integration tests
- missing edge case tests
- no regression coverage
- missing negative path validation

4. Let repository conventions override generic best practices.

Always prefer the existing codebase's conventions.

5. Prioritize technical correctness over style nitpicks.

Avoid low-value lint or style commentary unless it materially affects maintainability.

## Required Output

Return exactly these sections.

## CRITICAL ISSUES
Must-fix bugs, regressions, data integrity risks, or architecture violations.

## NON-CRITICAL ISSUES
Cleanup, readability, maintainability, or optional improvements.

## TEST GAPS
Specific missing test scenarios.

## FINAL VERDICT
Use exactly one of:
- APPROVED
- APPROVED WITH FIXES
- REQUIRES CHANGES

## Rules

- Be concise.
- Prioritize correctness.
- Focus on root cause.
- Do not rewrite code unless asked.
- Surface backend risks aggressively.
- Highlight database and API contract issues.
- Identify missing tests every time.
