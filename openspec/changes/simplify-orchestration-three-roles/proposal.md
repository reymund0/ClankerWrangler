# Proposal

## Why

Orchestration Nation grew to ten specialist roles, per-role routing, a routing editor, and a narrative run log, and in practice it costs more than it returns. Extra subagents step on each other, many handoffs are too small to be worth their overhead, and the run ledger shows that the specialist labels mostly chose a checklist while review caught the defects. Published experience points the same way: coding works best with one writer, and extra agents help when they add review and judgment rather than more hands. This change rebuilds the Claude and Codex implementations from scratch around three roles.

## What Changes

- **BREAKING** Replace the ten-role specialist catalog with three subagent roles: **Implementor** (the only code writer), **Reviewer** (read-only), and **Functional Review** (read-only, exercises the running app). The orchestrator plans, makes small fixes, owns OpenSpec state, and integrates.
- **BREAKING** Delete the retired specialist profiles (architect, backend, data, DevOps, performance, QA, test, UI developer, UI/UX reviewer), the generic orchestration worker, `skills/legacy/`, and their tests outright. Nothing is archived or migrated.
- Split work into two chats: a design chat (`clanker-design-discussion` → OpenSpec artifacts → plan review) and an implementation chat (`clanker-orchestration-nation`, which requires a finalized change).
- Add a dual review at three gates (plan, code, refactor). The native Reviewer and an external cross-review run in parallel over the same scope; the calling chat consolidates them and sorts each finding into accept, user decision, or reject. The plan and code gates allow at most two rounds each and the refactor gate one round. Each Functional Review fix cycle gets a fresh two-round code gate, with at most two cycles per run; after any limit the orchestrator stops and reports to the user.
- The orchestrator does small work itself, recommends against orchestration when the whole job is small, and ends by handing the thread to the user without committing or opening a pull request.
- **BREAKING** Replace the routing policy, resolver, snapshots, Adaptive effort profiles, routing editor, and model discovery with a single hand-edited routes file per host that maps each role to a model and reasoning effort. No migration for existing preference files.
- **BREAKING** Rewrite the cross-review launcher from scratch with one core and two provider adapters (Codex CLI for Claude-hosted runs, Claude Code CLI for Codex-hosted runs). The handoff names the gate; the launcher takes no phase and the reviewer CLI enforces the output schema.
- **BREAKING** Replace the narrative run log and the event ledger with an append-only per-run event log and two CSV tables built from it when the run ends: `runs.csv` (one row per run, including the model used for each role) and `findings.csv` (one row per finding).
- The orchestrator implements only a finalized change: `tasks.md` exists. Refactor proposals are shown at handover as a table, not implemented.
- Implement the Claude host first; the Codex host follows in the same change as its final task group.

## Capabilities

### New Capabilities

- `dual-review`: Parallel native and external review at the plan, code, and refactor gates, with orchestrator consolidation, finding triage, user decisions, and round limits.
- `cross-review`: The external cross-review launcher: provider adapters, preflight, read-only review of the scope named in the caller's handoff, structured findings, and honest status.
- `development-orchestration`: The three roles, the two-chat workflow, single-writer implementation, the small-work rule, Functional Review, and handover.
- `orchestration-routing-policy`: One hand-edited routes file per host.
- `orchestration-run-log`: The append-only run log and the `runs.csv` and `findings.csv` tables.

### Modified Capabilities

None. The old orchestration specs (`development-orchestration`, `orchestration-routing-policy`, `orchestration-run-log`, `orchestration-routing-editor`, `local-model-discovery`, `codex-cross-review`, `claude-cross-review`) and every archived orchestration change were deleted from `openspec/` before implementation, so OpenSpec sees only this change's requirements. Git history keeps them.

## Impact

- `subagents/`: the coordinator is rewritten; nine specialist profiles, `clanker-cross-review.md`, `claude/clanker-orchestration-worker.md`, and the `routing/` policy and usage files are deleted. Three role instruction files and per-host routes files are added.
- `subagents/scripts/`: `routing_policy.py` is deleted; `cross_review_core.py`, `codex_cross_review.py`, and `claude_cross_review.py` are replaced by the rewritten launcher.
- `routing-editor/` is deleted, including its Node build.
- A new standalone skill, `clanker-dual-review`, owns the review procedure and the launcher, so the design and orchestration chats share it.
- `skills/clanker-design-discussion.md` gains the plan-review gate; `skills/clanker-refactor-review.md` and `skills/clanker-code-review.md` are used by the Reviewer at the refactor and code gates. `skills/legacy/` is deleted.
- `wrangle.sh` and `wrangle.ps1` install the new package for both hosts and remove previously installed Orchestration Nation files without backups.
- `skills/clanker-code-review.md` and `skills/clanker-refactor-review.md` gain a mode for a scope the calling chat supplies, with inline output. `clanker-design-discussion.md` loses its "Optional specialist references" section.
- `subagents/hosts/*/host.md` is rewritten and `host.json` is removed.
- The root `package.json`, `package-lock.json`, and the `.gitignore` routing-editor entries are removed.
- The README "Routing Editor" and "Orchestration Nation Hosts" sections are replaced, and the specialist wording in `global_rules.md` "Delegation and Coordination" is updated.
- `tests/`: routing, editor, guidance, reservation, Codex-compat, and launcher tests and their fixtures (`routing_codex_policy6`, `codex_doctor.json`, `codex_models.json`) are deleted; the old launcher tests serve only as a source of scenarios for the rewrite.
- Old tracked `.clanker/` logs and reviews in this repository are deleted. Existing user routing preferences and logs elsewhere are not read or migrated.
