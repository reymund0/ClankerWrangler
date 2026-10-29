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
- Host reference: `references/host.md` (native dispatch, model and effort, token capture) and
  `host.json` in this skill's directory (the host name and cross-review provider).
- Review procedure: the `clanker-dual-review` skill.
- Run log helper: `scripts/clanker_log.py` in the `clanker-dual-review` skill's directory.
- Routes: `<agent-root>/clanker/routes.jsonc`. Each role uses the model and effort recorded in
  the run's start event for the whole run; only an explicit user request changes a route.

Read `references/host.md` before dispatching anything.

## 1. Check the change is finalized

The change must have `tasks.md` and pass `openspec validate <change> --strict`. If either is
missing or failing, stop, name what is missing, and point the user to the design chat
(`clanker-design-discussion`), unless the user explicitly tells you to proceed.

## 2. Start or resume the run

- **New run:** `python3 <dual-review dir>/scripts/clanker_log.py start --chat implementation
  --host <claude|codex> --change <change> --routes <agent-root>/clanker/routes.jsonc
  --orchestrator-model <your model/effort>`. If it reports an invalid route, show the message
  (it names the file and key) and stop; never substitute a model.
- **Resume:** `clanker_log.py replay --run <run>` rebuilds the gate, round, open findings,
  pending user decisions, functional cycles, and routes. Ask any pending user decision first,
  then continue from that point.

## 3. Small-job check

Before dispatching the Implementor, estimate the whole job. If you could finish it directly
without filling your context (a handful of lines in one area), stop, recommend doing it without
orchestration, and end the run with outcome `small-job-declined`. Continue only if the user
explicitly asks.

## 4. Implement

Start one Implementor thread with the routed model and effort (see the host reference). The
assignment gives:

- the change name and the tasks to implement, with their requirements and scenarios
- the files or area to work in and repository conventions that matter
- the checks to run
- the role file path, and the handoff it must return

Send every later fix (review findings, functional defects) to the same thread while it is
reachable. If a resumed chat cannot reach it, start one new Implementor seeded with a summary
from the run log; never run two writers.

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

## 5. Code gate

Run `clanker-dual-review` with gate `code`, the run ID, and the base
(`git merge-base <default branch> HEAD`). The scope is committed, staged, unstaged, and
untracked work against that base. Accepted findings go to the Implementor, or to you when small.
At most two rounds; if findings stay open after round two, the run ends `stopped-at-limit`
unless the user authorizes proceeding.

## 6. Functional Review

After the code gate passes:

- **Skip** when the change cannot be exercised through a browser, a CLI, or an API, and say why.
- Otherwise start Functional Review with the routed model and effort. The assignment gives the
  run ID, the requirements and scenarios to exercise, how to start the app, and the role file
  path. Log `round-start` and `round-end` with gate `functional` (round 1 is the first check),
  one `finding` per reported defect with source `functional`, and its usage.

Triage functional findings like review findings (`clanker-dual-review` step 4): accept only
confirmed defects with the smallest obvious fix; escalate the rest as `user-decision`; reject
unconfirmed ones with a reason.

**Fix cycles:** each cycle sends accepted defects to the Implementor, then runs a fresh code
gate (up to two rounds; round numbers keep counting), then a Functional Review recheck of the
failed and affected flows (the next functional round). At most two cycles per run. If defects
remain after the second recheck, stop, list them, and end the run `stopped-at-limit`.

## 7. Refactor gate

After Functional Review passes or is skipped, run `clanker-dual-review` with gate `refactor`
for one round. Present the consolidated proposals; the user accepts (`take`) or skips each, and
every choice is logged. Do not implement accepted proposals.

## 8. Handover

- Check off the OpenSpec tasks you verified.
- End the run: `clanker_log.py finish --run <run> --outcome done --notes "<short notes>"`. If a
  write fails, say so.
- Tell the user what changed, the checks and their results, anything left open, and the
  accepted refactor proposals for them to act on.

Do not commit, push, or open a pull request; the thread is the user's from here.

## Run log

The run log is `.clanker/runs/<run>.jsonl`, append-only, through `clanker_log.py`.
`clanker-dual-review` logs its own rounds, findings, triage, fixes, and decisions. You log:

- `start` (step 2) and `end` with the outcome: `done`, `stopped-at-limit`, `blocked`, or
  `small-job-declined` (through `finish`)
- `usage` for the Implementor and Functional Review, and for yourself if your runtime reports it
- functional rounds, findings, triage, and decisions (step 6)
- `fixed` for every fix, with `by: "implementor"` or `"orchestrator"`

Record only values from runtime evidence; leave the rest out. Never log secrets, private
payloads, or hidden reasoning.

## Host differences

The Claude and Codex hosts use this same procedure and the same role files. Only native
dispatch and the external reviewer differ; `references/host.md` covers them. If the host cannot
apply a routed model or effort, say so at run start instead of claiming the setting.
