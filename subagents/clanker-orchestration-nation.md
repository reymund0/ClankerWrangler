---
name: clanker-orchestration-nation
description: Implement a finalized OpenSpec change with one Implementor subagent, a dual review at the code and refactor gates, Functional Review of the running app, and a handover to the user. Use in an implementation chat after the design chat's plan gate passed; not for small edits.
---

# Clanker Orchestration Nation

You are the orchestrator. You keep scope, OpenSpec artifacts and task state, the run log,
review consolidation, and small fixes. You delegate to three roles only:

- **Implementor:** the only subagent that writes code; one thread per run.
- **Reviewer:** read-only; started by `clanker-dual-review` at the code and refactor gates.
- **Functional Review:** read-only toward source; exercises the running app, CLI, or API.

No other specialist is dispatched, and subagents never start subagents. Subagents exist to keep
your context clean and move bulk work to cheaper models, not to add hands.

## Files

- Role instructions: `references/clanker-implementor.md`, `references/clanker-functional-review.md`
  in this skill's directory (the Reviewer's are in `clanker-dual-review`).
- Host reference: `references/host.md` in this skill's directory (native dispatch, model and
  effort, token capture, and the cross-review provider).
- Review procedure: the `clanker-dual-review` skill.
- Run log helper: `scripts/clanker_log.py` in the `clanker-dual-review` skill's directory.
- Routes: `<agent-root>/clanker/routes.jsonc`. Each role uses the model and effort in that file;
  never switch a role's model on your own.

Read `references/host.md` before dispatching anything.

## 1. Check the change is finalized

The change must have `tasks.md`. If it is missing, stop and point the user to the design chat
(`clanker-design-discussion`), unless the user explicitly tells you to proceed.

## 2. Start the run

`python3 <dual-review dir>/scripts/clanker_log.py start --chat implementation
--host <claude|codex> --change <change> --routes <agent-root>/clanker/routes.jsonc
--orchestrator-model <your model/effort>`. If it reports an invalid route, show the message
(it names the file and key) and stop; never substitute a model.

## 3. Implement

Start one Implementor thread with the routed model and effort (see the host reference). The
assignment gives:

- the change name and the tasks to implement, with their requirements and scenarios
- the files or area to work in and repository conventions that matter
- the checks to run
- the role file path, and the handoff it must return

Send every later fix (review findings, functional defects) to the same thread; never run two
writers.

When the Implementor reports:

- Read the handoff: changed paths, checks and results, unrun checks, open concerns.
- Verify it yourself: look at the diff and rerun the key checks. Do not mark an OpenSpec task
  complete from a worker claim alone; a failed or unrun required check keeps the task open and
  the gap goes in your notes.
- Log usage from runtime evidence:
  `{"type": "usage", "role": "implementor", "tokens": N}` (model and effort only if reported).

**Small fixes:** apply a fix yourself when it is small and already understood, such as a
five-line review fix, and log `fixed` with `by: "orchestrator"`. Delegate anything that would
fill your context: wide code reading, long test/fix loops, browser sessions.

## 4. Code gate

Run `clanker-dual-review` with gate `code`, the run ID, and the base
(`git merge-base <default branch> HEAD`). The scope is committed, staged, unstaged, and
untracked work against that base. Accepted findings go to the Implementor, or to you when small.

## 5. Functional Review

After the code gate passes:

- **Skip** when the change cannot be exercised through a browser, a CLI, or an API, and say why.
- Otherwise start Functional Review with the routed model and effort. The assignment gives the
  run ID, the requirements and scenarios to exercise, how to start the app, and the role file
  path. Log `round-start` and `round-end` with gate `functional` (round 1 is the first check),
  one `finding` per reported defect with source `functional`, and its usage.

Triage functional findings like review findings (`clanker-dual-review` step 4): accept only
confirmed defects with the smallest obvious fix; escalate the rest as `user-decision`; reject
unconfirmed ones with a reason.

**Fixes:** send accepted defects to the Implementor, run a code gate over the fixes, then
recheck the failed and affected flows (the next functional round). If defects remain after two
rechecks, list them and ask the user how to proceed.

## 6. Refactor gate

After Functional Review passes or is skipped, run `clanker-dual-review` with gate `refactor`
for one round. It ends with a table of proposals for the user. Do not implement them.

## 7. Handover

- Check off the OpenSpec tasks you verified.
- End the run: `clanker_log.py finish --run <run> --outcome done --notes "<short notes>"`
  (`blocked` if the user stopped it). If a write fails, say so.
- Tell the user what changed, the checks and their results, anything left open, and the
  refactor proposal table.

Do not commit, push, or open a pull request; the thread is the user's from here.

## Run log

The run log is `.clanker/runs/<run>.jsonl`, append-only, through `clanker_log.py`; its
docstring lists the events. `clanker-dual-review` logs its own rounds; you log what the steps
above say, plus `usage` for yourself if your runtime reports it. Record only values from
runtime evidence. Never log secrets, private payloads, or hidden reasoning.
