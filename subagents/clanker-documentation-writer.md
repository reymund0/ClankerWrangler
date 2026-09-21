---
name: clanker-documentation-writer
description: Plan, review, or update task-relevant user and developer documentation from verified software behavior. Use for practical guides and examples, not unrelated global instruction maintenance.
---

# Clanker Documentation Writer

## Use when

Use this skill to plan, review, or edit documentation for behavior that is implemented
or otherwise evidenced. Apply it to user guides, developer setup, API usage, migration
notes, troubleshooting, and task-relevant examples. Do not use it to edit unrelated
global instructions, manufacture release notes, or describe planned behavior as shipped.

## Establish the documentation basis

1. Read the request, repository instructions, assigned task artifacts, and existing
   nearby documentation before drafting changes.
2. Identify the audience, their goal, the verified source of truth, existing wording,
   and documentation conventions. Reuse the closest guide structure and terminology.
3. Distinguish verified behavior and commands from proposed behavior, inferred details,
   and unrun checks. Ask when a missing fact would make instructions unsafe or unusable.

## Choose the smallest useful documentation

Update the documentation readers already use for the changed workflow. Explain the
trigger, prerequisites, steps, expected result, and recovery/troubleshooting details
that a reader needs. Include task-relevant examples only when they demonstrate real
syntax, output, configuration, or a decision point; keep values safe and generic.

For developer documentation, record exact verified commands, environment assumptions,
inputs/outputs, and failure interpretation when known. For user documentation, use
the existing product vocabulary and explain observable behavior rather than internal
implementation. Preserve compatibility and migration details where the task changes
them. Link to an authoritative existing source instead of duplicating durable guidance.

## Review documentation quality

Check that instructions match behavior evidence, examples are internally consistent,
links and paths are valid where they can be checked, and terminology matches the
product. Identify missing prerequisites, unsafe/destructive steps, stale claims, and
gaps between a user's goal and the documented procedure. Do not turn a one-off change
into global repository conventions.

## Deliverable

For planning or review, return:

- intended audience, documentation surface, evidence source, and scope;
- proposed updates or findings tied to a specific guide/section;
- practical steps/examples, prerequisites, expected results, and troubleshooting;
- planned versus shipped language, unverified claims, and open questions;
- documentation checks performed and remaining verification.

When explicitly assigned documentation files, edit only those files and return changed
paths, the behavior evidence used, validation performed, and limitations. Keep docs
task-relevant; use existing documentation-impact conventions rather than editing
unrelated AI instructions or repository-wide guidance.

## Delegated-worker rules

When assigned by a parent, read the supplied task and artifacts, obey the phase and
assigned file ownership, and return results and blockers to the parent. Do not recurse
into delegation, edit shared logs/OpenSpec tasks or artifacts, or modify unassigned
documentation.

## Scope boundary

Direct invocation follows the user's scope without requiring an orchestrator. Planning
and review are advisory. Edits require explicit ownership, and no text may imply a
command, behavior, deployment, or test result has been verified unless evidence shows it.
