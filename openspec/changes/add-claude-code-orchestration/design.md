# Design

## Context

See proposal.md (Why). Facts verified on 2026-10-13 that shape the approach:

- `routing_policy.py` hard-codes five interactions, ending in `claude-review`. `_provider_for_interaction` returns `claude` only for `claude-review`, and snapshots contain exactly one `global` document. `policy.json` is policy 6, preference schema 1.
- The user's Codex preferences (`~/.clanker/orchestration-routing.json`) select `gpt-6.1-sol` for planning and review and `gpt-6-luna` Adaptive for implementation, with custom profiles. Those IDs are absent from the bundled catalog and accepted as exact IDs.
- Both installers copy one identical bundle into `~/.claude/skills` and `~/.codex/skills`. Nothing manages `~/.claude/agents`, and nothing writes `~/.clanker`.
- The Claude Code Agent tool accepts a per-call `model` limited to the aliases `sonnet`, `opus`, `haiku` and `fable`, and an `effort` (low–max). Agent-definition frontmatter accepts `model`, including full IDs and `inherit`, plus `effort`, `tools` and `disallowedTools`. Model precedence is per-call, then frontmatter, then `CLAUDE_CODE_SUBAGENT_MODEL`, then the parent model. `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1`, `CLAUDE_CODE_EFFORT_LEVEL` and `agent.spawn` hooks can replace the request. Subagents may nest up to three levels by default. The parent receives the subagent's text result, not its observed model.
- Claude CLI initialize metadata reports, per alias, `resolvedModel` and `supportedEffortLevels` (sonnet and haiku both report low–max). Discovery currently fails because a `system/ui_invalidate` message precedes the response.
- Codex CLI 0.162.1: `codex exec` supports `-m`, `-c key=value` (per invocation), `-s read-only`, `--ephemeral`, `--output-schema`, `--json`, `-o`, `-C` and `--disable <feature>`. `codex review` supports only `--uncommitted`, `--base` or `--commit` scoping with free-text instructions, with no schema and no plan mode. `codex debug models` and `codex app-server` `model/list` report exact models and efforts without a model call. `codex login status` prints `Logged in using ChatGPT`. The `multi_agent` feature is stable and enabled by default.
- `claude_cross_review.py` (about 1,750 lines) is provider-specific only in executable resolution, `preflight`, `configured_review_model`, command construction and envelope parsing inside `invoke`, and some wording. Manifest validation, Git evidence, packet capture, readiness, report writing, freshness, diagnostics, progress and process containment are provider-neutral. `model_discovery.py` already imports its containment helpers.
- The unarchived `retire-unused-specialist-profiles` change modifies several of the same requirements. It will be archived first by separate user request, so this change's deltas are written against the resulting main specs.

## Goals / Non-Goals

**Goals:**
- Codex-led behavior and decisions stay identical for the same inputs, apart from added identity fields.
- Host, provider and execution identity are explicit everywhere a route is resolved, previewed, dispatched, logged or reviewed.
- Both external reviewers share one evidence and report contract.

**Non-Goals:**
- Running both hosts within one run, or switching host mid-run.
- Agent teams, daemons, a custom agent framework or new dependencies.
- Automatic model fallback, effort clamping, or importing one host's preferences into the other.
- Using `codex review` or Claude `ultrareview`.
- Certifying rendered UI or live behavior through static review.

## Decisions

### D1. Three orthogonal identities with one derivation rule

`host ∈ {codex, claude}` is fixed per run snapshot. Each interaction has `execution ∈ {native, external}`. `provider` is derived: native means the host's provider, external means the other provider. The resolver validates models against the derived provider instead of the interaction name. Capability evidence is checked against `(provider, execution)`, so a Claude-native worker is never routed through launcher preflight, and Codex external review never requires Codex collaboration tools.

*Alternative:* a free provider field per interaction. Rejected because it allows configurations that cannot run, such as a Codex-native worker under a Claude host.

### D2. Separate preference files per host, one schema

