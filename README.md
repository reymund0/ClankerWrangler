# ClankerWrangler

ClankerWrangler is a tiny home base for shared coding-agent rules and skills.

## Why ClankerWrangler?

I was getting tired of configuring all my different coding agents across my machines, so I decided to centralize them into one repo with a handy script. One set of rules, one skills folder, fewer tiny setup chores nibbling at my day.

## How To Run

**Windows** — Open an Administrator PowerShell window from this repo and run:

```powershell
.\wrangle.ps1
```

**Mac / Unix** — Open a terminal from this repo and run:

```bash
./wrangle.sh
```

The script wires the shared rules and skills into the supported agent config locations.

## Orchestration Nation

Work on a change happens in two chats:

1. **Design chat** (`clanker-design-discussion`): explore the approach, write the OpenSpec artifacts, then pass the plan gate through `clanker-dual-review`.
2. **Implementation chat** (`clanker-orchestration-nation`): implement the finalized change with one Implementor subagent, pass the code gate, run Functional Review against the running app when there is one, and finish with a refactor gate. It hands the thread back to you without committing.

The orchestrator delegates to three roles only: the **Implementor** (the only code writer), the **Reviewer** (read-only), and **Functional Review** (read-only toward source). At each gate the native Reviewer and an external cross-review from the other vendor's CLI run in parallel. The orchestrator then triages their findings and brings anything that would add a mechanism or isn't an obvious fix to you.

| Host | Native subagents | External review |
| --- | --- | --- |
| Claude Code | Agent tool with `clanker-implementor`, `clanker-reviewer`, `clanker-functional-review` | Codex CLI, logged in with ChatGPT |
| Codex | `spawn_agent` with the same three roles as custom agents in `~/.codex/agents/`; read-only roles are enforced by instructions only | Claude Code CLI, logged in with `claude auth login` |

Each subagent role's model and effort come from one hand-edited file per host, `<agent-root>/clanker/routes.jsonc` (for example `~/.claude/clanker/routes.jsonc`). The installer writes it only when it is missing and never overwrites your edits. The comments at its top hold the commands that list the models and efforts each CLI offers. The orchestrator itself runs on your session's model.

Each run appends events to `.clanker/runs/<run>.jsonl` in the project, which is replayed when a run resumes. When a run ends, it adds one row to `.clanker/runs.csv` and one row per finding to `.clanker/findings.csv`.

The review launcher only checks that the reviewer CLI is installed and logged in. It never logs in, switches billing, or changes the CLI's settings, so log in yourself first. Python 3.10+ is required.

## Step 4

💰 PROFIT. 💰
