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
Global and optional project routing preferences can override these worker defaults.
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
    routing_policy.py
    routing_editor.py
    model_discovery.py
  routing/
    policy.json
    usage.md
    ...example preferences
  editor/  (when built)
    index.html
    compatibility.json
    assets/
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

## Routing Editor

The local React editor starts with your specialist agents and one Claude cross-review
card. Choose a model and Adaptive or Fixed reasoning for each agent. **Customize by
activity** keeps planning, implementation, code review and visual review exceptions
optional. Changing an agent default preserves those exceptions; resetting an agent
field restores inheritance without deleting them. Existing settings are not migrated
or flattened. If inherited activities use different values, the card shows **Varies
by activity** until you choose a shared default.

Advanced activity defaults retain the earlier category settings. Adaptive ceilings
and model-specific tier profiles are also available under collapsed controls. Activity
choices retain configured exceptions even outside the suggested specialties. Your
parent session model and effort stay unchanged. Adaptive requires a complete model
profile; its advanced editor uses models reported by the local CLI.

**Python 3.10+ is required for native orchestration routing as well as Claude
reviews.** The optional source-checkout commands also require Node compatible with
Vite (20.19+ on the 20.x line, or 22.12+). Install the editor dependencies and build
once from the repository root:

```text
npm --prefix routing-editor ci
npm run editor:build
```

Then choose a mode, using the same commands on Windows, macOS, and Linux:

```text
npm run editor
npm run editor:dev
```

`editor` runs the built UI through the existing Python server. `editor:dev` starts
Python and Vite together for hot reload at **http://127.0.0.1:42069**. Vite fails
with a port-in-use error if 42069 is occupied instead of choosing a different port.
Use the printed token-bearing URL to open the authenticated editor. Both require an initial compatible build;
repeat `editor:build` after changing compatibility metadata. Neither command installs
dependencies automatically. The dependencies remain in `routing-editor/package-lock.json`;
the root launcher adds no packages.

Pass an optional project or isolated preference directory after the literal `"--"`
separator (quoting it also preserves it through PowerShell npm wrappers):

```text
npm run editor:dev "--" --project "path/to/my project" --global-config-dir "path/to/test preferences"
```

Without `--project`, only global preferences are editable. Paths you supply are
relative to the invocation directory; launcher-owned paths resolve from the checkout.
The launcher discovers Python 3.10+ automatically. Set `CLANKER_PYTHON` to an executable
path if needed (an executable only, not a shell command); an invalid explicit override
fails rather than selecting another interpreter. `node scripts/editor.mjs --help`
lists the supported options.

Open the printed local URL; Ctrl+C stops the owned servers. Both modes bind only to
loopback and use a temporary session token. Development forwards only authenticated
API requests with the expected Host and Origin to the fixed Python backend. These
commands cannot launch agents or call models. Avoid sharing the bootstrap URL.

Node remains optional when running an already-built source editor or an installed
bundle directly with Python:

```text
python subagents/scripts/routing_editor.py --project "path/to/my project"
```

Use a verified Python executable (`python3` may be appropriate). The root launcher
is a source-checkout convenience; installed bundles retain their Python-only startup.
Focused launcher integration checks run with `node --test tests/test_editor_launcher.mjs`
after installing dependencies and building the UI; they use temporary preferences.

After a build, run Wrangler to package it with the skill. From an installed bundle,
run its `scripts/routing_editor.py` with the same project argument. Wrangler copies
available build assets without running npm or starting a service. Without a build,
it installs the routing helpers and reports the editor unavailable. Incompatible
build/helper versions require rebuilding and reinstalling.

Preferences are sparse JSON files outside the installed bundle:

- Global: `~/.clanker/orchestration-routing.json`.
- Project: `<project>/.clanker/orchestration-routing.json`.

For isolated testing, start the editor with `--global-config-dir <temporary-directory>`.
The browser cannot change that destination or select arbitrary filesystem paths.
Reinstalling preserves preferences. Save confirms persistence; conflicts and failed
writes preserve the draft. Reset removes overrides by saving a valid empty versioned
document. Two editor instances coordinate saves; an unrelated text editor can still
race after the final revision check. Stale `.lock` files carry owner details: verify
the owner exited before manually removing a stale lock.

Precedence is bundled defaults, global activity, global agent, global activity-specific
specialist, project activity, project agent, project activity-specific specialist,
then explicit worker-assignment requests. The UI
shows sources and preview decisions. A selected project intentionally outranks global
settings. Preview is configuration evaluation, not proof of runtime/account access.
Unsupported requests never silently fall back to a different model or effort.