The Codex host keeps reading `~/.clanker/orchestration-routing.json`. The Claude host reads `~/.clanker/orchestration-routing-claude.json`. Both use schema 1 with the same sparse fields. The external-review interaction ID differs by host: `claude-review` under Codex, `codex-review` under Claude. The resolver validates each document against its host's interaction set, so a Codex file containing `codex-review`, or a Claude file containing `claude-review`, is rejected at its field path. Adaptive profiles stay provider-keyed (`claude:sonnet`, `codex:gpt-6.1-sol`) in each file.

*Alternative:* host profiles in one file (schema 2). Rejected for three reasons. It would migrate the user's existing file. Saving either host would change one shared revision, so concurrent edits for different hosts would conflict. And every existing consumer would need a schema change. Accepted cost: profiles customized for both hosts are edited twice.

### D3. Policy 7 with per-host catalogs; installed host is the snapshot default

`policy.json` keeps shared `roles`, `models` and `effort_orders`. It replaces the flat `interactions` and `defaults.interactions` with `hosts.codex` and `hosts.claude`. Each host entry lists its interactions in order, with `execution`, `label` and `default_model`, plus its route defaults and bundled Adaptive profiles. Codex defaults and profiles are copied unchanged from policy 6. Bundled profiles are host-scoped because a shared `codex:gpt-6.1-sol` profile would change profile provenance and fixed-effort warnings for existing Codex-host routes (plan review P3).

Claude defaults are planning `sonnet`, implementation `haiku`, native-review `sonnet`, visual-review `sonnet` and codex-review `gpt-6.1-sol`, all Adaptive. The catalog adds `sonnet`, `haiku` and `gpt-6.1-sol`. Claude-host bundled profiles are `claude:sonnet`, `claude:haiku` and `claude:opus` at medium/high/high, matching the existing Claude profiles, and `codex:gpt-6.1-sol` at medium/high/xhigh, matching the existing Codex Sol profiles.

`snapshot` gains `--host`. Without it, the helper uses the `host` from the bundle's installed `routing/host.json` (D6). If that file is absent, as in the source checkout, it defaults to `codex`, so existing Codex callers keep working. An explicit `--host` that differs from an installed `host.json` is rejected rather than silently honored. The snapshot records `host`. The fingerprint covers it. `sources.global` names the host file actually read. Decisions add `host`, `provider` and `execution`. The effective configuration adds `host` and per-interaction `provider` and `execution`.

`POLICY_VERSION` becomes 7, and policy-6 snapshots are rejected with new-run guidance, following the existing convention. The editor's `compatibility.json` and the Node launcher constant become policy 7.

*Alternative:* keep policy 6 and add a sibling policy file for the Claude host. Rejected because it would split the deterministic resolver's source of truth and leave snapshots unable to state the host.

### D4. Claude-native capability gate

For a Claude host, capability evidence is the active Agent tool's advertised models and efforts, transcribed by the parent (provider `claude`, execution `native`). Dispatch is allowed only when the exact resolved model string is advertised with that effort. An exact ID such as `claude-sonnet-5-5` is therefore blocked unless the runtime advertises it for per-call use. It is never translated to an alias.

The request may include `overrides`: a list of observed route-replacing settings, such as `CLAUDE_CODE_SUBAGENT_MODEL` with `_FORCE`, `CLAUDE_CODE_EFFORT_LEVEL` or an `agent.spawn` hook. Any entry blocks dispatch with a limitation naming the setting; the resolver never guesses the substituted value. A plain `CLAUDE_CODE_SUBAGENT_MODEL` without `_FORCE` does not override an explicit per-call model, so it is reported as context, not as a block.

The host reference requires the parent to check these settings before the first dispatch and to record observed model and effort as unknown unless the runtime reports them. Live acceptance additionally checks subagent transcripts for a model field and records the result as evidence only where present.

### D5. One generic Claude worker definition

The installer writes `<claude-root>/agents/clanker-orchestration-worker.md`, generated from `subagents/claude/clanker-orchestration-worker.md`. Its frontmatter carries `name`, `description` ("Clanker Orchestration Nation assignments only…") and `disallowedTools: Agent`, with no `model` or `effort`. The body covers the worker boundaries: read the supplied instruction path first, stay within assigned ownership, do not delegate, write no shared log or OpenSpec state, and follow the reply contract.

