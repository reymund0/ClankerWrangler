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

1. Check for planning artifacts.
   - Determine the current Jira ticket key if known (from the current chat session or by asking the user).
   - If a ticket key is known, look for `.clanker\tmp\{YYYY-MM-DD}-{TICKET_KEY}\` (use the most recent date-stamped directory if multiple exist).
   - If `refined-ticket-final.md` exists in that directory, read it and extract the **Acceptance Criteria** section. This is the authoritative checklist for AC coverage.
   - If `plan-final.md` exists in that directory, read it and extract the **Validation criteria** and **Test plan** sections. Use these as a secondary layer for test gap identification.
   - If neither file is found, skip AC coverage and note that in the output.

2. Inspect the current repository state.

Review:
- changed files between the current branch and `main`
- implementation diff between the current branch and `main`
- test changes between the current branch and `main`

Use this command to identify touched files:

```powershell
git diff --name-status main...HEAD
```

Use the branch diff for the full review:

```powershell
git diff main...HEAD
```

3. Identify all changed files.

Create a short section:

## CHANGED FILES
List each modified file and its likely purpose.

4. Review the implementation for:

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

5. Check AC coverage against the refined ticket (if available).
   - For each acceptance criterion extracted in step 1, determine whether it is:
     - `Covered` — implementation clearly satisfies it
     - `Partially covered` — implementation addresses it but incompletely
     - `Not covered` — no evidence of implementation or test coverage
   - Flag `Not covered` items as critical issues and `Partially covered` items as non-critical issues.
   - Additionally, check the plan's validation criteria and test plan (if available) against actual test coverage in the diff. Surface gaps in TEST GAPS — these inform the verdict but do not escalate it beyond `APPROVED WITH FIXES`.

6. Let repository conventions override generic best practices.

Always prefer the existing codebase's conventions.

7. Prioritize technical correctness over style nitpicks.

Avoid low-value lint or style commentary unless it materially affects maintainability.

## Required Output

Return exactly these sections.

## CHANGED FILES
List each changed file from `git diff --name-status main...HEAD` and its likely purpose.

## AC COVERAGE
If a refined ticket was found, list each acceptance criterion with its coverage status: `Covered`, `Partially covered`, or `Not covered`. Include a brief reason for any non-`Covered` item.
If no refined ticket was found, state: `No refined ticket available — AC coverage check skipped.`

## CRITICAL ISSUES
Must-fix bugs, regressions, data integrity risks, architecture violations, or `Not covered` acceptance criteria.

## NON-CRITICAL ISSUES
Cleanup, readability, maintainability, optional improvements, or `Partially covered` acceptance criteria.

## TEST GAPS
Specific missing test scenarios, including any gaps between the plan's validation criteria or test plan and the actual test coverage in the diff. State `None found` when no meaningful test gap exists.

## FINAL VERDICT
Use exactly one of:
- APPROVED
- APPROVED WITH FIXES
- REQUIRES CHANGES

Verdict criteria:
- Use `REQUIRES CHANGES` for correctness, regression, data integrity, API contract, security risks, or any `Not covered` acceptance criteria.
- Use `APPROVED WITH FIXES` for non-blocking improvements, meaningful test gaps, or `Partially covered` acceptance criteria.
- Use `APPROVED` only when no material issues remain and all acceptance criteria are `Covered`.

## Rules

- Be concise.
- Prioritize correctness.
- Focus on root cause.
- Every issue must include location, observed problem, user impact or risk, and suggested fix.
- Do not rewrite code unless asked.
- Surface backend risks aggressively.
- Highlight database and API contract issues.
- Always evaluate test coverage and state `None found` when no meaningful test gap exists.
