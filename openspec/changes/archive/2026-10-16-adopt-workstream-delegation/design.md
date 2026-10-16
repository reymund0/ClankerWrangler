# Design

## Context

See proposal.md for motivation. Current behavior:

- **The coordinator** (`subagents/clanker-orchestration-nation.md`) resolves a route and dispatches a worker per assignment.
- **The Claude host reference** says to "start a new worker rather than assuming an earlier worker's model or effort applies".
- **The Codex host reference** reuses an idle worker when its route matches. Codex runs already work close to a workstream model:
  - NA-446 split backend, authoring, and learner work by code area in `.clanker/NA446-CONTRACT.md`;
  - NA-468 and NA-446 reused workers for follow-ups (`na468_form`, `na468_plan_review`, and the UI worker on 2026-10-07).
- **The shared spec** already says to "prefer suitable idle-worker reuse" ("Capacity-aware dispatch"), so the Claude host has drifted from it.

**Evidence from NA-358** (Claude host, 2026-10-15; subagent transcripts in the author-ai-monorepo session `d8cc5366`):

- Seven threads were started: six Haiku implementation workers and one Sonnet review. A1 ran 1m49s; A6 ran 3m11s.
- Every fresh worker's first call was about 62K tokens: instructions, tools, and handoff. The workers then re-read the OpenSpec artifacts before doing anything.
- Context per call grew to 117K for A1, 227K for A5, 377K for R1, and 427K for A4.

**Cost evidence, input side only:**

- Prices are API list prices from the bundled claude-api reference, cached 2026-10-06.
- Output tokens are not included, because worker transcripts keep only partial output counts.
- On a subscription these are usage weight rather than dollars. The ratios are assumed to hold.

| Context per call | Haiku 5.5 | Sonnet 5.5 / Opus 5.5 |
|---|---|---|
| 62K | $0.0006 | $0.012 |
| 250K | $0.0125 | $0.05 |
| 1M | $0.05 | $0.20 |

Haiku moves to a 5× rate card once a prompt exceeds 100K tokens. Even so, a Haiku thread at 1M costs about what the Opus parent costs per call at 250K.

What NA-358 cost:

| | Cost |
|---|---|
| All Haiku workers together | $2.96 |
| R1 (Sonnet review) | $4.93 |
| Parent while orchestrating (110 calls, average context 203K) | $5.58 |
| **Parent during browser QA (385 calls, average context 485K)** | **$42.17** |

Simulated alternatives:

| Alternative | Cost | As run |
|---|---|---|
| A5 continued in A4's thread | $1.27 | $0.46 fresh |
| A6 continued in A5's thread | $0.56 | $0.24 fresh |
| Parent doing A6 itself (10–30 calls at its 264K context) | $0.53–1.59 | $0.24 (A6 worker) |

**Claude Code behavior** (Claude Code documentation: sub-agents, model configuration, environment variables):

- Subagents auto-compact near the model's limit, about 967K tokens for 1M-context models.
- A per-agent `autoCompactWindow` setting (100K–1M) exists from v2.1.296.
- `SendMessage` resumes a subagent with its full history and the model and effort it was started with.
- Compaction appears in the subagent transcript as a `compact_boundary` entry with `preTokens`.

## Goals / Non-Goals

**Goals:**

- One host-neutral delegation model in the coordinator. Host references describe only how to start and continue a thread.
- Fewer threads, with context reused where that is cheap and helpful.
- A parent context that stays small.
- A run log you can analyze in a spreadsheet, with no end-of-run step.

**Non-Goals:**

- Routing-policy, resolver, editor, or installer changes.
- New scripts.
- Changing the Haiku implementation default. The ledger supplies the evidence for that decision later.
- Changes to external cross-review launchers or verdicts.
- Escalating a struggling workstream to a stronger route (D5).

## Decisions

### D1. The unit of delegation is a workstream thread

Build work is grouped into workstreams, and each workstream keeps one thread for all of its assignments (see the workstream requirements in the development-orchestration delta).

**Why: continuity, not token savings.** On Haiku, reuse is roughly cost-neutral to slightly more expensive. Continuing A4's thread for A5 would have cost about $1.27, against $0.46 for a fresh worker, because every call carries the thread's history. The difference is cents. What reuse buys is a thread that already knows its earlier decisions and the code it read, which matters most for fixing its own work. That trade is accepted unless the ledger shows real waste. The run's large savings come from D6 and D9.