Dispatch passes `subagent_type: clanker-orchestration-worker` with explicit `model` and `effort`. Before the first Claude-native dispatch, and again after any reload, the parent checks the definitions that could shadow the worker. Those are project `.claude/agents/clanker-orchestration-worker.md` files from the working directory up to the repository root, and any `--agents` or managed definition the session reports. A same-name definition that is not byte-identical to the installed one blocks Claude-native dispatch with the source named (plan review P5). Live acceptance includes a negative case with a temporary project shadow. Role guidance still comes from the handoff's absolute reference path, as for Codex workers.

On install, an existing file at that path is replaced only when it carries the installer's marker. Otherwise it is moved to `<claude-root>/backups/orchestration-nation/clanker-orchestration-worker[-N].md`. Link and type checks match the existing bundle protections. The Codex root gets no agent definition.

*Alternatives:* ten per-role definitions, rejected for auto-invocation and shadowing risk and a larger install surface with little added value; no definition, rejected because recursion prevention would rest on prose alone.

### D6. Harness-neutral coordinator; installers deploy the host configuration

`clanker-orchestration-nation.md` keeps every host-neutral rule: scope, role catalog, handoff, readiness, communication, integration and logging. It never names a harness. It drops the "Claude Code is supported only through the external cross-review launcher" sentence. It tells the parent to read `references/host.md` and `routing/host.json` before resolving any route, and to stop and report the missing prerequisite if either is absent. Installed bundles are self-describing. Running the coordinator directly from the source checkout, where host files live at `subagents/hosts/<host>/`, requires the user to name the host. The parent then passes `--host` explicitly and never infers it.

Each installer deploys its own harness's files from `subagents/hosts/<host>/`. The Codex root gets the `codex` files, the Claude root gets the `claude` files.
- `host.md` → `references/host.md`. It covers native dispatch mechanics (the tool name, how model and effort are passed, history forking), how to transcribe capability evidence, settings and override checks, capacity limits, the reviewer's prerequisites, and recording of observed settings. `codex/host.md` holds the text moved from the current coordinator, verbatim where possible, so the Codex procedure does not change in meaning.
- `host.json` → `routing/host.json`, a fixed-schema document: `{"schema_version": 1, "host": "codex", "preferences_file": "orchestration-routing.json", "external_review": {"interaction": "claude-review", "launcher": "scripts/claude_cross_review.py"}}`. `preferences_file` is a bare file name resolved under `<home>/.clanker/`. The Claude version names `orchestration-routing-claude.json`, `codex-review` and `scripts/codex_cross_review.py`. `routing_policy.py` validates `host.json` strictly. The host it names must exist in the policy, and its external-review interaction must match that host's catalog.

This keeps harness awareness to three places, all deployed configuration: preference loading, native dispatch, and the selected external reviewer.

*Alternatives:* a coordinator that asks the model to pick `host-codex.md` or `host-claude.md` for its runtime, rejected because it relies on the model identifying its harness; two full coordinators, rejected because about 200 lines would be duplicated and drift-prone.

### D6a. One cross-review reference

Merge the review contract into a single `subagents/clanker-cross-review.md`. It covers selection, packet preparation, manifest, plan and implementation criteria, run and collect, findings and reconciliation, recheck limits, and write coordination. It refers to "the external reviewer" and to the launcher named in `routing/host.json`. Reviewer-specific prerequisites (Claude subscription login and settings checks; Codex ChatGPT login and override checks) live in the corresponding `host.md`.

`clanker-claude-cross-review.md` is retired. Both installers move an installed `references/clanker-claude-cross-review.md` into `backups/orchestration-nation/` using the existing retirement preflight, naming and failure rules. Manifests that list the old reference path in `guidance_paths` keep working wherever the file still exists, because guidance is any readable explicit path. After the backup, such a manifest fails preparation with the missing path and the replacement `references/clanker-cross-review.md` named. This is the one documented manifest migration (plan review P6). Manifests are per-review parent artifacts, so it affects only re-preparation of pre-upgrade manifests.

### D7. Shared cross-review core with thin reviewer adapters

