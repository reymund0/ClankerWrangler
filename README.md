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

## Legacy Skills

Deprecated skills live in `skills/legacy/`. They are not installed, and both wrangle scripts delete any previously installed copy of them from each agent's skills folder on the next run.

## Orchestration Nation

After running the installer, start a Codex session with your chosen model and invoke:

```text
$clanker-orchestration-nation <your development task>
```

The skill selects specialists for the task: product, architecture, UX/UI design and
review, backend, data, UI development, QA, code/security review, documentation, DevOps, and
performance engineering. It requests GPT-5.6 Sol for planning and review and
GPT-5.6 Terra for implementation, choosing reasoning effort for each assignment.
It uses Codex's native subagent tools and reports unavailable models or tools;
this skill keeps your selected session model and effort as the orchestrator. Astra or
Fable are optional suggestions where available; choosing another parent model does
not require approval. Sol/Terra are worker defaults that you can also override.

The coordinator, twelve native specialist instruction files, and Claude cross-review
guidance live in the root-level `subagents/` directory. Each specialist keeps its own method, context, deliverables,
and verification. The coordinator passes each selected native specialist file to its subagent and
requires it to read that file before working. Claude receives an explicit review packet
through the supporting launcher.

Both wrangle installers package this as **one visible skill**, alongside your existing
standalone skills:

```text
<agent-root>/skills/clanker-orchestration-nation/
  SKILL.md
  scripts/
    claude_cross_review.py
  references/
    clanker-claude-cross-review.md
    clanker-backend-developer.md
    clanker-ui-ux-reviewer.md
    ...other specialist instruction files
```

The specialists are supporting Markdown files, so they do not create separate skill
menu entries. Codex UI metadata is generated only for the coordinator. The existing
`clanker-code-review` stays in `skills/` as a shared standalone workflow. If an earlier
installation created separate specialist skill folders, the installer moves those
folders, including custom content, to `<agent-root>/backups/orchestration-nation/`
with collision-safe names. It preserves unrelated skills and does not create native
custom-agent definitions or change model settings.

`clanker-ui-ux-reviewer` inspects the running application's visuals and user flows,
including responsive layouts, interaction states, and accessibility cues. Its findings
include observed evidence and untested areas; code inspection alone cannot pass a
visual review. For example:

```text
$clanker-orchestration-nation Review the UI at <application URL> using the UI/UX reviewer.
```

Skills supply reusable instructions; subagents are separate workers that use those
instructions. Native custom-agent profiles are another option:
[Codex uses TOML definitions](https://learn.chatgpt.com/docs/agent-configuration/subagents)
and [Claude Code uses Markdown definitions](https://code.claude.com/docs/en/sub-agents).
This bundle uses explicit instruction handoffs so Codex can select a different model
and reasoning level per worker assignment. **Codex is the supported orchestration host.**
Both clients receive the package for distribution consistency, but Claude-led orchestration
is not supported yet. Claude Code participates only as an external reviewer; the
Sol/Terra defaults apply to native Codex workers.

Meaningful changes use OpenSpec requirements, design, and tasks as the shared
plan. Existing planning and implementation boundaries still apply; small fixes
can follow a lightweight path. Initialize OpenSpec in the target project when
needed so its workflows are available there.

Routing decisions and results are appended to
`.clanker/YYYY-MM-DD-orchestration-nation.md` in the project being worked on. Each
run records selected roles, requested model/reasoning settings, brief reasons,
verification, and blockers. Multiple sessions on the same date preserve earlier
entries, and resumed runs keep their original log file.

## Claude Cross-Review

The Codex orchestrator requests an independent Claude Code review for substantial
plans before implementation and integrated features before completion. Typical triggers
are API/data contracts, consequential architecture, auth, migrations, deployment, and
performance risk. Small low-risk edits skip it by default. Explicit requests and opt-outs
prevail; planning-only work stays in planning. For example:

```text
$clanker-orchestration-nation Plan team invitations with OpenSpec and Claude cross-review. Planning only.
$clanker-orchestration-nation Implement team-invitations and cross-review the integrated result with Claude.
$clanker-orchestration-nation Fix this label; skip Claude cross-review.
```

Cross-review requires a Git checkout, Python 3.10+ (standard library only), and an installed Claude Code
CLI, and a subscription login. The wrangle installers package the helper; they do not
install Python/Claude or sign in. Run `claude` yourself to authenticate with your
subscription. Conflicting API keys/provider overrides are reported instead of silently
using API billing. The launcher accepts an absolute Claude executable path if PATH has
not refreshed. It checks the CLI capabilities needed for restricted execution.

Your selected Codex model remains the orchestrator. Claude cross-reviews default to
**Opus 5** (`claude-opus-5`), with an explicit per-review model override available.
This leaves your regular Claude Code model settings unchanged. Codex selects review effort from scope and risk: **Low** for
explicitly requested mechanical checks, **Medium** for routine bounded plans/code,
and **High** for complex architecture, cross-layer contracts, security, data,
deployment/recovery, or complex performance reviews. Rechecks reassess remaining
risk; they do not automatically use a lower effort. Codex logs the selection and reason.
Specify a Claude model/effort in your request to override those settings. Unsupported settings and unknown
authentication block the review rather than trigger fallback.

Claude uses the same specialist instructions as native workers: Codex selects the
relevant roles and explicitly supplies their files, such as architect and data engineer
for a data-contract review. Their guidance shapes the critique while Claude remains
read-only; live visual inspection and actual test execution stay with native workers.

Claude receives a temporary snapshot of selected files, requirements, and test evidence,
with read/search tools only. Packets are capped at 8 MB including metadata, with
1 MB per file or diff; narrow oversized scope. Sensitive names and recognizable
credential content are excluded, and Codex must inspect selected scope for other secrets.
It cannot edit the application, run a shell, launch more
agents, or inspect the live browser. Codex checks its findings and assigns justified
fixes. The initial review does not include another reviewer's conclusions.

Reports are saved beneath `.clanker/reviews/<run-id>/<phase>-<attempt>/` and linked from
the daily orchestration log. Each includes coverage, findings, settings, limitations,
and execution status. Source changes invalidate an earlier verdict. A failed or partial
review remains visible; an explicit waiver is recorded as a waiver, never a pass.
Default execution bounds are 600 seconds and 20 turns, with one automatic recheck per
phase after fixes or additional context.

For direct launcher use, read its help from the loaded package:

```powershell
python subagents/scripts/claude_cross_review.py --help
```

Use a verified Python executable (the command may be `python3` on your machine).
The coordinator reference documents the manifest and review procedure. In an installed
skill, the helper is at `scripts/claude_cross_review.py` beside `SKILL.md`.
Review execution requires explicit `--effort <selected-effort>`; there is no fixed
default. Existing direct commands must add that argument. Freshness-only
`--check-current <report.json>` does not require it.

## Cross-Review Verification

Run the focused deterministic tests with a Python 3.10+ interpreter:

```powershell
python -m unittest discover -s tests -p "test_*cross_review*.py" -v
```

Installer tests redirect all agent roots to temporary directories. Live authenticated
Claude reviews are separate checks that consume subscription usage; deterministic test
success alone does not establish live authentication, model access, or platform coverage.

## Step 4

💰 PROFIT. 💰
