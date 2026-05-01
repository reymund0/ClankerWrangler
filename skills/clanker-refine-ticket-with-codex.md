---
name: clanker-refine-ticket-with-codex
description: Fetch a Jira ticket through the Atlassian MCP server, combine it with local repo context, rewrite it into a planning-ready engineering ticket using strict validation rules, and use the local Codex CLI to review and improve the refined output.
---

When invoked, follow this workflow exactly.

## Purpose

Turn a Jira ticket into a planning-ready engineering ticket with strict validation, then use Codex as a second-opinion reviewer before presenting the final result.

This workflow should act as a pre-planning quality gate.

Do not allow ambiguous tickets to proceed without clearly flagging blockers.

Codex is a reviewer, not the owner of the ticket refinement. The invoking agent owns the final refined ticket.

## Model Selection

Use `gpt-5.5` by default for Codex review steps.

If `gpt-5.5` is not available in the local Codex account, authentication mode, or rollout state, retry once with `gpt-5.4`.

Allow overriding the review model with the `CODEX_REVIEW_MODEL` environment variable.

Use `model_reasoning_effort=xhigh` by default. Use `high` only if the user explicitly asks for a lower reasoning model.

Keep Codex in `read-only` sandbox mode for all review steps.

## Invocation behavior

- Preferred usage: `/clanker-refine-ticket-with-codex MR-42`
- If no Jira ticket key is provided, ask the user for the ticket key before continuing.
- If Jira data cannot be fetched, report that the Jira connection failed, include any error message encountered, and stop the skill run.

## Workflow

1. Identify the Jira ticket key from user input.

2. Use the Atlassian MCP tools to fetch the Jira issue.

3. Pull ticket context:
   - ticket key
   - summary / title
   - description
   - acceptance criteria
   - status
   - priority
   - labels
   - epic / parent
   - subtasks
   - linked issues
   - comments
   - attachments metadata

4. Keep context focused:
   - summarize at most 5 decision-relevant comments
   - omit or count the rest unless they contain scope, acceptance criteria, blockers, or technical constraints
   - list linked issues by default
   - expand only directly relevant dependencies / blockers
   - do not expand more than 3 linked issues without asking the user
   - mention attachments without deeply expanding unless clearly critical
   - aggressively compress long comment threads

5. If Jira fetch fails:
   - report that the Jira connection failed
   - include any error message encountered
   - stop the skill run

6. Inspect the local repository:
   - identify likely impacted modules
   - locate similar existing implementations
   - capture technical constraints
   - note existing conventions and architecture boundaries
   - call out likely files or layers affected

7. Rewrite the ticket into this structure:

   - Title
   - Jira Source
   - Objective
   - Business / Product Context
   - Current Behavior
   - Desired Behavior
   - Scope
   - Out of Scope
   - Assumptions
   - Relevant Repo Context
   - Likely Impacted Areas
   - Risks
   - Ambiguities
   - Acceptance Criteria
   - Readiness Validation, only when one or more validation items are `Missing`
   - Validation / Test Requirements
   - Blocking Questions
   - Suggested Decisions Needed

   Each assumption must include:
   - source: `Jira`, `repo context`, or `inference`
   - impact: `low`, `medium`, or `high`
   - confidence: `low`, `medium`, or `high`

8. Strict validation requirements

Before marking the ticket ready, explicitly validate all of the following:

   - Is the expected behavior clearly defined?
   - Is success measurable?
   - Is scope bounded?
   - Are edge cases called out?
   - Are failure states understood?
   - Are dependencies / linked tickets known?
   - Are UX expectations clear if this is a UI ticket?
   - Are API contracts / request-response expectations clear?
   - Are DB / migration impacts understood?
   - Are auth / permissions requirements clear?
   - Are testing expectations clear?
   - Is rollback / risk mitigation needed?

Track each readiness validation item internally as:
   - `Satisfied`
   - `Missing`
   - `Not applicable`

Only include the **Readiness Validation** section in the final refined ticket when one or more items are `Missing`.
When included, list only the `Missing` items with brief reasons. Do not display `Satisfied` or `Not applicable` items.

9. If any unresolved ambiguity could materially change architecture, implementation sequence, schema, UX flow, or testing strategy:

   DO NOT mark as ready

10. Instead, produce a **Blocking Questions** section.

These questions should be:
   - concise
   - implementation-relevant
   - decision-focused
   - prioritized by impact

11. Extract comment-driven decisions:
   - product clarifications
   - scope shifts
   - PM / stakeholder decisions
   - technical constraints mentioned later in comments

12. When linked issues exist:
    - identify blockers
    - identify prerequisite work
    - identify shared dependencies
    - highlight cross-ticket coupling risks