Adaptive maps mechanical, routine, complex, and exceptional work using the selected
model profile, then applies its ceiling. An unset ceiling uses the model default;
an explicit inherited ceiling remains when only the model changes. The initial Luna
mapping is medium/high/xhigh/max with an xhigh default ceiling. Thus max requires
both exceptional scope and a ceiling allowing it. Mappings are editable starting
policies, not quality guarantees or billing limits. Claude defaults stay Opus 5 and
low/medium/high by scope, with supported explicit effort overrides available.

New model selections come only from metadata advertised by installed Codex and Claude
CLIs. Manual model-ID entry and bundled alternative choices are not offered. Catalog loading is separate from
preferences. Use **Refresh models** to retry discovery; results are cached in memory
for five minutes, and a failed refresh keeps the last successful choices marked stale.
Refreshing does not change your draft, selected models, or reasoning levels. If the
server lacks discovery support, current saved/inherited selections remain visible but
new choices require a CLI catalog. Models absent from that catalog are labeled and
disabled for new selection. Advanced profile creation also uses CLI model choices. Its tier and ceiling fields
use model-specific effort dropdowns; unknown metadata is explicitly marked unverified.

**Preview model and reasoning** shows the predicted route without launching an agent
or saving temporary session choices.

Discovery does not send prompts or run model inference. Codex may use its existing
login and maintain its own cache/logs or refresh credentials; the helper never reads
credentials or edits CLI settings. Claude uses isolated bare-mode metadata and does
not verify account entitlement. Catalogs are suggestions, not dispatch authorization.
Aliases remain exact tokens and may resolve differently later. A newly selected model
needs its own Adaptive profile or Fixed mode; discovery never invents a tier mapping. Astra has a
bundled Adaptive profile (low/medium/high/xhigh, default ceiling xhigh), so selecting
it does not require creating a profile. Claude CLI choices `default`, `opus[1m]`,
`claude-fable-5-1[1m]`, and `sonnet` use the existing review mapping
(low/medium/high/high, ceiling high). Alias labels are preserved as reported;
`opus[1m]` identifies an Opus alias with a 1M context designation, not a pinned version.
Haiku reports unknown effort metadata and has no inferred Adaptive mapping.

Optional `CLANKER_CODEX` and `CLANKER_CLAUDE` environment variables select absolute
local executable files before starting the editor, not commands or argument strings.
Windows supports native executables and resolves Codex's known npm vendor executable;
Claude `.cmd`/`.ps1` shims are unsupported. Missing CLIs or required isolation controls
produce an unavailable status without installing software or weakening restrictions.
Node is still unnecessary when serving an installed, built editor through Python.

A run snapshots preferences under `.clanker/routing-snapshots/`; saving affects new
runs. An explicit reload creates another snapshot for future assignments without
changing already-running workers. Invalid saved files or missing Python block routing
with an actionable message. Only an explicit user instruction can bypass a named
invalid preferences file for a run. New runs use policy version 2; frozen version-1
snapshots retain their original routing. Preference schema remains 1. Older helpers
reject the new `agents` key, so rollback requires a deliberately exported pre-agent
document and matching helpers/assets; no automatic preference backup is created.

See [routing usage](subagents/routing/usage.md) for CLI commands, request/schema examples,
capability checks, logging fields, recommended ignore patterns, and rollback. Target
projects can version the routing JSON while ignoring logs, snapshots, `.lock`, and
`.tmp` files. The editor and installers do not change their ignore files.

Run focused checks from the repository root and editor directory respectively:

```powershell
python -B -m unittest discover -s tests -p "test_routing*.py" -v
python -B -m unittest tests.test_model_discovery tests.test_cross_review_process -v
cd routing-editor
npm test
npm run build
```

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
Default execution bounds are 2700 seconds (45 minutes) and 20 turns, with one automatic recheck per
phase after fixes or additional context. Override the wall-clock limit for an individual
review with `--timeout-seconds`; the turn limit is separate. The longer default allows
20–30 minute reviews to complete without removing the finite execution bound.

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

The local routing editor supplies its session token in each served HTML page. Open
the plain local URL; refresh after a server restart to pick up the new session.
No environment file or token-bearing bookmark is required. API token, Host and
Origin checks remain enforced in development and built-server modes.

Use **Run Wrangler** in the source-checkout editor to install this checkout’s rules
and skills into the local clients. It shows output and completion status, preserves
routing preferences, and does not save unsaved editor changes. Installed editor
bundles without the source checkout cannot run the installer.
