## Why

ClankerWrangler distributes individual coding workflows but has no shared way to coordinate a full-stack team of Codex subagents. The user wants explicit model and reasoning selection, OpenSpec continuity, and a readable record of orchestration decisions while learning what works.

## What Changes

- Keep the `clanker-orchestration-nation` coordinator and twelve dedicated specialist instruction files under root-level `subagents/`; reuse `clanker-code-review` for the review role.
- Define substantive specialist workflows, inputs, boundaries, deliverables, and verification for product, architecture, UX/UI design and visual review, backend, data, UI implementation, QA, review, documentation, DevOps, and performance work. Require workers to read the resolved specialist file before domain work.
- Preserve the user-selected session model and effort for orchestration; default planning/review workers to GPT-5.6 Sol and implementation workers to GPT-5.6 Terra, with task-specific worker reasoning and disclosed limitations. Astra or Fable are optional parent suggestions where available.
- Coordinate meaningful changes through OpenSpec and require evidence before marking tasks complete.
- Add a concise, client-neutral delegation policy to global_rules.md and clarify that existing explicit authorization remains valid within its scope.
- Validate UI changes with a dedicated UI/UX reviewer that inspects rendered screens and interactions, reports evidence and coverage limits, and leaves fixes to implementers.
- Append session decisions and outcomes to `.clanker/YYYY-MM-DD-orchestration-nation.md` without overwriting previous runs.
- Install one discoverable orchestration skill with twelve bundled specialist references in both clients; preserve earlier standalone specialist installations in backups outside skill discovery.
- Document invocation and validate fresh installs, migration, and repeated runs using isolated installer destinations.

## Capabilities

### New Capabilities

- `development-orchestration`: Scope-aware delegation, specialist assignments, OpenSpec handoffs, and integration verification.
- `orchestration-run-log`: Session-attributed decision and outcome records in the existing Clanker output directory.

### Modified Capabilities

None.

## Impact

Adds one coordinator and twelve specialist source files in `subagents/`, a README usage section, and OpenSpec change artifacts. Both installers keep regular `skills/*.md` discovery and add one orchestration package with reference files. Upgrade migration preserves old standalone specialist folders under the selected agent root's `backups/orchestration-nation/` directory. The shared global_rules.md source gains delegation, selected OpenSpec context, and authorization guidance for the installed CLAUDE.md/AGENTS.md copies. Global model configuration remains unchanged. The workflow uses native Codex subagent tools; it adds no package, API service, permanent agent process, or automatic deployment.
