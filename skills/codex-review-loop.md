---
name: codex-review-loop
description: Create an implementation plan, send it to the local Codex CLI for review using GPT-5.5 when available, reconcile the feedback, and optionally implement.
---

When invoked, follow this workflow exactly.

## Purpose

Use Claude to create the initial implementation plan, use the local Codex CLI as a second-opinion reviewer, then reconcile the feedback into a final implementation plan before implementation begins.

Codex is a reviewer, not the owner of the plan. Claude owns the final implementation plan.

## Model Selection

Use `gpt-5.5` by default for Codex review steps.

If `gpt-5.5` is not available in the local Codex account, authentication mode, or rollout state, retry once with `gpt-5.4`.

Allow overriding the review model with the `CODEX_REVIEW_MODEL` environment variable.

Use `model_reasoning_effort=high` by default. Use `xhigh` only if the user explicitly asks for the deepest possible review.

Keep Codex in `read-only` sandbox mode for all review steps.

## Workflow

1. Read the user's request and inspect the codebase as needed.

2. Produce a concise implementation plan with these sections:
   - Goal
   - Assumptions
   - Files likely to change
   - Step-by-step implementation sequence
   - Risks / edge cases
   - Test plan

3. Write the plan to `.claude\tmp\codex-plan.md`.
   - Create the directory if it does not exist.

4. Run the local Codex CLI from PowerShell in non-interactive, read-only mode.

PowerShell command for plan review:

    New-Item -ItemType Directory -Force .claude\tmp | Out-Null

    $codexModel = if ($env:CODEX_REVIEW_MODEL) { $env:CODEX_REVIEW_MODEL } else { "gpt-5.5" }
    $fallbackModel = "gpt-5.4"
    $plan = Get-Content .claude\tmp\codex-plan.md -Raw

    $prompt = @"
    Review this implementation plan for a software change.
    Be critical and practical.

    Look for:
    - missing edge cases
    - overengineering
    - risky assumptions
    - missing tests
    - simpler alternatives
    - likely integration problems

    Return exactly these sections:
    1. Major concerns
    2. Minor concerns
    3. Suggested changes to the plan
    4. Should implementation proceed as-is?

    Plan:
    $plan
    "@

    $prompt | codex exec `
      --model $codexModel `
      --sandbox read-only `
      -c model_reasoning_effort=high `
      -c model_verbosity=medium `
      --output-last-message .claude\tmp\codex-review.txt `
      -

    if ($LASTEXITCODE -ne 0 -and $codexModel -ne $fallbackModel) {
      Write-Host "Codex review with $codexModel failed. Retrying with $fallbackModel..."
      $prompt | codex exec `
        --model $fallbackModel `
        --sandbox read-only `
        -c model_reasoning_effort=high `
        -c model_verbosity=medium `
        --output-last-message .claude\tmp\codex-review.txt `
        -
    }

5. Read `.claude\tmp\codex-review.txt`.

6. Summarize Codex's feedback in the conversation.
   - Mention whether Codex used `gpt-5.5` or fell back to `gpt-5.4`.

7. Revise the plan based only on useful feedback.
   - Keep feedback that is concrete, relevant, and actionable.
   - Reject feedback that is vague, unnecessary, or inconsistent with the repo's existing patterns.

8. Save final plan to `.claude\tmp\codex-plan-final.md` and present the revised plan under this exact heading:

    FINAL IMPLEMENTATION PLAN

9. Do not begin implementation unless the user asked to proceed.

10. If implementation proceeds:
    - implement the final plan
    - follow existing repo conventions
    - avoid unnecessary refactors outside the ticket scope
    - run relevant tests when possible

11. After implementation, run a second Codex review.

PowerShell command for post-implementation review:

    New-Item -ItemType Directory -Force .claude\tmp | Out-Null

    $codexModel = if ($env:CODEX_REVIEW_MODEL) { $env:CODEX_REVIEW_MODEL } else { "gpt-5.5" }
    $fallbackModel = "gpt-5.4"

    $prompt = @"
    Review the implemented changes in this repository.

    Focus on:
    - bugs
    - regressions
    - missing tests
    - maintainability issues
    - risky changes
    - anything that does not match the intended plan

    Return exactly these sections:
    1. Critical issues
    2. Non-critical issues
    3. Recommended fixes
    4. Overall verdict
    "@

    $prompt | codex exec `
      --model $codexModel `
      --sandbox read-only `
      -c model_reasoning_effort=high `
      -c model_verbosity=medium `
      --output-last-message .claude\tmp\codex-post-review.txt `
      -

    if ($LASTEXITCODE -ne 0 -and $codexModel -ne $fallbackModel) {
      Write-Host "Codex post-implementation review with $codexModel failed. Retrying with $fallbackModel..."
      $prompt | codex exec `
        --model $fallbackModel `
        --sandbox read-only `
        -c model_reasoning_effort=high `
        -c model_verbosity=medium `
        --output-last-message .claude\tmp\codex-post-review.txt `
        -
    }

12. Read `.claude\tmp\codex-post-review.txt`.

13. Apply worthwhile fixes from the post-implementation review.
    - Prioritize correctness, regressions, and missing test coverage.
    - Ignore low-value nitpicks unless they materially improve maintainability.

14. End with a concise summary containing:
    - what was implemented
    - which Codex model reviewed it
    - what Codex caught
    - what changed after review

## Rules

- Treat Codex as a reviewer, not the owner of the plan.
- Claude owns the final implementation plan.
- Prefer the repo's existing patterns over generic best practices when they conflict.
- Keep scope tight.
- Do not let Codex feedback cause unnecessary redesign unless it identifies a meaningful risk.
- Use `gpt-5.5` by default.
- Fall back to `gpt-5.4` if `gpt-5.5` is unavailable.
- Keep Codex in `read-only` mode for review steps.
- Do not use `--full-auto` for review steps because it implies `workspace-write` sandboxing.
