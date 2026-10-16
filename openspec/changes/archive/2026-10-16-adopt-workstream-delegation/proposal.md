# Proposal

## Why

The first Claude-hosted run (NA-358, run `20261015T090642-0700-d8cc5366`) started a new worker for every assignment: seven threads, two of which did 2–3 minutes of work. The Claude host reference says "start a new worker" every time, which contradicts the shared rule to prefer idle-worker reuse. The parent also ran 45 minutes of browser QA itself, which cost about $42 of the run's roughly $61 in input tokens. The run log made analysis hard: its timestamps were estimated, its outcome labels were ambiguous, and its closing route-outcome table could not capture QA that continued after "completion". Both hosts need one delegation model that reuses context where it helps and keeps the orchestrator's own context small.

## What Changes

- **Workstreams.** Build work is grouped by code area. Each workstream has one native thread, a lead role, and optional extra role checklists. Follow-ups in that area, such as review fixes or problems the parent finds, go back to the same thread.
- **Boundaries.** Work across a stack boundary (for example API and UI) is split into separate workstreams only when the parent can write the contract between them up front and both sides are substantial. Otherwise one workstream carries both checklists. No full-stack role is added.
- **Route at thread start.** A workstream's route is resolved once, from its lead role and the hardest tier expected in its area. Continued threads keep that route, and the parent does not change it on its own. No routing-policy or resolver change.
- **Delegation threshold.** The parent keeps only fixes it has already diagnosed that take a few calls, plus its own git, OpenSpec, and log work, and logs a reason. Everything else is delegated.
- **Retirement.** A thread retires when its work is parent-verified. Unfinished work that is abandoned, or left when a run ends blocked or interrupted, retires as `blocked`. Compaction is left to the host default and recorded when it happens.
- **Reviewer rechecks.** A native reviewer performs its own single recheck in the same thread. Its brief has the finding IDs, the fix diff, and a check for regressions in the changed lines. A fresh reviewer is used when the spec or design changed or the scope grew. External cross-review is unchanged.
- **Lean orchestrator.** Browser QA and long acceptance work run in a worker that owns the browser state, not in the parent, unless the user directs otherwise.
- **Run log.** Timestamps come from the host clock at write time. A new append-only ledger, `.clanker/orchestration-ledger.csv`, gets one row per event. Workstream outcomes are recorded on each thread's retire row, which **replaces** the closing route-outcome table added by `add-claude-code-orchestration`.
- **Host references describe mechanics only.** Claude continues a thread with `SendMessage`; Codex reuses an idle worker. This removes the Claude host's "always start a new worker" rule.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-orchestration`: changes and adds requirements for:
  - the delegation threshold;
  - workstream threads, their boundaries, route, and retirement;
  - reviewer recheck reuse;
  - keeping browser and long acceptance work out of the parent.

  It also revises capacity-aware dispatch and host-specific native dispatch to match.
- `orchestration-run-log`: adds clock-sourced timestamps, the CSV analysis ledger, and per-workstream outcomes, and removes the closing route-outcome requirement ("First-pass route outcome") they replace.

## Impact

- **Guidance:**
  - `subagents/clanker-orchestration-nation.md`
  - `subagents/hosts/claude/host.md`
  - `subagents/hosts/codex/host.md`
  - `subagents/routing/usage.md`
  - `subagents/claude/clanker-orchestration-worker.md`

  Installers deploy these unchanged; installed copies update on the next install.
- **Tests:** guidance assertions in `tests/test_orchestration_guidance.py`, which currently check for the route-outcome table.
- **No change to:**
  - the routing policy, resolver, or bundled defaults;
  - the cross-review launchers;
  - the routing editor;
  - installer behavior.
- **Sequencing:**
  - This change removes "First-pass route outcome" and modifies "Host-specific native dispatch". Both came from `add-claude-code-orchestration`, which also edited the same guidance files.
  - That change was archived on 2026-10-16 (`openspec/changes/archive/2026-10-16-add-claude-code-orchestration/`), so its requirements are now in the main specs.
- **Out of scope:**
  - the cross-review verdict fix;
  - a transcript helper script;
  - the Sonnet routing trial and any bundled-default change;
  - escalating a struggling workstream to a stronger route, by any mechanism.
