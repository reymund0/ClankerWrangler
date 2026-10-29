# Design

## Context

See proposal.md for motivation. Today's package is:

- a 334-line coordinator
- nine specialist profiles and a generic Claude worker definition
- a policy-driven resolver (`routing_policy.py`, about 880 lines) with snapshots and Adaptive effort profiles
- a Vite routing editor with model discovery
- a narrative daily log plus a 14-column event ledger
- a cross-review launcher (`cross_review_core.py`, about 1,700 lines, plus one adapter per provider)

This change rebuilds it from scratch. Existing configuration, logs, and installed files are discarded, not migrated.

Evidence that shaped the design:

- **The ledger from seven `author-ai-monorepo` runs (23 worker threads).** Five lead roles were never used, half the threads needed revision, and almost every defect came from native or external review. Every piece of work the orchestrator kept for itself was a two-line fix.
- **External evidence.** CooperBench (2026) found coding success fell as agents were added to shared files. Cognition reports multi-agent setups work when writes stay single-threaded. Anthropic reports a cheap executor with a stronger advisor beats the executor alone at lower cost.

## Goals / Non-Goals

**Goals:**

- One code writer per run; every other subagent is read-only.
- Subagents exist to keep the orchestrator's context clean and move bulk work to cheaper models.
- One review procedure, reused at the plan, code, and refactor gates.
- A log that answers six questions:
  1. Does delegation save money?
  2. Do both reviewers contribute?
  3. How good is the Implementor?
  4. Is code review missing defects?
  5. Is triage tuned well?
  6. Where did an interrupted run stop?
- Claude and Codex hosts share all role and review guidance; only dispatch and the external reviewer differ.

**Non-Goals:**

- Parallel Implementors, workstreams, or file-ownership maps inside a run.
- Implementing accepted refactor proposals, committing, pushing, or opening pull requests.
- Migrating old preference files, logs, or installed specialist files.
- A routing UI.

## Decisions

### Three roles, one writer

```
CHAT 1  clanker-design-discussion
  explore --> OpenSpec artifacts + tasks --> clanker-dual-review (plan)
                                               |
                         consolidate, <=2 rounds, user decisions,
                         accepted fixes = artifact edits by this chat
                                               v
                                      runs.csv row (chat=design, done)
CHAT 2  clanker-orchestration-nation
  finalized? (tasks.md, validate --strict) --no--> stop
      |
  size check --small--> recommend no orchestration, stop (user may insist)
      v
  Implementor --> clanker-dual-review (code, <=2 rounds) --fixes--> Implementor
                     | pass
                     v
                  Functional Review (if runnable)
                     | defects: Implementor -> fresh code gate (<=2 rounds)
                     |          -> recheck; <=2 such cycles
                     v pass/skipped
                  clanker-dual-review (refactor, 1 round) --> user accepts/skips
                     v
                  final CSV rows --> handover with accepted proposals listed
```

The roles are:

- **Orchestrator:** keeps planning, OpenSpec state, the run log, consolidation, and small fixes.
- **Implementor:** one active thread per run. If a resumed chat cannot reach the earlier thread, a new one starts, seeded with a summary replayed from the run log.
- **Reviewer:** read-only; returns findings inline. It uses `clanker-code-review` criteria at the code gate, `clanker-refactor-review` criteria at the refactor gate, and an artifact review at the plan gate.
- **Functional Review:** read-only toward source. It exercises the running app and writes evidence only under `.clanker/functional/<run>/`.
- **No nesting:** subagents never start subagents.

The Implementor profile includes a **high-risk areas** section covering:

- security: authentication and access control, secrets, input validation, trust boundaries
- migrations and data integrity
- deploy and rollback

*Alternative considered:* keeping two or three specialist checklists as optional lenses. Rejected because the ledger showed labels did not change outcomes.

### Small-work rule

The orchestrator applies a fix itself when it is small and already understood, for example a five-line review fix. Before dispatching the Implementor, it estimates the whole job. If the job can be finished directly without filling the orchestrator's context, it stops and recommends doing it without orchestration; the user can tell it to continue anyway. The orchestrator delegates wide code reading, long test/fix loops, and browser sessions.

### Dual review as its own skill

A new standalone skill, `clanker-dual-review`, is invoked by the design chat (plan gate) and the orchestration chat (code and refactor gates). The skill says "caller" for whichever chat invokes it.

Each round runs these steps:

1. Fix the scope. For code and refactor, that is the committed diff from the base plus staged, unstaged, and untracked work. For plan, it is the change's artifacts.
2. Start the Reviewer subagent and the cross-review launcher (a background shell command) in parallel over that scope.
3. Wait for both. Consolidate: merge duplicates and mark each finding's source as `native`, `cross`, or `both`.
4. Triage each finding skeptically, treating it as a claim to verify, not an instruction. Two reviewers agreeing is not enough on its own.
   - **accept:** only when the caller confirmed the failure against the artifacts or code and the fix is the smallest obvious one. Accepted findings are fixed by the caller or the Implementor; at the plan gate, fixes are artifact edits by the design chat.
   - **user-decision:** any fix that would add a mechanism, state, configuration, a requirement, or a safeguard beyond the smallest obvious fix. Also any planning oversight, and any non-obvious remedy. The caller says what the fix would add and why it may be overengineering, and the gate waits for the user's take/skip.
   - **reject:** an unconfirmed or wrong finding, with a one-line reason.

   This rule exists because this change's own plan review showed the failure mode. The caller accepted reviewer-suggested safeguards (content hashing, retry-safe finalization, stale-run detection) that the user later cut as overengineering.
5. Append the events to the run log.

Rules for passing and rounds:

- A plan or code gate passes only when both reviewers completed the latest round, every accepted finding is fixed and checked, and every user decision is answered.
- The refactor gate passes once every proposal has a recorded accept or skip. Accepted proposals are listed at handover, not implemented.
- If a reviewer failed or was incomplete, no gate passes unless the user explicitly authorizes proceeding.
- The plan and code gates allow two rounds; round two covers the fixes and the code they touched. The refactor gate is one round.
- If findings are still open after round two, the caller stops with `stopped-at-limit` unless the user authorizes proceeding. A fix the user takes after round two is checked by the caller's own verification, not a third round.

`clanker-refactor-review` and `clanker-code-review` gain a caller-supplied-scope mode. In that mode they review the supplied scope, including uncommitted work, and return their output inline instead of writing `.clanker/refactor/*.md`.

*Alternative considered:* a procedure reference bundled into each calling skill. Rejected because three copies would drift apart.

### Functional Review loop

If the change can't be exercised through a browser, CLI, or API, Functional Review is skipped with the reason. Functional findings are triaged like review findings.

Each fix cycle runs Implementor → a fresh code gate (up to two rounds) → a Functional Review recheck. At most two cycles are allowed, so the worst case is six code rounds per run. After that the orchestrator stops with `stopped-at-limit`.

### Routes: one hand-edited file per host

The routes file is installed as `<agent-root>/clanker/routes.jsonc`, written only when absent. It is JSON plus full-line `//` comments; readers drop comment lines before parsing. The comments carry copy-paste commands for listing the models and efforts each CLI offers locally. Both commands are metadata-only and make no model call:

```jsonc
// List Codex models and reasoning efforts:
// (printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"clientInfo":{"name":"models","version":"1"},"capabilities":{}}}' '{"jsonrpc":"2.0","method":"initialized","params":{}}' '{"jsonrpc":"2.0","id":2,"method":"model/list","params":{"limit":100}}'; sleep 6) | codex app-server 2>/dev/null | python3 -c 'import json,sys;[print(r["model"],"->",", ".join(e["reasoningEffort"] for e in r["supportedReasoningEfforts"] or [])) for l in sys.stdin for m in [json.loads(l)] if m.get("id")==2 for r in m["result"]["data"]]'
//
// List Claude models and effort levels:
// (printf '%s\n' '{"type":"control_request","request_id":"m","request":{"subtype":"initialize"}}'; sleep 8) | claude -p --input-format stream-json --output-format stream-json --verbose --tools "" --no-session-persistence 2>/dev/null | python3 -c 'import json,sys;[print(x["value"],"->",", ".join(x.get("supportedEffortLevels") or [])) for l in sys.stdin for m in [json.loads(l)] if m.get("type")=="control_response" for x in m["response"]["response"]["models"]]'
{
  "host": "claude",
  "roles": {
    "implementor":  {"model": "haiku",       "effort": "medium"},
    "reviewer":     {"model": "sonnet",      "effort": "high"},
    "functional":   {"model": "sonnet",      "effort": "medium"},
    "cross-review": {"model": "gpt-6.1-sol", "effort": "high"}
  }
}
```

- The orchestrator's model is the user's session model.
- There is no resolver, Adaptive tiering, snapshot, or precedence chain.
- A file that is invalid JSON, names the wrong `host`, or has an entry without string `model` and `effort` blocks the role that needs it.
- Environment variables that force a subagent model are not checked separately; the observed-model columns in `runs.csv` expose them.

*Alternatives considered:* a slim editor (extra upkeep for about four values) and models hard-coded in the skill (changing a model would mean editing guidance).

### Claude host: role agent definitions

The installer writes `clanker-implementor`, `clanker-reviewer`, and `clanker-functional-review`. The two read-only definitions omit edit tools but keep Bash for `git diff`, tests, and starting the app. The orchestrator passes `model` and `effort` from `routes.jsonc` when it starts each subagent.

### Codex host

The Codex host shares the role instruction files and `clanker-dual-review`. Dispatch uses Codex's native collaboration tools, with the role instruction path passed in the assignment. The external reviewer is the Claude Code CLI adapter. It is built as the final task group.

### Cross-review launcher rewrite