Move the provider-neutral machinery out of `claude_cross_review.py` into a new `subagents/scripts/cross_review_core.py`. That covers manifest validation, Git evidence, packet capture, readiness, prompt and output-schema building, model-report validation, report writing, freshness (`--check-current`), legacy write checks, diagnostics, progress logging and process containment. The core defines a small reviewer interface: resolve the executable, run preflight, build the command, and parse the envelope into a validated report plus observed settings. It also defines a shared `main(adapter)` that owns argument parsing, the stage sequence and the report.

`claude_cross_review.py` becomes the Claude adapter. It keeps its file name, CLI flags, `opus` default, preflight checks, report shape and exit codes, and re-exports the names that existing callers import. Those callers are `model_discovery.py`, which uses `start_review_process` and `ReviewError`, and the existing tests. Existing tests therefore pass without edits, apart from patch targets that move to the core module.

`codex_cross_review.py` is the Codex adapter (D8). Reports add `reviewer: {provider, execution: "external", host, executable, version}`, keeping existing fields. `host` is the other provider, because an external reviewer is never the host's provider (plan review P7). Each adapter owns its output schema and normalizes its envelope into the shared validator's input. The Codex schema is strict: every property is required, optional lists are required arrays that may be empty, and there are no nulls. The shared validator stays unchanged (plan review P4). Report directories stay `<output>/<run_id>/<phase>-<n>`, so Claude and Codex attempts in one run remain distinguishable. Cross-provider names in shared code are generalized; for example, `claude_running` progress fields are written as `reviewer_running`, while still reading the old name.

Both installers copy `cross_review_core.py` into the bundle's `scripts/` alongside the adapters.

*Alternative:* have the Codex adapter import `claude_cross_review.py` directly, leaving the code in place. That is less churn, but makes the Codex launcher depend on a Claude-named module and leaves provider-neutral code mixed with Claude specifics. Rejected at the owner's direction.

### D8. Codex invocation contract

```
codex exec --ephemeral -s read-only -C <repository> -m <model>
           -c model_reasoning_effort="<effort>" --disable multi_agent
           --output-schema <packet>/_clanker_packet/review-schema.json
           -o <attempt>/last-message.json --json  < prompt
```

Preflight makes no model call. It checks, in order:

1. `--version`.
2. That `exec --help` lists every flag used.
3. That `codex doctor --json`, run with the same working directory, environment and `-c` arguments as the review, reports `stored auth mode` `chatgpt`, `stored API key` false, and `model provider` `openai`. Doctor reads the effective persistent, project and invocation configuration and redacts secrets. Any other value, a missing field or a failing check blocks (plan review P1).
4. That no `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `CODEX_API_KEY` or alternate provider override is present in the environment or in launcher-supplied `-c` arguments.
5. That `codex debug models` advertises the exact model and the requested effort; an unadvertised pair blocks.

Probe results (manual plan review, 2026-10-13, `gpt-6.1-sol`/high):
- The strict schema was accepted.
- The read-only sandbox read a file under the system temporary directory outside `-C`.
- No command required approval. A shell here-document failed because the sandbox denied its temporary-file write, which is a limitation, not a block.
- JSONL reported `thread.started` (thread id), `command_execution` and `agent_message` items, and `turn.completed` usage. It reported no model or effort field, so observed model and effort are recorded as unknown and usage as observed.
- With `multi_agent` disabled, no agent-spawn items appeared. The adapter fails the attempt on any item type that denotes collaboration or agent spawning, and records other unrecognized item types as limitations.

The packet stays in the launcher's existing owned temporary directory. Read roots are passed in the prompt as additional read-only context, not as `--add-dir`, because `--add-dir` grants write access.

The launcher never passes `--dangerously-*`, `--approve-for-me`, `--ignore-user-config` or login commands, and writes nothing to `$CODEX_HOME`. The JSONL stream supplies observed model and usage when present, and evidence of any spawned agent; observed spawning fails the attempt as it does for Claude. Effort is required and has no default. Model defaults to the resolved route only; the launcher has no implicit default.

*Alternative:* `codex review --base`. Rejected because it cannot review plans, accept a packet, return the required schema or cover selected untracked and external evidence.

### D9. Host-scoped editor

`PreferenceStore` maps `host → fixed path` (`--global-config-dir` still isolates both). API requests carry `host ∈ {codex, claude}`, and unknown values are rejected before any file access. `/api/config?host=` returns that host's document, revision, effective configuration and interaction catalog. `/api/save` validates against that host and locks only that file. `/api/preview` resolves through `snapshot_from_documents(..., host=)` and `resolve`.

The frontend adds a header host selector. Each host keeps its own draft and errors, so switching never discards or merges drafts. The selector shows unsaved-change counts per host. Matrix columns, the external-review row, the provider for model choices and specialist availability all come from the selected host's catalog instead of the hard-coded `claude-review` and `codex` filters. Run Wrangler remains host-independent.

### D10. Run log and review evidence

Run-start records the host and its preference source. Each dispatch and external-review block opens with a readable settings line, for example `Model: haiku · Reasoning: Adaptive/straightforward → medium · Observed: unknown`,. The values come from resolver JSON and launcher reports, never transcribed by hand. Both launchers write requested and observed model and effort into `report.json` and `summary.md`. Token usage is not a logged or reported field. The existing Claude `observed_settings.model_usage` block stays unchanged for compatibility, and because it is the source of the observed Claude model. Codex usage events remain only in the attempt's raw `events.jsonl` diagnostics.

The closing entry adds a per-assignment route-outcome table: assignment, role, requested model/effort/tier, and outcome (`first-pass`, `revised`, `rerouted` with the replacement route, or `blocked`). The parent decides outcomes from its own verification, not from worker readiness claims. Across runs, this shows whether a route such as Haiku implementation at a given tier gets work right the first time. Resolver JSON already carries host, provider and execution after D3, and is appended unchanged. External review entries link the reviewer-identified report. The closing summary keeps native review, external review and runtime/visual acceptance as separate evidence states.

## Risks / Trade-offs

- [Policy 7 breaks policy-6 snapshots and editor assets] → This is the established new-run convention. Installers ship matching assets, and the editor rejects mismatches with rebuild instructions.
- [Codex-led regression while generalizing the resolver] → A regression test resolves a fixture matrix of interaction × role × tier × flags against a copy of the user's real Codex preferences, using policy-6 and policy-7 code paths. It asserts identical model, effort, limitations and provenance apart from the added identity fields.
- [The Agent tool accepts only aliases, so exact Claude IDs cannot be dispatched per call] → The gate blocks with an explicit limitation, and the editor labels exact IDs as requiring runtime support. Pinning exact IDs through frontmatter is deferred.
- [Claude subagent observed model is not reported to the parent] → Record unknown. Live acceptance inspects transcripts and records what is or is not available, without inferring it.
- [Codex `--output-schema` may require strict schemas (all properties required, `additionalProperties: false`)] → The schema is written in strict form, with optional fields expressed as nullable. The manual plan-review probe verifies acceptance before implementation.
- [Read-only sandbox commands may be denied or need approval] → Denials are limitations. Required coverage determines completeness. No bypass flags are added.
- [`codex doctor --json` field labels may change between CLI versions] → Fail closed on missing or renamed fields, and cover the exact labels with fixture tests.
- [Global agent definition could shadow or overwrite a user agent] → Marker-checked replacement, backup of unmarked files, and a distinctive name. A project-level definition with the same name would win at runtime; the host reference requires the parent to report this if the worker's boundaries are not acknowledged.
- [Two preference files drift] → Intentional: each host's preferences are independent. The editor shows the active host and destination prominently.

## Migration Plan

1. The user archives `retire-unused-specialist-profiles` (separate request). Then this change's deltas are validated.
2. Install the complete bundle with both installers. The Codex preference file is untouched, and no Claude preference file is created; a missing file means bundled defaults.
3. Start new runs. Policy-6 snapshots are rejected.
4. Rollback: restore the previous bundle and matching editor assets, and remove `clanker-orchestration-worker.md` (or restore its backup). Preference files need no rollback. The Claude-host file is ignored by policy-6 helpers.

## Open Questions

- Resolved 2026-10-14 by live run `20261014T111646-0700-claude-1`: subagent transcripts record `message.model` (for example `claude-haiku-5-5` for a `haiku` request) and `effort`/`perTurnEffort`. The parent may record these as observed settings for that worker. They are not reported to the parent's tool result, so without transcript access observed values stay unknown.
