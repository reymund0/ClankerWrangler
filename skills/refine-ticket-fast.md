---
name: refine-ticket-fast
description: Fetch a Jira ticket through the Atlassian MCP server, combine it with local repo context, and rewrite it into a planning-ready engineering ticket using fast-mode assumptions.
---

When invoked, follow this workflow exactly.

## Purpose

Turn a rough or underspecified Jira ticket into a planning-ready engineering ticket.

Use Jira as the source of truth for ticket context, then inspect the local repository to align the refined ticket with the existing codebase and patterns.

This is a fast-mode refinement workflow:
- make reasonable assumptions
- do not block on every ambiguity
- clearly label open questions
- produce something that is usually ready for planning

## Invocation behavior

- Preferred usage: `/refine-ticket-fast MR-42`
- If no Jira ticket key is provided, ask the user for the ticket key before continuing.
- If Jira data cannot be fetched, fall back to any manual ticket text the user provided.
- If neither Jira data nor manual ticket text is available, stop and ask for ticket information.

## Workflow

1. Identify the Jira ticket key from the user input.

2. Use the Atlassian MCP tools to fetch the Jira issue.

3. Pull the most useful ticket context first:
   - ticket key
   - summary / title
   - description
   - acceptance criteria if present
   - status
   - priority
   - labels
   - parent / epic if present
   - subtasks if present
   - linked issues
   - comments
   - attachments metadata

4. Keep Jira context selective and compact:
   - summarize comments unless there are only a few short comments
   - list linked issues by default
   - only expand linked issues if they appear directly relevant to implementation
   - mention attachments or screenshots, but do not deeply inspect them unless the ticket is obviously UI-heavy or the attachment is clearly critical
   - avoid bloating context with long comment chains or large linked issue trees unless they are clearly important

5. If Jira fetch fails:
   - fall back to the user's manually provided ticket text
   - clearly note that Jira context was unavailable
   - continue refinement if enough information exists

6. Inspect the local repository for relevant implementation context:
   - identify likely modules, folders, or files involved
   - look for existing patterns that should shape the ticket
   - note constraints implied by the current architecture
   - prefer observed repo conventions over generic advice

7. Rewrite the ticket into a concise engineering-ready format with these sections:

   - Title
   - Jira Source
   - Objective
   - Background / Context
   - Current Behavior
   - Desired Behavior
   - Scope
   - Out of Scope
   - Assumptions
   - Relevant Repo Context
   - Likely Impacted Areas
   - Risks / Ambiguities
   - Acceptance Criteria
   - Validation / Test Notes
   - Open Questions

8. Fast-mode refinement rules:
   - make reasonable assumptions instead of stopping for every missing detail
   - explicitly label assumptions
   - convert vague requirements into proposed acceptance criteria when possible
   - preserve uncertainty in an Open Questions section instead of blocking progress
   - keep the refined ticket practical and implementation-oriented
   - do not overengineer or expand scope unnecessarily

9. When comments are present:
   - extract decisions, clarifications, scope shifts, and hidden requirements
   - ignore low-value discussion that does not affect implementation
   - call out contradictions between the description and the comments if found

10. When linked issues are present:
    - list them briefly
    - expand only the ones that appear directly relevant to requirements, dependencies, blockers, or shared implementation work

11. When attachments are present:
    - mention them in the ticket summary
    - state whether they were not expanded
    - if the issue appears UI-driven and the attachment seems likely to matter, note that the planner or implementer should inspect it before coding

12. End with one of these exact verdicts:

    READY FOR PLANNING

    or

    NEEDS DECISION BEFORE PLANNING

13. Default to READY FOR PLANNING unless a missing decision would materially change the implementation approach.

## Output style

- Be concise, structured, and practical.
- Optimize for handoff into a planning skill.
- Do not dump raw Jira data unless necessary.
- Synthesize Jira + repo context into a cleaner engineering ticket.
- Prefer clarity over completeness.
- Keep the final output readable enough that another agent could plan from it immediately.

## Rules

- Jira is the starting source of truth, but comments may override or clarify the description.
- Repo context should shape the refined ticket whenever implementation constraints are visible.
- Do not let linked issues or comments explode the context window without a good reason.
- Summarize aggressively when information is long but low-signal.
- Mention attachments without deeply pulling them unless clearly necessary.
- Fall back gracefully to manual ticket text if Jira is unavailable.
- Fast mode should move the work forward, not stall on ambiguity.