The launcher is a new, smaller Python core with two adapters, `codex` and `claude`, and three phases, `plan`, `implementation`, and `refactor`.

- **Preflight:** the CLI is present and logged in; no login attempts or billing changes.
- **Packet:** the committed diff from the base plus staged, unstaged, and untracked changes, and the selected paths.
- **Invocation:** read-only, with a 45-minute default limit.
- **Findings:** validated JSON with IDs unique per report, severity `blocking`, `major`, `minor`, `info`, or `proposal`, a location, and a remedy.
- **Report:** `report.json` with an honest status, plus requested and observed settings and usage.

Before writing code, skim the old launcher tests for the 5–6 failure modes that matter most, such as malformed reviewer output, process timeouts, effort handling, and preflight diagnostics. Cover those with new tests.

### Log: append-only run log plus two final CSV tables

Each run, design or orchestration, writes one append-only event log at `.clanker/runs/<run>.jsonl`. The run ID is `<YYYYMMDD-HHMMSS>-<change>`. Every state change appends one JSON line and nothing is rewritten:

- `start`: host, chat, change, and per-role routes
- `round-start` and `round-end`
- `finding`, `triage`, `fixed`, `user-decision`
- `usage`
- `end` (outcome)

The design chat's run ends when its plan gate passes (`done`), stops at the limit, or is blocked.

Resume replays the log. That rebuilds the gate, round, open findings, pending decisions, cycles, and the routes recorded at start; a `routes.jsonc` edit applies only to new runs.

Outcomes are `done`, `stopped-at-limit`, `blocked`, or `small-job-declined`.

At the end, a helper script, `clanker_log.py`, replays the log and appends the final rows with Python's `csv` writer. If a write fails, it says so.

```
runs.csv     run, chat (design|implementation), host, change, started, ended,
             outcome, orchestrator_model, implementor_model, reviewer_model,
             functional_model, cross_review_model,
             orchestrator_tokens, implementor_tokens, reviewer_tokens,
             functional_tokens, cross_review_tokens, cross_review_seconds,
             plan_rounds, code_rounds, refactor_rounds, functional_cycles,
             small_fixes_by_orchestrator, notes

findings.csv run, gate (plan|code|functional|refactor), round, id,
             source (native|cross|both|functional),
             severity (blocking|major|minor|info|proposal), summary,
             triage (accept|user-decision|reject), user_decision (take|skip|),
             fixed_by (implementor|orchestrator|), reason
```

- **Model columns** hold `model/effort` as observed, or `<model>/<effort> (req)` when only the request is known.
- **Tokens** come from runtime evidence. On Claude this is the subagent completion usage (`subagent_tokens`) or the transcripts; for cross-review it is `report.json`. Missing values stay empty.
- **The design chat** writes its own run log and `runs.csv` row.

### Installation

`wrangle.sh` and `wrangle.ps1` install:

- `clanker-orchestration-nation` with role references
- `clanker-dual-review` with the launcher and `clanker_log.py`
- the existing standalone skills
- `routes.jsonc` if absent
- on Claude, the three agent definitions

Cleanup uses a hard-coded list of retired installed names: old specialist references, `clanker-cross-review.md`, the `clanker-orchestration-worker` agent, the routing helpers and policy, the editor build, the old launchers, the legacy skills, and the old `backups/orchestration-nation` handling. The installer deletes those paths without backups and prints each one. The list is needed because the source files that drove the old cleanup are deleted.

## Risks / Trade-offs

- [A launcher rewrite reintroduces bugs the old tests caught] → Cover the handful of failure modes that matter most with new tests.
- [Read-only roles still have Bash] → Edit tools are removed from their agent definitions, and their instructions forbid writes. An occasional stray edit would show up in review.
- [Up to six code rounds per run is costly on hard changes] → The user chose a fresh budget per cycle; the two-cycle cap bounds it, and `runs.csv` shows actual round counts.
- [The Implementor on a cheap model struggles] → The user can raise its route in `routes.jsonc`; the orchestrator never switches models mid-run.
- [One writer is slower than parallel writers on large multi-area changes] → Accepted. Large independent pieces go to separate sessions.
- [Deleting installed files removes user edits to them] → Accepted per user direction; the installer prints what it removed.
- [The Codex host's native dispatch may not support per-subagent model, effort, or thread continuation] → Validate in the Codex task group. If unsupported, report the limitation at run start.

## Migration Plan

There is no migration. Installing the new version replaces the package, writes a fresh `routes.jsonc`, and deletes the listed retired installed files. Old tracked `.clanker/` logs and reviews in this repository are deleted; in other projects they are left alone and ignored. Rollback means reinstalling from the previous git revision. The old main specs and archived orchestration changes were already deleted from `openspec/` during planning, so archiving this change creates the five specs fresh.

## Open Questions

- What exact Codex collaboration-tool parameters set model and effort and continue a worker thread? To be confirmed against the current Codex release during the Codex task group; this does not change the specs.