13. When attachments exist:
    - mention them
    - indicate they were not deeply inspected
    - explicitly recommend inspection if UI behavior depends on them

14. End the draft refined ticket with one of these exact verdicts:

    READY FOR PLANNING

    or

    NEEDS DECISION BEFORE PLANNING

15. Strict verdict rule

Default to:

    NEEDS DECISION BEFORE PLANNING

READY FOR PLANNING is allowed only when:
   - all material readiness validation items are `Satisfied` or `Not applicable`
   - the **Blocking Questions** section is `None`
   - no medium-impact or high-impact assumption is based only on inference

Otherwise, use:

    NEEDS DECISION BEFORE PLANNING

16. Save the Codex review inputs to `.clanker\tmp`.
    - Create the directory if it does not exist.
    - Save the draft refined ticket to `.clanker\tmp\refined-ticket.md`.
    - Save summarized Jira decision-making context to `.clanker\tmp\refined-ticket-jira-context.md`.
    - Save summarized repo context to `.clanker\tmp\refined-ticket-repo-context.md`.

17. Run the local Codex CLI from PowerShell in non-interactive, read-only mode.

PowerShell command for ticket refinement review:

    New-Item -ItemType Directory -Force .clanker\tmp | Out-Null

    $codexModel = if ($env:CODEX_REVIEW_MODEL) { $env:CODEX_REVIEW_MODEL } else { "gpt-5.5" }
    $fallbackModel = "gpt-5.4"
    $reviewOutput = ".clanker\tmp\refined-ticket-codex-review.txt"
    $modelOutput = ".clanker\tmp\refined-ticket-codex-review-model.txt"
    $usedCodexModel = $null

    Remove-Item -LiteralPath $reviewOutput -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $modelOutput -Force -ErrorAction SilentlyContinue

    $refinedTicket = Get-Content .clanker\tmp\refined-ticket.md -Raw
    $jiraContext = Get-Content .clanker\tmp\refined-ticket-jira-context.md -Raw
    $repoContext = Get-Content .clanker\tmp\refined-ticket-repo-context.md -Raw

    $prompt = @"
    Review this refined engineering ticket.
    Be critical and practical.

    Look for:
    - Jira decisions, scope changes, or constraints omitted from the refined ticket
    - repo context that is omitted, misrepresented, or inconsistent with the refined ticket
    - missing acceptance criteria
    - unclear desired behavior
    - unresolved ambiguity hidden as an assumption
    - missing implementation-impacting questions
    - missing repository constraints
    - missing readiness validation blockers or reasons
    - assumptions missing source, impact, or confidence
    - missing validation or test requirements
    - scope that is too broad or too vague
    - verdict mismatch, especially tickets marked ready despite blockers

    Return exactly these sections:
    1. Major concerns
    2. Minor concerns
    3. Suggested changes to the refined ticket
    4. Is the readiness verdict justified?

    Jira decision-making context:
    $jiraContext

    Repo context:
    $repoContext

    Refined ticket:
    $refinedTicket
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

18. Read `.clanker\tmp\refined-ticket-codex-review.txt`.

19. Summarize Codex's feedback in the conversation.
    - Read `.clanker\tmp\refined-ticket-codex-review-model.txt` and mention the exact Codex model that produced the review.

20. Revise the refined ticket based only on useful feedback.
    - Keep feedback that is concrete, relevant, and actionable.
    - Reject feedback that is vague, unnecessary, or inconsistent with the repo's existing patterns.
    - Do not let Codex convert material uncertainty into assumptions.

21. Save the final refined ticket to `.clanker\tmp\refined-ticket-final.md`.
    - Do not output the final refined ticket contents in the conversation.
    - Tell the user the final refined ticket was saved and provide the file path so they can view it themselves.

## Output style

- concise
- engineering-focused
- decision-oriented
- planning-ready
- high signal

Do not optimize for speed.
Optimize for preventing rework.

## Rules

- Strict mode is a quality gate
- Codex is a reviewer, not the owner of the refined ticket
- The invoking agent owns the final refined ticket
- ambiguity should be surfaced, not assumed away
- do not convert major ambiguity into assumptions
- assumptions are allowed only for low-impact details
- every assumption must include source, impact, and confidence
- major product / technical uncertainty must become blocking questions
- repo constraints should override generic best practices
- prioritize correctness and implementation clarity over speed
- Use `gpt-5.5` by default.
- Fall back to `gpt-5.4` if `gpt-5.5` is unavailable.
- Keep Codex in `read-only` mode for review steps.
- Do not use `--full-auto` for review steps because it implies `workspace-write` sandboxing.
