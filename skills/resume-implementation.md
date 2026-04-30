---
name: resume-implementation
description: Resume a previously paused implementation by reconciling the existing conversation plan with the current repository state and continuing from the next incomplete step.
---

When invoked, follow this workflow exactly.

## Purpose

Resume an interrupted implementation safely without redoing completed work.

This skill is intended for use after:
- usage limits interrupted implementation
- the session was paused and resumed later
- additional edits were made in another tool such as Cursor or Windsurf
- the user wants to continue from the existing plan in the same conversation

The primary objective is to re-baseline the current repository state before making further changes.

## Workflow

1. Review the existing conversation context.

Identify:
- the finalized implementation plan
- any previous implementation steps completed in this conversation
- previously discussed files
- known blockers or unfinished steps

2. Inspect the current repository state.

Check:
- current git branch
- current working directory
- current git diff
- staged changes
- unstaged changes
- newly created files
- deleted files

3. Compare the current repository state against the prior implementation plan.

Create a concise checkpoint summary with:

   - Completed steps
   - Partially completed steps
   - Remaining steps
   - Files already modified
   - Files likely still needing work

4. If changes were made outside this conversation
   (for example in Cursor, Windsurf, Codex, or manual edits),
   treat the repository as the source of truth.

Do not assume the previous conversation state is still accurate.

5. Before continuing implementation, present this exact section:

   RESUME CHECKPOINT SUMMARY

6. Explicitly state the next recommended step.

Example:

   NEXT STEP: Implement API validation in MediaTemplateController

7. Only continue implementation after the checkpoint summary is complete.

8. Continue from the next incomplete step only.

Do NOT:
- repeat completed work
- overwrite valid existing changes
- reapply already implemented logic
- recreate files that already exist

9. Preserve repo conventions and existing code style.

10. If the current repo state materially conflicts with the original plan,
    first present:

   PLAN DRIFT DETECTED

Then summarize:
- what changed
- whether the plan should be revised
- the safest next step

11. If uncertainty exists, prefer inspecting files over assuming prior context.

12. End with one of:

   READY TO CONTINUE IMPLEMENTATION

   or

   NEEDS PLAN REBASELINE

## Rules

- Repository state is the source of truth
- Existing conversation plan is secondary to actual code state
- Never duplicate completed work
- Always checkpoint before continuing
- Prefer safe continuation over fast continuation
- Detect plan drift aggressively