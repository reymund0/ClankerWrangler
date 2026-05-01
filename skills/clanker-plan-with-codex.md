---
name: clanker-plan-with-codex
description: Create an implementation plan, send it to the local Codex CLI for review using GPT-5.5 when available, and reconcile the feedback into a final plan before implementation begins.
---

When invoked, follow this workflow exactly.

## Purpose

Use the invoking agent to create the initial implementation plan, use the local Codex CLI as a second-opinion reviewer, then reconcile the feedback into a final implementation plan before implementation begins.

Codex is a reviewer, not the owner of the plan. The invoking agent owns the final implementation plan.

This skill is only for implementation plan construction. It does not perform implementation.

## Model Selection

Use `gpt-5.5` by default for Codex review steps.

If `gpt-5.5` is not available in the local Codex account, authentication mode, or rollout state, retry once with `gpt-5.4`.

Allow overriding the review model with the `CODEX_REVIEW_MODEL` environment variable.

Use `model_reasoning_effort=xhigh` by default. Use `high` only if the user explicitly asks for a lower reasoning model.

Keep Codex in `read-only` sandbox mode for all review steps.

## Workflow

1. Read the user's request and inspect the codebase as needed.

2. Produce a concise implementation plan with these sections:
   - Goal
   - Assumptions
   - Out of scope
   - Files likely to change
   - Step-by-step implementation sequence
   - Risks / edge cases
   - Open questions / blockers
   - Validation criteria
   - Test plan

3. Write the planning inputs to `.clanker\tmp`.
   - Create the directory if it does not exist.
   - Save the user's request to `.clanker\tmp\codex-request.md`.
   - Save a concise repo-context summary to `.clanker\tmp\codex-context.md`.
   - Save the draft plan to `.clanker\tmp\codex-plan.md`.

4. Run the local Codex CLI from PowerShell in non-interactive, read-only mode.

PowerShell command for plan review:

    New-Item -ItemType Directory -Force .clanker\tmp | Out-Null

    $codexModel = if ($env:CODEX_REVIEW_MODEL) { $env:CODEX_REVIEW_MODEL } else { "gpt-5.5" }
    $fallbackModel = "gpt-5.4"
    $reviewOutput = ".clanker\tmp\codex-review.txt"
    $modelOutput = ".clanker\tmp\codex-review-model.txt"
    $usedCodexModel = $null

    Remove-Item -LiteralPath $reviewOutput -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $modelOutput -Force -ErrorAction SilentlyContinue

    $request = Get-Content .clanker\tmp\codex-request.md -Raw
    $repoContext = Get-Content .clanker\tmp\codex-context.md -Raw
    $plan = Get-Content .clanker\tmp\codex-plan.md -Raw

    $prompt = @"
    Review this implementation plan for a software change.
    Be critical and practical.

    Look for:
    - mismatch between the user request and the plan
    - missing repo context or ignored repository conventions
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

    User request:
    $request

    Repo context:
    $repoContext

    Plan:
    $plan
    "@

    $prompt | codex exec `
      --model $codexModel `
      --sandbox read-only `
      -c model_reasoning_effort=xhigh `
      -c model_verbosity=medium `
      --output-last-message $reviewOutput `
      -

    if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $reviewOutput)) {
      $usedCodexModel = $codexModel
    }
    elseif ($codexModel -ne $fallbackModel) {
      Write-Host "Codex review with $codexModel failed. Retrying with $fallbackModel..."
      Remove-Item -LiteralPath $reviewOutput -Force -ErrorAction SilentlyContinue

      $prompt | codex exec `
        --model $fallbackModel `
        --sandbox read-only `
        -c model_reasoning_effort=xhigh `
        -c model_verbosity=medium `
        --output-last-message $reviewOutput `
        -

      if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $reviewOutput)) {
        $usedCodexModel = $fallbackModel
      }
    }

    if ($null -eq $usedCodexModel) {
      throw "Codex review failed; no current review output was created."
    }

    Set-Content -LiteralPath $modelOutput -Value $usedCodexModel

5. Read `.clanker\tmp\codex-review.txt`.

6. Summarize Codex's feedback in the conversation.
   - Read `.clanker\tmp\codex-review-model.txt` and mention the exact Codex model that produced the review.

7. Revise the plan based only on useful feedback.
   - Keep feedback that is concrete, relevant, and actionable.
   - Reject feedback that is vague, unnecessary, or inconsistent with the repo's existing patterns.

8. Save final plan to `.clanker\tmp\codex-plan-final.md`.
   - Do not output the final plan contents in the conversation.
   - Tell the user the final plan was saved and provide the file path so they can view it themselves.

9. Do not begin implementation unless the user separately asks to proceed after reviewing the final plan.

## Rules

- Treat Codex as a reviewer, not the owner of the plan.
- The invoking agent owns the final implementation plan.
- Prefer the repo's existing patterns over generic best practices when they conflict.
- Keep scope tight.
- Do not let Codex feedback cause unnecessary redesign unless it identifies a meaningful risk.
- Use `gpt-5.5` by default.
- Fall back to `gpt-5.4` if `gpt-5.5` is unavailable.
- Keep Codex in `read-only` mode for review steps.
- Do not use `--full-auto` for review steps because it implies `workspace-write` sandboxing.
- Do not implement changes as part of this skill.
