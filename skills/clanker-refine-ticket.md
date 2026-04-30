---
name: clanker-refine-ticket
description: Fetch a Jira ticket through the Atlassian MCP server, combine it with local repo context, and rewrite it into a planning-ready engineering ticket using strict validation rules.
---

When invoked, follow this workflow exactly.

## Purpose

Turn a Jira ticket into a planning-ready engineering ticket with strict validation.

Unlike fast mode, strict mode must identify missing decisions that could materially change the implementation approach.

This workflow should act as a pre-planning quality gate.

Do not allow ambiguous tickets to proceed without clearly flagging blockers.

## Invocation behavior

- Preferred usage: `/clanker-refine-ticket MR-42`
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
   - summarize comments unless only a few short comments exist
   - list linked issues by default
   - expand only directly relevant dependencies / blockers
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
   - Readiness Validation
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

In the **Readiness Validation** section, mark each item as:
   - `Satisfied`
   - `Missing`
   - `Not applicable`

Include a brief reason for each status.

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

14. End with one of these exact verdicts:

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
- ambiguity should be surfaced, not assumed away
- do not convert major ambiguity into assumptions
- assumptions are allowed only for low-impact details
- every assumption must include source, impact, and confidence
- major product / technical uncertainty must become blocking questions
- repo constraints should override generic best practices
- prioritize correctness and implementation clarity over speed
