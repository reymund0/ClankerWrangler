# Proposal

## Why

Orchestration Nation supports only Codex as the orchestration host. Claude Code participates only through the external cross-review launcher, and installing the same coordinator bundle into Claude does not make Claude-led orchestration work. Users who lead from Claude Code (Opus orchestrating, Sonnet planning and reviewing, Haiku implementing) need the same routing, ownership, evidence and review contracts, with Codex as the independent reviewer, and without regressing the existing Codex-led workflow or its saved preferences.

## What Changes

- Add an explicit **orchestration host** (`codex` or `claude`), distinct from model **provider** and from **native** versus **external** execution. Native workers always use the host's provider. External cross-review uses the other provider through a guarded CLI launcher.
- Keep the Codex-led workflow and its preference file `~/.clanker/orchestration-routing.json` unchanged in path, contents, precedence, defaults and worker contracts. Add a separate Claude-led preference file `~/.clanker/orchestration-routing-claude.json` that uses the same schema 1 and the same deterministic resolver.
- **BREAKING**: Advance routing policy from version 6 to 7. The bundled policy defines per-host interaction catalogs and defaults while sharing roles, models and effort orders. Bundled Adaptive profiles are host-scoped. Snapshots, effective configuration and route decisions record `host`, plus `provider` and `execution` for each route. Snapshot creation defaults to the Codex host, so existing Codex callers keep working. Policy-6 snapshots are rejected with the existing new-run guidance.
- Claude-led bundled defaults: Sonnet for planning, native review and visual review; Haiku for implementation and testing; `codex-review` uses `gpt-6.1-sol`. All of them use Adaptive effort. Model aliases and exact IDs remain subject to runtime capability evidence.
- Claude-native dispatch requires the model/effort pair advertised by the active Claude Agent tool. Environment or hook overrides that would replace the requested route (for example `CLAUDE_CODE_SUBAGENT_MODEL`, `CLAUDE_CODE_EFFORT_LEVEL`, `agent.spawn` hooks) block it with an explicit limitation. Requested and observed settings stay separate; unknown observed settings remain unknown.
- Add a Codex cross-review launcher for plan and implementation reviews. It reuses the existing packet, Git evidence, coverage, findings, reconciliation, timeout, diagnostics and process-containment machinery, moved into a shared `cross_review_core.py`, with the Claude and Codex launchers as thin reviewer adapters. It invokes `codex exec` with an explicit model, a per-invocation effort, a read-only sandbox, ephemeral sessions and a structured output schema. It never logs in, switches billing, edits persistent Codex settings or bypasses approvals.
- Make the coordinator body harness-neutral. Each installer deploys its harness's `references/host.md` (native dispatch, capability evidence, reviewer prerequisites) and `routing/host.json` (host, preference path, external-review interaction and launcher). Harness awareness is confined to that deployed configuration.
- Replace `clanker-claude-cross-review.md` with one shared `clanker-cross-review.md` contract used by both reviewers. Installers back up the old installed reference with the existing retirement handling.
- Install one generic Claude agent definition (`clanker-orchestration-worker`) into the Claude agent root. It carries worker boundaries, disallows the Agent tool so workers cannot spawn further subagents, and sets no model or effort. Both installers keep the existing bundle, repeat-install, preference and link protections, and gain collision-safe handling for that definition.
- Add an orchestration-host selector to the routing editor. Each host has its own preference file, revision, lock and draft. Preview, save and effective-route display are host-scoped and use the same resolver as dispatch.
- Fix Claude model discovery, which currently rejects the CLI's initialize response because a new startup notification precedes it. The Claude-led editor depends on this discovery.
- Record host, provider and execution kind in run-log routing evidence and external review reports. Every dispatch and review entry gets a readable line with the requested model and reasoning level and the observed values (or unknown). The closing entry summarizes each worker assignment's route and whether it was accepted first pass, revised, rerouted or blocked.

## Capabilities

### New Capabilities

- `codex-cross-review`: Independent Codex CLI plan and implementation review under a Claude Code orchestrator, with explicit scoped evidence, ChatGPT-login preflight, explicit model/effort, structured findings and honest completion status.

### Modified Capabilities

- `development-orchestration`: Support Codex and Claude Code as orchestration hosts with host-specific native dispatch, shared specialist guidance, host-matched external review, and installation of the generic Claude worker definition.
- `orchestration-routing-policy`: Host-scoped preference sources and defaults, host/provider/execution identity, Claude-native capability gating, and policy-7 snapshot compatibility.
- `orchestration-routing-editor`: Explicit host selection with isolated host-specific load, preview and save.
- `orchestration-run-log`: Record host, provider and execution kind, plus readable requested and observed model and reasoning settings, in routing and review evidence; summarize each assignment's first-pass route outcome.
- `claude-cross-review`: Remain the external reviewer for Codex-led runs; replace the "unsupported orchestration host" behavior with host-matched reviewer selection, and share packet/report machinery with Codex review.
- `local-model-discovery`: Tolerate CLI startup notifications before the metadata response, and present native choices for the selected host.

## Impact

- Code: `subagents/scripts/routing_policy.py`, `subagents/routing/policy.json`, `subagents/scripts/claude_cross_review.py` (reduced to the Claude adapter), new `subagents/scripts/cross_review_core.py` and `subagents/scripts/codex_cross_review.py`, `routing-editor/scripts/routing_editor.py`, `routing-editor/scripts/model_discovery.py`, the editor frontend (`src/`), `routing-editor/public/compatibility.json` and the Node launcher policy constant, `wrangle.sh` and `wrangle.ps1`.
- Guidance: `subagents/clanker-orchestration-nation.md`, new `subagents/hosts/{codex,claude}/host.md` and `host.json`, `subagents/clanker-cross-review.md` (replacing `clanker-claude-cross-review.md`), a new Claude worker definition source, `subagents/routing/usage.md`, and the README/install guidance. Specialist role files stay provider-neutral and unchanged except where they name Codex as the only host.
- Tests: focused additions to `tests/` and `routing-editor/tests/` and frontend vitest suites, using temporary configuration and installation roots.
- Compatibility: existing Codex preference bytes are preserved. A policy-7 helper and matching editor assets must be installed together, and new runs need fresh snapshots. Claude-led runs require Claude Code with Agent-tool support. Codex review requires the Codex CLI with ChatGPT login.
- No new dependencies, agent teams, daemons or custom agent frameworks.
- This proposal authorizes planning only. It does not implement the change, install into real agent roots, modify saved preferences, change authentication, or archive the retirement change.
