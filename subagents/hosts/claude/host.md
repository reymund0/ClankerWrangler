# Claude Code Host Reference

Loaded by the coordinator for Claude-led runs, alongside `routing/host.json`
(`host: claude`, preference file `orchestration-routing-claude.json`, external review
`codex-review` through `scripts/codex_cross_review.py`). It holds the Claude-specific
procedure; the coordinator and specialist guidance are shared with the Codex host.
Keep the user's parent model and effort. The parent runs the coordinator; workers
and the external reviewer never do.

## Native dispatch

Use the Agent tool. Start every worker with `subagent_type: clanker-orchestration-worker`,
the generic worker installed at `<claude-root>/agents/clanker-orchestration-worker.md`.
The worker's definition sets no model or effort and disallows the Agent tool, so it
cannot start further agents; it returns any need to delegate to the parent as a blocker
or recommendation. Pass the resolver's `model` and `effort` as the Agent call's `model`
and `effort` arguments for that assignment, always explicitly. Do not rely on the
parent's model, the worker definition, or an environment default to select them.

The worker gets role guidance from the absolute instruction path in the handoff, exactly
as native Codex workers do; the generic definition only carries the worker boundaries.
Prefer a focused assignment. Requested settings are not proof of observed settings.

## Capability evidence

Native capability evidence is the model and effort options the active Agent tool
advertises for a per-call selection. Transcribe them into `capabilities` with
`provider: claude`, a `source` naming the Agent tool description, and a `models` map of
each advertised model value to its advertised efforts. Models are the aliases the tool
lists (for example `sonnet`, `opus`, `haiku`, `fable`) and efforts are its accepted levels
(`low`, `medium`, `high`, `xhigh`, `max`). Transcribe exactly what the tool lists.

An exact model ID in a route, such as `claude-sonnet-5-5`, is dispatchable only if the
tool advertises that exact string with the requested effort. Never translate an exact ID
to an alias, never pick a nearby model, and never lower or raise the effort: a blocked
route stays blocked and is reported with its requested pair. The saved catalog and the
CLI's model listing are guidance, not proof of per-call availability.

## Route-replacing settings

Before the first Claude-native dispatch of a run, and again after any settings reload,
check for settings that would replace the requested model or effort. Report only the
setting names, never values or secrets:

- `CLAUDE_CODE_SUBAGENT_MODEL` together with `CLAUDE_CODE_SUBAGENT_MODEL_FORCE`. A plain
  `CLAUDE_CODE_SUBAGENT_MODEL` does not replace an explicit per-call model; note it as
  context, not as an override.
- `CLAUDE_CODE_EFFORT_LEVEL`.
- An `agent.spawn` hook that can rewrite the request.

Look in the process environment and in the `env` entries and hooks of the user, project,
local, and managed Claude settings the session reports. Put each observed replacing
setting in the request's `overrides` list. Any entry blocks that dispatch: report the
setting by name and do not claim the requested settings were used.

## Worker definition shadowing

Before the first Claude-native dispatch of a run, and again after any reload, check every
definition that could shadow the worker by name:

- `.claude/agents/clanker-orchestration-worker.md` in the working directory and each
  parent directory up to the repository root.
- Any `--agents` or managed definition the session reports with that name.

If any same-name definition is not byte-identical to the installed
`<claude-root>/agents/clanker-orchestration-worker.md`, block Claude-native dispatch,
name the shadowing source, and do not rely on its tools or settings. If the installed
definition itself is absent, block Claude-native dispatch too: report the missing file and
that the installer must be run, and do not substitute another agent type. When running
from the source checkout (the user named the host), compare any project, `--agents`, or
managed definition against `subagents/claude/clanker-orchestration-worker.md` instead.
If a worker does not acknowledge the generic worker boundaries, report that as possible
shadowing.

## Concurrency and worker reuse

Limit concurrent assignments to three, or the runtime's lower limit, counting any
external review; run at most one external review per run at a time. Start independent
workers in the same turn. After a capacity rejection, do not repeat the same spawn until
capacity changes, and never count the rejected assignment as running.

The coordinator decides when a workstream's thread continues. To continue one, find the
worker with `ListAgents` and send the continued assignment with `SendMessage` to the
name or ID it lists; do not start a new Agent call for it. The continued worker keeps the
model and effort it was started with, so the Agent call that started it is the
workstream's only model and effort selection. If `ListAgents` no longer lists the worker
or `SendMessage` cannot reach it, start a new worker on the workstream's route with a
parent-written summary, as the coordinator describes.

## Observed settings

The parent receives the worker's text result, not its observed model or effort. Record
observed model and effort as unknown unless the runtime reports them for that worker;
never copy the request or a worker's self-description into observed fields. Where subagent
transcripts expose a model field, live acceptance may record it as evidence for that
worker only.

For a workstream's retire row, read the observed values from the worker's transcript,
`~/.claude/projects/<project>/<session-id>/subagents/agent-<id>.jsonl`:

```text
jq -sc '[.[] | select(.type == "assistant")] as $a | {model: ([$a[].message.model] | unique), effort: ([$a[].effort | select(.)] | unique), final_context: ($a[-1].message.usage | .input_tokens + .cache_read_input_tokens + .cache_creation_input_tokens), compactions: [.[] | select(.subtype == "compact_boundary") | .compactMetadata.preTokens]}' <transcript>
```

It prints the models and efforts recorded on the worker's calls, the last call's context
size in tokens, and the context size before each compaction. These fields are observed,
not documented; if the transcript is missing or a field is absent, record `unknown`.

## External reviewer: Codex CLI

External cross-review under this host uses the Codex CLI through
`scripts/codex_cross_review.py`; it never uses native Claude workers and does not need
the Agent tool. Resolve the packet's `codex-review` route through the coordinator run
snapshot and dispatch procedure in `routing/usage.md`, and pass the resolved model and
effort explicitly; the launcher has no default for either. Reassess remaining risk for
each recheck.

Prerequisites, all checked by the launcher before any model call:

- An installed Codex CLI logged in with ChatGPT. The launcher never logs in, switches
  billing, or edits persistent Codex settings; if it blocks, report the prerequisite
  and let the user act.
- No `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `CODEX_API_KEY`, alternate model provider, or
  stored API key in the effective configuration. Report names only.
- The exact model and effort advertised by the CLI's local model metadata.

Run `scripts/codex_cross_review.py` as a background command (the Bash tool's
`run_in_background`) and collect its receipt when it completes. Never run it in the
foreground: foreground commands time out after 2 minutes by default (10 minutes at most),
while a review may run for the launcher's 2700-second default.

The review runs read-only with an ephemeral session and no nested agents. Normal CLI and
managed permissions apply; do not add approval or sandbox bypass options. Persistent
Codex settings stay unchanged and unreported effective settings stay unknown.
