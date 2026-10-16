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

## Routing Editor

From the repo root, run `npm run dev` and open the printed local URL.

First time? You'll need Python 3.10+ and Node 20.19+ (or 22.12+), then:

```bash
npm --prefix routing-editor ci
npm run build
npm run dev
```

The launcher selects the newest runnable Python 3.10+ from unversioned and versioned executables on `PATH`, plus `/opt/homebrew/bin` and `/usr/local/bin` on macOS. To pin an installation, run `CLANKER_PYTHON=/absolute/path/to/python3 npm run dev`. An invalid override fails without falling back.

## Orchestration Nation Hosts

Orchestration Nation can be led from Codex or from Claude Code. Both installers put the same coordinator, specialist guidance, and shared cross-review reference into each agent, plus that agent's own host reference (`references/host.md`) and host configuration (`routing/host.json`). The coordinator reads those two files to learn its host, its preference file, how to dispatch native workers, and which external reviewer to use.

On either host the coordinator groups build work into workstreams by code area. Each workstream keeps one worker thread for its follow-ups, such as review fixes, at the route resolved when the thread started, and retires that thread once the parent has verified its work. Each run appends to the daily log `.clanker/YYYY-MM-DD-orchestration-nation.md` and adds one row per event to `.clanker/orchestration-ledger.csv` for spreadsheet analysis.

| Host | Native workers | External review | Preference file |
| --- | --- | --- | --- |
| Codex | Codex collaboration tools | Claude Code CLI (`scripts/claude_cross_review.py`) | `~/.clanker/orchestration-routing.json` |
| Claude Code | Agent tool with the `clanker-orchestration-worker` agent | Codex CLI (`scripts/codex_cross_review.py`) | `~/.clanker/orchestration-routing-claude.json` |

The two preference files use the same schema and are independent: neither host reads or changes the other's file, and the installers never write either one. A missing file means bundled defaults. Claude-led defaults are Sonnet for planning and reviews, Haiku for implementation, and `gpt-6.1-sol` for the Codex review, all Adaptive.

To lead from Claude Code you need Python 3.10+, Claude Code with Agent-tool support, and, for external review, the Codex CLI logged in with ChatGPT. The review launcher only checks that login: it never logs in, switches billing, uses API keys, or edits Codex settings, so use the official Codex login flow yourself first. `./wrangle.sh` (or `.\wrangle.ps1`) also installs the generic worker at `<claude-root>/agents/clanker-orchestration-worker.md`. If an unmanaged file already has that name, it is moved to `<claude-root>/backups/orchestration-nation/` before the worker is written. Codex gets no agent definition.

The routing editor opens with a host selector. Each host edits its own preference file with its own draft, and `--global-config-dir <temporary-directory>` redirects both files when you want to try it without touching real preferences. Routing policy 7 requires the installed helpers and editor build to match, and snapshots from policy 6 are rejected, so install the complete bundle and start new runs.

## Step 4

💰 PROFIT. 💰
