# Codex Host Reference

Loaded by the coordinator for Codex-led runs, alongside `routing/host.json`
(`host: codex`, preference file `orchestration-routing.json`, external review
`claude-review` through `scripts/claude_cross_review.py`). It holds the Codex-specific
procedure; the coordinator and specialist guidance are shared with the Claude host.

## Native dispatch

Use native Codex collaboration tools. Do not substitute a local Codex CLI or custom
agent framework when native delegation is unavailable.

Use the returned `model` and `effort` as the native tool's model and reasoning-effort
arguments. Prefer an empty history fork with a focused assignment; a bounded history
is allowed when needed. A full-history fork inherits parent settings and must not be
used to select worker settings. Requested settings are not proof of observed settings.

## Capability evidence

Native capability evidence comes from the active collaboration tool, not the saved
model catalog. Transcribe the advertised model and reasoning-effort combinations into
`capabilities` with `provider: codex`, a `source` naming the tool description, and a
`models` map of model to supported efforts. Supply only what the tool actually lists;
do not extrapolate from the catalog or from a model's name.

## Capacity and worker reuse

Limit concurrent assignments to three, or the runtime's lower limit, counting Claude
review; run at most one Claude review per run at a time.

The coordinator decides when a workstream's thread continues. To continue one, send the
continued assignment to the workstream's idle worker through the collaboration tools; it
keeps the model and effort it was started with. If that worker is no longer available,
start a new worker on the workstream's route with a parent-written summary, as the
coordinator describes. After a capacity rejection, do not repeat the same spawn until
capacity changes, and never count the rejected assignment as running.

## Observed settings

Record observed worker model and effort only when the runtime reports them; otherwise
record them as unknown. Never copy requested settings into the observed fields.

## External reviewer: Claude Code

External cross-review under this host uses the Claude Code CLI through
`scripts/claude_cross_review.py`. The launcher requires an installed Claude Code CLI
and confirmed subscription login.

Model selection is independent of the Codex parent and native worker defaults. Resolve
the packet's `claude-review` route using the coordinator run snapshot and dispatch
procedure in `routing/usage.md`; reassess remaining risk for each recheck. Pass the
resolved model and effort explicitly. Keep persistent Claude settings unchanged and
unknown effective settings unknown. Do not silently switch to API billing, install
software, edit persistent configuration, or initiate login. If preflight blocks, report
the specific prerequisite.

The launcher checks subscription authentication and invocation capabilities. Normal CLI
and managed permissions apply. Do not add permission-bypass flags or send a resume
argument by default; each initial review forms its own judgment.
