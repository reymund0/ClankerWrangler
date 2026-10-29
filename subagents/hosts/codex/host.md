# Codex Host Reference

How the orchestrator and `clanker-dual-review` dispatch on Codex. `host.json` names the host
(`codex`) and the cross-review provider (`claude`).

## Native dispatch

Use Codex's multi-agent tools. Start each role with `spawn_agent`, giving it:

- the assignment as the message, starting with the absolute path of the role file to read:
  `references/clanker-implementor.md` or `references/clanker-functional-review.md` in the installed
  `clanker-orchestration-nation` skill (`~/.codex/skills/clanker-orchestration-nation/`), or for
  the Reviewer only the path of the round's handoff file
- `model` and `reasoning_effort` from the role's route, as recorded in the run's start event,
  always explicitly; the routes file is the user's explicit model choice
- `fork_context: false`, so the subagent starts from the assignment instead of this chat's history

Codex checks each spawn: an unknown model or an effort the model does not support is rejected.
Report that rejection and stop; never retry on another model.

Limits on Codex:

- There are no per-role agent definitions or per-agent sandboxes, so Reviewer and Functional Review
  are read-only by their instructions only. Check `git status` after each read-only role returns
  and report any file it changed.
- Spawned agents can spawn their own agents; the role files forbid it.

## Continuing the Implementor

Send follow-up fixes to the same Implementor with `send_input` and its agent ID, then `wait_agent`
for the reply. If it was closed, `resume_agent` it first. If it cannot be resumed, start one new
Implementor on the same route, seeded with a summary from the run log. Close read-only agents with
`close_agent` once their reply is in; keep the Implementor open until handover.

## Tokens and observed settings

Codex returns a subagent's final answer, not its token usage or the model it ran on. Leave those
out of the usage events; `runs.csv` then shows the routed values with `(req)` and empty tokens.

## External reviewer: Claude Code CLI

Cross-review runs the `clanker-dual-review` launcher with `--provider claude` as a background
shell command, with the `cross-review` route's model and effort. The command needs network access
and write access to `~/.claude`, which Codex's default sandbox blocks, so run it with escalated
permissions (asking the user to approve if needed). Read its `report.json` when it exits.

The Claude Code CLI must be installed and logged in (`claude auth login`); the launcher never logs
in for you. The reviewer reads the role file and criteria from `~/.claude/skills`, so the Claude
package must be installed too. It runs with read tools and read-only git commands only, so it
cannot run tests; it reports that as a limitation.

## Confirmed tool parameters

Checked against Codex CLI 0.162.1 with the `multi_agent` feature on (the default) and
`multi_agent_v2` off. `spawn_agent` takes the message, `agent_type`, `fork_context`, `model`, and
`reasoning_effort`; follow-ups use `send_input`, `wait_agent`, `close_agent`, and `resume_agent`.
With `multi_agent_v2` on, follow-ups use `followup_task` and `send_message` instead, and spawns
take `task_name` and `fork_turns` (`"none"` in place of `fork_context: false`).
