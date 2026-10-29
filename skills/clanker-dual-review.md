---
name: clanker-dual-review
description: Run the native Reviewer and an external cross-review in parallel over the same scope at the plan, code, or refactor gate, then consolidate, triage skeptically, collect user decisions, and log the round. Invoked by clanker-design-discussion (plan gate) and clanker-orchestration-nation (code and refactor gates); not for standalone code review.
---

# Clanker Dual Review

One procedure for the three review gates. "Caller" means the chat that invoked this skill: the
design chat at the plan gate, the orchestration chat at the code and refactor gates. The caller
owns triage, fixes, the run log, and the user conversation; the reviewers only report.

## Files

- Reviewer role instructions: `references/clanker-reviewer.md` in this skill's directory.
- Cross-review launcher: `scripts/cross_review.py` in this skill's directory.
- Run log helper: `scripts/clanker_log.py` in this skill's directory.
- Routes: `<agent-root>/clanker/routes.jsonc` (`~/.claude/clanker/routes.jsonc` on Claude,
  `~/.codex/clanker/routes.jsonc` on Codex). Use the `reviewer` and `cross-review` routes
  recorded in the run's start event, not the file's current values.

The caller has already started a run (`clanker_log.py start`) and passes its run ID. Use
`clanker_log.py replay` to find the current gate and round when resuming.

## Gates

| Gate | Caller | Scope | Reviewer criteria | Cross-review phase | Rounds |
|---|---|---|---|---|---|
| `plan` | design chat | the change's OpenSpec artifacts | plan criteria in the role file | `plan` | at most 2 |
| `code` | orchestration chat | implementation against the base | `clanker-code-review`, caller-supplied scope | `implementation` | at most 2 per code gate |
| `refactor` | orchestration chat | implementation against the base | `clanker-refactor-review`, caller-supplied scope | `refactor` | 1 |

## 1. Fix the scope

Both reviewers get the same scope.

- **plan:** the change directory, `openspec/changes/<change>/`.
- **code and refactor:** the committed diff from the stated base plus staged, unstaged, and
  untracked work. State the base explicitly (for example `git merge-base main HEAD`); uncommitted
  work is always included.
- **round two:** the same base, with the earlier findings and a list of the fixes and the files
  they touched, so both reviewers check the fixes and the code around them.

## 2. Start both reviewers at once

Log `{"type": "round-start", "gate": G, "round": R}` first. Round numbers count up across the
run for each gate, so a fresh code gate after a functional fix cycle continues the numbering.

In the same turn, start both, and wait for both before going on:

- **Cross-review**, as a background shell command. Write a manifest, then run the launcher with
  the routed model and effort:

  ```json
  {"phase": "plan", "base": null, "paths": ["openspec/changes/<change>"], "focus": "round-two notes, if any"}
  ```

  ```bash
  python3 <skill-dir>/scripts/cross_review.py --provider <codex on Claude | claude on Codex> \
    --manifest <manifest> --out .clanker/reviews/<run>/<gate>-<round> \
    --model <cross-review model> --effort <cross-review effort>
  ```

  The launcher runs read-only, stops after 45 minutes, and always writes `report.json` with
  `status` (`clean`, `changes_requested`, `incomplete`, `failed`), `findings`, `diagnostic`,
  `observed`, `usage`, and `seconds`.
- **Native Reviewer** subagent with the routed model and effort. On Claude, start the
  `clanker-reviewer` agent with `model` and `effort` from the `reviewer` route. On Codex, use the
  host's native dispatch. Give it the gate, the scope, the absolute path of the role file, and
  for code or refactor the absolute path of the criteria skill. It replies inline with a JSON
  array of findings and a coverage note, and writes no files.

When both finish, log `{"type": "round-end", "gate": G, "round": R, "native": <status>,
"cross": <report status>}`, using `clean`, `changes_requested`, `incomplete`, or `failed` for the
native reviewer too. Log usage from runtime evidence only:

- `{"type": "usage", "role": "reviewer", "tokens": N}` from the subagent's completion usage,
  plus `model` and `effort` only if the runtime reports them.
- `{"type": "usage", "role": "cross-review", "seconds": S, "tokens": N}` from `report.json`,
  where tokens are `input_tokens + output_tokens`; add `model` and `effort` only when
  `observed` is not `unknown`. Omit any value the report does not have.

## 3. Consolidate

Merge both lists into one. Give each consolidated finding an ID `C1`, `C2`, … unique within this
gate and round, mark its source `native`, `cross`, or `both` (both reviewers describe the same
problem), and keep the higher severity when they differ. Log one `finding` event per consolidated
finding: `gate`, `round`, `id`, `source`, `severity`, `summary`.

## 4. Triage skeptically

Treat every finding as a claim to check, not an instruction. Two reviewers agreeing is not enough
by itself. For each finding, read the cited artifact or code and decide:

- **accept** only when you confirmed the failure yourself and the fix is the smallest obvious one.
- **user-decision** when the fix would add a mechanism, state, a configuration option, a
  requirement, or a safeguard beyond the smallest obvious fix; when the finding exposes a
  planning oversight; or when the remedy is not obvious. Retry bookkeeping, hashing, extra
  validation layers, and new options are typical examples. Tell the user what the fix would add
  and why it may be overengineering.
- **reject** when you cannot confirm it or it is wrong, with a one-line reason.

At the refactor gate, every confirmed proposal is a `user-decision` (the user accepts or skips
it); unconfirmed proposals are rejected.

Log `{"type": "triage", "gate": G, "round": R, "id": ID, "triage": T, "reason": "..."}`.

## 5. Fix accepted findings

- **plan:** the design chat edits the artifacts itself.
- **code:** small, understood fixes by the orchestrator; the rest by the Implementor.
- **refactor:** nothing is fixed; accepted proposals are listed at handover.

Check each fix (re-read the edit, run the relevant test) and log
`{"type": "fixed", "gate": G, "round": R, "id": ID, "by": "orchestrator" | "implementor"}`.
At the plan gate, artifact edits by the design chat log `by: "orchestrator"`.

## 6. Ask the user

At the end of the round, show the user:

- each `user-decision` finding with what its fix would add and why it may be overengineering
- the number of accepted and rejected findings, with the one-line reject reasons

Wait for take or skip on each. Log `{"type": "user-decision", "gate": G, "round": R, "id": ID,
"decision": "take" | "skip"}`. A finding the user takes is handled as accepted: fix it, check
it, and log `fixed`.

## 7. Pass, repeat, or stop

- **A reviewer failed or was incomplete** (for example a cross-review preflight that reports the
  CLI missing or not logged in): report which one and its diagnostic, and ask the user whether to
  proceed. No gate passes without the user's explicit go-ahead.
- **plan or code gate passes** when both reviewers completed the latest round, every accepted
  finding is fixed and checked, and every user decision is answered. A round with no accepted or
  pending findings passes.
- **Round two:** if round one left accepted findings that were fixed, run one more round over the
  fixes (step 1, round two). Fixes the user takes after round two are checked by the caller's own
  verification, not a third round.
- **Limit:** if findings are still open after round two, stop with outcome `stopped-at-limit`
  and list them, unless the user explicitly authorizes proceeding.
- **refactor gate** runs one round and passes once every proposal has a recorded accept (`take`)
  or skip. Accepted proposals are listed at handover, not implemented.

Tell the caller the result: passed, stopped at the limit, or waiting on the user. Ending the
run (`clanker_log.py finish`) is the caller's job.

## Rules

- The reviewers never edit files. Only the caller (or the Implementor it dispatches) fixes.
- Never report a gate as passed, a reviewer as complete, or a log write as done when it was not.
  If a `clanker_log.py` command fails, tell the user.
- Do not log secrets, raw private payloads, or hidden reasoning; summaries only.
