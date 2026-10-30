# Claude Code Host Reference

How the orchestrator and `clanker-dual-review` dispatch on Claude Code. `host.json` names the
host (`claude`) and the cross-review provider (`codex`).

## Native dispatch

Start each role with the Agent tool and the installed agent definition:

| Role | `subagent_type` | Route |
|---|---|---|
| Implementor | `clanker-implementor` | `implementor` |
| Reviewer | `clanker-reviewer` | `reviewer` |
| Functional Review | `clanker-functional-review` | `functional` |

Pass the route's model and effort, as recorded in the run's start event, as the Agent call's
`model` and `effort` arguments, always explicitly. If the Agent tool does not accept the routed
model or effort, report that at run start and do not claim the setting.

The definitions live in `~/.claude/agents/`. Reviewer and Functional Review have no Edit, Write,
or NotebookEdit tools; none of the three can start other agents. If a definition is missing,
stop and tell the user to run the installer; do not substitute another agent type.

## Continuing the Implementor

Send follow-up fixes to the same Implementor with `SendMessage`, using the name or ID from
`ListAgents`. A continued thread keeps the model and effort it started with. If `ListAgents` no
longer lists it or `SendMessage` cannot reach it, start one new Implementor on the same route,
seeded with a summary of the work so far.

## Tokens and observed settings

- **Tokens:** each Agent completion reports `subagent_tokens` in its usage. Log that number as
  the role's `usage` tokens.
- **Observed model:** the parent does not see a subagent's model. To record it, read the
  subagent transcript, `~/.claude/projects/<project>/<session-id>/subagents/agent-<id>.jsonl`:

  ```bash
  jq -r 'select(.type == "assistant") | .message.model' <transcript> | sort -u
  ```

  Log the model it prints. If the transcript or field is missing, leave the model out of the
  usage event; `runs.csv` then shows the routed value with `(req)`. Never copy the request or a
  subagent's self-description into observed fields.

## External reviewer: Codex CLI

Cross-review runs the `clanker-dual-review` launcher with `--provider codex` as a background
Bash command (`run_in_background`), with the `cross-review` route's model and effort. You are
notified when it exits; read its `report.json` then. The Codex CLI must be installed and logged
in; the launcher never logs in for you.