**Alternatives:**
- *One thread per assignment* (the Claude status quo): every follow-up starts without the context of the work it is fixing.
- *Parent-only, with subagents just for reviews*: rejected on cost. Parent calls at a 200K+ context cost more than a fresh Haiku worker.

### D2. A workstream is defined by code area, with roles as checklists

A workstream owns files; its role profiles are checklists it applies. Follow-up routing then follows the existing ownership rule, and parallel independent areas stay possible. Role profiles are about 500 words each, roughly half shared process text and half a domain checklist, so carrying two costs little next to starting a thread.

**Alternatives:**
- *One thread per role*: this forces independent same-role work to run one piece after the other. In NA-446 the authoring and learner work, both UI, ran in parallel.
- *A new full-stack role*: unnecessary once a workstream can carry several checklists.

### D3. Split across a boundary only with an up-front contract and enough work on both sides

NA-446 shows the pattern: the parent wrote the contract before dispatch, and both sides were large. Without a written contract, parallel threads would wait on each other or conflict.

**Alternative:** always split by layer. That adds a coordination seam for thin slices.

### D4. The route is resolved once, at thread start, from the lead role and the hardest expected tier

The resolver still takes one `role`. Continued assignments keep the thread's route; a resumed Claude subagent keeps the model and effort it was started with.

**Alternatives:**
- *The strongest route among all the checklists*: the policy has no model ranking, so this would need code.
- *Re-resolving each follow-up and reusing only on a match*: a change in tier assessment would force a new thread.

**Accepted cost:** easier early work runs at the higher effort.

### D5. No escalation step in v1

A workstream keeps its route. When a thread struggles, the parent continues it, takes the fix over, or asks the user. The parent never switches routes on its own; a different route needs an explicit user choice, as it does today.

The Codex plan review (WSD-P1) showed why even a guidance-only escalation step was not simple:
- Re-resolving often cannot raise effort: the bundled Haiku profile maps both involved and demanding to high.
- The only other source of a higher effort is `session_override`, which `usage.md` restricts to explicit user choices.

**Alternatives:**
- *Escalation at a higher effort, or with a user-approved model*: needs a rule for where the higher effort comes from.
- *An escalation model in routing policy*: needs code and editor changes.

Both are deferred until ledger data shows whether escalation would fix hard cases.

### D6. Delegation threshold: written criteria plus a logged reason

The parent keeps fixes it has already diagnosed that take a few calls, plus its own git, OpenSpec, and log work. The tier breaks ties. The cost data drove this: "the parent does small tasks" saves handoff friction but not money.

**Alternatives:**
- *Tier-only*: misfires on small involved work such as A6.
- *Size thresholds*: there is no data to set them.

### D7. Threads retire at the end of their workstream; compaction uses the host default

On Haiku, reuse costs cents, and the main cost is the parent. Unfinished work retires as `blocked` when it is abandoned, or when the run ends blocked or interrupted. That keeps failed threads in the outcome data without an end-of-run step (WSD-P3). A thread waiting on a user decision stays active.

**Alternatives:**
- *A follow-up count limit*: arbitrary.
- *A 150K size limit*: it solves a small problem.
- *`autoCompactWindow` set to 100K to avoid Haiku's rate cliff*: rejected for three reasons. Workers already start at 62K. Each compaction is a call over the whole context and loses detail. The one worker definition is shared with reviewers, and R1 needed 377K.

**Revisit** with a 300–400K window if the ledger's `final_context` shows threads ballooning.

### D8. Reviewers recheck in their own thread, with guardrails

A recheck costs roughly the same reused or fresh (estimated under $1 either way for NA-358), because a fresh reviewer must re-read the large files. Continuity wins on accuracy and on number of calls. The brief's regression check counters anchoring. A fresh reviewer is used when the spec, design, or scope moved. External review keeps its fresh-session launcher.

**Alternative:** one-shot reviewers with narrow briefs.

### D9. Acceptance runs outside the orchestrator

Browser and long acceptance work goes to a worker that owns the browser, which the existing `clanker-ui-ux-reviewer` visual-review route already provides. It starts at about 62K context instead of inheriting the parent's 286K-plus.

**Alternative:** keep QA in the parent. That was the largest single cost in NA-358.

### D10. Logging: clock timestamps and an append-only CSV ledger

The narrative daily log stays as it is: routing JSON once per workstream, dispositions, and the completion entry. A CSV ledger gets one row per event, and outcomes go on retire rows. Each continued assignment is tagged `followup_kind` `defect` or `scope`, so a spreadsheet can count defect fixes and scope changes per workstream without any totals stored on the retire row (WSD-P2). Rows are appended with Python's standard `csv` writer through a documented one-line command. Python 3.10+ is already a prerequisite.

**Alternatives:**
- *A closing table*: there is no reliable end of run. NA-358's QA and task updates landed after "completion".
- *A markdown ledger table*: renders well but imports into spreadsheets less directly.
- *`echo` appends*: break on commas and quotes.
- *A helper script*: not needed for v1.

### D11. Policy lives in the coordinator; host references hold only mechanics

The reuse, delegation, retirement, and acceptance rules move to the coordinator. Each host reference only says how to work with threads:

- **Claude:** find threads with `ListAgents` and continue one with `SendMessage`.
- **Codex:** reuse an idle worker through its collaboration tools.

The Claude host's "start a new worker" sentence is removed. The Claude host reference also documents a jq command that reads `message.model`, `effort`, and the last call's context size from a subagent transcript, for the retire row.

## Risks / Trade-offs

- **Continued threads carry their whole history into every call.** → Accepted at Haiku prices. `final_context` is logged per thread, and compaction can be revisited (D7).
- **A continued thread acts on an outdated understanding** after a spec revision. → The continued-assignment brief must state revisions (Workstream threads scenario).
- **The reviewer is anchored on its own findings.** → The recheck brief requires a regression check of the changed lines. A fresh reviewer is used when the ground moved.
- **Haiku crosses its 100K rate cliff quickly**, since it starts at 62K. → Accepted. It is still cheaper per call than parent work at the parent's typical context.
- **Background-worker continuation through `SendMessage` needed a live check on the Claude CLI.** → Verified 2026-10-16 (task 6.3). Steps:
  1. A background `clanker-orchestration-worker` was started at `haiku`/`low` and completed its first assignment.
  2. `SendMessage` to its agent ID resumed it ("Resuming agent"). It answered the continued assignment from its own history, without re-reading the file.
  3. Its transcript (`subagents/agent-<id>.jsonl`) shows every call before and after continuation as `message.model` `claude-haiku-5-5` with `effort` and `perTurnEffort` `low`.
  4. The documented jq command printed `{"model":["claude-haiku-5-5"],"effort":["low"],"final_context":51702,"compactions":[]}`.

  The "new thread with a summary" path remains the fallback when a worker is no longer reachable.
- **Concurrent appends from two runs** could interleave rows. → Each row is a single short append and carries its run ID. Accepted without locking.
- **Observed values depend on the transcript format.** The subagent transcript location and compaction entry are documented; field names such as `message.model` were observed, not documented. → Use them when readable, record `unknown` otherwise.
- **The cost figures are input-side estimates from one run.** → The ledger gathers real per-workstream data for later tuning.
- **"A few calls" is a judgment call.** → The logged reasons give the data to tighten the delegation rule.

## Migration Plan

1. Archive `add-claude-code-orchestration` (done 2026-10-16). This change removes or modifies requirements it added and edits the same guidance files.
2. Update the guidance:
   - the coordinator, for policy;
   - both host references, for mechanics;
   - `subagents/routing/usage.md`, for resolving once per workstream;
   - the worker definition text, so workers accept continued assignments with restated ownership.
3. Update the assertions in `tests/test_orchestration_guidance.py` and reinstall both hosts with the existing installers.
4. Run one live check that `SendMessage` continues a finished background Claude worker on its original model and effort (done 2026-10-16; see Risks).
5. Use the next real feature run as the trial, and compare its ledger rows with NA-358.

**Rollback:** revert the guidance files and reinstall. Existing daily logs are untouched; the ledger file can be kept or deleted.

## Open Questions

- Whether Codex idle workers survive into a resumed Codex session. Only the resumed-session path depends on this, and it already falls back to a new thread with a summary.
